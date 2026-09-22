"""Bounded in-memory jobs with a separate optional Python engine process."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock
import uuid

from evaluation_contract import normalize_request
from evaluation_results import evaluation_payload

ROOT = Path(__file__).resolve().parent


class EvaluationRuntime:
    def __init__(self, engine_root, python, timeout=60, tilesim_python=None):
        self.engine_root, self.python = Path(engine_root).resolve(), str(Path(python).absolute())
        self.tilesim_python = str(Path(tilesim_python).absolute()) if tilesim_python else None
        self.timeout, self.jobs, self.lock = timeout, {}, Lock()
        self.pool = ThreadPoolExecutor(max_workers=2)
        try:
            self.capabilities = {'ready': True, **self.invoke({'probe': True})}
        except (OSError, ValueError, subprocess.SubprocessError):
            self.capabilities = {'ready': False, 'reason': '评估环境不可用，请核对启动参数与依赖。'}

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
            self.jobs[job_id] = {'id': job_id, 'status': 'queued', 'request': request}
        self.pool.submit(self.run, job_id, request)
        return {'id': job_id, 'status': 'queued'}

    def run(self, job_id, request):
        with self.lock:
            self.jobs[job_id]['status'] = 'running'
        try:
            raw = self.invoke(request)
            payload = evaluation_payload(request, raw, job_id)
            update = {'status': 'completed', 'payload': payload}
        except subprocess.TimeoutExpired:
            update = {'status': 'failed', 'reason': '评估超时，请缩小本批次范围后重试。'}
        except Exception:
            update = {'status': 'failed', 'reason': '评估失败，请检查计算环境后重试。'}
        with self.lock:
            self.jobs[job_id].update(update)

    def get(self, job_id):
        with self.lock:
            value = self.jobs.get(job_id)
            return deepcopy({k: v for k, v in value.items() if k != 'request'}) if value else None

    def close(self):
        self.pool.shutdown(wait=True)
