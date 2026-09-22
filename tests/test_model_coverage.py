"""Observe shape, model identity and missing-field semantics without optional engines."""
from copy import deepcopy
import unittest

from opscope.offline.catalog_data import catalog_payload
from opscope.offline.matrix_data import evaluation_comparison_issues
from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.evaluation_results import evaluation_payload
from opscope.evaluation.tilesim_adapters import logical_work, model_inputs, normalize_legacy
from opscope.evaluation.tilesim_contract import hardware_mapping, unsupported
from tests.test_tilesim import tile_result


def fa_request():
    op = next(o for o in catalog_payload()['operators'] if o['id'] == 'train:flash_attention')
    return normalize_request({'configuration': {'operator_id': op['id'], 'inputs': op['inputs']},
                              'hardware_ids': ['ascend', 'tilesim:910B4'], 'method_ids': ['tilesim']})


class CoverageTest(unittest.TestCase):
    def test_shapes_and_logical_work(self):
        # BNSD must retain batch and heads, not bind either to sequence length.
        config = fa_request()['configuration']
        args = model_inputs(config, '/tmp/chip.yaml', {'cube_core_num': 20, 'vec_core_num': 40})
        self.assertEqual(args['input_dict'], {'B': 2, 'N': 32, 'S1': 512, 'S2': 512,
                                             'D1': 128, 'D2': 128, 'DTYPE': 'BF16'})
        work = logical_work(config)
        self.assertEqual(work['flops'], 8657043456)
        self.assertEqual(work['read_bytes'], 25165824)
        self.assertEqual(work['outputs'][0]['shape'], [2, 32, 512, 128])
        config = deepcopy(config)
        for t in config['inputs']: t['shape'][1] = 8
        self.assertEqual(logical_work(config)['flops'], work['flops'] / 4)

    def test_mapping_and_precision_are_explicit(self):
        # Shared mappings must remain visible; BF16 is never silently cast to FP16.
        self.assertEqual(hardware_mapping('ascend')['borrowed_from'], '910B4')
        self.assertEqual(hardware_mapping('b300')['borrowed_from'], 'H200')
        self.assertEqual(hardware_mapping('modeling:B200_POD')['model'], 'GB200')
        self.assertIsNone(hardware_mapping('tilesim:910B1')['borrowed_from'])
        config = fa_request()['configuration']
        self.assertIsNone(unsupported(config, 'tilesim:910B4'))
        self.assertIn('缺少 BF16', unsupported(config, 'h100'))
        for t in config['inputs']: t['dtype'] = 'fp16'
        self.assertIn('UB / L0', unsupported(config, 'r200'))
        self.assertIsNone(unsupported(config, 'h200'))

    def test_legacy_units_and_placeholders(self):
        # Legacy L1 counts elements; CUBE is a rate, not cycles. Genuine zero survives.
        result = normalize_legacy({'component_latency': {'CUBE': 0}, 'mem_volume': {'L1_cache': 10, 'UB_cache': 20},
                                   'compute_workload': {'CUBE': 900, 'VEC': 0}, 'l2_hit_rate': 0})
        self.assertIsNone(result['aic_cycles'])
        self.assertEqual(result['aiv_cycles'], 0)
        self.assertEqual(result['data_transfer'], {'L1_cache': 20, 'UB_cache': 20})
        self.assertEqual(result['aic_cube_time'], 0)
        self.assertIsNone(result['aic_mte1_time'])

    def test_no_trace_and_borrowed_config_reach_ui(self):
        # A real result without trace must render; borrowed models cannot imply SKU speedup.
        request = fa_request(); value = tile_result()
        value.update(events=[], formula='FA formula', tiling_input={})
        value['engine']['mode'] = 'dsl-theo'
        value['model_result'].update(aic_cycles=None, aiv_cycles=None, l2_access_rate=None)
        value['hardware_spec']['borrowed_from'] = '910B4'
        raw = {'rows': [{'hardware': h, 'method': 'tilesim', 'status': 'succeeded', 'result': value}
                        for h in request['hardware_ids']]}
        rows = [r for r in evaluation_payload(request, raw, 'coverage')['results'] if r['available']]
        self.assertIsNone(rows[0]['execution']['trace_view'])
        self.assertIn('不输出事件流水', rows[0]['details']['pipeline'])
        self.assertIn('借用 910B4', rows[0]['matrix']['note'])
        self.assertIn('理论预测', rows[0]['matrix']['note'])
        self.assertIn('FA formula', rows[0]['details']['compute'])
        self.assertIn('包含借用配置，不能代表真实型号差异', evaluation_comparison_issues(*rows))
