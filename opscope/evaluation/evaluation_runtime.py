"""Bounded in-memory jobs with a separate optional Python engine process."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Lock
import uuid

from .evaluation_contract import normalize_request
from .evaluation_results import evaluation_payload, stamp
from .worker_stream import stream_worker

ROOT = Path(__file__).resolve().parent


class EvaluationRuntime:
    def __init__(self, engine_root=None, python=None, timeout=60, tilesim_python=None):
        self.engine_root = Path(engine_root).resolve() if engine_root else ROOT.parents[1]
        self.python = str(Path(python or sys.executable).absolute())
        self.tilesim_python = self._tilesim_python(tilesim_python)
        self.timeout, self.jobs, self.lock = timeout, {}, Lock()
        self.pool = ThreadPoolExecutor(max_workers=2)
        try:
            self.capabilities = {'ready': True, **self.invoke({'probe': True})}
        except (OSError, ValueError, subprocess.SubprocessError):
            self.capabilities = {'ready': False, 'reason': '评估环境不可用，请核对启动参数与依赖。'}

    def _tilesim_python(self, override):
        if override:
            return str(Path(override).absolute())
        try:
            import importlib.metadata
            if importlib.metadata.version('msopmodeling') == '1.0.9':
                return self.python
        except importlib.metadata.PackageNotFoundError:
            pass
        return None

    def invoke_roofline(self, request):
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        # Explicit roots prevent an inherited PYTHONPATH selecting another backend.
        env.pop('PYTHONPATH', None)
        result = subprocess.run([self.python, '-B', str(ROOT / 'engine_worker.py'), str(self.engine_root)],
                                input=json.dumps(request), text=True, capture_output=True,
                                cwd=self.engine_root, env=env, timeout=self.timeout)
        if result.returncode:
            raise ValueError('评估进程失败，请核对运行环境。')
        return json.loads(result.stdout)

    def invoke_tilesim(self, request):
        if not self.tilesim_python:
            raise ValueError('TileSim interpreter not configured')
        with tempfile.TemporaryDirectory(prefix='opscope-tilesim-') as directory:
            env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                   'MPLCONFIGDIR': directory, 'XDG_CACHE_HOME': directory}
            env.pop('PYTHONPATH', None)
            result = subprocess.run([self.tilesim_python, '-B', str(ROOT / 'tilesim_worker.py')],
                                    input=json.dumps(request), text=True, capture_output=True,
                                    cwd=directory, env=env, timeout=self.timeout)
        if result.returncode:
            raise ValueError('TileSim environment unavailable')
        return json.loads(result.stdout)

    def invoke(self, request):
        if request.get('probe'):
            caps = self.invoke_roofline(request)
            if self.tilesim_python:
                try:
                    caps.update(self.invoke_tilesim(request))
                except (OSError, ValueError, subprocess.SubprocessError):
                    caps.update(tilesim=False, tilesim_reason='TileSim环境不可用或版本未经验证')
            return caps
        result = self.invoke_roofline(request)
        if 'tilesim' not in request['method_ids'] or not self.tilesim_python:
            return result
        try:
            tile_rows = self.invoke_tilesim(request)['rows']
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            reason = 'TileSim评估超时，请缩小形状' if isinstance(exc, subprocess.TimeoutExpired) else 'TileSim环境或执行失败'
            tile_rows = [{'hardware': h, 'method': 'tilesim', 'status': 'failed',
                          'result': None, 'reason': reason} for h in request['hardware_ids']]
        result['rows'] = [r for r in result['rows'] if r['method'] != 'tilesim'] + tile_rows
        return result

    def submit(self, body):
        request = normalize_request(body)
        if not self.capabilities['ready']:
            raise ValueError(self.capabilities['reason'])
        with self.lock:
            if sum(j['status'] in {'queued', 'running'} for j in self.jobs.values()) >= 2:
                raise ValueError('正在处理其他评估，请稍后重试。')
            while len(self.jobs) >= 12:
                old = next(k for k, v in self.jobs.items() if v['status'] not in {'queued', 'running'})
                del self.jobs[old]
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {'id': job_id, 'status': 'queued', 'created_at': stamp(), 'request': request}
        self.pool.submit(self.run, job_id, request)
        return {'id': job_id, 'status': 'queued'}

    def stream_method(self, request, kind, on_row):
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        env.pop('PYTHONPATH', None)
        if kind == 'roofline':
            command = [self.python, '-B', str(ROOT / 'engine_worker.py'), str(self.engine_root)]
            return stream_worker(command, request, (self.timeout, self.engine_root, env), on_row)
        with tempfile.TemporaryDirectory(prefix='opscope-tilesim-') as directory:
            env.update(MPLCONFIGDIR=directory, XDG_CACHE_HOME=directory)
            command = [self.tilesim_python, '-B', str(ROOT / 'tilesim_worker.py')]
            stream_worker(command, request, (self.timeout, directory, env), on_row)

    def stream(self, request, on_row):
        groups = [('roofline', [m for m in request['method_ids'] if m != 'tilesim' or not self.tilesim_python])]
        if self.tilesim_python and 'tilesim' in request['method_ids']:
            groups.append(('tilesim', ['tilesim']))
        for kind, methods in groups:
            if not methods:
                continue
            finished = set()
            def forward(row):
                if row['status'] in {'succeeded', 'failed', 'unsupported'}:
                    finished.add((row['hardware'], row['method']))
                on_row(row)
            try:
                self.stream_method({**request, 'method_ids': methods}, kind, forward)
                if len(finished) != len(request['hardware_ids']) * len(methods):
                    raise ValueError('incomplete results')
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                reason = f'{kind}评估超时，请缩小范围' if isinstance(exc, subprocess.TimeoutExpired) else f'{kind}环境或执行失败'
                for hardware in request['hardware_ids']:
                    for method in methods:
                        if (hardware, method) not in finished:
                            on_row({'hardware': hardware, 'method': method, 'status': 'failed',
                                    'result': None, 'reason': reason})

    def publish(self, job_id, request, rows, status='running', reason=None):
        payload = evaluation_payload(request, {'rows': list(rows.values()), 'status': status}, job_id)
        with self.lock:
            job = self.jobs[job_id]
            job.update(status=status, payload=payload, revision=job.get('revision', 0) + 1)
            if reason:
                job['reason'] = reason

    def run(self, job_id, request):
        rows = {(h, m): {'hardware': h, 'method': m, 'status': 'queued',
                        'result': None, 'reason': '等待评估'}
                for h in request['hardware_ids'] for m in request['method_ids']}
        def receive(row):
            key = row['hardware'], row['method']
            if key not in rows or rows[key]['status'] in {'succeeded', 'failed', 'unsupported'}:
                raise ValueError('unexpected worker result')
            rows[key] = {**row, 'finished_at': stamp() if row['status'] != 'running' else None}
            self.publish(job_id, request, rows)
        self.publish(job_id, request, rows)
        try:
            self.stream(request, receive)
            self.publish(job_id, request, rows, 'completed')
        except Exception as exc:
            reason = '评估超时，请缩小本批次范围后重试。' if isinstance(exc, subprocess.TimeoutExpired) else '评估失败，请检查计算环境后重试。'
            for row in rows.values():
                if row['status'] in {'queued', 'running'}:
                    row.update(status='failed', reason=reason)
            self.publish(job_id, request, rows, 'failed', reason)

    def get(self, job_id, since_revision=None):
        with self.lock:
            value = self.jobs.get(job_id)
            if value is None:
                return None
            fields = {k: v for k, v in value.items() if k != 'request' and
                      (k != 'payload' or since_revision != value.get('revision'))}
        # Published payloads are immutable; copying large traces need not block workers.
        return deepcopy(fields)

    def history(self):
        with self.lock:
            jobs = [dict(id=job['id'], created_at=job.get('created_at'), status=job['status'],
                         completed_at=job['payload']['evaluation'].get('completed_at'),
                         operator=job['request']['configuration']['operator'],
                         configuration_hash=job['request']['configuration_hash'],
                         success_count=job['payload']['evaluation']['success_count'],
                         total=job['payload']['evaluation']['total'])
                    for job in self.jobs.values()
                    if job['status'] in {'completed', 'failed'} and 'payload' in job]
        return sorted(jobs, key=lambda item: item['created_at'] or '', reverse=True)

    def close(self):
        self.pool.shutdown(wait=True)
