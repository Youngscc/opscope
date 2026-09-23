"""New catalog formulas and TileSim adapters must preserve actual tensor semantics."""
import unittest

from opscope.offline.catalog_data import catalog_payload
from opscope.evaluation.bundled_roofline import hardware_catalog, peak
from opscope.evaluation.catalog_roofline import simulate, unsupported
from opscope.evaluation.engine_worker import engine_identity, roofline
from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.evaluation_results import evaluation_payload
from opscope.evaluation.tilesim_adapters import api_request, logical_work, model_shapes
from opscope.evaluation.tilesim_contract import unsupported as tile_unsupported


OPS = {op['id']: op for op in catalog_payload()['operators']}


def configuration(identifier, attributes=None):
    op = OPS[identifier]
    body = {'configuration': {'operator_id': identifier, 'inputs': op['inputs'],
                              'attributes': attributes if attributes is not None else
                                            {p['name']: p['default'] for p in op.get('parameters', [])}},
            'hardware_ids': ['h200'], 'method_ids': ['roofline']}
    return normalize_request(body)['configuration']


class CatalogAdaptationTest(unittest.TestCase):
    def test_batched_linear_formula_tracks_shape(self):
        # The 3D batch axis remains in the public output; FLOPs scale with sequence length.
        config = configuration('infer:MatMul')
        result = simulate(config, 'H200_Server')
        self.assertEqual(result['flops'], 2 * 1 * 2048 * 4096 * 11008)
        self.assertEqual(result['outputs'][0]['shape'], [1, 2048, 11008])
        config['inputs'][0]['shape'][1] = 1024
        shorter = simulate(config, 'H200_Server')
        self.assertEqual(shorter['flops'], result['flops'] // 2)
        self.assertEqual(shorter['outputs'][0]['shape'], [1, 1024, 11008])
        self.assertEqual(shorter['backend'], 'roofline')

    def test_missing_formula_and_hardware_peak_stay_missing(self):
        # No formula and no precision peak produce a reason, never a zero-time success.
        self.assertIn('没有 FLOPs', unsupported(configuration('infer:GatherV2', {'axis': 0}), 'H200_Server'))
        self.assertIn('峰值', unsupported(configuration('infer:QuantBatchMatmulV3'), 'Adevice03_POD'))
        with self.assertRaisesRegex(ValueError, '目录公式'):
            simulate(configuration('infer:MoeGatingTopK'), 'H200_Server')

    def test_fp8_peak_uses_existing_tops_field(self):
        # FP8 is stored as TOPS in the hardware snapshot; a zero field remains unsupported.
        hardware = hardware_catalog()['hardware']
        self.assertEqual(peak(hardware['H200_Server'], 'cube', 'fp8'), 1979e12)
        self.assertEqual(peak(hardware['B200_Server'], 'cube', 'fp4'), 9000e12)
        self.assertEqual(peak(hardware['Adevice03_POD'], 'cube', 'fp8'), 0)
        config = configuration('infer:QuantBatchMatmulV3')
        self.assertIsNone(unsupported(config, 'H200_Server'))
        result = simulate(config, 'H200_Server')
        self.assertGreater(result['latency_us'], 0)
        self.assertEqual(result['backend'], 'roofline')

    def test_model_attributes_validate_scope(self):
        # Explicit values are required where tensor shape cannot carry a runtime axis.
        with self.assertRaisesRegex(ValueError, '累加轴'):
            configuration('infer:Cumsum')
        with self.assertRaisesRegex(ValueError, '工作量公式'):
            configuration('infer:Cumsum', {'axis': 1})
        with self.assertRaisesRegex(ValueError, '输出仅对应'):
            configuration('infer:TorchSum', {'axis': 2})
        with self.assertRaisesRegex(ValueError, '置换顺序'):
            configuration('infer:Transpose', {'permutation': [0, 0, 1]})

    def test_tilesim_linear_and_reduction_requests(self):
        # Engine shapes flatten batch only for simulation; logical outputs keep B,S,N.
        linear = configuration('infer:Linear')
        inputs, outputs = model_shapes(linear)
        self.assertEqual(inputs, [[2048, 4096], [4096, 4096]])
        self.assertEqual(outputs, [[2048, 4096]])
        self.assertEqual(logical_work(linear)['outputs'][0]['shape'], [1, 2048, 4096])
        reduction = configuration('infer:TorchSum')
        args = api_request(reduction, '/tmp/910B1.yaml', theoretical=True)
        self.assertEqual(args['op_name'], 'ReduceSum')
        self.assertEqual(args['extra_param']['reduce_axis'], [1])
        self.assertEqual(logical_work(reduction)['outputs'][0]['shape'], [1, 4096])

    def test_tilesim_known_bandwidth_holes_block_before_execution(self):
        # The audit found these exact missing GB200/R200 paths with explicit FP16.
        config = configuration('infer:Sigmoid')
        self.assertIsNone(tile_unsupported(config, 'tilesim:910B1'))
        config['inputs'][0]['dtype'] = 'fp16'
        self.assertIn('带宽表', tile_unsupported(config, 'b200'))
        self.assertIn('带宽表', tile_unsupported(config, 'r200'))
        reduction = configuration('infer:TorchSum')
        reduction['inputs'][0]['dtype'] = 'fp16'
        self.assertIn('带宽表', tile_unsupported(reduction, 'b200'))

    def test_new_tilesim_adapters_reject_changed_tensor_contracts(self):
        # UI permits shape edits; adapter bounds must reject ranks it cannot map.
        reduction = configuration('infer:TorchSum')
        reduction['inputs'][0]['shape'] = [2048, 4096]
        self.assertIn('三维输入', tile_unsupported(reduction, 'tilesim:910B1'))
        transpose = configuration('infer:Transpose')
        transpose['inputs'][1]['shape'] = [4]
        self.assertIn('perm 张量', tile_unsupported(transpose, 'tilesim:910B1'))
        gather = configuration('infer:GatherV2', {'axis': 0})
        gather['inputs'][-1]['shape'] = [2]
        self.assertIn('axis 张量', tile_unsupported(gather, 'tilesim:910B1'))

    def test_catalog_mode_is_visible_in_result_details(self):
        # Formula-only estimates must not look like the bundled baseline or a calibrated run.
        op = OPS['infer:MatMul']
        request = normalize_request({'configuration': {'operator_id': op['id'], 'inputs': op['inputs']},
                                     'hardware_ids': ['h200'], 'method_ids': ['roofline']})
        result = roofline(request['configuration'], 'H200_Server', engine_identity())
        payload = evaluation_payload(request, {'rows': [{'hardware': 'h200', 'method': 'roofline',
                                                         'status': 'succeeded', 'result': result}]}, 'catalog')
        row = next(r for r in payload['results'] if r['id'] == 'catalog-h200-roofline')
        self.assertEqual(row['source_label'], '目录公式')
        self.assertIn('目录公式解析', row['details']['evidence'])
        self.assertIn('不包含原 Kepler', row['details']['evidence'])
        self.assertIn('此模式未进行校准', row['details']['evidence'])
        self.assertFalse(row['measurement'])


if __name__ == '__main__':
    unittest.main()
