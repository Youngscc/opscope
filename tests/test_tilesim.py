"""Check TileSim isolation, numeric scopes and real-data display contracts."""
from copy import deepcopy
import subprocess
import unittest
from unittest.mock import patch

from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.evaluation_results import evaluation_payload
from opscope.evaluation.evaluation_runtime import EvaluationRuntime
from opscope.evaluation.tilesim_contract import OPERATOR_KINDS, unsupported
from opscope.evaluation.tilesim_adapters import api_request, logical_work, output_tensors
from opscope.evaluation.tilesim_details import trace_geometry, union_time
from opscope.evaluation.tilesim_worker import compact_events
from opscope.offline.catalog_data import catalog_payload
from tests.test_evaluation import request_body, raw_result


def tile_result():
    value = raw_result(10)
    events = [{'name': 'copy_GM_to_L1', 'ts': 0, 'dur': 4, 'pid': 'AIC_0', 'tid': 'AIC_MTE2', 'ph': 'X'},
              {'name': 'mmad', 'ts': 2, 'dur': 8, 'pid': 'AIC_0', 'tid': 'CUBE', 'ph': 'X'}]
    model = {k: 0 for k in ('aic_cube_time', 'aic_mte1_time', 'aic_mte2_time', 'aic_fixpipe_time',
                           'aiv_vec_time', 'aiv_mte2_time', 'aiv_mte3_time', 'aic_cycles', 'aiv_cycles')}
    model.update(aic_cube_time=8, aic_mte2_time=4, aic_cycles=14800,
                 l2_access_rate=.25, data_transfer={'GM_2_L1': 1048576})
    value.update(backend='tilesim', compute_us=None, memory_us=None, bound=None,
                 events=events, model_result=model, tiling_input={'tm':128,'tn':256,'tk1':512,'tk0':128},
                 engine={'name':'tilesim','revision':'1.0.9'}, hardware_hash='910B1')
    value['hardware_spec'] = {'name':'Ascend 910B1','model_spec':{'clock_freq':1850,
       'core_config':{'cube_core_num':24,'vec_core_num':48},'local_mem':{'L1':512,'L0C':128},'share_mem':{'L2':196608}}}
    return value


class TileSimTest(unittest.TestCase):
    def test_allowlist_and_limits(self):
        # Explicit mapped models are allowed; bounds still prevent runaway traces.
        body = request_body(); body['hardware_ids'] = ['tilesim:910B1']
        config = normalize_request(body)['configuration']
        self.assertIsNone(unsupported(config, 'tilesim:910B1'))
        self.assertIsNone(unsupported(config, 'ascend'))
        config['inputs'][0]['shape'][0] = 129
        self.assertIn('尾块', unsupported(config, 'tilesim:910B1'))
        config['inputs'][0]['shape'][0] = 1048576
        self.assertIn('上限', unsupported(config, 'tilesim:910B1'))
        config['operator_id'] = 'train:flash_attention'
        self.assertIn('BNSD', unsupported(config, 'tilesim:910B1'))

    def test_trace_union_not_sum_and_full_axis(self):
        # Overlapping channels occupy 10us, not 12us; all lanes share the same run-wide axis.
        events = tile_result()['events']
        self.assertEqual(union_time(events), 10)
        view = trace_geometry(events, 10)
        self.assertEqual(view['cores'][0]['active_percent'], 100)
        self.assertEqual(view['cores'][0]['count'], 2)
        self.assertEqual(view['ticks'], ['0.000','2.500','5.000','7.500','10.000'])
        self.assertIn('M 160.0000 0 h 640.0000', view['cores'][0]['lanes'][1]['path'])

    def test_expanded_operator_contracts(self):
        # Every declared adapter has a complete default catalog contract, except the intentionally unresolved FA alias.
        catalog = catalog_payload()
        for operator_id in OPERATOR_KINDS:
            op = next(item for item in catalog['operators'] if item['id'] == operator_id)
            config = {'operator_id': operator_id, 'key': op['key'],
                      'attributes': {field['name']: field['default'] for field in op.get('parameters', [])},
                      'inputs': [{key: tensor[key] for key in ('name', 'role', 'shape', 'dtype')}
                                 for tensor in op['inputs']]}
            if any(None in tensor['shape'] for tensor in config['inputs']):
                self.assertEqual(operator_id, 'infer:FlashAttentionScore')
                self.assertIn('BNSD', unsupported(config, 'tilesim:910B1'))
                continue
            if operator_id in {'infer:Cumsum', 'infer:GatherV2'}:
                self.assertIn('axis', unsupported(config, 'tilesim:910B1'))
                continue
            self.assertIsNone(unsupported(config, 'tilesim:910B1'), operator_id)
            work = logical_work(config)
            self.assertGreaterEqual(work['flops'], 0)
            self.assertGreater(work['read_bytes'], 0)
            self.assertEqual(work['outputs'], output_tensors(config))

    def test_layernorm_and_theoretical_requests_preserve_semantics(self):
        # LayerNorm fills the missing beta explicitly; Cast remains a TileSim theoretical model.
        catalog = catalog_payload()
        def config(operator_id):
            op = next(item for item in catalog['operators'] if item['id'] == operator_id)
            return {'operator_id': operator_id, 'key': op['key'],
                    'inputs': [{key: tensor[key] for key in ('name', 'role', 'shape', 'dtype')}
                               for tensor in op['inputs']]}
        layer = api_request(config('train:layernorm'), '/tmp/910B1.yaml')
        self.assertEqual(layer['op_name'], 'LayerNormV3')
        self.assertEqual(layer['input_shapes'], [[1024, 4096], [4096], [4096]])
        self.assertEqual(layer['output_shapes'], [[1024, 4096], [1024, 1], [1024, 1]])
        cast = api_request(config('infer:Cast'), '/tmp/910B1.yaml', theoretical=True)
        self.assertEqual(cast['op_name'], 'Cast')
        self.assertEqual(cast['backend_type'], 'theo')
        self.assertEqual(cast['output_precision'], ['FP32'])

    def test_cost_theoretical_result_is_labeled_theoretical(self):
        # A cost-model theoretical result must not be presented as an engineering prediction.
        body = request_body(); body['hardware_ids'] = ['tilesim:910B1']; body['method_ids'] = ['tilesim']
        request = normalize_request(body); result = tile_result()
        result['engine']['mode'] = 'cost-theo'
        raw = {'rows': [{'hardware': 'tilesim:910B1', 'method': 'tilesim',
                         'status': 'succeeded', 'result': result}]}
        row = next(r for r in evaluation_payload(request, raw, 'theo')['results'] if r['available'])
        self.assertEqual(row['source_label'], '理论预测')
        self.assertIn('成本模型理论模式', row['details']['overview'])

    def test_invalid_trace_is_not_shown(self):
        # Trace outside latency and zero/NaN durations are not accepted as usable simulation evidence.
        events = tile_result()['events']
        self.assertEqual(compact_events({'traceEvents':events}, 10), events)
        for value in (0, -1, float('nan'), 20):
            bad = deepcopy(events); bad[0]['dur'] = value
            with self.assertRaises(ValueError): compact_events({'traceEvents':bad}, 10)

    def test_payload_has_no_fake_wait_or_reference(self):
        # Same-run model/cache/trace reach details and export; no legacy synthetic metrics leak in.
        body = request_body(); body['hardware_ids'] = ['tilesim:910B1']; body['method_ids'] = ['tilesim']
        request = normalize_request(body)
        raw = {'rows':[{'hardware':'tilesim:910B1','method':'tilesim','status':'succeeded','result':tile_result()}]}
        data = evaluation_payload(request, raw, 'tile')
        row = next(r for r in data['results'] if r['available'])
        self.assertEqual(row['task']['actual_backend'], 'tilesim')
        self.assertEqual(row['execution']['kind'], 'tile_simulation')
        self.assertEqual(len(row['execution']['events']), 2)
        self.assertNotIn('events', row['raw_result'])
        self.assertIsNone(row['deviation_percent'])
        self.assertIsNone(row['execution']['compute_us'])
        self.assertNotIn('wait_us', row['execution'])
        self.assertIn('25%', row['details']['memory'])
        self.assertIn('1 MiB', row['details']['memory'])
        self.assertIn('TileSim', row['details']['overview'])
        self.assertNotIn('HBM 实际流量', row['details']['memory'])
        self.assertFalse(row['synthetic'])

    @patch.object(EvaluationRuntime, 'invoke', return_value={'roofline':True, 'tilesim':True})
    def test_optional_interpreter_preserves_roofline(self, _):
        # A failing TileSim subprocess must leave successful Roofline results intact.
        runtime = EvaluationRuntime('/tmp/engine','/tmp/roofline/python', tilesim_python='/tmp/tile/.venv/bin/python')
        self.addCleanup(runtime.close)
        self.assertIn('/.venv/bin/python', runtime.tilesim_python)
        request = normalize_request(request_body())
        good = {'hardware':'h200','method':'roofline','status':'succeeded','result':raw_result()}
        with patch.object(runtime, 'invoke_roofline', return_value={'rows':[good]}), patch.object(runtime, 'invoke_tilesim', side_effect=subprocess.TimeoutExpired('tilesim',60)):
            # Call the original dispatcher despite the constructor probe mock.
            result = ORIGINAL_INVOKE(runtime, request)
        self.assertEqual(result['rows'][0], good)
        self.assertEqual(result['rows'][1]['status'], 'failed')
        self.assertIn('超时', result['rows'][1]['reason'])


ORIGINAL_INVOKE = EvaluationRuntime.invoke
