"""Validated, JSON-only input contract; independent of the optional engine."""
import hashlib
import json
import math

from catalog_data import all_hardware, catalog_payload
from fixtures import METHODS

BASIC = {'matmul', 'linear', 'bmm', 'flash_attention', 'layernorm', 'rms_norm',
         'swiglu', 'embedding', 'silu', 'gelu', 'softmax'}
ALIASES = {'ascend': 'Adevice03_Server', 'h100': 'H100_Server',
           'h200': 'H200_Server', 'b200': 'B200_Server', 'b300': 'B300_Server'}
BOUNDARY = 'operator performance model; no host or transfers; device kernel unspecified'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def selected_ids(value, allowed):
    if not isinstance(value, list) or not value or len(value) > len(allowed):
        raise ValueError('请至少选择一个有效比较项。')
    if any(not isinstance(x, str) or x not in allowed for x in value):
        raise ValueError('比较项不在内置目录中。')
    return list(dict.fromkeys(value))


def normalize_request(body):
    if not isinstance(body, dict) or not isinstance(body.get('configuration'), dict):
        raise ValueError('缺少算子配置。')
    catalog = catalog_payload()
    config = body['configuration']
    op = next((x for x in catalog['operators'] if x['id'] == config.get('operator_id')), None)
    if op is None:
        raise ValueError('未知算子模板。')
    inputs = config.get('inputs')
    if not isinstance(inputs, list) or len(inputs) != len(op['inputs']):
        raise ValueError('输入张量数量与模板不符。')
    tensors = [normalize_tensor(t, template, catalog['dtypes'])
               for t, template in zip(inputs, op['inputs'])]
    options = config.get('options', {})
    if not isinstance(options, dict) or options not in ({}, catalog['default_config']['options']):
        raise ValueError('当前评估不支持转置、非默认布局或累加精度选项。')
    canonical = {'operator_id': op['id'], 'operator': op['display_name'], 'key': op['key'],
                 'domain': op['domain'], 'inputs': tensors, 'options': options,
                 'boundary': BOUNDARY, 'source': op['source']}
    supported = op['id'] == 'demo:matmul' or (op['domain'] == 'train' and op['key'] in BASIC)
    if supported:
        validate_tensors(op['key'], tensors)
    hardware = selected_ids(body.get('hardware_ids'), {x['id'] for x in all_hardware(catalog)})
    methods = selected_ids(body.get('method_ids'), {x[0] for x in METHODS})
    return {'configuration': canonical, 'hardware_ids': hardware, 'method_ids': methods,
            'supported': supported, 'configuration_hash': digest(canonical)}


def normalize_tensor(tensor, template, dtypes):
    if not isinstance(tensor, dict):
        raise ValueError('张量配置格式错误。')
    shape, dtype = tensor.get('shape'), tensor.get('dtype')
    if (not isinstance(shape, list) or not 1 <= len(shape) <= 8 or
            any(type(d) is not int or not 1 <= d <= 1048576 for d in shape) or
            math.prod(shape) > 2 ** 40):
        raise ValueError('形状需要1至8个正整数维度，每维不超过1048576，总元素不超过2^40。')
    if dtype not in dtypes:
        raise ValueError('未知 dtype。')
    return {'name': template['name'], 'role': template['role'], 'shape': shape, 'dtype': dtype}


def validate_tensors(key, tensors):
    shapes = [t['shape'] for t in tensors]
    dtypes = [t['dtype'] for t in tensors]
    floats = dtypes[:1] if key == 'embedding' else dtypes
    if len(set(floats)) != 1 or floats[0] not in {'fp16', 'bf16', 'fp32'}:
        raise ValueError('当前模板支持一致的 FP16 / BF16 / FP32 浮点输入。')
    a = shapes[0]
    valid = True
    if key in {'matmul', 'linear', 'bmm'}:
        b = shapes[1]
        rank = 3 if key == 'bmm' else 2
        valid = len(a) == len(b) == rank
        if valid:
            valid = a[-1] == (b[-1] if key == 'linear' else b[-2])
            valid = valid and (key != 'bmm' or a[0] == b[0])
    elif key == 'flash_attention':
        valid = len(a) == 4 and all(s == a for s in shapes)
    elif key in {'rms_norm', 'layernorm'}:
        valid = len(a) == 2 and shapes[1] == [a[-1]]
    elif key == 'embedding':
        valid = len(a) == 2 and dtypes[1] in {'int32', 'int64'}
    elif key == 'swiglu':
        valid = len(a) == 2 and all(len(s) == 2 for s in shapes[1:])
        if valid:
            g, u, d = shapes[1:]
            valid = g == u and g[1] == a[1] and d == [a[1], g[0]]
    if not valid:
        raise ValueError('形状不符合当前评估模板；矩阵维度、权重或 Attention 的 BNSD 必须匹配。')


def hardware_key(identifier):
    if identifier in ALIASES:
        return ALIASES[identifier]
    catalog_ids = {x['id'] for x in catalog_payload()['hardware']}
    return identifier.removeprefix('modeling:') if identifier in catalog_ids else None
