"""Self-contained subset of modeling's uncalibrated Roofline backend."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

DATA = Path(__file__).with_name('data') / 'roofline_hardware.json'
DTYPE_BYTES = {'fp16': 2, 'bf16': 2, 'fp32': 4, 'int32': 4, 'int64': 8}
CUBE_OPS = {'matmul', 'linear', 'bmm', 'flash_attention'}
NPU_CUBE_EFF = {'matmul': .70, 'linear': .70, 'bmm': .64, 'flash_attention': .1486}
NPU_VECTOR_US_PER_MELEM = {'silu': 2.78, 'gelu': 4.51, 'softmax': 5.36, 'swiglu': 1.77}
NPU_NORM_US_PER_MELEM = {'layernorm': (9.2, 5.4), 'rms_norm': (6.8, 2.2)}
NPU_LATENCY_FLOOR = {'matmul': 1, 'linear': 1, 'bmm': 1, 'flash_attention': 0,
                     'silu': 1, 'gelu': 1.5, 'swiglu': 2, 'softmax': 3,
                     'layernorm': 4, 'rms_norm': 3, 'embedding': .5}
NPU_MEMORY_TIER_AWARE = {'embedding', 'silu', 'gelu', 'swiglu', 'softmax', 'layernorm', 'rms_norm'}


@dataclass(frozen=True)
class Tensor:
    name: str
    shape: tuple[int, ...]
    dtype: str

    @property
    def elements(self):
        return math.prod(self.shape)

    @property
    def bytes(self):
        return self.elements * DTYPE_BYTES[self.dtype]


def hardware_catalog():
    return json.loads(DATA.read_text())


def tensors(config):
    return [Tensor(t['name'], tuple(t['shape']), t['dtype']) for t in config['inputs']]


def output_for(key, items):
    a = items[0]
    if key == 'matmul':
        return Tensor('output', (*a.shape[:-2], a.shape[-2], items[1].shape[-1]), a.dtype)
    if key == 'linear':
        return Tensor('output', (*a.shape[:-1], items[1].shape[0]), a.dtype)
    if key == 'bmm':
        return Tensor('output', (a.shape[0], a.shape[1], items[1].shape[-1]), a.dtype)
    if key == 'embedding':
        return Tensor('output', (*items[1].shape, a.shape[-1]), a.dtype)
    return Tensor('output', a.shape, a.dtype)


def matrix_work(key, items, output):
    a, b = items[:2]; size = DTYPE_BYTES[a.dtype]
    if key == 'bmm':
        batch, m, k, n = a.shape[0], a.shape[1], a.shape[2], b.shape[2]
    elif key == 'linear':
        batch, m, k, n = 1, math.prod(a.shape[:-1]), a.shape[-1], b.shape[0]
    else:
        batch, m, k, n = math.prod(a.shape[:-2]) if len(a.shape) > 2 else 1, a.shape[-2], a.shape[-1], b.shape[-1]
    flops = 2.0 * batch * m * n * k
    read = batch * m * k * size + batch * k * n * size
    return flops, read, output.bytes


def attention_work(items, output):
    q, k = items[:2]; batch, heads, sq, dim = q.shape; sk = k.shape[2]
    flops = 4.0 * batch * heads * sq * sk * dim + 4.0 * batch * heads * sq * sk
    read = q.bytes + items[1].bytes + items[2].bytes
    return flops, read, output.bytes


def swiglu_work(items, output):
    hidden, gate, up, down = items; batch = math.prod(hidden.shape[:-1]); width = hidden.shape[-1]
    intermediate = max(gate.shape[0] if gate.shape[1] == width else gate.shape[1],
                       up.shape[0] if up.shape[1] == width else up.shape[1])
    flops = 6.0 * batch * width * intermediate + 5.0 * batch * intermediate
    read = (batch * width + 3 * intermediate * width) * DTYPE_BYTES[hidden.dtype]
    return flops, read, output.bytes


def vector_work(key, items, output):
    first = items[0]; count = first.elements; size = DTYPE_BYTES[first.dtype]
    if key == 'layernorm':
        return 7.0 * count, (count + 2 * first.shape[-1]) * size, output.bytes
    if key == 'rms_norm':
        return 6.0 * count, (count + first.shape[-1]) * size, output.bytes
    if key == 'embedding':
        index_bytes = items[1].bytes
        return 0.0, output.bytes * 2 + index_bytes, output.bytes
    factor = {'silu': 4.0, 'gelu': 4.0, 'softmax': 4.0}[key]
    return factor * output.elements, sum(t.bytes for t in items), output.bytes


def work(config):
    key, items = config['key'], tensors(config); output = output_for(key, items)
    if key in {'matmul', 'linear', 'bmm'}:
        values = matrix_work(key, items, output)
    elif key == 'flash_attention':
        values = attention_work(items, output)
    elif key == 'swiglu':
        values = swiglu_work(items, output)
    else:
        values = vector_work(key, items, output)
    return (*values, output)


def efficiency(value, thresholds):
    for limit, ratio in thresholds:
        if value < limit:
            return ratio
    return thresholds[-1][1]


def peak(spec, unit, dtype):
    suffix = 'tops' if dtype.startswith('int') or dtype in {'fp8', 'fp4'} else 'tflops'
    key = f'{dtype}_{suffix}'
    return float(spec['compute'][unit].get(key, 0)) * 1e12


def simulate(config, hardware):
    catalog = hardware_catalog(); spec = catalog['hardware'][hardware]
    flops, read_bytes, write_bytes, output = work(config)
    key = config['key']; is_adevice = hardware.startswith('Adevice03_')
    compute_eff = spec['compute']['compute_ratio']
    compute_eff = compute_eff if compute_eff is not None else efficiency(flops, ((1e9, .5), (1e10, .55), (1e11, .6), (math.inf, .5)))
    total_bytes = read_bytes + write_bytes
    memory_eff = spec['memory']['bw_gmem_ratio']
    memory_eff = memory_eff if memory_eff is not None else efficiency(total_bytes, ((1e6, .4), (1e8, .7), (math.inf, .85)))
    unit = 'cube' if key in CUBE_OPS else 'vector'
    throughput = peak(spec, unit, config['inputs'][0]['dtype']) * compute_eff
    compute_us = flops / throughput * 1e6 if throughput > 0 and flops > 0 else 0.0
    if is_adevice and key in NPU_CUBE_EFF and unit == 'cube':
        compute_us = flops / (peak(spec, unit, config['inputs'][0]['dtype']) * NPU_CUBE_EFF[key]) * 1e6
    if is_adevice and key in NPU_VECTOR_US_PER_MELEM:
        compute_us = NPU_VECTOR_US_PER_MELEM[key] * output.elements / 1e6
    if is_adevice and key in NPU_NORM_US_PER_MELEM:
        small, large = NPU_NORM_US_PER_MELEM[key]
        compute_us = (small if output.elements < 1_000_000 else large) * output.elements / 1e6
    memory_gbps = spec['memory']['hbm_bandwidth_gbps']
    if is_adevice and key in NPU_MEMORY_TIER_AWARE:
        eligible = [t for t in spec['memory']['tiers'] if t['capacity_mb'] > 0 and total_bytes <= t['capacity_mb'] * 1e6]
        if eligible:
            memory_gbps = max(t['bandwidth_gbps'] for t in eligible)
    bandwidth = memory_gbps * 1e9 * memory_eff
    memory_us = total_bytes / bandwidth * 1e6 if bandwidth > 0 else 0.0
    floor = NPU_LATENCY_FLOOR.get(key, 0) if is_adevice else 0
    latency_us = max(compute_us, memory_us, 1e-3, floor)
    bound = 'compute' if compute_us >= memory_us else 'memory'
    return {'latency_us': latency_us, 'compute_us': compute_us, 'memory_us': memory_us,
            'flops': flops, 'read_bytes': read_bytes, 'write_bytes': write_bytes,
            'arithmetic_intensity': flops / total_bytes if total_bytes else math.inf,
            'bound': bound, 'backend': 'roofline', 'calibration_source': '',
            'outputs': [{'name': output.name, 'shape': list(output.shape), 'dtype': output.dtype,
                         'bytes': output.bytes}], 'hardware_spec': spec,
            'upstream_revision': catalog['upstream_revision']}
