"""Optional engine process. No task store, HTTP submission, or shared Hub."""
import contextlib
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from evaluation_contract import digest, hardware_key


def engine_identity(root):
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    files = {'roofline': 'backend/simulator/backends/roofline.py',
             'hardware_spec': 'backend/hardware/spec.py',
             'operator_contract': 'backend/web/services/train/op_sim.py'}
    return {'name': 'roofline', 'revision': revision or 'unknown',
            'files': {name: hashlib.sha256((root / path).read_bytes()).hexdigest() for name, path in files.items()}}


def capabilities():
    from backend.simulator.backends.tilesim import _TILE_SIM_AVAILABLE
    from backend.calibration.calibration_lookup import default_lib_dir
    return {'roofline': True, 'tilesim_installed': _TILE_SIM_AVAILABLE,
            'tilesim': False, 'calibration_available': default_lib_dir() is not None,
            'tilesim_reason': '当前硬件与算子组合尚未完成适配验证' if _TILE_SIM_AVAILABLE else '未安装 TileSim 组件'}


def node_for(config):
    from backend.common.ir import OpNode, TensorMeta
    from backend.common.ir.types import dtype_from_str
    from backend.web.services.train.op_sim import OP_TYPE_MAP, _infer_outputs
    inputs = [TensorMeta.from_shape_dtype(t['name'], tuple(t['shape']), dtype_from_str(t['dtype']))
              for t in config['inputs']]
    key = config['key']
    outputs = _infer_outputs(key, inputs)
    return OpNode(id='evaluation', op_type=OP_TYPE_MAP[key], inputs=inputs, outputs=outputs)


def roofline(config, hardware, identity):
    from backend.hardware import load
    from backend.simulator.backends.roofline import RooflineSimulator
    from backend.calibration.calibration_lookup import default_lib_dir
    hw = load(hardware)
    node = node_for(config)
    if hw.peak_flops(node.inputs[0].dtype) <= 0:
        raise ValueError('hardware precision unavailable')
    started = time.monotonic()
    result = RooflineSimulator().simulate(node, hw)
    fields = ('latency_us', 'compute_us', 'memory_us', 'flops', 'read_bytes',
              'write_bytes', 'arithmetic_intensity', 'bound', 'backend', 'calibration_source')
    values = {k: getattr(result, k) for k in fields}
    if result.backend != 'roofline' or not math.isfinite(result.latency_us) or result.latency_us < 0:
        raise ValueError('invalid backend result')
    if result.calibration_source == 'regression':
        values.update(compute_us=None, memory_us=None, bound=None)
    tensors = [{'name': t.id, 'shape': list(t.shape), 'dtype': t.dtype.value,
                'bytes': t.mem_bytes} for t in node.outputs]
    spec = {'name': hw.name, 'chip_name': hw.chip_name, 'soc_version': hw.soc_version,
            'compute': asdict(hw.compute), 'memory': asdict(hw.memory),
            'vendor': hw.vendor, 'device_type': hw.device_type, 'borrowed_from': hw.borrowed_from}
    library = default_lib_dir()
    calibration_hash = None
    if library:
        calibration_hash = digest({str(p.relative_to(library)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(library.rglob('*.json'))})
    return {**values, 'outputs': tensors, 'hardware_spec': spec, 'hardware_hash': digest(spec),
            'engine': {**identity, 'calibration_hash': calibration_hash},
            'wall_time_ms': (time.monotonic() - started) * 1000}


def evaluate(request, root):
    identity, caps = engine_identity(root), capabilities()
    rows = []
    for hardware in request['hardware_ids']:
        for method in request['method_ids']:
            row = {'hardware': hardware, 'method': method, 'status': 'unsupported', 'result': None}
            key = hardware_key(hardware)
            reason = unavailable_reason(request, method, key, caps)
            if reason:
                row['reason'] = reason
            else:
                try:
                    row.update(status='succeeded', result=roofline(request['configuration'], key, identity))
                except Exception as exc:
                    row.update(status='failed', reason=f'评估失败（{type(exc).__name__}），请核对算子与硬件配置。')
            rows.append(row)
    return {'rows': rows, 'capabilities': caps}


def unavailable_reason(request, method, key, caps):
    if method == 'profile':
        return '尚未接入实测参考'
    if method in {'method3', 'method4'}:
        return '尚未配置评估组件'
    if method == 'tilesim':
        return caps['tilesim_reason']
    if not request['supported']:
        return '当前输入形式暂未适配评估'
    if key is None:
        return '当前方法未配置此硬件，或正式型号尚未确认'
    return None


def main():
    root = Path(sys.argv[1]).resolve()
    for path in (root, root / 'backend/train', root / 'tilesim'):
        sys.path.insert(0, str(path))
    # Upstream import-time diagnostics must not corrupt the JSON protocol.
    with contextlib.redirect_stdout(sys.stderr):
        request = json.load(sys.stdin)
        result = capabilities() if request.get('probe') else evaluate(request, root)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
