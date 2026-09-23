"""Snapshot only public operator assets and dimension defaults, never task data."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
target = Path(__file__).resolve().parents[1] / 'opscope/evaluation/data/operator_specs.json'
catalog = json.loads((target.parents[3] / 'data/modeling-catalog.json').read_text())
source = root / 'backend/web/services/infer/operator_catalog.py'
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == '_DIM_DEFAULTS' for t in n.targets))
operators = {}
for op in catalog['operators']:
    if op['domain'] != 'infer' or not op['configurable']:
        continue
    path = root / op['source']['path']
    operators[op['id']] = {'spec': json.loads(path.read_text()), 'source': {
        'path': op['source']['path'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
payload = {'upstream_revision': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
           'defaults': ast.literal_eval(node.value), 'operators': operators}
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
