"""Strict analytic Roofline for snapshotted operator assets; no dynamic eval."""
import ast
from functools import lru_cache
import json
import math
import operator
from pathlib import Path

from .bundled_roofline import DTYPE_BYTES, efficiency, hardware_catalog, peak

DATA = Path(__file__).with_name('data') / 'operator_specs.json'
OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)
ARITH = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
         ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv}
BYTES = {**DTYPE_BYTES, 'fp8': 1, 'int8': 1, 'bool': 1, 'uint8': 1, 'uint64': 8}
EXCLUDED = {'infer:START', 'infer:END', 'infer:MoeGatingTopK',
            'infer:QuantLightningIndexer', 'infer:SparseIndexSelect', 'infer:Embedding'}
UNIT_OVERRIDE = {
    'MatMulV3': 'cube', 'Linear': 'cube', 'MatMul': 'cube', 'TorchMm': 'cube',
    'ColumnParallelLinear': 'cube', 'RowParallelLinear': 'cube',
    'ColumnParallelLinearQuant': 'cube', 'MoEGate': 'cube',
    'SituAndMul': 'vector', 'DynamicQuant': 'vector', 'MoETopK': 'vector',
    'AddRMSNormQuant': 'vector', 'RMSNormGated': 'vector', 'RMSNormQuant': 'vector',
    'RopeComplex': 'vector', 'RopeInterLeave': 'vector',
    'TorchAdd': 'vector', 'TorchMul': 'vector', 'TorchSoftmax': 'vector',
    'TorchCumsum': 'vector', 'TorchSort': 'vector', 'TorchSum': 'vector',
}


@lru_cache(maxsize=1)
def asset_catalog():
    return json.loads(DATA.read_text())


def value(node, context):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in context: raise ValueError(f'缺少维度参数 {node.id}')
        return context[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        right = value(node.right, context)
        if right == 0 and isinstance(node.op, (ast.Div, ast.FloorDiv)):
            raise ValueError('维度公式除数为零')
        return ARITH[type(node.op)](value(node.left, context), right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = value(node.operand, context)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'min', 'max'}:
        if not 1 <= len(node.args) <= 4 or node.keywords: raise ValueError('不支持的公式参数')
        return (min if node.func.id == 'min' else max)(value(x, context) for x in node.args)
    raise ValueError('不支持的资产公式')


def positive_int(number, label, zero=False):
    if not isinstance(number, (float, int)) or not math.isfinite(number) or number != int(number):
        raise ValueError(f'{label} 不是整数')
    result = int(number)
    if not (0 if zero else 1) <= result <= 2 ** 40:
        raise ValueError(f'{label} 超出模型范围')
    return result


def shape(expression, context):
    node = ast.parse(str(expression), mode='eval').body
    terms = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    if not 1 <= len(terms) <= 8: raise ValueError('输出维度数量不合法')
    return [positive_int(value(term, context), '维度', zero=True) for term in terms]


def symbols(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} - {'min', 'max'}


def infer_symbol(node, expected, context, name):
    def equals(candidate):
        try: return value(node, {**context, name: candidate}) == expected
        except (ValueError, OverflowError, ZeroDivisionError): return False
    low, high = 1, 1048576
    while low <= high:
        middle = (low + high) // 2
        actual = value(node, {**context, name: middle})
        if actual == expected: return middle
        if actual < expected: low = middle + 1
        else: high = middle - 1
    raise ValueError(f'{name} 无法由输入形状推导')


def dimension_context(spec, config, defaults):
    templates = [*spec.get('inputs', []), *spec.get('params', [])]
    context = {**defaults, 'B': config['inputs'][0]['shape'][0],
               'batch_size': config['inputs'][0]['shape'][0], 'tp_size': 1, 'o_tp_size': 1}
    bound = {'B', 'batch_size', 'tp_size', 'o_tp_size'}
    equations = []
    for template, tensor in zip(templates, config['inputs']):
        parsed = ast.parse(str(template.get('shape', '[1]')), mode='eval').body
        terms = parsed.elts if isinstance(parsed, (ast.List, ast.Tuple)) else [parsed]
        if len(terms) != len(tensor['shape']): raise ValueError(f"{tensor['name']} 与资产维度数不一致")
        for term, dim in zip(terms, tensor['shape']):
            if isinstance(term, ast.Name):
                if term.id in bound and context[term.id] != dim: raise ValueError(f'维度 {term.id} 不一致')
                context[term.id] = dim; bound.add(term.id)
            else: equations.append((term, dim))
    for term, dim in equations:
        missing = symbols(term) - bound
        if len(missing) == 1:
            name = missing.pop(); context[name] = infer_symbol(term, dim, context, name); bound.add(name)
        elif len(missing) > 1 and value(term, context) != dim:
            raise ValueError(f"需要明确维度参数 {', '.join(sorted(missing))}")
        if value(term, context) != dim: raise ValueError('输入张量维度互相矛盾')
    context.update({'input_length': config['inputs'][0]['shape'][1] if len(config['inputs'][0]['shape']) > 1 else 1,
                    'phase': 'prefill', 'world_size': 1, 'dp_size': 1, 'pp_size': 1,
                    'cp_size': 1, 'ep_size': 1})
    return context


def resolve(config):
    catalog = asset_catalog(); entry = catalog['operators'].get(config['operator_id'])
    if entry is None or config['operator_id'] in EXCLUDED:
        raise ValueError('当前算子没有可验证的目录公式')
    spec = entry['spec']; inputs = config['inputs']
    templates = [*spec.get('inputs', []), *spec.get('params', [])]
    if len(inputs) != len(templates) or not spec.get('outputs'):
        raise ValueError('资产输入或输出定义不完整')
    if any(tensor['dtype'] != template.get('dtype') for tensor, template in zip(inputs, templates)):
        raise ValueError('此目录公式只验证资产原始 dtype；当前输入精度需单独适配')
    if not spec.get('compute_flops'):
        raise ValueError('资产没有 FLOPs 公式')
    context = dimension_context(spec, config, catalog['defaults'])
    output = []
    for item in spec['outputs']:
        dims = shape(item['shape'], context)
        dtype = item.get('dtype') or inputs[0]['dtype']
        if dtype not in BYTES: raise ValueError(f'输出 dtype {dtype} 缺少字节口径')
        output.append({'name': item.get('name') or 'output', 'shape': dims, 'dtype': dtype,
                       'bytes': math.prod(dims) * BYTES[dtype]})
    flops = {}
    for dtype, formula in spec['compute_flops'].items():
        flops[dtype] = positive_int(value(ast.parse(str(formula), mode='eval').body, context), 'FLOPs', zero=True)
    read = sum(math.prod(t['shape']) * BYTES[t['dtype']] for t in inputs)
    return spec, output, flops, read, sum(o['bytes'] for o in output)


def unsupported(config, hardware):
    try:
        spec, outputs, flops, read, write = resolve(config)
        hw = hardware_catalog()['hardware'][hardware]
        unit = unit_for(config, spec)
        if unit not in {'cube', 'vector'}: return '资产计算单元没有对应 Roofline 峰值'
        if any(flops[dtype] and peak(hw, unit, dtype) <= 0 for dtype in flops):
            return '硬件缺少算子公式所需精度/单元的峰值规格'
        if hw['memory']['hbm_bandwidth_gbps'] <= 0: return '硬件缺少 HBM 带宽规格'
        if not outputs or read + write <= 0: return '资产输出或字节工作量不完整'
    except (ValueError, KeyError, OverflowError) as exc:
        return str(exc)
    return None


def simulate(config, hardware):
    reason = unsupported(config, hardware)
    if reason: raise ValueError(reason)
    spec, outputs, flops, read, write = resolve(config)
    hw = hardware_catalog()['hardware'][hardware]
    total_flops = sum(flops.values()); total_bytes = read + write
    compute_eff = hw['compute']['compute_ratio']
    if compute_eff is None:
        compute_eff = efficiency(total_flops, ((1e9, .5), (1e10, .55), (1e11, .6), (math.inf, .5)))
    memory_eff = hw['memory']['bw_gmem_ratio']
    if memory_eff is None:
        memory_eff = efficiency(total_bytes, ((1e6, .4), (1e8, .7), (math.inf, .85)))
    compute_us = sum(amount / (peak(hw, unit_for(config, spec), dtype) * compute_eff) * 1e6
                     for dtype, amount in flops.items() if amount)
    memory_us = total_bytes / (hw['memory']['hbm_bandwidth_gbps'] * 1e9 * memory_eff) * 1e6
    return {'latency_us': max(compute_us, memory_us, 1e-3), 'compute_us': compute_us,
            'memory_us': memory_us, 'flops': total_flops, 'read_bytes': read,
            'write_bytes': write, 'arithmetic_intensity': total_flops / total_bytes,
            'bound': 'compute' if compute_us >= memory_us else 'memory',
            'backend': 'roofline', 'calibration_source': '', 'outputs': outputs,
            'hardware_spec': hw, 'model_note': '按目录公式和硬件峰值推导；不包含原 Kepler 的融合、静态开销或校准。',
            'upstream_revision': asset_catalog()['upstream_revision']}


def unit_for(config, spec):
    return spec.get('compute_unit') or UNIT_OVERRIDE.get(config['key'])
