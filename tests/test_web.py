"""HTTP contracts and host integration, without external modeling or simulators."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

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

JOB = 'a' * 32


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
