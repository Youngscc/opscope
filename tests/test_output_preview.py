"""Output form references must distinguish matrix and weight layouts."""
import unittest
from opscope.offline.catalog_data import catalog_payload


class OutputPreviewTests(unittest.TestCase):
    def test_matrix_axes_and_dtype(self):
        ops = {op['id']: op for op in catalog_payload()['operators']}
        row = ops['demo:matmul']['output_preview'][0]
        self.assertEqual([(r['input'], r['axis']) for r in row['shape_refs']], [(0, 0), (1, 1)])
        self.assertEqual([r['alternate'] for r in row['shape_refs']], [1, 0])
        self.assertEqual(row['dtype_input'], 0)
        self.assertEqual(ops['train:linear']['output_preview'][0]['shape_refs'][-1], {'input': 1, 'axis': 0})
        self.assertEqual(len(ops['train:bmm']['output_preview'][0]['shape_refs']), 3)
        self.assertTrue(ops['infer:Mul']['output_preview'][0]['same_shape'])
        self.assertEqual(ops['infer:Cast']['output_preview'][0]['dtype'], 'fp32')
        self.assertEqual(ops['infer:SwiGlu']['output_preview'], [])
