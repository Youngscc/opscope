"""Check task context, units and provenance independently of a running backend."""
import unittest

from build import build_payload
from task_details import facts


class TaskDetailTest(unittest.TestCase):
    def setUp(self):
        self.results = {row['id']: row for row in build_payload()['results']}

    def test_tensor_footprint(self):
        # Two FP16 inputs and one FP16 output have distinct read/write totals.
        row = self.results['demo-ascend-roofline']
        workload = row['workload']
        self.assertEqual([t['bytes'] for t in workload['tensors']], [33554432] * 3)
        self.assertEqual([t['role'] for t in workload['tensors']], ['input', 'input', 'output'])
        self.assertEqual(workload['input_bytes'], 67108864)
        self.assertEqual(workload['output_bytes'], 33554432)
        self.assertEqual(workload['logical_bytes'], 100663296)
        self.assertEqual(workload['flops'], 137438953472)
        self.assertAlmostEqual(workload['arithmetic_intensity'], 1365.3333333333333)
        self.assertFalse(workload['transpose_a'])
        self.assertEqual(workload['accumulator_dtype'], 'FP32')
        self.assertIn('输出（形状推导）', row['details']['inputs'])
        self.assertIn('96 MiB', row['details']['inputs'])

    def test_requested_method_is_not_execution(self):
        # Choosing TileSim never fabricates a backend run or a successful job.
        row = self.results['demo-h100-tilesim']
        self.assertEqual(row['task']['requested_method'], 'tilesim')
        self.assertEqual(row['task']['status'], 'demo')
        for key in ['task_id', 'run_id', 'actual_backend', 'started_at', 'wall_time_ms', 'report_uri']:
            self.assertIsNone(row['task'][key])
        self.assertIn('扩展字段示例', row['details']['overview'])
        self.assertEqual(row['task']['workload_id'], self.results['demo-h100-roofline']['task']['workload_id'])
        self.assertNotEqual(row['id'], self.results['demo-h100-roofline']['id'])

    def test_missing_hardware_and_unavailable_results(self):
        # Unknown specs are null, including for available synthetic results.
        snapshot = self.results['demo-h100-profile']['hardware_snapshot']
        self.assertEqual(snapshot['name'], 'NVIDIA H100')
        self.assertEqual(snapshot['status'], 'not_captured')
        for key in ['memory_gib', 'hbm_bandwidth_gbs', 'l2_mib', 'fp16_peak_tflops', 'compute_units']:
            self.assertIsNone(snapshot[key])
        missing = self.results['demo-r200-roofline']
        self.assertEqual(missing['task']['status'], 'unavailable')
        self.assertNotIn('details', missing)
        self.assertNotIn('latency_us', missing)

    def test_overview_matches_result_and_regression_absence(self):
        # H200 regression has a total but no invented compute/memory/bound values.
        row = self.results['demo-h200-roofline']
        self.assertIn('145.00 μs', row['details']['overview'])
        self.assertIn('<dt>主要瓶颈</dt><dd>—</dd>', row['details']['overview'])
        self.assertIsNone(row['execution']['compute_us'])
        self.assertEqual(set(row['details']), {'overview', 'inputs', 'hardware', 'latency', 'compute', 'memory', 'pipeline', 'evidence'})
        self.assertIn('<dd>0</dd>', facts([('zero', 0)]))
        self.assertIn('<dd>—</dd>', facts([('missing', None)]))
        self.assertIn('&lt;unsafe&gt;', facts([('label', '<unsafe>')]))
