"""Verify comparison geometry and incompatible/missing result boundaries."""
import copy
import unittest

from build import build_payload
from matrix_data import chart_scales, comparison_issues, nice_ceiling, pair_summary, parsed_facts, prepare_matrix


class MatrixDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload()
        cls.rows = {row['id']: row for row in cls.payload['results']}

    def test_shared_scales_and_marker_positions(self):
        # Same zero-based axis for every row; H100 157us occupies 52.33333%.
        scales = self.payload['matrix']['scales']
        self.assertEqual(scales['latency_max'], 300)
        self.assertEqual(scales['error_max'], 25)
        self.assertEqual(scales['latency_ticks'][2], {'position': 50, 'label': '150'})
        roofline = self.rows['demo-h100-roofline']['matrix']
        self.assertAlmostEqual(roofline['latency_width'], 52.33333)
        self.assertAlmostEqual(roofline['error_position'], 43.82716)
        self.assertEqual(roofline['error_label'], '-3.1%')
        self.assertEqual(self.rows['demo-h100-profile']['matrix']['error_position'], 50)

    def test_missing_and_zero_are_distinct(self):
        # An unavailable cell has no mark; zero duration has a valid width of zero.
        missing = self.rows['demo-r200-profile']
        self.assertIsNone(missing['matrix']['latency_width'])
        self.assertIsNone(missing['matrix']['error_position'])
        self.assertEqual(missing['sections'], {})
        zero = copy.deepcopy(self.rows['demo-h100-roofline'])
        zero.update(latency_us=0, deviation_percent=-100)
        prepare_matrix([zero])
        self.assertEqual(zero['matrix']['latency_width'], 0)
        self.assertIsNotNone(zero['matrix']['error_position'])
        self.assertEqual(nice_ceiling(0), 1)

    def test_pair_direction_and_multiple_changed_factors(self):
        # B-minus-A is explicit, and changing hardware plus method forbids a ratio.
        a, b = self.rows['demo-h100-roofline'], self.rows['demo-h100-tilesim']
        pair = pair_summary(a, b)
        self.assertEqual(pair['issues'], [])
        self.assertAlmostEqual(pair['delta_percent'], 19 / 157 * 100)
        self.assertIn('+12.1%', pair['text'])
        cross = pair_summary(a, self.rows['demo-h200-tilesim'])
        self.assertEqual(cross['issues'], ['硬件与方法同时变化'])
        self.assertIsNone(cross['delta_percent'])
        same_method = pair_summary(a, self.rows['demo-h200-roofline'])
        self.assertEqual(same_method['issues'], [])

    def test_workload_and_provenance_guard(self):
        # Identical input names alone cannot establish the same output or timing contract.
        a = self.rows['demo-h100-roofline']
        b = copy.deepcopy(a)
        b['workload']['tensors'][-1]['shape'] = [4096, 2048]
        self.assertEqual(comparison_issues(a, b), ['输入输出不同'])
        b = copy.deepcopy(a)
        del b['workload']['boundary']
        self.assertEqual(comparison_issues(a, b), ['计时边界未提供'])
        b = copy.deepcopy(a)
        b['synthetic'] = False
        self.assertIn('真实来源与硬件/引擎契约尚未校验', comparison_issues(a, b))

    def test_unknown_detail_rows_do_not_become_equal_facts(self):
        # Unknown specs must remain visible in a differences-only comparison.
        sections = self.rows['demo-h200-roofline']['sections']
        self.assertEqual(set(sections), {'overview', 'cost', 'execution', 'context', 'source'})
        hardware = sections['context'][1]['facts']
        peak = next(row for row in hardware if row['label'] == 'FP16 峰值（TFLOP/s）')
        self.assertEqual(peak, {'label': 'FP16 峰值（TFLOP/s）', 'value': '—', 'known': False})
        costs = sections['overview'][1]['extra']
        self.assertIn('回归仅提供总耗时', costs)
        self.assertNotIn('<dl', costs)
        facts = parsed_facts('<dl><dt>zero</dt><dd>0</dd><dt>unknown</dt><dd>—</dd></dl>')
        self.assertTrue(facts[0]['known'])
        self.assertFalse(facts[1]['known'])

    def test_no_reference_and_zero_denominator(self):
        # Chart scales stay finite with no data, and zero baselines never produce Infinity.
        self.assertEqual(chart_scales([])['latency_max'], 1)
        a = copy.deepcopy(self.rows['demo-h100-roofline'])
        a['latency_us'] = 0
        summary = pair_summary(a, self.rows['demo-h100-tilesim'])
        self.assertIsNone(summary['delta_percent'])
        self.assertIn('未定义', summary['text'])
