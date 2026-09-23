"""Standalone report content follows the same result and comparison contracts."""
import unittest

from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.evaluation_results import evaluation_payload
from opscope.evaluation.html_reports import comparison_report, single_report
from opscope.evaluation.tilesim_details import trace_geometry
from tests.test_evaluation import raw_result, request_body


def job(identifier, latency):
    body = request_body()
    body['hardware_ids'], body['method_ids'] = ['h100'], ['roofline']
    request = normalize_request(body)
    raw = {'rows': [{'hardware': 'h100', 'method': 'roofline',
                     'status': 'succeeded', 'result': raw_result(latency)}]}
    payload = evaluation_payload(request, raw, identifier)
    return {'id': identifier, 'status': 'completed', 'created_at': '2026-09-23T00:00:00+00:00',
            'payload': payload}


class HtmlReportsTest(unittest.TestCase):
    def test_comparison_report_uses_same_delta_and_source_fields(self):
        # A=200, B=100 μs yields the same -50% as the time-comparison API.
        page = comparison_report(job('a'*32, 200), job('b'*32, 100))
        self.assertIn('两次评估对比报告', page)
        self.assertIn('-50.0%', page)
        self.assertIn('200 μs', page)
        self.assertIn('100 μs', page)
        self.assertIn('引擎版本', page)
        self.assertNotIn('src="http', page)

    def test_single_report_preserves_no_trace_without_fabricating_events(self):
        # Roofline has no event stream, but all structural prediction fields remain readable.
        record = job('a'*32, 200)
        row = next(item for item in record['payload']['results'] if item['available'])
        page = single_report(record, row)
        self.assertIn('200', page)
        self.assertIn('没有事件明细', page)
        self.assertIn('输入输出', page)
        self.assertIn('模型字节数不代表实际 HBM 计数器', page)
        self.assertNotIn('id="event-data"', page)

    def test_event_report_embeds_all_events_without_script_breakout(self):
        # Event names are hostile text, while zero start and overlapping lanes remain intact.
        record = job('a'*32, 200)
        row = next(item for item in record['payload']['results'] if item['available'])
        events = [{'name': '</script><img src=x onerror=alert(1)>', 'pid': 'AIC_0',
                   'tid': 'CUBE', 'ph': 'X', 'ts': 0, 'dur': 3},
                  {'name': 'copy', 'pid': 'AIC_0', 'tid': 'AIC_MTE2', 'ph': 'X', 'ts': 1, 'dur': 2}]
        row['execution'].update(events=events, trace_view=trace_geometry(events, 200))
        page = single_report(record, row)
        self.assertIn('id="event-data"', page)
        self.assertIn('AIC_MTE2', page)
        self.assertIn('2 个原始模拟事件', page)
        self.assertIn('类型', page)
        self.assertIn("['name','pid','tid','ph','ts','dur']", page)
        self.assertNotIn('</script><img', page)
        self.assertIn('\\u003c/script', page)
