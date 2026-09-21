"""Copy tracked modeling catalog metadata, without importing its application."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess


def literal_assignment(path, name):
    for node in ast.parse(path.read_text()).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(node.value)
    raise ValueError(f'{name} not found in {path}')


def provenance(root, path):
    return {'path': str(path.relative_to(root)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def dimension(node, defaults):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.Name):
        return defaults[node.id]
    if isinstance(node, ast.BinOp):
        left, right = dimension(node.left, defaults), dimension(node.right, defaults)
        operations = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                      ast.Mult: lambda: left * right, ast.Div: lambda: left / right,
                      ast.FloorDiv: lambda: left // right}
        return operations[type(node.op)]()
    raise ValueError('Unsupported expression')


def tensor_template(tensor, role, defaults):
    expression = tensor.get('shape', '')
    nodes = ast.parse(str(expression), mode='eval').body
    nodes = nodes.elts if isinstance(nodes, (ast.List, ast.Tuple)) else [nodes]
    shape = []
    for node in nodes:
        try:
            value = dimension(node, defaults)
            shape.append(int(value) if value == int(value) and value > 0 else None)
        except (KeyError, ValueError, ZeroDivisionError, TypeError):
            shape.append(None)
    unknown = sorted({node.id for node in ast.walk(ast.parse(str(expression)))
                      if isinstance(node, ast.Name) and node.id not in defaults})
    return {'name': tensor['name'], 'role': role, 'shape': shape,
            'dtype': tensor.get('dtype', 'bf16'), 'expression': str(expression),
            'unresolved_dimensions': unknown}


def operator_entries(root, tracked):
    train_path = root / 'backend/web/services/train/op_sim.py'
    defaults = literal_assignment(root / 'backend/web/services/infer/operator_catalog.py', '_DIM_DEFAULTS')
    entries = []
    for op in literal_assignment(train_path, 'OP_CATALOG'):
        entries.append({'id': 'train:' + op['key'], 'key': op['key'], 'name': op['label'],
                        'domain': 'train', 'category': op['category'], 'op_type': op['op_type'],
                        'description': '', 'configurable': True, 'reason': None,
                        'inputs': [tensor_template(t, 'input', defaults) for t in op['input_template']],
                        'outputs': [], 'source': provenance(root, train_path)})
    families = literal_assignment(root / 'backend/infra/database/task_store_assets.py', 'OPERATOR_FAMILIES')
    base = 'backend/inference/data/operators/'
    paths = [p for family in families for p in sorted(tracked)
             if p.startswith(base + family + '/') and p.endswith('.json') and p.count('/') == 5]
    paths += [p for p in sorted(tracked) if p.startswith(base) and p.endswith('.json') and p.count('/') == 4]
    seen = set()
    for relative in paths:
        path = root / relative
        spec = json.loads(path.read_text())
        key = spec.get('name') or path.stem  # Match modeling's asset seeder, including legacy vision keys.
        if key in seen:
            continue
        seen.add(key)
        category = spec.get('category') or path.stem.split('_', 1)[0]
        communication = category.lower() == 'communication'
        entries.append({'id': 'infer:' + key, 'key': key, 'name': spec.get('name') or spec.get('op_name') or key,
                        'domain': 'infer', 'category': category, 'op_type': spec.get('op_type') or spec.get('type') or path.stem,
                        'description': spec.get('description', ''), 'configurable': not communication,
                        'reason': '通信算子 · 单算子入口未提供' if communication else None,
                        'inputs': [tensor_template(t, role, defaults) for field, role in [('inputs', 'input'), ('params', 'parameter')] for t in spec.get(field, [])],
                        'outputs': spec.get('outputs', []), 'source': provenance(root, path)})
    return entries


def hardware_entries(root, tracked):
    merged = {}
    for relative in sorted(tracked):
        if not re.fullmatch(r'backend/hardware/(train|infer)/[^/]+\.yaml', relative):
            continue
        path = root / relative
        # Read only plain top-level catalog scalars; never parse nested specs as equivalent.
        fields = dict(re.findall(r'^([a-z_]+):\s*([^\n]*)$', path.read_text(), re.M))
        domain = path.parent.name
        if fields.get('train_enable' if domain == 'train' else 'inference_enable', '1') != '1':
            continue
        name = fields['name']
        item = merged.setdefault(name, {'id': 'modeling:' + name, 'name': name,
                                       'family': fields.get('device_type', 'unknown').upper(),
                                       'vendor': fields.get('vendor', '').upper(),
                                       'chip': fields.get('chip_name'), 'group': 'modeling',
                                       'note': fields.get('label', name), 'profiles': {}})
        item['profiles'][domain] = {**provenance(root, path), 'label': fields.get('label', name)}
    return list(merged.values())


def snapshot(root):
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True).splitlines()
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    return {'schema': 'modeling-catalog-snapshot-v1', 'revision': revision,
            'scope': 'tracked built-in catalog; excludes user database and production overlays',
            'operators': operator_entries(root, tracked), 'hardware': hardware_entries(root, tracked)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modeling', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data/modeling-catalog.json')
    args = parser.parse_args()
    result = snapshot(args.modeling.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Saved {len(result['operators'])} operator entries and {len(result['hardware'])} hardware systems")
