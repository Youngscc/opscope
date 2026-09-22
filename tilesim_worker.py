"""Run the audited TileSim DSL path in an isolated interpreter and directory."""
import contextlib
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

from evaluation_contract import digest
from tilesim_contract import MAX_EVENTS, TILE_HARDWARE, TILING, unsupported


def setup():
    dist = importlib.metadata.distribution('msopmodeling')
    if dist.version != '1.0.9':
        raise ValueError('unverified engine version')
    root = Path(dist.locate_file('tilesim'))
    sys.path.insert(0, str(root))
    from ops.engineering_model.cube_op.matmul_l0 import EngMatmulL0
    import yaml
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob('*.py'))}
    return root, EngMatmulL0, yaml, {'name': 'tilesim', 'revision': dist.version,
                                  'mode': 'dsl-eng', 'source_hash': digest(files)}


def compact_events(trace, latency):
    if not isinstance(trace, dict) or not isinstance(trace.get('traceEvents'), list):
        raise ValueError('missing trace')
    events = trace['traceEvents']
    if not 0 < len(events) <= MAX_EVENTS:
        raise ValueError('trace event limit')
    result = []
    for event in events:
        ts, dur = event['ts'], event['dur']
        if any(not math.isfinite(v) for v in (ts, dur)) or ts < 0 or dur <= 0 or ts + dur > latency + 1e-6:
            raise ValueError('invalid event time')
        result.append({k: event[k] for k in ('name', 'ts', 'dur', 'pid', 'tid', 'ph')})
    return result


def run_one(config, hardware, engine):
    root, cls, yaml, identity = engine
    soc = TILE_HARDWARE[hardware]
    path = root / f'core/config/arc_config/{soc}/{soc}.yaml'
    spec = yaml.safe_load(path.read_text())
    core = spec['core_config']
    tensors = config['inputs']; a, b = (t['shape'] for t in tensors)
    dtype = tensors[0]['dtype']; dtype_name = {'fp16': 'FP16', 'bf16': 'BF16'}[dtype]
    inputs = {'input_shapes': [a, b], 'output_shapes': [[a[0], b[1]]],
              'input_dtypes': [dtype_name, dtype_name], 'output_dtypes': [dtype_name],
              'accelerator': str(path), 'aic_core_num': core['cube_core_num'],
              'aiv_core_num': core['vec_core_num'], 'extra_param': {'tuning_candidates': [dict(TILING)]}}
    start = time.monotonic()
    result = cls(cls.op_input_convert(inputs)).run()
    if not math.isfinite(result.latency) or result.latency <= 0:
        raise ValueError('invalid latency')
    raw = asdict(result)
    events = compact_events(result.trace, result.latency)
    raw.pop('trace')
    raw['small_pkt_transfer'] = {str(k): v for k, v in result.small_pkt_transfer.items()}
    flops = 2 * a[0] * a[1] * b[1]
    read, write = (math.prod(a) + math.prod(b)) * 2, a[0] * b[1] * 2
    # Include referenced CSVs as well as the chip YAML in the model identity.
    configs = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((root / 'core/config').rglob('*')) if p.is_file() and p.suffix in {'.yaml', '.csv'}}
    return {'backend': 'tilesim', 'latency_us': result.latency, 'compute_us': None,
            'memory_us': None, 'bound': None, 'calibration_source': None,
            'flops': flops, 'read_bytes': read, 'write_bytes': write, 'arithmetic_intensity': flops / (read + write),
            'outputs': [{'name': 'output', 'shape': [a[0], b[1]], 'dtype': dtype, 'bytes': write}],
            'hardware_spec': {'name': f'Ascend {soc}', 'chip_name': soc, 'soc_version': soc,
                              'model_spec': spec, 'memory': {}}, 'hardware_hash': digest({'soc': soc, 'configs': configs}),
            'engine': {**identity, 'config_hash': digest(configs)}, 'events': events,
            'tiling_input': dict(TILING), 'model_result': raw,
            'wall_time_ms': (time.monotonic() - start) * 1000}


def evaluate(request, engine):
    rows = []
    for hardware in request['hardware_ids']:
        reason = unsupported(request['configuration'], hardware)
        row = {'hardware': hardware, 'method': 'tilesim', 'status': 'unsupported', 'result': None, 'reason': reason}
        if not reason:
            try:
                row.update(status='succeeded', result=run_one(request['configuration'], hardware, engine))
            except Exception as exc:
                row.update(status='failed', reason=f'TileSim执行失败（{type(exc).__name__}）；未使用其他方法替代')
        rows.append(row)
    return {'rows': rows}


def main():
    with contextlib.redirect_stdout(sys.stderr):
        request = json.load(sys.stdin)
        engine = setup()
        result = {'tilesim': True, 'tilesim_installed': True, 'tilesim_version': '1.0.9',
                  'tilesim_hardware': list(TILE_HARDWARE), 'tilesim_reason': None} if request.get('probe') else evaluate(request, engine)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
