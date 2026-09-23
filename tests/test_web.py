"""HTTP contracts and host integration, without external modeling or simulators."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.web.app import create_app
    from backend.web.routes.opscope import router
    from backend.web.settings import Settings
except ImportError:
    FastAPI = None

from opscope.offline.build import build_payload
from opscope.evaluation.evaluation_contract import normalize_request
from tests.test_evaluation import request_body
from tests.test_time_comparison import payload as comparison_payload, row as comparison_row
from tests.test_html_reports import job as report_job

JOB = 'a' * 32


@unittest.skipIf(FastAPI is None, 'Install backend/requirements-dev.txt to test FastAPI')
class SettingsTest(unittest.TestCase):
    def test_legacy_engine_environment_does_not_configure_service(self):
        # Old paths must not override the bundled runtime; active port settings still apply.
        with patch.dict('os.environ', {'OPSCOPE_ENGINE_ROOT': '/old/modeling',
                                       'OPSCOPE_ENGINE_PYTHON': '/old/python',
                                       'OPSCOPE_TILESIM_PYTHON': '/old/tilesim/python',
                                       'OPSCOPE_PORT': '8770',
                                       'OPSCOPE_FRONTEND_PORT': '5174'}):
            settings = Settings.from_env()
        self.assertEqual((settings.port, settings.frontend_port), (8770, 5174))
        self.assertFalse(hasattr(settings, 'engine_root'))
        self.assertFalse(hasattr(settings, 'engine_python'))
        self.assertFalse(hasattr(settings, 'tilesim_python'))


class Runtime:
    capabilities = {'ready': True, 'tilesim': False}
    def __init__(self):
        self.body = None
        self.job = {'id': JOB, 'status': 'completed', 'payload': build_payload()}
    def submit(self, body):
        self.body = normalize_request(body)
        return {'id': JOB, 'status': 'queued'}
    def get(self, job_id, since_revision=None):
        if job_id != JOB: return None
        value = deepcopy(self.job)
        if since_revision is not None and since_revision == value.get('revision'):
            value.pop('payload', None)
        return value
    def history(self):
        return [{'id': JOB, 'created_at': '2026-09-23T00:00:00+00:00', 'operator': 'MatMul'}]


@unittest.skipIf(FastAPI is None, 'Install backend/requirements-dev.txt to test FastAPI')
class WebTest(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(frontend_dist=Path(self.temp.name))
        (self.settings.frontend_dist / 'index.html').write_text('<div id="app">Vue entry</div>')
        self.client = TestClient(create_app(self.settings, self.runtime), base_url='http://127.0.0.1:8768')
        self.addCleanup(self.client.close)

    def test_bootstrap_and_static_routes(self):
        # Vue obtains the same catalog/fixture contract and unknown APIs never become HTML.
        response = self.client.get('/api/opscope/bootstrap')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['catalog']['groups']), 94)
        self.assertTrue(response.json()['synthetic'])
        self.assertIn('Vue entry', self.client.get('/opscope').text)
        self.assertEqual(self.client.get('/api/unknown').status_code, 404)
        self.assertEqual(self.client.get('/.env').status_code, 404)
        self.assertEqual(self.client.get('/static/missing.js').status_code, 404)
        self.assertEqual(self.client.get('/api/health').json()['status'], 'ok')

    def test_selected_matrix_report(self):
        # Two cells from one payload, including partial runs, are enough; never fall back on a missing job.
        path = '/api/opscope/results/compare/report'
        query = {'left': 'demo-h100-roofline', 'right': 'demo-h100-tilesim'}
        response = self.client.get(path, params=query)
        self.assertEqual(response.status_code, 200)
        self.assertIn('双结果对比报告', response.text)
        self.assertIn('synthetic=true', response.text)
        self.assertIn('width:78.5%', response.text)
        self.assertIn('+12.1%', response.text)
        self.assertIn('attachment;', response.headers['content-disposition'])
        self.runtime.job['status'] = 'running'
        self.assertEqual(self.client.get(path, params={**query, 'job': JOB}).status_code, 200)
        self.assertEqual(self.client.get(path, params={**query, 'job': 'b' * 32}).status_code, 404)
        self.assertEqual(self.client.get(path, params={**query, 'right': query['left']}).status_code, 400)
        self.assertEqual(self.client.get(path, params={**query, 'right': 'unknown'}).status_code, 404)
        self.assertEqual(self.client.get(path, params={**query, 'right': 'demo-r200-profile'}).status_code, 409)
        cross = self.client.get(path, params={**query, 'right': 'demo-h200-tilesim'})
        self.assertIn('硬件与方法同时变化', cross.text)
        self.assertNotIn('B 相对 A 耗时', cross.text)
        row = next(row for row in self.runtime.job['payload']['results'] if row['id'] == query['left'])
        row['id'] = '<script>alert(1)</script>'
        escaped = self.client.get(path, params={**query, 'job': JOB, 'left': row['id']})
        self.assertNotIn(row['id'], escaped.text)
        self.assertIn('&lt;script&gt;', escaped.text)

    def test_local_host_origin_and_body_limits(self):
        # Reject foreign origins and oversized streamed JSON before a job is submitted.
        path = '/api/opscope/evaluations'
        self.assertEqual(self.client.post(path, json={}, headers={'Origin':'https://untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.get('/api/health', headers={'Host':'untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.post(path, content='x', headers={'Content-Type':'text/plain'}).status_code, 415)
        self.assertEqual(self.client.post(path, content=' ' * 65537, headers={'Content-Type':'application/json'}).status_code, 413)
        self.assertIsNone(self.runtime.body)

    def test_submit_poll_and_snapshot(self):
        # Canonical shape and job ID survive HTTP; downloaded HTML retains synthetic provenance.
        response = self.client.post('/api/opscope/evaluations', json=request_body(), headers={'Origin':'http://127.0.0.1:5173'})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['id'], JOB)
        self.assertEqual(self.runtime.body['configuration']['inputs'][0]['shape'], [4096,4096])
        self.assertEqual(self.client.get(f'/api/opscope/evaluations/{JOB}').json()['status'], 'completed')
        snap = self.client.get(f'/api/opscope/evaluations/{JOB}/snapshot')
        self.assertEqual(snap.status_code, 200)
        self.assertIn('attachment', snap.headers['content-disposition'])
        self.assertIn('"synthetic": true', snap.text)
        self.runtime.job['status'] = 'running'
        self.assertEqual(self.client.get(f'/api/opscope/evaluations/{JOB}/snapshot').status_code, 409)
        self.assertEqual(self.client.get('/api/opscope/evaluations/unknown').status_code, 404)

    def test_running_payload_and_revision_poll(self):
        # Running responses may contain usable cards; unchanged polls omit their large traces.
        self.runtime.job.update(status='running', revision=3)
        path = f'/api/opscope/evaluations/{JOB}'
        current = self.client.get(path+'?since_revision=2').json()
        self.assertEqual(current['status'], 'running')
        self.assertIn('payload', current)
        unchanged = self.client.get(path+'?since_revision=3').json()
        self.assertNotIn('payload', unchanged)
        self.assertEqual(unchanged['revision'], 3)
        self.assertEqual(self.client.get(path+'/snapshot').status_code, 409)

    def test_time_history_and_invalid_comparison(self):
        # History is lightweight; an identical or expired pair does not masquerade as a comparison.
        history = self.client.get('/api/opscope/evaluations/history')
        self.assertEqual(history.json()[0]['id'], JOB)
        path = '/api/opscope/evaluations/compare'
        self.assertEqual(self.client.get(path, params={'left': JOB, 'right': JOB}).status_code, 400)
        self.assertEqual(self.client.get(path, params={'left': JOB, 'right': 'b'*32}).status_code, 404)

    def test_time_comparison_http_contract(self):
        # The API returns precomputed paired bars and a signed change for two terminal jobs.
        other = 'b' * 32
        first = {'status': 'completed', 'payload': comparison_payload([comparison_row()], JOB)}
        second = {'status': 'completed', 'payload': comparison_payload([comparison_row(latency=8)], other)}
        self.runtime.get = lambda job_id, since_revision=None: {JOB:first, other:second}.get(job_id)
        response = self.client.get('/api/opscope/evaluations/compare', params={'left':JOB,'right':other})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rows'][0]['delta_percent'], -20)
        self.assertEqual(response.json()['summary']['comparable'], 1)

    def test_download_standalone_reports(self):
        # Both report routes serve downloadable HTML from terminal retained jobs only.
        other = 'b' * 32
        jobs = {JOB: report_job(JOB, 200), other: report_job(other, 100)}
        self.runtime.get = lambda job_id, since_revision=None: jobs.get(job_id)
        single = self.client.get(f'/api/opscope/evaluations/{JOB}/report',
                                 params={'hardware': 'h100', 'method': 'roofline'})
        self.assertEqual(single.status_code, 200)
        self.assertIn('attachment', single.headers['content-disposition'])
        self.assertIn('200 μs', single.text)
        compare = self.client.get('/api/opscope/evaluations/compare/report',
                                  params={'left': JOB, 'right': other})
        self.assertEqual(compare.status_code, 200)
        self.assertIn('-50.0%', compare.text)
        self.assertEqual(self.client.get(f'/api/opscope/evaluations/{JOB}/report',
                                         params={'hardware': 'h200', 'method': 'roofline'}).status_code, 404)
        jobs[JOB]['status'] = 'running'
        self.assertEqual(self.client.get(f'/api/opscope/evaluations/{JOB}/report',
                                         params={'hardware': 'h100', 'method': 'roofline'}).status_code, 404)

    def test_mount_in_existing_fastapi_host(self):
        # The host owns authentication/lifecycle; router works without standalone middleware.
        host = FastAPI()
        host.state.opscope_runtime = self.runtime
        host.include_router(router)
        with TestClient(host) as client:
            self.assertEqual(client.get('/api/opscope/capabilities').json()['ready'], True)
            self.assertEqual(client.post('/api/opscope/evaluations', json=request_body()).status_code, 202)

    def test_standalone_startup_uses_bundled_engine(self):
        # A fresh clone owns its runtime; no external modeling path is required.
        with TestClient(create_app(self.settings), base_url='http://127.0.0.1:8768') as client:
            capabilities = client.get('/api/opscope/capabilities').json()
            self.assertTrue(capabilities['ready'])
            self.assertTrue(capabilities['roofline'])
            body = request_body(); body['hardware_ids'] = ['h100']; body['method_ids'] = ['roofline']
            self.assertEqual(client.post('/api/opscope/evaluations', json=body).status_code, 202)
