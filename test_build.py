"""Check presentation math and provenance without invoking model backends."""
import math
import unittest

from build import FLOPS, LOGICAL_BYTES, build_payload, deviation


class PresentationDataTest(unittest.TestCase):
    def test_workload_units(self):
        # Logical bytes include one read of A/B and one write of FP16 C.
        self.assertEqual(FLOPS, 137438953472)
        self.assertEqual(LOGICAL_BYTES, 100663296)

    def test_deviation_and_missing_reference(self):
        # A missing reference is distinct from a zero-valued result.
        self.assertTrue(math.isclose(deviation(190, 248), -23.387096774193548))
        self.assertIsNone(deviation(12, None))
        self.assertIsNone(deviation(None, 12))
        self.assertIsNone(deviation(12, 0))
        self.assertEqual(deviation(0, 12), -100)

    def test_reference_and_chart_scale(self):
        # All cards use one 320 us scale, independent of visible filters.
        results = {row['id']: row for row in build_payload()['results']}
        self.assertEqual(results['demo-ascend-profile']['deviation'], '参考基线')
        self.assertEqual(results['demo-h100-roofline']['deviation'], '-3.1%')
        self.assertEqual(results['demo-ascend-profile']['bar_width'], 77.5)
        self.assertEqual(results['demo-h100-profile']['bar_width'], 50.625)
        self.assertIn('248.00 μs', results['demo-ascend-profile']['details']['latency'])
        for row in results.values():
            if row['available']:
                self.assertNotIn('p50', row['details']['latency'])
                self.assertNotIn('<svg', row['details']['latency'])

    def test_provenance_and_absent_details(self):
        # Unsupported combinations stay absent; simulator totals do not imply traces.
        payload = build_payload()
        self.assertTrue(payload['synthetic'])
        self.assertEqual(len(payload['results']), 24)
        for row in payload['results']:
            self.assertTrue(row['synthetic'])
            if not row['available']:
                self.assertNotIn('latency_us', row)
        results = {row['id']: row for row in payload['results']}
        self.assertFalse(results['demo-ascend-accel']['available'])
        self.assertTrue(results['demo-b200-profile']['available'])
        self.assertFalse(results['demo-b200-accel']['available'])
        self.assertIn('扩展字段示例', results['demo-h100-tilesim']['details']['pipeline'])
        self.assertIn('<svg', results['demo-h100-tilesim']['details']['pipeline'])
        self.assertIn('计算估算', results['demo-h100-roofline']['details']['latency'])

    def test_summary_matches_detail_and_preserves_missing(self):
        # Outer charts and drill-downs share fixtures; analytical models have no counters.
        results = {row['id']: row for row in build_payload()['results']}
        profile = results['demo-h100-profile']
        summary = profile['summary']
        self.assertEqual(summary['throughput'], '848.4')
        self.assertTrue(math.isclose(summary['throughput_width'], 35.35))
        self.assertEqual(summary['memory']['traffic'], 104)
        self.assertEqual(summary['memory']['hit'], 78)
        self.assertEqual(summary['memory']['bandwidth'], '0.67')
        self.assertEqual(summary['activity'][0]['label'], 'Tensor')
        self.assertEqual(summary['activity'][0]['value'], 82)
        self.assertIn('104 MiB', profile['details']['memory'])
        self.assertIn('78%', profile['details']['memory'])
        self.assertIn('82%', profile['details']['compute'])
        self.assertIn('848.4 TFLOP/s', profile['details']['compute'])
        self.assertIsNone(results['demo-h100-roofline']['summary']['memory'])
        self.assertEqual(results['demo-h100-tilesim']['summary']['activity'][0]['value'], 75)
        self.assertEqual(results['demo-ascend-profile']['summary']['activity'][0]['label'], 'Cube')
        self.assertEqual(results['demo-h100-accel']['summary']['memory']['traffic'], 120)

    def test_expanded_execution_records(self):
        # Fixtures cover 17 combinations; local events must remain inside one execution.
        results = build_payload()['results']
        available = [row for row in results if row['available']]
        self.assertEqual(len(available), 17)
        for row in available:
            record = row['execution']
            self.assertTrue(record['synthetic'])
            self.assertLessEqual(row['summary']['throughput_width'], 100)
            for field in ('compute', 'memory'):
                if record[field + '_us'] is None:
                    self.assertEqual(row[field], '—')
                else:
                    self.assertIn(f"{record[field + '_us']:.1f} μs", row[field])
            if record['kind'] == 'analytic':
                self.assertEqual(record['events'], [])
                self.assertNotIn('kernel', record)
                self.assertIn('不生成指令级流水', row['details']['pipeline'])
                continue
            self.assertEqual(len(record['events']), 12)
            self.assertEqual(len(record['instances']), 24)
            self.assertEqual(record['cycles'], round(row['latency_us'] * record['clock_mhz']))
            self.assertIn(record['kernel'], row['details']['evidence'])
            for event in record['events']:
                self.assertGreaterEqual(event['start_us'], 0)
                self.assertGreater(event['end_us'], event['start_us'])
                self.assertLessEqual(event['end_us'], row['latency_us'])

    def test_blackwell_and_unsupported_identity(self):
        # Mock data cannot establish Blackwell simulator support or identify an unknown SKU.
        results = {row['id']: row for row in build_payload()['results']}
        self.assertEqual(results['demo-b300-profile']['latency_us'], 84.0)
        self.assertEqual(results['demo-b200-tilesim']['source_label'], '扩展字段示例')
        self.assertIn('Blackwell', results['demo-b300-accel']['reason'])
        self.assertIn('正式 SKU', results['demo-r200-profile']['reason'])
        self.assertEqual(results['demo-b200-profile']['execution']['tile'], [128, 256, 128])

    def test_roofline_is_one_method_with_explicit_calibration(self):
        # One result per hardware; metadata follows the total and never fabricates regression parts.
        payload = build_payload()
        self.assertEqual([item['id'] for item in payload['methods']],
                         ['profile', 'roofline', 'tilesim', 'accel'])
        rows = [row for row in payload['results'] if row['method'] == 'roofline']
        self.assertEqual(len(rows), 6)
        results = {row['hardware']: row for row in rows}
        for hardware, source in [('ascend', 'bucket'), ('h100', 'aggregate'), ('h200', 'regression')]:
            row = results[hardware]
            self.assertEqual(row['source_label'], '已校准')
            self.assertEqual(row['execution']['calibration']['source'], source)
            self.assertIn(row['execution']['calibration']['version'], row['details']['evidence'])
        generic = results['b200']
        self.assertEqual(generic['source_label'], '通用估算')
        self.assertEqual(generic['latency_us'], 76.0)
        self.assertIn('未命中校准数据', generic['details']['evidence'])
        regression = results['h200']
        self.assertEqual(regression['latency_us'], 145.0)
        self.assertIsNone(regression['execution']['compute_us'])
        self.assertIsNone(regression['execution']['memory_us'])
        self.assertIsNone(regression['bound'])
        self.assertIn('回归仅提供总耗时', regression['details']['latency'])
        self.assertNotIn('模型有效计算上界', regression['details']['compute'])
        self.assertNotIn('模型有效带宽', regression['details']['memory'])


if __name__ == '__main__':
    unittest.main()
