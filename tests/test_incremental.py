"""Prove results are observable before subsequent combinations finish."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import patch

from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.evaluation_runtime import EvaluationRuntime
from opscope.evaluation.worker_stream import stream_worker
from tests.test_evaluation import request_body, raw_result


class IncrementalTest(unittest.TestCase):
    def runtime(self):
        with patch.object(EvaluationRuntime, 'invoke', return_value={'roofline': True}):
            runtime = EvaluationRuntime('/tmp/engine', sys.executable)
        self.addCleanup(runtime.close)
        return runtime

    def test_first_card_published_before_second_finishes(self):
        # A barrier keeps the second result pending while the first is already queryable.
        runtime = self.runtime()
        body = request_body(); body['method_ids'] = ['roofline']
        first, release = Event(), Event()
        def stream(request, receive):
            receive({'hardware':'h100','method':'roofline','status':'succeeded','result':raw_result(200)})
            first.set()
            if not release.wait(5): raise RuntimeError('test barrier timeout')
            receive({'hardware':'h200','method':'roofline','status':'succeeded','result':raw_result(100)})
        with patch.object(runtime, 'stream', side_effect=stream):
            job = runtime.submit(body)
            try:
                self.assertTrue(first.wait(5))
                partial = runtime.get(job['id'])
                self.assertEqual(partial['status'], 'running')
                info = partial['payload']['evaluation']
                self.assertEqual((info['finished_count'], info['success_count'], info['total']), (1,1,2))
                self.assertIsNone(info['completed_at'])
                rows = {r['hardware']: r for r in partial['payload']['results'] if r['method']=='roofline'}
                self.assertEqual(rows['h100']['latency_us'], 200)
                self.assertEqual(rows['h200']['task']['status'], 'queued')
                self.assertIsNone(rows['h200']['latency_us'])
                self.assertNotIn('payload', runtime.get(job['id'], partial['revision']))
            finally:
                release.set()
            runtime.pool.shutdown(wait=True)
        final = runtime.get(job['id'], partial['revision'])
        self.assertEqual(final['status'], 'completed')
        self.assertEqual(final['payload']['evaluation']['finished_count'], 2)
        a = next(r for r in final['payload']['results'] if r['id']==rows['h100']['id'])
        self.assertEqual(a['task']['finished_at'], rows['h100']['task']['finished_at'])
        self.assertEqual(final['payload']['matrix']['pairs'][a['id']+'|'+rows['h200']['id']]['delta_percent'], -50)

    def test_process_failure_preserves_published_card(self):
        # A later timeout must not erase the already accepted zero-latency value.
        runtime = self.runtime()
        body = request_body(); body['method_ids'] = ['roofline']
        request = normalize_request(body)
        runtime.jobs['job'] = {'id':'job','status':'queued'}
        def stream(request, kind, receive):
            receive({'hardware':'h100','method':'roofline','status':'succeeded','result':raw_result(0)})
            raise subprocess.TimeoutExpired('worker',60)
        with patch.object(runtime,'stream_method',side_effect=stream):
            runtime.run('job',request)
        final = runtime.get('job')['payload']
        rows = {r['hardware']:r for r in final['results'] if r['method']=='roofline'}
        self.assertEqual(rows['h100']['latency_us'],0)
        self.assertTrue(rows['h100']['available'])
        self.assertEqual(rows['h200']['task']['status'],'failed')
        self.assertIn('超时',rows['h200']['reason'])
        self.assertEqual((final['evaluation']['success_count'],final['evaluation']['finished_count']),(1,2))

    def test_worker_flushes_before_exit(self):
        # The child cannot exit until the parent has received its first event.
        with tempfile.TemporaryDirectory() as directory:
            gate = Path(directory)/'continue'
            code = "import json,time,pathlib; print(json.dumps({'row':{'status':'succeeded'}}),flush=True)\nwhile not pathlib.Path('continue').exists(): time.sleep(.01)\nprint(json.dumps({'done':True}),flush=True)"
            rows, errors, received = [], [], Event()
            def receive(row): rows.append(row); received.set()
            def run():
                try: stream_worker([sys.executable,'-c',code],{},(5,directory,os.environ.copy()),receive)
                except Exception as error: errors.append(error)
            thread = Thread(target=run); thread.start()
            try:
                self.assertTrue(received.wait(3))
                self.assertTrue(thread.is_alive())
                self.assertEqual(rows,[{'status':'succeeded'}])
            finally:
                gate.touch(); thread.join(6)
            self.assertFalse(errors)
            self.assertFalse(thread.is_alive())

    def test_worker_timeout_retains_delivered_events(self):
        # Timeout kills a stalled process, while the first flushed event remains accepted.
        rows=[]
        code="import json,time; print(json.dumps({'row':{'status':'succeeded'}}),flush=True); time.sleep(20)"
        with self.assertRaises(subprocess.TimeoutExpired):
            stream_worker([sys.executable,'-c',code],{},(.5,Path.cwd(),os.environ.copy()),rows.append)
        self.assertEqual(rows,[{'status':'succeeded'}])
