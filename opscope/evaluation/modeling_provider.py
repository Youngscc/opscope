"""Thin HTTP adapter; all operator definitions, hardware and models live upstream."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from threading import Lock, Event
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from opscope.offline.catalog_data import pending_results
from opscope.offline.fixtures import METHODS, method_config
from opscope.offline.matrix_data import prepare_matrix
from .evaluation_contract import digest, normalize_tensor, selected_ids
from .evaluation_results import evaluation_payload
from .evaluation_runtime import EvaluationRuntime


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('建模服务发生重定向，请配置最终服务地址')


class ModelingClient:
    def __init__(self, base_url, timeout=15, headers_file=None):
        url = urlsplit(base_url)
        if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('无效的建模服务地址')
        self.base_url, self.timeout = base_url.rstrip('/'), timeout
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if headers_file:
            values = json.loads(Path(headers_file).read_text())
            allowed = {'x-user-account', 'x-user-name', 'x-user-l3dept', 'x-user-l4dept', 'x-user-l5dept'}
            if not isinstance(values, dict) or not set(values) <= allowed or any(
                    not isinstance(v, str) or '\n' in v or '\r' in v for v in values.values()):
                raise ValueError('身份文件需要有效的 x-user-* 请求头 JSON')
            if url.scheme != 'https' and url.hostname not in {'localhost', '127.0.0.1', '::1'}:
                raise ValueError('携带身份时，非本机建模服务必须使用 HTTPS')
            self.headers.update(values)
        self.opener = build_opener(NoRedirect())

    def request(self, path, body=None):
        data = json.dumps(body, allow_nan=False).encode() if body is not None else None
        request = Request(self.base_url + path, data=data,
                          headers=self.headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc).get('detail', f'HTTP {exc.code}')
            except (ValueError, AttributeError):
                detail = f'HTTP {exc.code}'
            raise ValueError(f'建模服务拒绝请求：{detail}') from exc
        except (URLError, TimeoutError) as exc:
            raise ValueError('建模服务连接失败，未切换到本地计算') from exc


def catalog_payload(catalog):
    hardware = catalog['hardware']
    rows = pending_results(hardware)
    for row in rows:
        row['synthetic'] = False
    workload = {'operator': catalog['default_config']['operator'], 'boundary': catalog['default_config']['boundary']}
    return dict(schema='opscope-remote-v1', synthetic=False, notice='模型预测 · 非设备实测',
                catalog=catalog, hardware=hardware, methods=[method_config(m[0]) for m in METHODS],
                results=deepcopy(rows), pending_results=rows, matrix=prepare_matrix(rows), workload=workload)


class ModelingRuntime(EvaluationRuntime):
    def __init__(self, base_url, timeout=120, client=None):
        self.client = client or ModelingClient(base_url)
        self.timeout, self.jobs, self.lock = timeout, {}, Lock()
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.stopping = Event()
        self.catalog = None
        self.remote_jobs = {}
        self.capabilities = {'ready': False, 'reason': '正在连接建模服务'}
        self.refresh()

    def refresh(self):
        try:
            response = self.client.request('/api/train/simulate/op/catalog')
            if response['capabilities'].get('strict_operator_contract') != 1:
                raise ValueError('建模服务不支持严格单算子接口，请更新后端')
            self.catalog = response['catalog']
            self.capabilities = {**response['capabilities'], 'provider': 'modeling'}
        except (ValueError, KeyError) as exc:
            self.capabilities = {'ready': False, 'provider': 'modeling', 'reason': str(exc)}

    def bootstrap(self):
        self.refresh()
        if not self.capabilities['ready'] or self.catalog is None:
            raise ValueError(self.capabilities['reason'])
        return catalog_payload(deepcopy(self.catalog))

    def normalize(self, body):
        if not isinstance(body, dict) or not isinstance(body.get('configuration'), dict):
            raise ValueError('缺少算子配置')
        if self.catalog is None:
            raise ValueError(self.capabilities['reason'])
        catalog, config = deepcopy(self.catalog), body['configuration']
        op = next((op for op in catalog['operators'] if op['id'] == config.get('operator_id')), None)
        if op is None or not op['configurable']:
            raise ValueError((op or {}).get('reason') or '未知算子，请刷新目录')
        if config.get('source', {}).get('sha256') != op['source']['sha256']:
            raise ValueError('算子版本已变化，请重新选择')
        inputs = config.get('inputs')
        if not isinstance(inputs, list) or len(inputs) != len(op['inputs']):
            raise ValueError('输入数量与模板不符')
        if config.get('options'):
            raise ValueError('当前共享入口不接受布局覆盖')
        attributes = config.get('attributes') or {}
        allowed = {field['name']: field for field in op.get('parameters', [])}
        if not isinstance(attributes, dict) or set(attributes) - allowed.keys():
            raise ValueError('包含未声明的算子参数')
        for name, value in attributes.items():
            field = allowed[name]
            items = value if field['type'] in {'integer_list', 'permutation'} and isinstance(value, list) else [value]
            if not items or len(items) > 16 or any(type(v) is not int or not field.get('minimum', 1) <= v <= field.get('maximum', 1048576) for v in items):
                raise ValueError(f'{name} 参数超出允许范围')
        tensors = [normalize_tensor(t, template, catalog['dtypes']) for t, template in zip(inputs, op['inputs'])]
        canonical = {**catalog['default_config'], 'operator_id': op['id'], 'operator': op['name'],
                     'key': op['key'], 'inputs': tensors, 'attributes': deepcopy(attributes), 'source': op['source']}
        return dict(configuration=canonical, configuration_hash=digest(canonical),
                    hardware_ids=selected_ids(body.get('hardware_ids'), {h['id'] for h in catalog['hardware']}, '硬件'),
                    method_ids=selected_ids(body.get('method_ids'), {m[0] for m in METHODS}, '方法'),
                    catalog=catalog, operator=op, cancelled=Event())

    def make_payload(self, request, raw, job_id):
        return evaluation_payload(request, raw, job_id, catalog_payload(request['catalog']))

    def stream(self, request, on_row):
        for hardware in request['hardware_ids']:
            for method in request['method_ids']:
                row = dict(hardware=hardware, method=method, result=None)
                if self.stopping.is_set() or request['cancelled'].is_set():
                    on_row({**row, 'status': 'failed', 'reason': '批次已取消，未继续提交'})
                    continue
                if method not in {'roofline', 'tilesim'}:
                    on_row({**row, 'status': 'unsupported', 'reason': 'lookup 尚未接入数据源'})
                    continue
                on_row({**row, 'status': 'running', 'reason': '正在提交建模任务'})
                try:
                    value = self.evaluate(request, hardware, method)
                    on_row({**row, **value})
                except ValueError as exc:
                    on_row({**row, 'status': 'failed', 'reason': str(exc)})

    def evaluate(self, request, identifier, method):
        op, config = request['operator'], request['configuration']
        hw = next(h for h in request['catalog']['hardware'] if h['id'] == identifier)
        body = dict(strict=True, operator=op['key'], operator_asset_id=op.get('asset_id'),
                    operator_hash=op['source']['sha256'], hardware={'asset_id': hw['asset_id']},
                    hardware_domain=hw['domain'], hardware_hash=hw['sha256'],
                    simulation=method, inputs=config['inputs'], parameters=config['attributes'])
        job = self.client.request('/api/train/simulate/op', body)
        run_id = job['internal_run_id']
        with self.lock:
            self.remote_jobs[run_id] = True
        try:
            return self.poll(run_id, method, request['cancelled'])
        finally:
            with self.lock:
                self.remote_jobs.pop(run_id, None)

    def poll(self, run_id, method, cancelled=None):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline and not self.stopping.is_set() and not (cancelled and cancelled.is_set()):
            job = self.client.request(f'/api/jobs/{run_id}')
            if job['status'] == 'succeeded':
                value = job['result']
                if not isinstance(value, dict) or value.get('contract') != 'strict-operator-v1':
                    raise ValueError('建模结果契约不匹配')
                if value['status'] == 'succeeded' and value['result'].get('backend') != method:
                    raise ValueError('实际方法与请求不一致，结果已拒绝')
                if value['status'] == 'succeeded':
                    value['result']['upstream_run_id'] = str(run_id)
                    value['result']['user_calibration'] = value.get('user_calibration')
                return value
            if job['status'] in {'failed', 'cancelled'}:
                detail = (job.get('error_info') or {}).get('detail') or {}
                raise ValueError(detail.get('reason') or job.get('error') or '远程任务失败或取消')
            self.stopping.wait(0.3)
        try:
            self.client.request(f'/api/jobs/{run_id}/cancel', {})
        except ValueError:
            raise ValueError('等待超时，取消请求未确认；远程任务可能仍在运行') from None
        raise ValueError('等待已终止，已请求取消远程任务')

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise ValueError('评估记录不存在或已过期')
            job['request']['cancelled'].set()
            return {'id': job_id, 'status': 'cancelling' if job['status'] in {'queued', 'running'} else job['status']}

    def close(self):
        self.stopping.set()
        self.pool.shutdown(wait=True)
