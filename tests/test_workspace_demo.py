"""Static mode presents complete samples, never inferred hardware support."""
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from opscope.offline.build import build_payload
from opscope.offline.workspace_demo import workspace_payload


class WorkspaceDemoTests(unittest.TestCase):
    def test_standalone_html_has_no_external_asset_dependencies(self):
        # A recipient should need only this file, with no module fetches or backend access.
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []

            def handle_starttag(self, tag, attrs):
                self.tags.append((tag, dict(attrs)))

        parser = Tags()
        html = (Path(__file__).resolve().parents[1] / 'opscope-demo.html').read_text()
        parser.feed(html)
        scripts = [attrs for tag, attrs in parser.tags if tag == 'script']
        self.assertEqual(scripts, [{}])
        self.assertFalse(any(tag in {'link', 'base', 'iframe'} for tag, _ in parser.tags))
        self.assertIn("connect-src 'none'", html)
        self.assertIn('选择算子', html)
        self.assertIn('载入 MatMul 示例', html)

    def test_complete_matrix_and_original_dataset_are_independent(self):
        original = build_payload()
        demo = workspace_payload(original)
        # Unsupported catalog combinations must not become synthetic 'supported' rows.
        self.assertEqual({h['id'] for h in demo['hardware']},
                         {'ascend', 'h100', 'h200', 'b200', 'b300'})
        self.assertEqual(len(demo['results']), 25)
        self.assertTrue(all(r['available'] and r['synthetic'] for r in demo['results']))
        self.assertGreater(len(original['results']), len(demo['results']))
        self.assertTrue(demo['synthetic'])
        rows = {row['id']: row for row in demo['results']}
        self.assertEqual(rows['demo-ascend-profile']['latency_us'], 248.0)
        self.assertEqual(rows['demo-h100-roofline']['latency_us'], 157.0)
        self.assertIsNone(rows['demo-h200-roofline']['execution']['compute_us'])
        # Pair selection excludes comparing a result with itself.
        self.assertEqual(len(demo['matrix']['pairs']), 25 * 24)

    def test_completed_dialog_samples_do_not_change_original_results(self):
        # Supplemental values belong only to the static copy; GPU has no NPU counters.
        original = build_payload()
        before = json.dumps(original, sort_keys=True)
        demo = workspace_payload(original)
        self.assertEqual(json.dumps(original, sort_keys=True), before)
        for row in demo['results']:
            sample = row['presentation_sample']
            self.assertTrue(sample['synthetic'])
            self.assertAlmostEqual(sample['bandwidth_gbs'], sample['traffic_mib']*2**20/row['latency_us']/1000)
            for sections in row['sections'].values():
                for section in sections:
                    self.assertFalse(any(f['value']=='—' for f in section['facts']))
            if row['hardware']!='ascend':
                self.assertIsNone(row['analysis']['metrics']['ub_utilization'])
                self.assertEqual(row['sections']['overview'][2]['facts'][2]['label'], '共享内存占用率')
            if row['method']=='roofline':
                self.assertIsNone(sample['execution'])
                self.assertIn('解析模型', row['sections']['execution'][0]['extra'])
            self.assertIsNone(row['task']['run_id'])

    def test_detail_card_geometry_and_idle_overlay_use_sample_values(self):
        # Card widths use the displayed sample's peak/latency; analytic rows stay trace-free.
        rows = workspace_payload(build_payload())['results']
        row = next(r for r in rows if r['id']=='demo-ascend-profile')
        compute = row['sections']['cost'][0]['facts']
        self.assertAlmostEqual(compute[2]['width'], 554.2/640*100)
        self.assertAlmostEqual(compute[3]['width'], 72)
        self.assertIn('未命中 22.0%', row['sections']['cost'][1]['facts'][5]['subtitle'])
        self.assertIn('detail-idle-guide', row['sections']['execution'][0]['extra'])
        self.assertIn('Fixpipe', row['sections']['execution'][0]['extra'])
        roofline = next(r for r in rows if r['id']=='demo-ascend-roofline')
        self.assertNotIn('detail-idle-guide', roofline['sections']['execution'][0]['extra'])

    def test_catalog_and_empty_templates_allow_selection_without_reusing_samples(self):
        original = build_payload()
        demo = workspace_payload(original)
        # Browsing retains all contracts; only the exact default has performance samples.
        self.assertEqual(demo['catalog'], original['catalog'])
        self.assertFalse(demo['presentation']['configuration_locked'])
        self.assertEqual(len(demo['pending_results']), 25)
        self.assertEqual({r['hardware'] for r in demo['pending_results']},
                         {h['id'] for h in demo['hardware']})
        for row in demo['pending_results']:
            self.assertFalse(row['available'])
            self.assertTrue(row['synthetic'])
            self.assertIsNone(row['latency_us'])
            self.assertIsNone(row.get('execution'))
            self.assertEqual(row['task']['status'], 'not_run')
            self.assertEqual(row['reason'], '未预设该配置的示例结果')
        self.assertTrue(all(r['reason'] == '尚未评估' for r in original['pending_results']))

    def test_checked_in_asset_matches_generated_data(self):
        # The standalone bundle must consume the same Python-prepared figures and geometry.
        path = Path(__file__).resolve().parents[1] / 'frontend/src/data/workspace-demo.json'
        self.assertEqual(json.loads(path.read_text()), workspace_payload(build_payload()))


if __name__ == '__main__':
    unittest.main()
