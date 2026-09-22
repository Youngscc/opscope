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

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if __package__:
    from .evaluation_contract import digest
    from .tilesim_contract import MAX_EVENTS, FA_TILING, TILING, hardware_mapping, unsupported
    from .tilesim_adapters import (CLASSIC_NAMES, THEORETICAL_NAMES, api_request,
                                   logical_work, model_inputs, model_note, operator_kind,
                                   legacy_flash_attention, normalize_legacy)
else:
    from evaluation_contract import digest
    from tilesim_contract import MAX_EVENTS, FA_TILING, TILING, hardware_mapping, unsupported
    from tilesim_adapters import (CLASSIC_NAMES, THEORETICAL_NAMES, api_request,
                                  logical_work, model_inputs, model_note, operator_kind,
                                  legacy_flash_attention, normalize_legacy)


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


def run_model(config, path, core, cls):
    soc = path.stem
    kind = operator_kind(config)
    if kind in {'flash_attention', 'flash_attention_score'} and soc == 'H200':
        result = legacy_flash_attention(config, path)
        return result['latency'], normalize_legacy(result), [], 'cost-eng', result
    if kind in CLASSIC_NAMES:
        from api.operator_api.op_latency_predict_engineering import op_latency_predict
        result = op_latency_predict(api_request(config, path))
        if 'error' in result:
            raise ValueError(result['error'])
        return result['latency'], normalize_legacy(result), [], 'cost-eng', result
    if kind in THEORETICAL_NAMES:
        from api.operator_api.op_latency_predict import op_latency_predict
        result, _hints = op_latency_predict(api_request(config, path, theoretical=True))
        if 'error' in result:
            raise ValueError(result['error'])
        return result['latency'], normalize_legacy(result), [], 'cost-theo', result
    mode = 'dsl-eng' if soc in {'910B1', '910B4'} else 'dsl-theo'
    if mode == 'dsl-theo':
        from ops.theoretical_model.cube_op.matmul import TheoMatMul
        cls = TheoMatMul
    elif kind in {'flash_attention', 'flash_attention_score'}:
        from ops.engineering_model.cv_fused_op.flash_attention_single_task import EngFlashAttention
        cls = EngFlashAttention
    inputs = model_inputs(config, path, core)
    if mode == 'dsl-theo':
        inputs.pop('extra_param')
    from core.backend.tile_op_costmodel.tile_op_registry import reset_tile_op_cache
    reset_tile_op_cache()
    result = cls(cls.op_input_convert(inputs)).run()
    raw = asdict(result); raw.pop('trace')
    raw['small_pkt_transfer'] = {str(k): v for k, v in result.small_pkt_transfer.items()}
    events = compact_events(result.trace, result.latency) if mode == 'dsl-eng' else []
    if mode == 'dsl-theo':
        # These fields are dataclass defaults; the theoretical evaluator does not populate them.
        for key in ('aic_cycles', 'aiv_cycles', 'l2_access_rate', 'aic_mte1_time'):
            raw[key] = None
    return result.latency, raw, events, mode, None


def run_one(config, hardware, engine):
    root, cls, yaml, identity = engine
    mapping = hardware_mapping(hardware); soc = mapping['model']
    path = root / f'core/config/arc_config/{soc}/{soc}.yaml'
    spec = yaml.safe_load(path.read_text())
    start = time.monotonic()
    latency, raw, events, mode, api_result = run_model(config, path, spec['core_config'], cls)
    if not math.isfinite(latency) or latency <= 0:
        raise ValueError('invalid latency')
    work = logical_work(config)
    configs = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((root / 'core/config').rglob('*')) if p.is_file() and p.suffix in {'.yaml', '.csv'}}
    tiling = FA_TILING if operator_kind(config) in {'flash_attention', 'flash_attention_score'} else TILING
    return {'backend': 'tilesim', 'latency_us': latency, 'compute_us': None,
            'memory_us': None, 'bound': None, 'calibration_source': None, **work,
            'arithmetic_intensity': work['flops'] / (work['read_bytes'] + work['write_bytes']),
            'hardware_spec': {'name': f'TileSim {soc}', 'chip_name': soc, 'soc_version': soc,
                              'model_spec': spec, 'memory': {}, **mapping},
            'hardware_hash': digest({'soc': soc, 'configs': configs}),
            'engine': {**identity, 'mode': mode, 'config_hash': digest(configs)}, 'events': events,
            'tiling_input': dict(tiling) if mode == 'dsl-eng' else {}, 'model_result': raw,
            'model_note': model_note(config),
            'api_placeholder_fields': ['gm_volume', 'ideal_time_by_mem', 'ideal_time_by_cube', 'ideal_time_by_vec', 'ideal_ratio'] if api_result else [],
            'api_result': api_result, 'wall_time_ms': (time.monotonic() - start) * 1000}


def evaluate(request, engine, on_row=None):
    rows = []
    for hardware in request['hardware_ids']:
        reason = unsupported(request['configuration'], hardware)
        row = {'hardware': hardware, 'method': 'tilesim', 'status': 'unsupported', 'result': None, 'reason': reason}
        if not reason:
            if on_row:
                on_row({**row, 'status': 'running', 'reason': '正在评估…'})
            try:
                row.update(status='succeeded', result=run_one(request['configuration'], hardware, engine))
            except Exception as exc:
                row.update(status='failed', reason=f'TileSim执行失败（{type(exc).__name__}）；未使用其他方法替代')
        rows.append(row)
        if on_row:
            on_row(row)
    return {'rows': rows}


def main():
    output = sys.stdout
    def emit(row):
        print(json.dumps({'row': row}, ensure_ascii=False, allow_nan=False), file=output, flush=True)
    with contextlib.redirect_stdout(sys.stderr):
        request = json.load(sys.stdin)
        engine = setup()
        result = {'tilesim': True, 'tilesim_installed': True, 'tilesim_version': '1.0.9',
                  'tilesim_hardware': ['910B1', '910B4', 'H200', 'GB200', 'R200'], 'tilesim_reason': None} if request.get('probe') else evaluate(request, engine, emit if request.get('_stream') else None)
    print(json.dumps({'done': True} if request.get('_stream') else result, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
