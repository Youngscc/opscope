"""Explicit mappings and bounded inputs for the installed TileSim models."""
import math

if __package__:
    from .evaluation_contract import hardware_key
else:
    from evaluation_contract import hardware_key

TILE_HARDWARE = {'tilesim:910B1': '910B1', 'tilesim:910B4': '910B4'}
# Matches the external backend's HW_INFO_MAPPING; matching is never a SKU certification.
CHIP_MODELS = {'Adevice03': '910B4', 'H100': 'H200', 'H200': 'H200',
               'B200': 'GB200', 'B300': 'H200', 'R200': 'R200'}
TILING = {'tm': 128, 'tn': 256, 'tk1': 512, 'tk0': 128}
FA_TILING = {'t_s1c': 256, 't_s1v': 128, 't_d1': 128, 't_d2': 128,
             't_dv': 128, 't_s2c': 128, 't_s2v': 128, 'n_s2': 2}
MAX_EVENTS = 80000
MAX_MODEL_ELEMENTS = 2 ** 30
OPERATOR_KINDS = {
    'demo:matmul': 'matmul', 'train:matmul': 'matmul', 'infer:TorchMm': 'matmul',
    'train:linear': 'linear', 'infer:MatMulV3': 'linear', 'train:bmm': 'bmm',
    'train:flash_attention': 'flash_attention', 'infer:FlashAttentionScore': 'flash_attention_score',
    'train:layernorm': 'layernorm', 'infer:LayerNormV4': 'layernorm_v4',
    'train:rms_norm': 'rmsnorm', 'infer:RmsNorm': 'rmsnorm',
    'infer:GemmaRmsNorm': 'gemma_rmsnorm', 'infer:AddRmsNorm': 'add_rmsnorm',
    'train:silu': 'swish', 'train:gelu': 'gelu', 'train:softmax': 'softmax',
    'infer:TorchSoftmax': 'softmax', 'infer:Mul': 'mul', 'infer:TorchMul': 'mul',
    'infer:TorchAdd': 'add', 'infer:Sigmoid': 'sigmoid', 'infer:SwiGlu': 'swiglu',
    'train:embedding': 'gather', 'infer:Cast': 'cast',
    'infer:DynamicQuant': 'dynamic_quant', 'infer:MoeGatingTopK': 'moe_topk',
    'infer:TransposeBatchMatMul': 'transpose_bmm',
}


def hardware_mapping(hardware):
    chip = TILE_HARDWARE.get(hardware) or (hardware_key(hardware) or '').split('_')[0]
    model = TILE_HARDWARE.get(hardware) or CHIP_MODELS.get(chip)
    return {'requested_chip': chip, 'model': model,
            'borrowed_from': model if model and model != chip else None}


def unsupported(config, hardware):
    model = hardware_mapping(hardware)['model']
    if model is None:
        return 'TileSim 缺少此硬件的配置映射'
    kind = OPERATOR_KINDS.get(config['operator_id'])
    if kind is None:
        return missing_contract_reason(config)
    inputs = config['inputs']
    dtypes = {t['dtype'] for t in inputs}
    if model not in {'910B1', '910B4'} and 'bf16' in dtypes:
        return f'TileSim 的 {model} 配置缺少 BF16 计算/向量参数；未改用 FP16'
    if kind in {'flash_attention', 'flash_attention_score'}:
        if len(inputs) != 3 or any(len(t['shape']) != 4 or t['shape'] != inputs[0]['shape'] for t in inputs):
            return 'FlashAttention 需要相同 BNSD 形状的 Q / K / V'
        if any(d is None for d in inputs[0]['shape']):
            return 'FlashAttention 的 BNSD 维度必须全部填写'
        if len(dtypes) != 1 or not dtypes <= {'fp16', 'bf16'}:
            return 'TileSim FlashAttention 支持一致的 FP16 / BF16 输入'
        if model in {'GB200', 'R200'}:
            return f'TileSim 的 {model} 配置缺少 FA 工程模式需要的 UB / L0 存储参数'
        b, n, s, d = inputs[0]['shape']
        estimate = math.ceil(b * n * s / 256) * math.ceil(s / 256) * math.ceil(d / 128) * 150
        if estimate > MAX_EVENTS:
            return 'TileSim FA 流水规模超过本地上限，请缩小形状'
        return None
    if any(math.prod(t['shape']) > MAX_MODEL_ELEMENTS for t in inputs):
        return 'TileSim 输入规模超过本地模型上限'
    if kind in {'matmul', 'linear'}:
        return matrix_reason(config, model)
    if kind == 'bmm':
        a, b = inputs[:2]
        if len(a['shape']) != 3 or len(b['shape']) != 3 or a['shape'][0] != b['shape'][0] or a['shape'][2] != b['shape'][1]:
            return 'TileSim BMM 需要批次相同且 K 维匹配的三维输入'
    if kind == 'transpose_bmm':
        a, b = inputs[:2]
        if len(a['shape']) != 3 or len(b['shape']) != 3 or a['shape'][0] != b['shape'][0] or a['shape'][2] != b['shape'][1]:
            return 'TransposeBatchMatMul 需要批次相同且 K 维匹配的三维输入'
    if kind in {'layernorm', 'rmsnorm', 'gemma_rmsnorm'}:
        if inputs[0]['shape'][-1] != inputs[1]['shape'][-1]:
            return '归一化权重长度必须等于输入最后一维'
    if kind == 'add_rmsnorm' and (inputs[0]['shape'] != inputs[1]['shape'] or inputs[0]['shape'][-1] != inputs[2]['shape'][-1]):
        return 'AddRmsNorm 的两个输入和 gamma 维度必须匹配'
    if kind == 'swiglu' and inputs[0]['shape'][-1] % 2:
        return 'SwiGLU 输入最后一维必须能平均拆成 gate 和 up'
    if kind == 'moe_topk' and (len(inputs[0]['shape']) != 2 or inputs[0]['shape'][1] < 8):
        return 'MoeGatingTopK 需要二维分数输入且专家数不少于默认 top_k=8'
    floats = [t['dtype'] for t in inputs if t['dtype'] not in {'int32', 'int64'}]
    if not floats or len(set(floats)) != 1 or floats[0] not in {'fp16', 'bf16', 'fp32'}:
        return 'TileSim 此算子需要一致的 FP16 / BF16 / FP32 浮点输入'
    return None


def matrix_reason(config, model):
    kind = OPERATOR_KINDS[config['operator_id']]
    a, b = config['inputs'][:2]
    a_shape, b_shape = a['shape'], b['shape']
    if len(a_shape) != 2 or len(b_shape) != 2:
        return 'TileSim MatMul / Linear 当前需要二维输入'
    k_b = b_shape[-1] if kind == 'linear' else b_shape[0]
    n = b_shape[0] if kind == 'linear' else b_shape[1]
    if a_shape[1] != k_b:
        return 'TileSim MatMul / Linear 的 K 维必须匹配'
    if a['dtype'] != b['dtype'] or a['dtype'] not in {'fp16', 'bf16'}:
        return 'TileSim MatMul / Linear 支持一致的 FP16 / BF16 输入'
    if model in {'GB200', 'R200'}:
        return f'TileSim 的 {model} 配置缺少理论模式需要的 L0C → L2 带宽参数'
    m, k = a_shape
    if any(d < 128 or d % 128 for d in (m, n, k)):
        return 'TileSim 当前已验证维度为128的倍数；尾块暂未开放'
    estimate = math.ceil(m / 128) * math.ceil(n / 256) * (math.ceil(k / 512) * 14 + 1)
    if estimate > MAX_EVENTS:
        return 'TileSim 流水规模超过本地上限，请缩小矩阵形状'
    return None


def missing_contract_reason(config):
    key = config['key'].lower()
    if key in {'cumsum', 'torchcumsum', 'transpose', 'gatherv2'}:
        return 'TileSim 模型存在，但当前配置缺少 axis / perm 的实际值'
    if 'groupedmatmul' in key or 'moegatingtopk' in key:
        return 'TileSim 模型存在，但当前配置缺少 group_list / top_k 等运行值'
    if key in {'cast', 'dynamicquantv2', 'quantbatchmatmulv3'}:
        return 'TileSim 模型存在，但当前模板缺少目标 dtype、量化参数或完整输入'
    if key == 'swiglu':
        return '当前模板是融合 SwiGLU MLP，不等同于 TileSim 的 SwiGLU 激活'
    return 'TileSim 未提供与当前算子边界等价且已验证的模型'
