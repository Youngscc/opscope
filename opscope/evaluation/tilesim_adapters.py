"""Versioned TileSim operator adapters; every mapping preserves its assumptions."""
import math

if __package__:
    from .tilesim_contract import FA_TILING, TILING, OPERATOR_KINDS
else:
    from tilesim_contract import FA_TILING, TILING, OPERATOR_KINDS

CLASSIC_NAMES = {'bmm': 'BatchMatMulV2', 'layernorm': 'LayerNormV3',
                 'layernorm_v4': 'LayerNormV3', 'rmsnorm': 'RmsNorm',
                 'gemma_rmsnorm': 'RmsNorm', 'add_rmsnorm': 'AddRmsNorm',
                 'swish': 'Swish', 'gelu': 'Gelu', 'softmax': 'Softmax',
                 'mul': 'Mul', 'add': 'Add', 'gather': 'GatherV2',
                 'dynamic_quant': 'DynamicQuant', 'moe_topk': 'MoeGatingTopK',
                 'transpose_bmm': 'TransposeBatchMatMul'}
THEORETICAL_NAMES = {'sigmoid': 'Sigmoid', 'swiglu': 'Swiglu', 'cast': 'Cast'}
DTYPE_BYTES = {'bool': 1, 'int8': 1, 'uint8': 1, 'fp8': 1, 'fp16': 2,
               'bf16': 2, 'int32': 4, 'fp32': 4, 'int64': 8, 'uint64': 8}
ENG_DTYPES = {'bf16': 'DT_BF16', 'fp16': 'FLOAT16', 'fp32': 'FLOAT',
              'fp8': 'INT8', 'int8': 'INT8', 'int32': 'INT32',
              'int64': 'INT64', 'uint64': 'UINT64', 'bool': 'BOOL'}
THEO_DTYPES = {'bf16': 'BF16', 'fp16': 'FP16', 'fp32': 'FP32', 'fp8': 'INT8',
               'int8': 'INT8', 'int32': 'INT32', 'int64': 'INT64', 'bool': 'BOOL'}


def operator_kind(config):
    return OPERATOR_KINDS.get(config['operator_id'])


def flatten(shape):
    return [math.prod(shape[:-1]), shape[-1]] if len(shape) > 2 else list(shape)


def tensor(name, shape, dtype):
    return {'name': name, 'shape': list(shape), 'dtype': dtype,
            'bytes': math.prod(shape) * DTYPE_BYTES[dtype]}


def matmul_shapes(config):
    kind = operator_kind(config)
    a, b = (t['shape'] for t in config['inputs'][:2])
    if kind == 'linear':
        a, b = flatten(a), [b[-1], b[-2]]
    return list(a), list(b)


def output_tensors(config):
    kind = operator_kind(config); ts = config['inputs']; dtype = ts[0]['dtype']; shapes = [t['shape'] for t in ts]
    if kind in {'matmul', 'linear'}:
        a, b = matmul_shapes(config); return [tensor('output', [a[0], b[1]], dtype)]
    if kind == 'bmm':
        a, b = shapes[:2]; return [tensor('output', [a[0], a[1], b[2]], dtype)]
    if kind == 'flash_attention': return [tensor('output', shapes[0], dtype)]
    if kind == 'flash_attention_score':
        b, n, s, d = shapes[0]
        return [tensor('softmax_max', [b, n, s, 8], 'fp32'),
                tensor('softmax_sum', [b, n, s, 8], 'fp32'),
                tensor('softmax_out', [0, 0, 0, 0], dtype),
                tensor('attention_out', [b, n, s, d], dtype)]
    if kind in {'layernorm', 'layernorm_v4'}:
        x = shapes[0]; rows = math.prod(x[:-1]); return [tensor('y', x, dtype), tensor('mean', [rows, 1], 'fp32'), tensor('rstd', [rows, 1], 'fp32')]
    if kind in {'rmsnorm', 'gemma_rmsnorm'}:
        x = shapes[0]; return [tensor('y', x, dtype), tensor('rstd', [math.prod(x[:-1]), 1], 'fp32')]
    if kind == 'add_rmsnorm':
        x = shapes[0]; return [tensor('y', x, dtype), tensor('rstd', [math.prod(x[:-1]), 1], 'fp32'), tensor('residual', x, dtype)]
    if kind == 'swiglu':
        x = shapes[0]; return [tensor('output', [*x[:-1], x[-1] // 2], dtype)]
    if kind == 'gather':
        weight, indices = shapes; return [tensor('output', [*indices, weight[-1]], dtype)]
    if kind == 'cast': return [tensor('output', shapes[0], 'fp32')]
    if kind == 'dynamic_quant':
        x = shapes[0]; return [tensor('output', x, 'int8'), tensor('scale', x[:-1], 'fp32')]
    if kind == 'moe_topk':
        x = shapes[0]; return [tensor('scores', [x[0], 8], dtype),
                               tensor('expert_idx', [x[0], 8], 'int32'),
                               tensor('normalized_scores', x, 'fp32')]
    if kind == 'transpose_bmm':
        a, b = shapes[:2]; return [tensor('output', [a[0], a[1], b[2]], dtype)]
    return [tensor('output', shapes[0], dtype)]


def model_shapes(config):
    kind = operator_kind(config); shapes = [list(t['shape']) for t in config['inputs']]
    outputs = [o['shape'] for o in output_tensors(config)]
    if kind in {'matmul', 'linear'}:
        a, b = matmul_shapes(config); return [a, b], [outputs[0]]
    if kind in {'layernorm', 'layernorm_v4'}:
        x = flatten(shapes[0]); return [x, [x[-1]], [x[-1]]], [x, [x[0], 1], [x[0], 1]]
    if kind in {'rmsnorm', 'gemma_rmsnorm'}:
        x = flatten(shapes[0]); return [x, [x[-1]]], [x, [x[0], 1]]
    if kind == 'add_rmsnorm':
        x = flatten(shapes[0]); return [x, flatten(shapes[1]), [x[-1]]], [x, [x[0], 1], x]
    if kind in {'swish', 'gelu', 'softmax', 'sigmoid', 'swiglu', 'cast'}:
        x = flatten(shapes[0]); return [x], [flatten(outputs[0])]
    if kind in {'mul', 'add'}:
        return [flatten(s) for s in shapes], [flatten(outputs[0])]
    if kind == 'gather':
        return [shapes[0], [math.prod(shapes[1])]], [[math.prod(shapes[1]), shapes[0][-1]]]
    if kind in {'dynamic_quant', 'moe_topk', 'transpose_bmm'}:
        return shapes, outputs
    return shapes, outputs


def tile_dtypes(config, theoretical=False):
    kind = operator_kind(config); table = THEO_DTYPES if theoretical else ENG_DTYPES
    dtypes = [t['dtype'] for t in config['inputs']]
    if kind in {'layernorm', 'layernorm_v4'}: dtypes = [dtypes[0]] * 3
    output = [o['dtype'] for o in output_tensors(config)]
    return [table[d] for d in dtypes], [table[d] for d in output]


def api_request(config, path, theoretical=False):
    kind = operator_kind(config); inputs, outputs = model_shapes(config)
    input_dtypes, output_dtypes = tile_dtypes(config, theoretical)
    name = (THEORETICAL_NAMES if theoretical else CLASSIC_NAMES)[kind]
    request = {'op_name': name, 'accelerator': str(path), 'input_shapes': inputs,
               'output_shapes': outputs, 'input_precision': input_dtypes,
               'output_precision': output_dtypes}
    if theoretical: request['backend_type'] = 'theo'
    return request


def model_inputs(config, path, core):
    shapes = [t['shape'] for t in config['inputs']]; dtype = config['inputs'][0]['dtype'].upper()
    fa = operator_kind(config) in {'flash_attention', 'flash_attention_score'}
    if not fa: shapes = list(matmul_shapes(config))
    output = shapes[0] if fa else [shapes[0][0], shapes[1][1]]
    args = {'accelerator': str(path), 'input_shapes': shapes, 'output_shapes': [output],
            'input_dtypes': [dtype] * len(shapes), 'output_dtypes': [dtype],
            'aic_core_num': core['cube_core_num'], 'aiv_core_num': core['vec_core_num']}
    if fa:
        b, n, s, d = shapes[0]; args['input_dict'] = {'B': b, 'N': n, 'S1': s, 'S2': s, 'D1': d, 'D2': d, 'DTYPE': dtype}
    args['extra_param'] = {'tuning_candidates': [dict(FA_TILING if fa else TILING)]}
    return args


def logical_work(config):
    kind = operator_kind(config); inputs = config['inputs']; outputs = output_tensors(config)
    shapes = [t['shape'] for t in inputs]; elements = math.prod(shapes[0])
    if kind in {'matmul', 'linear'}:
        a, b = matmul_shapes(config); flops, formula = 2 * a[0] * a[1] * b[1], '2 × M × N × K'
    elif kind == 'bmm':
        a, b = shapes[:2]; flops, formula = 2 * a[0] * a[1] * a[2] * b[2], '2 × B × M × N × K'
    elif kind in {'flash_attention', 'flash_attention_score'}:
        b, n, s, d = shapes[0]; flops, formula = b * n * s * s * (4 * d + 4), 'B × N × S² × (4D + 4)'
    elif kind == 'transpose_bmm':
        a, b = shapes[:2]; flops, formula = 2 * a[0] * a[1] * a[2] * b[2], '2 × B × M × N × K'
    else:
        factor = {'layernorm': 5, 'layernorm_v4': 5, 'rmsnorm': 4, 'gemma_rmsnorm': 5,
                  'add_rmsnorm': 5, 'swish': 4, 'gelu': 8, 'softmax': 5, 'mul': 1,
                  'add': 1, 'sigmoid': 4, 'swiglu': 5, 'gather': 0, 'cast': 0,
                  'dynamic_quant': 2, 'moe_topk': 1}[kind]
        flops, formula = elements * factor, f'{factor} × 元素数' if factor else '数据搬运模型'
    read_bytes = sum(math.prod(t['shape']) * DTYPE_BYTES[t['dtype']] for t in inputs)
    write_bytes = sum(o['bytes'] for o in outputs)
    return {'flops': flops, 'read_bytes': read_bytes, 'write_bytes': write_bytes,
            'formula': formula, 'outputs': outputs}


def model_note(config):
    kind = operator_kind(config)
    if kind in {'flash_attention', 'flash_attention_score'}: return 'FA 模型将 B×N 合入查询维度；中间精度和缓存复用采用引擎内置假设。'
    if kind == 'moe_topk': return '当前目录未暴露 top_k 标量；按目录默认 top_k=8 建模。'
    if kind == 'layernorm': return '当前模板未提供 beta；适配器补充零 beta，TileSim 仍按完整 affine LayerNorm 的数据路径估算。'
    if kind == 'layernorm_v4': return '当前模板未提供 gamma/beta 数值；适配器按单位 gamma、零 beta 的完整 LayerNorm 数据路径估算。'
    if kind == 'gemma_rmsnorm': return 'TileSim 使用普通 RMSNorm 成本模型；Gemma 的 gamma+1 额外逐元素加法计入逻辑工作量，未单独进入模型流水。'
    if kind == 'gather': return '训练 Embedding 按 axis=0 的 GatherV2 建模；索引展平不改变查表元素数。'
    return None


def legacy_flash_attention(config, path):
    from api.operator_api.op_latency_predict_engineering import op_latency_predict
    tensors = config['inputs']; dtype = ENG_DTYPES[tensors[0]['dtype']]
    result = op_latency_predict({'op_name': 'FlashAttention', 'accelerator': str(path),
                                 'input_shapes': [t['shape'] for t in tensors],
                                 'output_shapes': [tensors[0]['shape']],
                                 'input_precision': [dtype] * 3, 'output_precision': [dtype],
                                 'extra_param': {'layout': 'BNSD'}})
    if 'error' in result:
        raise ValueError('TileSim engineering API failed')
    return result


def normalize_legacy(result):
    keys = {'CUBE': 'aic_cube_time', 'MTE1': 'aic_mte1_time', 'MTE2': 'aic_mte2_time',
            'FIXPIPE': 'aic_fixpipe_time', 'VEC': 'aiv_vec_time',
            'MTE2_AIV': 'aiv_mte2_time', 'MTE3': 'aiv_mte3_time'}
    values = {target: result['component_latency'].get(source) for source, target in keys.items()}
    transfers = {k: v * (2 if k == 'L1_cache' else 1) for k, v in result['mem_volume'].items()}
    # Engineering API's CUBE workload is a rate, not a cycle count.
    return {**values, 'aic_cycles': None,
            'aiv_cycles': result['compute_workload'].get('VEC'),
            'l2_access_rate': result.get('l2_hit_rate'), 'data_transfer': transfers,
            'tuning_result': result.get('tiling_info', {})}
