"""The designer receives editable templates and the exact existing sample datasets."""
import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DesignBlocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.blocks = {}
        self.active = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if tag in {'script', 'style'} and 'id' in values:
            self.active = values['id']
            self.blocks[self.active] = {'attrs': values, 'content': ''}

    def handle_data(self, data):
        if self.active:
            self.blocks[self.active]['content'] += data

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.active = None


class DesignHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'opscope-ui-design.html').read_text()
        cls.parser = DesignBlocks()
        cls.parser.feed(cls.html)

    def test_single_file_has_no_external_assets_or_backend_connections(self):
        # The recipient can preview without the source checkout or a running API.
        scripts = [attrs for tag, attrs in self.parser.tags if tag == 'script']
        self.assertTrue(all('src' not in attrs for attrs in scripts))
        self.assertFalse(any(tag in {'link', 'iframe', 'base'} for tag, _ in self.parser.tags))
        self.assertEqual([s['id'] for s in scripts if s.get('type') is None], ['designer-runtime'])
        self.assertIn("connect-src 'none'", self.html)
        self.assertNotIn('/Users/', self.html)
        self.assertNotIn('@import', self.parser.blocks['designer-styles']['content'])

    def test_data_blocks_keep_all_original_values_and_synthetic_semantics(self):
        # Separating JSON from layout must not alter latency, identities, geometry or missing fields.
        for block, asset in [('designer-matrix-data', 'workspace-demo.json'),
                             ('designer-optimization-data', 'optimization-demo.json')]:
            data = json.loads(self.parser.blocks[block]['content'])
            self.assertEqual(data, json.loads((ROOT / 'frontend/src/data' / asset).read_text()))
            self.assertTrue(data['synthetic'])
        matrix = json.loads(self.parser.blocks['designer-matrix-data']['content'])
        self.assertEqual(len(matrix['results']), 25)
        self.assertEqual(matrix['results'][0]['latency_us'], 248.0)
        # The bundle reads the JSON block instead of containing another embedded result copy.
        self.assertNotIn('demo-ascend-profile', self.parser.blocks['designer-runtime']['content'])

    def test_pages_and_interactive_components_are_editable_and_mapped_to_source(self):
        # A design change can be moved back to its Vue component without reverse engineering a bundle.
        sources = {block['attrs']['data-source']: block['content'] for block in self.parser.blocks.values()
                   if block['attrs'].get('type') == 'text/x-template'}
        required = {'src/pages/OpScopePage.vue', 'src/pages/OptimizationPage.vue', 'src/pages/MegaKernelPage.vue',
                    'src/components/OperatorConfig.vue', 'src/components/ResultMatrix.vue',
                    'src/components/ResultDetails.vue', 'src/components/ExportDialog.vue',
                    'src/components/TraceView.vue', 'src/components/Modal.vue'}
        self.assertTrue(required <= sources.keys())
        self.assertIn('选择算子', sources['src/components/ResultMatrix.vue'])
        self.assertIn('@configure=', sources['src/pages/OpScopePage.vue'])
        self.assertIn('应用配置', sources['src/components/OperatorConfig.vue'])
        self.assertIn('v-for=', sources['src/components/ResultMatrix.vue'])
        self.assertIn('@click=', sources['src/pages/MegaKernelPage.vue'])

    def test_every_template_and_runtime_script_are_valid_browser_javascript(self):
        if not shutil.which('node'):
            self.skipTest('Node is required for browser-template syntax verification')
        data = {'templates': [b['content'] for b in self.parser.blocks.values()
                              if b['attrs'].get('type') == 'text/x-template'],
                'runtime': self.parser.blocks['designer-runtime']['content']}
        script = """
import {readFileSync} from 'node:fs';
import {compile} from '@vue/compiler-dom';
const data=JSON.parse(readFileSync(0,'utf8'));
for(const template of data.templates) {
  // TypeScript assertions must be removed before runtime template compilation.
  new Function('Vue', compile(template,{mode:'function'}).code);
}
new Function(data.runtime);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(data),
                                text=True, cwd=ROOT / 'frontend', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
