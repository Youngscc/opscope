"""Conservative scope for the audited standalone DSL engine."""
import math

TILE_HARDWARE = {'tilesim:910B1': '910B1', 'tilesim:910B4': '910B4'}
TILING = {'tm': 128, 'tn': 256, 'tk1': 512, 'tk0': 128}
MAX_EVENTS = 80000


def unsupported(config, hardware):
    if hardware not in TILE_HARDWARE:
        return 'TileSim 当前支持 Ascend 910B1 / 910B4；未借用其他芯片配置'
    if config['operator_id'] not in {'demo:matmul', 'train:matmul'}:
        return 'TileSim 当前已适配二维 MatMul；其他算子尚未验证'
    inputs = config['inputs']
    if len(inputs) != 2 or any(len(t['shape']) != 2 for t in inputs):
        return 'TileSim 需要两个二维矩阵'
    a, b = inputs
    if a['dtype'] != b['dtype'] or a['dtype'] not in {'fp16', 'bf16'}:
        return 'TileSim 当前支持一致的 FP16 / BF16 输入'
    m, k = a['shape']; bk, n = b['shape']
    if k != bk or any(d < 128 or d % 128 for d in (m, n, k)):
        return 'TileSim 当前已验证维度为128的倍数；尾块暂未开放'
    estimate = math.ceil(m / 128) * math.ceil(n / 256) * (math.ceil(k / 512) * 14 + 1)
    if estimate > MAX_EVENTS:
        return 'TileSim 流水规模超过本地上限，请缩小矩阵形状'
    return None
