"""Contract and failure tests run without the optional external engine."""
import shutil
import subprocess
import unittest
from unittest.mock import patch

from build import build_payload, render_page
from engine_worker import unavailable_reason
from evaluation_contract import digest, hardware_key, normalize_request
from evaluation_results import evaluation_payload
from evaluation_runtime import EvaluationRuntime


def request_body():
    return {'configuration': build_payload()['catalog']['default_config'],
            'hardware_ids': ['h100', 'h200'], 'method_ids': ['roofline', 'tilesim']}


def raw_result(latency=200):
    return {'latency_us': latency, 'compute_us': latency, 'memory_us': 25,
            'flops': 137438953472, 'read_bytes': 67108864, 'write_bytes': 33554432,
            'arithmetic_intensity': 1365.3333333333, 'bound': 'compute', 'backend': 'roofline',
            'calibration_source': '', 'wall_time_ms': 2,
            'outputs': [{'name': 'output', 'shape': [4096, 4096], 'dtype': 'fp16', 'bytes': 33554432}],
            'hardware_spec': {'name': 'H200_Server', 'chip_name': 'H200', 'soc_version': '',
                              'memory': {'capacity_gb': 141, 'hbm_bandwidth_gbps': 4800}},
            'hardware_hash': 'hw', 'engine': {'revision': 'test', 'calibration_hash': None}}


class EvaluationTest(unittest.TestCase):
    def test_canonical_input_ignores_client_identity(self):
        # Names, backend identities and formulas come from trusted catalog, never POST text.
        body = request_body()
        body['configuration'].update(operator='<script>bad</script>', key='exec', domain='other')
        body['configuration']['inputs'][0]['name'] = '<script>'
        r = normalize_request(body)
        self.assertEqual(r['configuration']['operator'], 'MatMul')
        self.assertEqual(r['configuration']['key'], 'matmul')
        self.assertEqual(r['configuration']['inputs'][0]['name'], 'A')
        self.assertEqual(r['configuration_hash'], digest(r['configuration']))

    def test_shape_dtype_and_options_are_checked(self):
        # Reject invalid dimensions, mixed dtype, and execution options the engine ignores.
        for value in ([], [True, 4096], [0, 4096], [4096, 2048], [2**30, 4096]):
            body = request_body()
            body['configuration']['inputs'][0]['shape'] = value
            with self.assertRaises(ValueError): normalize_request(body)
        for key, value in [('layout', 'column-major'), ('transpose_a', True), ('accumulator_dtype', 'fp16')]:
            body = request_body()
            body['configuration']['options'][key] = value
            with self.assertRaises(ValueError): normalize_request(body)
        body = request_body()
        body['configuration']['inputs'][0]['dtype'] = 'fp8'
        with self.assertRaises(ValueError): normalize_request(body)

    def test_unknown_methods_and_hardware(self):
        # A path or engine name cannot pass the fixed ID allowlist.
        for key in ('hardware_ids', 'method_ids'):
            body = request_body(); body[key] = ['../../private']
            with self.assertRaises(ValueError): normalize_request(body)
        self.assertEqual(hardware_key('h200'), 'H200_Server')
        self.assertIsNone(hardware_key('r200'))

    def test_unsupported_template_is_explicit(self):
        # Catalog presence is not formula certification.
        body = request_body()
        catalog = build_payload()['catalog']
        op = next(x for x in catalog['operators'] if x['id'] == 'infer:MatMul')
        body['configuration'] = {'operator_id': op['id'], 'inputs': [{**t, 'shape': [d or 1 for d in t['shape']]} for t in op['inputs']]}
        request = normalize_request(body)
        self.assertFalse(request['supported'])
        self.assertIn('暂未适配', unavailable_reason(request, 'roofline', 'H200_Server', {}))

    def test_tilesim_never_falls_back(self):
        # Missing simulator and absent measurements stay absent, not roofline/zero.
        request = normalize_request(request_body())
        reason = unavailable_reason(request, 'tilesim', 'H200_Server', {'tilesim_reason': '未安装 TileSim 组件'})
        self.assertEqual(reason, '未安装 TileSim 组件')
        self.assertEqual(unavailable_reason(request, 'profile', 'H200_Server', {}), '尚未接入实测参考')

    def test_result_numbers_missing_and_safe_details(self):
        # Backend numbers drive all views; no virtual rows or profiler reference leak in.
        request = normalize_request(request_body())
        raw = {'rows': [{'hardware': 'h200', 'method': 'roofline', 'status': 'succeeded', 'result': raw_result()},
                        {'hardware': 'h200', 'method': 'tilesim', 'status': 'unsupported', 'reason': '未安装', 'result': None}]}
        payload = evaluation_payload(request, raw, 'job')
        rows = {r['id']: r for r in payload['results']}
        row = rows['job-h200-roofline']
        self.assertEqual(row['latency_us'], 200)
        self.assertEqual(row['summary']['throughput'], '687.195')
        self.assertEqual(row['execution']['events'], [])
        self.assertIsNone(row['deviation_percent'])
        self.assertFalse(payload['synthetic'])
        self.assertEqual(sum(r['available'] for r in rows.values()), 1)
        self.assertIsNone(rows['job-h200-tilesim']['latency_us'])
        self.assertEqual(rows['job-h200-tilesim']['task']['status'], 'unsupported')
        self.assertEqual(row['matrix']['latency_width'], 80)
        self.assertIn('200 μs', row['details']['overview'])
        self.assertNotIn('合成', row['details']['evidence'])
        self.assertTrue(all(not r['synthetic'] for r in rows.values()))

    def test_prediction_pairs_and_snapshot(self):
        # Same configuration can compare predictions; demo baseline is retained only for explicit restore.
        request = normalize_request(request_body())
        raw = {'rows': [{'hardware': h, 'method': 'roofline', 'status': 'succeeded', 'result': raw_result(t)}
                        for h, t in [('h100', 200), ('h200', 100)]]}
        payload = evaluation_payload(request, raw, 'job')
        pair = payload['matrix']['pairs']['job-h100-roofline|job-h200-roofline']
        self.assertEqual(pair['delta_percent'], -50)
        self.assertIn('模型预测', pair['text'])
        page = render_page(payload)
        self.assertIn('"initial_configuration"', page)
        self.assertNotIn('/* INLINE_', page)
        self.assertEqual(sum(r['available'] for r in payload['demo_results']), 25)

    def test_zero_latency_remains_a_value(self):
        # Zero is valid data, but division-derived throughput and relative change stay missing.
        request = normalize_request(request_body())
        raw = {'rows': [{'hardware': h, 'method': 'roofline', 'status': 'succeeded', 'result': raw_result(t)}
                        for h, t in [('h100', 0), ('h200', 100)]]}
        payload = evaluation_payload(request, raw, 'zero')
        row = next(r for r in payload['results'] if r['id'] == 'zero-h100-roofline')
        self.assertTrue(row['available'])
        self.assertEqual(row['latency_us'], 0)
        self.assertEqual(row['summary']['throughput'], '—')
        self.assertIsNone(payload['matrix']['pairs']['zero-h100-roofline|zero-h200-roofline']['delta_percent'])
        throughput = next(f for f in row['sections']['overview'][0]['facts'] if f['label'] == '有效算力')
        self.assertFalse(throughput['known'])

    def test_escape_untrusted_detail_text(self):
        # Even local engine metadata is escaped before entering HTML.
        request = normalize_request(request_body()); r = raw_result()
        r['hardware_spec']['name'] = '<img src=x onerror=alert(1)>'
        payload = evaluation_payload(request, {'rows': [{'hardware':'h200','method':'roofline','status':'succeeded','result':r}]}, 'job')
        row = next(x for x in payload['results'] if x['available'])
        self.assertNotIn('<img', row['details']['hardware'])
        self.assertIn('&lt;img', row['details']['hardware'])
        self.assertNotIn('<img', render_page(payload))

    @patch.object(EvaluationRuntime, 'invoke', return_value={'roofline': True})
    def test_timeout_failure_and_venv_path(self, invoke):
        # Do not resolve the venv executable symlink into a base interpreter.
        runtime = EvaluationRuntime('/tmp/engine', '../modeling/.venv/bin/python')
        self.addCleanup(runtime.close)
        self.assertIn('/.venv/bin/python', runtime.python)
        request = normalize_request(request_body())
        runtime.jobs['job'] = {'id': 'job', 'status': 'queued', 'request': request}
        invoke.side_effect = subprocess.TimeoutExpired('worker', 60)
        runtime.run('job', request)
        result = runtime.get('job')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('超时', result['reason'])
        self.assertNotIn('request', result)

    def test_javascript_stale_response(self):
        # A completed old job must not replace a newly applied configuration.
        if not shutil.which('node'): self.skipTest('Node unavailable')
        result = subprocess.run(['node', '--test', 'test_evaluation_ui.cjs'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
