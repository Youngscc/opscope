"""Remote adapter contracts without installing either performance model."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from opscope.evaluation.modeling_provider import ModelingRuntime


def catalog():
    tensors = [dict(name=name, role='input', shape=[128, 128], dtype='fp16') for name in ('A', 'B')]
    op = dict(id='builtin:matmul', name='MatMul', key='matmul', inputs=tensors,
              configurable=True, source={'sha256': 'op1'}, asset_id=None)
    return dict(operators=[op], hardware=[dict(id='asset:1:train', asset_id=1, domain='train',
        name='H200', family='GPU', group='remote', profiles={}, sha256='hw1')],
        dtypes=['fp16'], default_config=dict(operator_id=op['id'], operator='MatMul', key='matmul',
        domain='operator', inputs=tensors, source=op['source'], options={}, attributes={}, boundary='single operator'))


class Client:
    def __init__(self):
        self.posts = []
        self.actual_backend = 'roofline'

    def request(self, path, body=None):
        if path.endswith('/catalog'):
            return {'catalog': catalog(), 'capabilities': {'ready': True, 'tilesim': True, 'strict_operator_contract': 1}}
        if path.endswith('/simulate/op'):
            self.posts.append(body)
            return {'internal_run_id': '23'}
        return {'status': 'succeeded', 'result': {'contract': 'strict-operator-v1', 'status': 'succeeded',
                                                 'result': {'backend': self.actual_backend}}}


class ModelingProviderTest(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.runtime = ModelingRuntime('http://example.invalid', client=self.client)
        self.addCleanup(self.runtime.close)

    def body(self):
        return dict(configuration=deepcopy(catalog()['default_config']), hardware_ids=['asset:1:train'], method_ids=['roofline'])

    def test_remote_catalog_does_not_read_local_snapshot(self):
        # A remote bootstrap stays functional even if the legacy snapshot loader fails.
        with patch('opscope.offline.catalog_data.catalog_payload', side_effect=AssertionError('local data used')):
            payload = self.runtime.bootstrap()
            req = self.runtime.normalize(self.body())
            self.assertEqual(payload['hardware'][0]['id'], 'asset:1:train')
            self.assertEqual(req['configuration']['source']['sha256'], 'op1')

    def test_submit_preserves_asset_hashes(self):
        # The bridge transports selected identities rather than local hardware values.
        req = self.runtime.normalize(self.body())
        self.runtime.evaluate(req, 'asset:1:train', 'roofline')
        sent = self.client.posts[0]
        self.assertTrue(sent['strict'])
        self.assertEqual(sent['hardware'], {'asset_id': 1})
        self.assertEqual((sent['operator_hash'], sent['hardware_hash']), ('op1', 'hw1'))

    def test_method_fallback_is_rejected(self):
        # A successful response from another backend is still invalid.
        with self.assertRaisesRegex(ValueError, '实际方法'):
            self.runtime.poll('23', 'tilesim')

    def test_stale_operator_rejected(self):
        # Same name with a different content hash must be reselected.
        body = self.body()
        body['configuration']['source']['sha256'] = 'old'
        with self.assertRaisesRegex(ValueError, '版本已变化'):
            self.runtime.normalize(body)

    def test_lookup_does_not_submit_model_job(self):
        # Unconnected lookup methods cannot produce invented measurements.
        req = self.runtime.normalize(self.body())
        req['method_ids'] = ['profile']
        rows = []
        self.runtime.stream(req, rows.append)
        self.assertEqual(rows[0]['status'], 'unsupported')
        self.assertEqual(self.client.posts, [])


class ModelingTransportTest(unittest.TestCase):
    def test_identity_headers_are_not_redirected(self):
        # A redirect must not forward the configured upstream identity elsewhere.
        from opscope.evaluation.modeling_provider import NoRedirect
        with self.assertRaisesRegex(ValueError, '重定向'):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid')

    def test_headers_file_requires_trusted_transport(self):
        # Identity is allowed only over TLS or on the local loopback interface.
        import tempfile
        from pathlib import Path
        from opscope.evaluation.modeling_provider import ModelingClient
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'headers.json'
            path.write_text('{"x-user-account":"test-only"}')
            with self.assertRaisesRegex(ValueError, 'HTTPS'):
                ModelingClient('http://example.invalid', headers_file=path)
            client = ModelingClient('https://example.invalid', headers_file=path)
            self.assertEqual(client.headers['x-user-account'], 'test-only')


class RemoteCancellationTest(unittest.TestCase):
    setUp = ModelingProviderTest.setUp
    body = ModelingProviderTest.body

    def test_cancelled_batch_submits_no_more_work(self):
        # A configuration switch must stop later hardware/method submissions too.
        req = self.runtime.normalize(self.body())
        self.runtime.jobs['test'] = {'status': 'running', 'request': req}
        self.assertEqual(self.runtime.cancel('test')['status'], 'cancelling')
        rows = []
        self.runtime.stream(req, rows.append)
        self.assertEqual(self.client.posts, [])
        self.assertEqual(rows[0]['status'], 'failed')
        self.assertIn('未继续提交', rows[0]['reason'])

    def test_active_poll_propagates_cancel(self):
        # Local cancellation invokes the existing upstream job cancellation endpoint once.
        from threading import Event
        event = Event()
        event.set()
        with patch.object(self.client, 'request', wraps=self.client.request) as call:
            with self.assertRaisesRegex(ValueError, '已请求取消'):
                self.runtime.poll('23', 'roofline', event)
            call.assert_called_once_with('/api/jobs/23/cancel', {})

class RemoteParametersTest(ModelingProviderTest):
    def test_symbol_parameters_are_frozen_and_forwarded(self):
        # Parameters participate in the configuration hash and reach the shared worker.
        self.runtime.catalog['operators'][0]['parameters'] = [dict(name='S', type='integer', minimum=1, maximum=1048576)]
        body = self.body()
        body['configuration']['attributes'] = {'S': 32}
        req = self.runtime.normalize(body)
        body['configuration']['attributes']['S'] = 64
        changed = self.runtime.normalize(body)
        self.assertNotEqual(req['configuration_hash'], changed['configuration_hash'])
        self.runtime.evaluate(req, 'asset:1:train', 'roofline')
        self.assertEqual(self.client.posts[0]['parameters'], {'S': 32})

    def test_undeclared_parameter_and_boolean_are_rejected(self):
        # A bool is not a dimension, and arbitrary context keys cannot be injected.
        self.runtime.catalog['operators'][0]['parameters'] = [dict(name='S', type='integer', minimum=1, maximum=1048576)]
        body = self.body()
        body['configuration']['attributes'] = {'S': True}
        with self.assertRaisesRegex(ValueError, '范围'):
            self.runtime.normalize(body)
        body['configuration']['attributes'] = {'other': 32}
        with self.assertRaisesRegex(ValueError, '未声明'):
            self.runtime.normalize(body)
