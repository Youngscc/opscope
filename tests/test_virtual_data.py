"""Placeholder methods expose synthetic totals without claiming execution evidence."""
import unittest

from opscope.offline.build import build_payload


class VirtualMethodsTest(unittest.TestCase):
    def test_method_order_and_lookup_presets(self):
        # Renaming/order must survive bootstrap, live results and exported row metadata.
        from opscope.evaluation.evaluation_contract import normalize_request
        from opscope.evaluation.evaluation_results import evaluation_payload
        from opscope.evaluation.engine_worker import unavailable_reason
        demo = build_payload()
        order = ['profile', 'method3', 'method4', 'roofline', 'tilesim']
        names = ['真机数据', 'MSKPP', 'ESL', 'Roofline', 'TileSim']
        request = normalize_request({'configuration': demo['catalog']['default_config'],
                                     'hardware_ids': ['h100'], 'method_ids': order})
        raw = []
        for method, name in zip(order[:3], names[:3]):
            reason = unavailable_reason(request, method, 'H200_Server', {})
            self.assertEqual(reason, f'{name}：未配置 lookup 数据源，暂无查表结果')
            raw.append({'hardware': 'h100', 'method': method, 'status': 'unsupported', 'reason': reason})
        live = evaluation_payload(request, {'rows': raw}, 'a' * 32)
        for payload in (demo, live):
            self.assertEqual([m['id'] for m in payload['methods']], order)
            self.assertEqual([m['name'] for m in payload['methods']], names)
            self.assertEqual([m['backend'] for m in payload['methods']], ['lookup'] * 3 + ['roofline', 'tilesim'])
            self.assertEqual([m['source'] for m in payload['methods'][:3]], ['lookup'] * 3)
            rows = [r for r in payload['results'] if r['hardware'] == 'h100']
            self.assertEqual([r['method'] for r in rows], order)
            self.assertEqual([r['method_name'] for r in rows], names)
            self.assertEqual([r['method_backend'] for r in rows[:3]], ['lookup'] * 3)
        for row in [r for r in live['results'] if r['hardware'] == 'h100'][:3]:
            self.assertFalse(row['available'])
            self.assertIsNone(row['latency_us'])
            self.assertIsNone(row['task']['actual_backend'])
            self.assertEqual(row['task']['status'], 'unsupported')
            self.assertEqual(row['task']['source'], 'lookup')

    def test_virtual_totals_and_missing_evidence(self):
        # All ten totals are intentional fixtures; no kernel, counter or backend is inferred.
        payload = build_payload()
        expected = {'ascend': (255, 239), 'h100': (170, 158), 'h200': (152, 146),
                    'b200': (100, 92), 'b300': (86, 81)}
        rows = [row for row in payload['results'] if row['available'] and row['method'] in {'method3', 'method4'}]
        self.assertEqual(len(rows), 10)
        for row in rows:
            index = 0 if row['method'] == 'method3' else 1
            self.assertEqual(row['latency_us'], expected[row['hardware']][index])
            self.assertTrue(row['synthetic'])
            self.assertEqual(row['source_label'], '虚拟数据')
            self.assertEqual(row['execution']['kind'], 'virtual')
            self.assertIsNone(row['task']['actual_backend'])
            self.assertIsNone(row['task']['task_id'])
            self.assertIsNone(row['bound'])
            self.assertIsNone(row['execution']['compute_us'])
            self.assertIsNone(row['execution']['memory_us'])
            self.assertIsNone(row['summary']['memory'])
            self.assertEqual(row['execution']['events'], [])
            self.assertNotIn('kernel', row['execution'])
        missing = [row for row in payload['results'] if row['hardware'] == 'r200']
        self.assertTrue(all(not row['available'] for row in missing))

    def test_chart_pair_and_detail_use_same_totals(self):
        # Matrix, plotted coordinates, paired percentages and modal totals stay consistent.
        payload = build_payload()
        rows = {row['id']: row for row in payload['results']}
        row = rows['demo-h100-method3']
        self.assertAlmostEqual(row['deviation_percent'], 8 / 162 * 100)
        self.assertEqual(row['matrix']['error_label'], '+4.9%')
        self.assertAlmostEqual(row['matrix']['latency_width'], 170 / 300 * 100, places=4)
        self.assertIn('170.00 μs', row['details']['overview'])
        self.assertIn('162.00 μs', row['details']['latency'])
        pair = payload['matrix']['pairs']['demo-h100-method3|demo-h100-method4']
        self.assertEqual(pair['issues'], [])
        self.assertAlmostEqual(pair['delta_percent'], -12 / 170 * 100)


if __name__ == '__main__':
    unittest.main()
