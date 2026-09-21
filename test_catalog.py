"""Verify standalone catalog identities, unknown dimensions and form isolation."""
import ast
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from build import build_payload
from catalog_data import catalog_payload
from tools.snapshot_catalog import dimension, tensor_template


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = catalog_payload()
        cls.operators = {op['id']: op for op in cls.catalog['operators']}

    def test_catalog_scope_and_entry_identity(self):
        # Preserve source domains, legacy asset keys, and excluded communication rows.
        self.assertEqual(Counter(op['domain'] for op in self.operators.values()),
                         {'demo': 1, 'train': 11, 'infer': 88})
        self.assertEqual(len(self.operators), len(self.catalog['operators']))
        self.assertEqual(sum(not op['configurable'] for op in self.operators.values()), 6)
        self.assertEqual(self.operators['infer:vision_patch_embed']['name'], 'VisionPatchEmbed')
        self.assertFalse(self.operators['infer:AllReduce']['configurable'])
        self.assertNotEqual(self.operators['train:matmul']['source'], self.operators['infer:MatMul']['source'])

    def test_defaults_preserve_unknown_dimensions_and_tensor_roles(self):
        # The modeling UI silently uses 1 here. This snapshot must retain missing head_dim.
        attention = self.operators['infer:FlashAttentionScore']
        self.assertEqual(attention['inputs'][0]['shape'], [1, 32, 2048, None])
        self.assertEqual(attention['inputs'][0]['unresolved_dimensions'], ['qk_head_dim'])
        embedding = self.operators['train:embedding']['inputs']
        self.assertEqual([t['dtype'] for t in embedding], ['bf16', 'int32'])
        vision = self.operators['infer:vision_patch_embed']['inputs']
        self.assertEqual([t['role'] for t in vision], ['input', 'parameter'])
        self.assertEqual(attention['outputs'][2]['shape'], '[0, 0, 0, 0]')

    def test_unique_visible_operators_preserve_all_input_forms(self):
        # Display duplicates merge without losing the different SwiGLU tensor contracts.
        groups = self.catalog['groups']
        self.assertEqual(len(groups), 94)
        self.assertEqual(len({group['name'].casefold() for group in groups}), 94)
        self.assertEqual(sum(len(group['variants']) for group in groups), 100)
        matmul = next(group for group in groups if group['id'] == 'matmul')
        self.assertEqual(matmul['variants'], ['demo:matmul', 'train:matmul', 'infer:MatMul'])
        swiglu = next(group for group in groups if group['id'] == 'swiglu')
        self.assertEqual([len(self.operators[key]['inputs']) for key in swiglu['variants']], [4, 1])
        for op in self.operators.values():
            self.assertNotRegex(op['template_label'], r'(?i)modeling|训练|推理')

    def test_expression_evaluation_is_restricted(self):
        # Unknown and fractional dimensions stay absent, and calls cannot execute.
        self.assertEqual(dimension(ast.parse('B * S // tp_size', mode='eval').body,
                                   {'B': 2, 'S': 128, 'tp_size': 4}), 64)
        for expression in ('[unknown]', '[3 / 2]', '[__import__("os")]', '[0]'):
            self.assertEqual(tensor_template({'name': 'x', 'shape': expression}, 'input', {})['shape'], [None])

    def test_hardware_profiles_and_placeholder(self):
        # POD/Server are distinct, and train/infer hashes prove specs are not conflated.
        devices = {hw['name']: hw for hw in self.catalog['hardware']}
        self.assertEqual(len(devices), 11)
        self.assertIn('H100_POD', devices)
        self.assertIn('H100_Server', devices)
        for device in devices.values():
            self.assertEqual(set(device['profiles']), {'train', 'infer'})
        profiles = devices['H100_Server']['profiles']
        self.assertNotEqual(profiles['train']['sha256'], profiles['infer']['sha256'])
        payload = build_payload()
        for row in payload['results']:
            if row['hardware'].startswith('modeling:'):
                self.assertFalse(row['available'])
                self.assertIsNone(row.get('latency_us'))
                self.assertNotIn('execution', row)
        self.assertNotIn('accel', {row['method'] for row in payload['results']})

    @unittest.skipUnless(shutil.which('node'), 'Node is required for form-state checks')
    def test_javascript_configuration_contract(self):
        # Exercise changed-shape/dtype isolation, actual catalog templates and restoration.
        result = subprocess.run(['node', 'test_configuration.cjs'],
                                cwd=Path(__file__).parent, input=json.dumps(build_payload()),
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
