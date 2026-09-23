"""Bundled Roofline process. No task store, external repository, or shared Hub."""
import contextlib
import hashlib
import json
import math
from pathlib import Path
import sys
import time

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if __package__:
    from .evaluation_contract import digest, hardware_key
    from .bundled_roofline import DATA, simulate
    from .catalog_roofline import simulate as simulate_catalog, unsupported as catalog_unsupported, DATA as CATALOG_DATA
else:
    from evaluation_contract import digest, hardware_key
    from bundled_roofline import DATA, simulate
    from opscope.evaluation.catalog_roofline import simulate as simulate_catalog, unsupported as catalog_unsupported, DATA as CATALOG_DATA


def engine_identity(_root=None):
    files = {'roofline': Path(__file__).with_name('bundled_roofline.py'),
             'catalog_roofline': Path(__file__).with_name('catalog_roofline.py'),
             'operator_specs': CATALOG_DATA, 'hardware_spec': DATA,
             'operator_contract': Path(__file__).with_name('evaluation_contract.py')}
    hardware = json.loads(DATA.read_text())
    return {'name': 'roofline', 'revision': hardware['upstream_revision'], 'bundled': True,
            'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}}


def capabilities():
    return {'roofline': True, 'tilesim_installed': False, 'tilesim': False,
            'calibration_available': False, 'tilesim_reason': '未安装 TileSim 组件'}


def roofline(config, hardware, identity):
    started = time.monotonic()
    catalog_mode = config['operator_id'].startswith('infer:')
    values = simulate_catalog(config, hardware) if catalog_mode else simulate(config, hardware)
    if values['backend'] != 'roofline' or not math.isfinite(values['latency_us']) or values['latency_us'] < 0:
        raise ValueError('invalid backend result')
    values.pop('upstream_revision', None)
    spec = values['hardware_spec']
    return {**values, 'hardware_hash': digest(spec),
            'engine': {**identity, 'mode': 'catalog-analytic' if catalog_mode else 'bundled-basic',
                       'calibration_hash': None},
            'wall_time_ms': (time.monotonic() - started) * 1000}


def evaluate(request, root, on_row=None):
    identity, caps = engine_identity(root), capabilities()
    rows = []
    for hardware in request['hardware_ids']:
        for method in request['method_ids']:
            row = {'hardware': hardware, 'method': method, 'status': 'unsupported', 'result': None}
            key = hardware_key(hardware)
            reason = unavailable_reason(request, method, key, caps)
            if method == 'roofline' and hardware in {'tilesim:910B1', 'tilesim:910B4'}:
                reason = '缺少此型号的 Roofline 规格（矩阵/向量峰值、整卡 HBM 带宽）；现有 TileSim 配置不能直接替代'
            if reason:
                row['reason'] = reason
            else:
                if on_row:
                    on_row({**row, 'status': 'running', 'reason': '正在评估…'})
                try:
                    row.update(status='succeeded', result=roofline(request['configuration'], key, identity))
                except Exception as exc:
                    row.update(status='failed', reason=f'评估失败（{type(exc).__name__}），请核对算子与硬件配置。')
            rows.append(row)
            if on_row:
                on_row(row)
    return {'rows': rows, 'capabilities': caps}


def unavailable_reason(request, method, key, caps):
    if method == 'profile':
        return '尚未接入实测参考'
    if method in {'method3', 'method4'}:
        return '尚未配置评估组件'
    if method == 'tilesim':
        return caps['tilesim_reason']
    if method == 'roofline' and request['configuration']['operator_id'].startswith('infer:'):
        return catalog_unsupported(request['configuration'], key) if key else '当前方法未配置此硬件'
    if not request['supported']:
        return '当前输入形式暂未适配评估'
    if key is None:
        return '当前方法未配置此硬件，或正式型号尚未确认'
    return None


def main():
    output = sys.stdout
    def emit(row):
        print(json.dumps({'row': row}, ensure_ascii=False, allow_nan=False), file=output, flush=True)
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    with contextlib.redirect_stdout(sys.stderr):
        request = json.load(sys.stdin)
        result = capabilities() if request.get('probe') else evaluate(request, root, emit if request.get('_stream') else None)
    print(json.dumps({'done': True} if request.get('_stream') else result, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
