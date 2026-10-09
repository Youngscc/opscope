"""Keep presentation samples internally consistent without asserting model accuracy."""
import json
from pathlib import Path
import unittest

from opscope.offline.optimization_demo import build_optimization_demo

ROOT = Path(__file__).resolve().parents[1]


class OptimizationDemoTests(unittest.TestCase):
    def setUp(self):
        self.data = build_optimization_demo()

    def test_generated_asset_matches_fixture_and_is_synthetic(self):
        # A stale asset or missing marker could misrepresent UI samples as real measurements.
        actual = json.loads((ROOT / 'frontend/src/data/optimization-demo.json').read_text())
        self.assertEqual(actual, self.data)
        self.assertTrue(actual['synthetic'])
        for row in actual['diagnostics'] + actual['mega'] + actual['families']:
            self.assertTrue(row['synthetic'])

    def test_only_final_results_are_published(self):
        # Both pages and their exports consume this asset: method provenance stays out.
        encoded = json.dumps(self.data, ensure_ascii=False).lower()
        for name in ('roofline', 'tilesim', 'mskpp', '真机数据', '方法', '证据',
                     '"esl"', '"evidence"', '"source"', '"agreement"'):
            self.assertNotIn(name, encoded)
        case = next(row for row in self.data['diagnostics'] if row['id'] == 'matmul/ascend-910b1/4096')
        self.assertEqual(case['latency_us'], 126.4)
        self.assertEqual(case['latency'], '126.4')
        self.assertEqual(case['bound'], '访存受限')
        self.assertEqual(case['location'], '数据搬入 → 矩阵计算')
        self.assertEqual(self.data['schema'], 'opscope-optimization-demo-v5')

    def test_diagnosis_is_specific_to_operator_and_hardware(self):
        # Switching a SKU must select a complete preset, not relabel the previous result.
        catalog = self.data['diagnostic_catalog']
        operators = {row['id']: row for row in catalog['operators']}
        hardware = {row['id']: row for row in catalog['hardware']}
        cases = {(row['operator_id'], row['hardware_id']): row for row in self.data['diagnostics']
                 if row['size_id'] == operators[row['operator_id']]['default_size']}
        self.assertEqual(set(cases), {(op, hw) for op in operators for hw in hardware})
        expected = {('matmul', 'ascend-910b1'): (126.4, '访存受限'),
                    ('matmul', 'ascend-910b4'): (112.6, '计算受限'),
                    ('attention', 'ascend-910b1'): (284.0, '同步等待'),
                    ('attention', 'ascend-910b4'): (238.8, '访存受限')}
        for (op, hw), case in cases.items():
            self.assertEqual((case['latency_us'], case['bound']), expected[(op, hw)])
            self.assertEqual(case['hardware'], hardware[hw]['name'])
            size = next(s for s in operators[op]['sizes'] if s['id'] == operators[op]['default_size'])
            self.assertEqual((case['shape'], case['dtype']), (size['shape'], operators[op]['dtype']))
            self.assertEqual(case['id'], f'{op}/{hw}/{size["id"]}')
        for op in operators:
            first, second = (cases[(op, hw)] for hw in hardware)
            for field in ('actions', 'gauges', 'timeline', 'focus_region'):
                self.assertNotEqual(first[field], second[field])

    def test_pipeline_focus_tracks_selected_hardware(self):
        # The visual highlight must use the selected result's time window and interval.
        cases = {row['id']: row for row in self.data['diagnostics']}
        matrix = cases['matmul/ascend-910b4/4096']
        self.assertEqual(matrix['focus_region'], {'start_us': 10, 'end_us': 32, 'left': 10, 'width': 22})
        self.assertEqual(matrix['timeline_title'], '计算集中在哪？')
        self.assertEqual(cases['attention/ascend-910b4/2048']['focus_range'], '56–88 μs')
        for case in cases.values():
            focus = case['focus_region']
            self.assertTrue(0 <= focus['left'] < focus['left'] + focus['width'] <= 100)
            self.assertAlmostEqual(focus['start_us'] / case['window_us'] * 100, focus['left'])
            self.assertAlmostEqual((focus['end_us'] - focus['start_us']) / case['window_us'] * 100, focus['width'])
            self.assertLessEqual(case['window_us'], case['latency_us'])

    def test_diagnostic_sizes_and_input_tensors_match_the_selected_preset(self):
        # All three axes of the selection must identify one complete sample, including tensor shapes.
        cases = {(c['operator_id'], c['hardware_id'], c['size_id']): c for c in self.data['diagnostics']}
        self.assertEqual(len(cases), 12)
        self.assertEqual(len(cases), len(self.data['diagnostics']))
        for operator in self.data['diagnostic_catalog']['operators']:
            self.assertEqual(len(operator['sizes']), 3)
            for size in operator['sizes']:
                for hardware in self.data['diagnostic_catalog']['hardware']:
                    case = cases[(operator['id'], hardware['id'], size['id'])]
                    self.assertEqual(case['dimensions'], size['dimensions'])
                    self.assertEqual(case['inputs'], size['inputs'])
                    self.assertEqual(case['shape'], ' × '.join(map(str, case['dimensions'])))
                    self.assertEqual(len(case['dimensions']), len(operator['axes']))
        small = cases[('matmul', 'ascend-910b1', '1024')]
        medium = cases[('matmul', 'ascend-910b1', '2048')]
        self.assertEqual((small['latency_us'], medium['latency_us']), (12.8, 34.8))
        self.assertEqual(small['inputs'], [{'name': 'A', 'shape': [1024, 1024], 'dtype': 'FP16'},
                                           {'name': 'B', 'shape': [1024, 1024], 'dtype': 'FP16'}])
        attention = cases[('attention', 'ascend-910b4', '512')]
        self.assertEqual(attention['latency_us'], 63.2)
        self.assertEqual(attention['focus_range'], '14–22 μs')
        self.assertEqual([r['name'] for r in attention['inputs']], ['Q', 'K', 'V'])
        self.assertTrue(all(r['shape'] == [1, 32, 512, 128] for r in attention['inputs']))

    def test_manual_families_keep_member_identity_and_types(self):
        # Family ownership includes fused operators; a scope switch never changes ownership.
        families = {family['id']: family for family in self.data['families']}
        self.assertEqual({key: value['member_count'] for key, value in families.items()},
                         {'matmul-family': 9, 'attention-family': 4})
        for family in families.values():
            self.assertEqual(family['definition'], 'manual')
            members = {member['id']: member for member in family['members']}
            self.assertEqual(len(members), family['member_count'])
            self.assertTrue({'operator', 'fusion'}.issubset({m['kind'] for m in members.values()}))
            for scope in family['scopes']:
                expected = {m['id'] for m in members.values() if m['scope_id'] == scope['id']}
                self.assertEqual(len(expected), scope['member_count'])
                for size in scope['sizes']:
                    case = next(c for c in self.data['mega'] if c['family_id'] == family['id']
                                and c['scope_id'] == scope['id'] and c['size'] == size['id'])
                    self.assertEqual({row['member_id'] for row in case['candidates']}, expected)
                    for row in case['candidates']:
                        member = members[row['member_id']]
                        self.assertEqual((row['name'], row['kind'], row['kind_label']),
                                         (member['name'], member['kind'], member['kind_label']))
        matrix = {m['id']: m for m in families['matmul-family']['members']}
        self.assertEqual(matrix['matmul/linear']['kind'], 'operator')
        self.assertEqual(matrix['fused/mega']['kind'], 'fusion')

    def test_family_membership_does_not_merge_comparison_scopes(self):
        # Shared family and repeated local IDs do not imply equivalent computation.
        cases = {case['id']: case for case in self.data['mega']}
        mm, fused, attention = (cases[key] for key in ('matmul-large', 'fused-large', 'attention-large'))
        self.assertEqual(mm['family_id'], fused['family_id'])
        self.assertNotEqual(mm['scope_id'], fused['scope_id'])
        self.assertFalse({r['member_id'] for r in mm['candidates']} &
                         {r['member_id'] for r in fused['candidates']})
        self.assertEqual(attention['comparisons']['separate']['mega']['speedup_label'], '2.63×')
        self.assertEqual(attention['shape'], '1 × 32 × 4096 × 128')
        self.assertEqual(attention['trend']['axis_label'], '序列长度 S')
        self.assertEqual(cases['attention-small']['winner'], 'v2')
        self.assertEqual(attention['winner'], 'mega')

    def test_comparisons_are_task_local_and_baseline_reversible(self):
        # Changing baseline must preserve identity = 1 and reciprocal pair ratios.
        for case in self.data['mega']:
            ids = {row['id'] for row in case['candidates']}
            self.assertEqual(set(case['comparisons']), ids)
            for base, pairs in case['comparisons'].items():
                self.assertEqual(set(pairs), ids)
                self.assertEqual(pairs[base]['speedup'], 1)
                self.assertEqual(pairs[base]['saved_label'], '+0.0 μs')
                for target, pair in pairs.items():
                    inverse = case['comparisons'][target][base]['speedup']
                    self.assertAlmostEqual(pair['speedup'] * inverse, 1, delta=.002)
        mm = self.data['mega'][0]
        self.assertEqual(mm['comparisons']['v1']['mega']['speedup_label'], '1.65×')
        self.assertEqual(mm['comparisons']['v1']['mega']['saved_label'], '+49.6 μs')

    def test_shape_switch_changes_winner_and_fusion_semantics(self):
        # The small-shape fixture deliberately reverses two implementations' ranking.
        cases = {case['id']: case for case in self.data['mega']}
        self.assertEqual(cases['matmul-large']['winner'], 'mega')
        self.assertEqual(cases['matmul-small']['winner'], 'v3')
        fused = cases['fused-large']
        self.assertEqual(fused['semantic'], 'GELU(XW + b)')
        rows = {r['id']: r for r in fused['candidates']}
        self.assertEqual((rows['separate']['launches'], rows['mega']['launches']), (3, 1))
        self.assertNotIn('v1', fused['comparisons'])

    def test_chart_coordinates_and_trend_values_match_ranking(self):
        # Chart geometry is generated in Python; plotted values match the numeric labels.
        for case in self.data['mega']:
            rows = case['candidates']
            self.assertEqual(rows, sorted(rows, key=lambda r: r['latency_us']))
            for row in rows:
                self.assertGreater(row['width'], 0)
                self.assertLessEqual(row['width'], 100)
                self.assertTrue(row['synthetic'])
                series = next(s for s in case['trend']['series'] if s['id'] == row['id'])
                index = 1 if case['size'] == '1024' else 3
                self.assertEqual(series['points'][index]['value'], f"{row['latency_us']:g} μs")
                for point in series['points']:
                    self.assertTrue(25 <= point['y'] <= 165)
        for case in self.data['diagnostics']:
            for lane in case['timeline']:
                for segment in lane['segments']:
                    self.assertTrue(0 <= segment['left'] < segment['left'] + segment['width'] <= 100)


if __name__ == '__main__':
    unittest.main()
