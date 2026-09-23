"""Two-run comparison keeps provenance gates and missing values visible."""
import unittest

from opscope.evaluation.time_comparison import compare_payload


def row(hardware='h100', method='roofline', latency=10, status='succeeded', **provenance):
    return {'id': f'job-{hardware}-{method}', 'hardware': hardware, 'method': method,
            'available': status == 'succeeded', 'synthetic': False,
            'latency_us': latency if status == 'succeeded' else None,
            'latency': str(latency) if status == 'succeeded' else '—',
            'reason': None if status == 'succeeded' else '缺少模型',
            'task': {'status': status}, 'provenance': {
                'configuration_hash': 'config', 'hardware_hash': 'hardware',
                'engine': {'revision': '1'}, **provenance}}


def payload(rows, name):
    return {'evaluation': {'id': name}, 'results': rows,
            'hardware': [{'id': 'h100', 'name': 'H100'}],
            'methods': [{'id': 'roofline', 'name': 'Roofline'}]}


class TimeComparisonTest(unittest.TestCase):
    def test_same_contract_produces_shared_scale_and_exact_counts(self):
        # One paired result moves from 10 to 8 μs; chart widths use one scale.
        result = compare_payload(payload([row()], 'A'), payload([row(latency=8)], 'B'))
        pair = result['rows'][0]
        self.assertEqual(pair['delta_percent'], -20)
        self.assertEqual(result['summary'], {'comparable': 1, 'faster': 1, 'slower': 0,
                                             'equal': 0, 'not_comparable': 0})
        self.assertGreater(pair['bars'][0], pair['bars'][1])
        self.assertEqual(pair['left']['latency_us'], 10)

    def test_changed_contract_and_missing_result_keep_values_without_delta(self):
        # A changed hardware spec and an unsupported right side must never look like zero latency.
        changed = compare_payload(payload([row()], 'A'),
                                  payload([row(latency=8, hardware_hash='other')], 'B'))['rows'][0]
        self.assertIn('硬件规格不同', changed['issues'])
        self.assertIsNone(changed['delta_percent'])
        self.assertEqual(changed['right']['latency_us'], 8)
        missing = compare_payload(payload([row()], 'A'),
                                  payload([row(status='unsupported')], 'B'))['rows'][0]
        self.assertIsNone(missing['right']['latency_us'])
        self.assertIsNone(missing['bars'])

    def test_zero_baseline_is_kept_but_ratio_is_undefined(self):
        # Zero is a known value, though (B-A)/A has no defined percentage.
        pair = compare_payload(payload([row(latency=0)], 'A'),
                               payload([row(latency=3)], 'B'))['rows'][0]
        self.assertEqual(pair['left']['latency_us'], 0)
        self.assertIsNone(pair['delta_percent'])
        self.assertEqual(pair['issues'], [])

    def test_unselected_combinations_do_not_inflate_summary(self):
        # Pending template rows outside a job are absent from that run's comparison axis.
        extra = row(hardware='other', status='not_run')
        result = compare_payload(payload([row(), extra], 'A'), payload([row()], 'B'))
        self.assertEqual(len(result['rows']), 1)
