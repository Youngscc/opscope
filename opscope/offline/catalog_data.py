"""Standalone catalogue and honest empty result templates for configuration UI."""
import json
from pathlib import Path

from .fixtures import HARDWARE, METHODS


TEMPLATE_LABELS = {
    'demo:matmul': '二维矩阵 · A × B（示例）',
    'train:matmul': '矩阵相乘 · A × B',
    'infer:MatMul': '权重投影 · x / weight',
    'train:linear': '二维输入 · input / weight',
    'infer:Linear': '批量输入 · x / weight',
    'train:rms_norm': '输入 + weight',
    'infer:RmsNorm': '输入 + gamma · 含 rstd 输出',
    'train:swiglu': '融合投影 · hidden + 三组权重',
    'infer:SwiGlu': '逐元素门控 · x',
    'train:embedding': '权重表 + indices',
    'infer:Embedding': '索引输入 · x / indices',
}


def operator_groups(operators):
    """One visible operator per name; retain differing tensor contracts as templates."""
    groups = {}
    for op in operators:
        key = op['name'].casefold().replace('_', '')
        group = groups.setdefault(key, {'id': key, 'name': op['name'],
                                       'category': op['category'], 'variants': []})
        op['group_id'] = key
        op['display_name'] = group['name']
        op['public_id'] = f"{key}:template-{len(group['variants']) + 1}"
        op['template_label'] = TEMPLATE_LABELS.get(op['id'], '默认输入')
        group['variants'].append(op['id'])
    return list(groups.values())


def catalog_payload():
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads(root.joinpath('data/modeling-catalog.json').read_text())
    demo = {'id': 'demo:matmul', 'key': 'matmul', 'name': 'MatMul', 'domain': 'demo',
            'category': 'Linear', 'op_type': 'MatMul', 'configurable': True,
            'reason': None, 'description': '用于界面对比的合成示例配置。',
            'inputs': [{'name': name, 'role': 'input', 'shape': [4096, 4096],
                        'dtype': 'fp16', 'expression': '[M, K]' if name == 'A' else '[K, N]',
                        'unresolved_dimensions': []} for name in ('A', 'B')],
            'outputs': [], 'source': {'path': 'fixtures.py', 'sha256': None}}
    catalog['operators'].insert(0, demo)
    catalog['groups'] = operator_groups(catalog['operators'])
    catalog['dtypes'] = sorted({'bf16', 'fp16', 'fp32', 'fp8', 'int8', 'int32', 'int64'} |
                               {t['dtype'] for op in catalog['operators'] for t in op['inputs']})
    catalog['default_config'] = {
        'operator_id': demo['id'], 'operator': demo['name'], 'key': demo['key'],
        'domain': 'demo', 'inputs': [{key: tensor[key] for key in ('name', 'role', 'shape', 'dtype')}
                                    for tensor in demo['inputs']],
        'options': {'layout': 'row-major', 'accumulator_dtype': 'fp32',
                    'transpose_a': False, 'transpose_b': False},
        'source': demo['source'], 'boundary': 'device kernel only'}
    return catalog


def all_hardware(catalog):
    demo = [{'id': item[0], 'name': item[1], 'family': item[2], 'note': item[3],
             'group': 'demo', 'profiles': {}} for item in HARDWARE]
    tile = [{'id': f'tilesim:{soc}', 'name': f'Ascend {soc}', 'family': 'NPU',
             'note': 'TileSim 工程模型 · 独立芯片配置', 'group': 'tilesim', 'profiles': {}}
            for soc in ('910B1', '910B4')]
    return demo + catalog['hardware'] + tile


def pending_results(hardware):
    rows = []
    for device in hardware:
        for method in METHODS:
            reason = '尚未评估'
            rows.append({'id': f"demo-{device['id']}-{method[0]}", 'hardware': device['id'],
                         'method': method[0], 'available': False, 'synthetic': True,
                         'reason': reason, 'latency_us': None, 'deviation_percent': None,
                         'matrix': {'latency_width': None, 'error_position': None, 'error_label': '—', 'note': reason},
                         'task': {'task_id': None, 'run_id': None, 'status': 'not_run',
                                  'requested_method': method[0], 'actual_backend': None, 'source': None},
                         'hardware_snapshot': {'id': device['id'], 'name': device['name'],
                                               'status': 'not_captured', 'catalog_profiles': device['profiles']}})
    return rows
