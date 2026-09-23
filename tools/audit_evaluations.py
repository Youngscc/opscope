"""Audit every catalogue template/method/hardware; never invent missing inputs."""
import argparse
import ast
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import contextlib
import csv
from datetime import datetime, timezone
import json
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import signal
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from opscope.offline.catalog_data import all_hardware, catalog_payload
from opscope.offline.fixtures import METHODS
from opscope.evaluation.evaluation_contract import normalize_request, hardware_key
from opscope.evaluation.engine_worker import capabilities, engine_identity, roofline, unavailable_reason
from opscope.evaluation.tilesim_contract import unsupported, hardware_mapping

ENGINE = None


def metadata():
    versions = {}
    for name in ('msopmodeling', 'scipy', 'numpy', 'sympy', 'pandas'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    paths = ['data/modeling-catalog.json', 'opscope/evaluation/tilesim_contract.py',
             'opscope/evaluation/tilesim_adapters.py', 'opscope/evaluation/bundled_roofline.py']
    return {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
            'dependencies': versions, 'source_sha256': {
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}


def model_inventory():
    root = Path(importlib.metadata.distribution('msopmodeling').locate_file('tilesim'))
    entries = {}
    for path in sorted(root.glob('ops/**/*.py')):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == 'register' and dec.args):
                    continue
                keys = dec.args[0].elts if isinstance(dec.args[0], (ast.List, ast.Tuple)) else [dec.args[0]]
                for key in keys:
                    entries.setdefault(ast.unparse(key).split('.')[-1], []).append(str(path.relative_to(root)))
    path = root / 'api/operator_api/op_latency_predict_engineering.py'
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'function_mapping' for t in node.targets):
            for key, value in zip(node.value.keys, node.value.values):
                entries.setdefault(ast.unparse(key).split('.')[-1], []).append('engineering:' + ast.unparse(value))
    return entries


def default_config(op):
    return {'operator_id': op['id'], 'options': {}, 'inputs': [
        {key: t[key] for key in ('name', 'role', 'shape', 'dtype')} for t in op['inputs']]}


def deadline(_signum, _frame):
    raise TimeoutError('model call exceeded 60 seconds')


def summarize(result):
    keys = ('latency_us', 'compute_us', 'memory_us', 'flops', 'read_bytes',
            'write_bytes', 'bound', 'outputs', 'engine', 'hardware_hash', 'model_note')
    return {**{k: result.get(k) for k in keys}, 'event_count': len(result.get('events', []))}


def run_tile(job):
    global ENGINE
    from opscope.evaluation.tilesim_worker import setup, run_one
    identity, config, hardware = job
    record = {'case_id': identity, 'status': 'failed'}
    with tempfile.TemporaryDirectory(prefix='opscope-audit-') as tmp:
        previous = os.getcwd()
        try:
            os.chdir(tmp)
            with open('model.log', 'w+') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                if ENGINE is None:
                    ENGINE = setup()
                started = time.monotonic()
                signal.signal(signal.SIGALRM, deadline)
                signal.alarm(60)
                try:
                    result = run_one(config, hardware, ENGINE)
                    record.update(status='succeeded', result=summarize(result))
                except Exception as exc:
                    record.update(status='timeout' if isinstance(exc, TimeoutError) else 'failed',
                                  reason=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
                finally:
                    signal.alarm(0)
                record['wall_seconds'] = round(time.monotonic() - started, 4)
                log.flush(); log.seek(0)
                if record['status'] != 'succeeded':
                    record['log_tail'] = log.read()[-4000:]
        finally:
            os.chdir(previous)
    return record


def preflight(op, hardware, method):
    row = {'case_id': f"{op['id']}|{hardware}|{method}", 'operator_id': op['id'],
           'operator': op['display_name'], 'hardware': hardware, 'method': method,
           'status': '', 'reason': '', 'latency_us': None, 'mode': ''}
    try:
        request = normalize_request({'configuration': default_config(op),
                                     'hardware_ids': [hardware], 'method_ids': [method]})
    except ValueError as exc:
        row.update(status='blocked_input', reason=str(exc))
        request = None
    if not op['configurable']:
        row.update(status='catalog_excluded', reason=op['reason'])
        return row, None
    if request is None:
        return row, None
    if method in {'profile', 'method3', 'method4'}:
        row.update(status='not_connected', reason=unavailable_reason(request, method, None, capabilities()))
        return row, None
    reason = (unsupported(request['configuration'], hardware) if method == 'tilesim' else
              unavailable_reason(request, method, hardware_key(hardware), capabilities()))
    if method == 'roofline' and hardware.startswith('tilesim:'):
        reason = '缺少此型号的 Roofline 规格（矩阵/向量峰值、整卡 HBM 带宽）'
    if reason:
        row.update(status='unsupported', reason=reason)
        return row, None
    return row, request['configuration']


def collect(catalog, output):
    rows, jobs, executions = [], [], []
    identity = engine_identity()
    for op in catalog['operators']:
        for hw in all_hardware(catalog):
            for method, *_ in METHODS:
                row, config = preflight(op, hw['id'], method)
                rows.append(row)
                if config is None:
                    continue
                if method == 'tilesim':
                    jobs.append((row['case_id'], config, hw['id']))
                    continue
                try:
                    result = roofline(config, hardware_key(hw['id']), identity)
                    row.update(status='succeeded', latency_us=result['latency_us'], mode='roofline')
                    executions.append({'case_id': row['case_id'], 'status': 'succeeded', 'result': summarize(result)})
                except Exception as exc:
                    row.update(status='failed', reason=f'{type(exc).__name__}: {exc}')
                    executions.append({**row, 'traceback': traceback.format_exc()})
    (output / 'templates.json').write_text(json.dumps(catalog['operators'], ensure_ascii=False, indent=2)+'\n')
    return rows, jobs, executions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    (output / 'environment.json').write_text(json.dumps(metadata(), ensure_ascii=False, indent=2)+'\n')
    (output / 'tilesim-model-inventory.json').write_text(json.dumps(model_inventory(), ensure_ascii=False, indent=2)+'\n')
    catalog = catalog_payload()
    rows, jobs, executions = collect(catalog, output)
    indexed = {r['case_id']: r for r in rows}
    print(f'{len(rows)} cases; {len(executions)} Roofline executions; {len(jobs)} TileSim executions', flush=True)
    with (output / 'executions.jsonl').open('w') as log:
        for record in executions:
            log.write(json.dumps(record, ensure_ascii=False)+'\n')
        log.flush()
        with ProcessPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(run_tile, job) for job in jobs]
            for n, future in enumerate(as_completed(pending), 1):
                record = future.result(); executions.append(record)
                row = indexed[record['case_id']]; result = record.get('result', {})
                row.update(status=record['status'], reason=record.get('reason', ''),
                           latency_us=result.get('latency_us'), mode=result.get('engine', {}).get('mode', ''))
                log.write(json.dumps(record, ensure_ascii=False)+'\n'); log.flush()
                if n % 10 == 0 or record['status'] != 'succeeded':
                    print(f'{n}/{len(jobs)} {record["case_id"]} {record["status"]} {record.get("reason", "")[:180]}', flush=True)
    with (output / 'cases.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary = {'created_at': datetime.now(timezone.utc).isoformat(), 'templates': len(catalog['operators']),
               'visible_operators': len(catalog['groups']), 'hardware': len(all_hardware(catalog)),
               'cases': len(rows), 'actual_executions': len(executions),
               'by_method': {m: dict(Counter(r['status'] for r in rows if r['method'] == m)) for m, *_ in METHODS}}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
