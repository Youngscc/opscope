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
        self.assertIn('25 组预设结果', html)

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

    def test_checked_in_asset_matches_generated_data(self):
        # The standalone bundle must consume the same Python-prepared figures and geometry.
        path = Path(__file__).resolve().parents[1] / 'frontend/src/data/workspace-demo.json'
        self.assertEqual(json.loads(path.read_text()), workspace_payload(build_payload()))


if __name__ == '__main__':
    unittest.main()
