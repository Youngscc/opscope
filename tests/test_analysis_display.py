"""Hanguang-shaped examples preserve units, missing values and platform boundaries."""
import unittest

from build import build_payload
from opscope.offline.analysis_display import analysis_view, sample_analysis
from opscope.offline.optimization_demo import build_optimization_demo


class AnalysisDisplayTests(unittest.TestCase):
    def test_ratios_zero_and_missing_are_not_interchangeable(self):
        view = analysis_view({'metrics': {'l2_cache_hit_rate': .86, 'mfu': 0, 'ub_utilization': None}})
        self.assertEqual([row['display'] for row in view['metrics']], ['86.0%', '0.0%', '—'])
        self.assertEqual([row['width'] for row in view['metrics']], [86, 0, None])
        self.assertEqual(view['cycles'], '—')
        self.assertTrue(all(row['value'] is None for row in view['pipes']))

    def test_component_cycles_never_become_total_latency_or_total_cycles(self):
        raw = sample_analysis(248)
        view = analysis_view(raw)
        self.assertEqual(raw['performance'], {'latency_us': 248, 'cycles': None})
        self.assertEqual(view['pipes'][0]['display'], '80')
        self.assertEqual(view['cycles'], '—')
        raw['performance']['cycles'] = 0
        self.assertEqual(analysis_view(raw)['cycles'], '0')
        self.assertEqual(raw['trace'], {'format': None, 'file': None})

    def test_matrix_keeps_latency_and_does_not_assign_npu_fields_to_gpu(self):
        rows = {row['id']: row for row in build_payload()['results']}
        npu, gpu = rows['demo-ascend-profile'], rows['demo-h100-profile']
        self.assertEqual(npu['analysis']['performance']['latency_us'], npu['latency_us'])
        self.assertEqual(len(npu['analysis']['pipe_cycles']['components']), 7)
        self.assertIsNone(gpu['analysis']['pipe_cycles']['components'])
        self.assertIsNone(gpu['analysis']['metrics']['ub_utilization'])
        self.assertEqual(gpu['latency_us'], 162)
        lookup = rows['demo-ascend-method3']
        self.assertNotIn('analysis', lookup)
        resource = next(section for section in lookup['sections']['overview'] if section['key'] == 'analysis')
        self.assertTrue(all(not fact['known'] for fact in resource['facts']))
        self.assertTrue(all('analysis' not in row for row in build_payload()['pending_results']))

    def test_optimization_and_members_share_the_display_contract(self):
        data = build_optimization_demo()
        rows = data['diagnostics'] + [row for case in data['mega'] for row in case['candidates']]
        for row in rows:
            self.assertTrue(row['synthetic'])
            self.assertEqual(row['analysis']['performance']['latency_us'], row['latency_us'])
            self.assertEqual(row['analysis_view'], analysis_view(row['analysis']))
            self.assertTrue(all(0 <= value <= 1 for value in row['analysis']['metrics'].values()))
            self.assertNotIn('engine', row['analysis'])
        self.assertEqual(data['diagnostics'][0]['analysis_view']['metrics'][1]['display'], '46.0%')

    def test_explicit_demo_clock_and_traffic_rates(self):
        # Equivalent cycles are labeled and export the sample clock, never summed pipes.
        raw = sample_analysis(126.4, clock_mhz=1500)
        self.assertEqual(raw['performance']['cycles'], 189600)
        self.assertEqual(raw['sample_clock_mhz'], 1500)
        self.assertEqual(analysis_view(raw)['cycle_label'], '等效周期')
        data = build_optimization_demo()
        for case in data['mega']:
            for row in case['candidates']:
                self.assertEqual(row['traffic_bandwidth'],
                                 f"{row['traffic_mib'] * 2**20 / row['latency_us'] / 1000:.1f}")
