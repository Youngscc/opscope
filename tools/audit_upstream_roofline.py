"""Read-only control: run modeling's single-operator helpers without its database."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from opscope.evaluation.evaluation_contract import normalize_request
from tools.audit_evaluations import default_config


def load_helpers(root):
    # Importing op_sim directly initializes the application's job store.
    # Compile only its pure model/context builders, unchanged from the source.
    sys.path.insert(0, str(root))
    from backend.inference.kepler.engine.chips.config import AIChipConfig
    from backend.inference.kepler.engine.common.model_config import ModelConfig
    from backend.inference.kepler.engine.executor import execute_model
    source = root / 'backend/web/services/infer/op_sim.py'
    names = {'_shape_nodes', '_bind_dimensions', '_build_context', '_tensor_payload', '_build_model'}
    nodes = [n for n in ast.parse(source.read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name in names
             or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_DTYPE_BYTES' for t in n.targets)]
    catalog = root / 'backend/web/services/infer/operator_catalog.py'
    assignment = next(n for n in ast.parse(catalog.read_text()).body
                      if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_DIM_DEFAULTS' for t in n.targets))
    defaults = ast.literal_eval(assignment.value)
    ns = {'ast': ast, 'ModelConfig': ModelConfig, 'TaskDomainError': ValueError,
          'default_dimension_context': lambda: defaults.copy()}
    code = 'from __future__ import annotations\n' + '\n\n'.join(ast.unparse(n) for n in nodes)
    exec(compile(code, str(source), 'exec'), ns)
    return ns, AIChipConfig, execute_model


def probe(op, hardware, root, helpers):
    row = {'operator_id': op['id'], 'hardware': hardware, 'source': op['source']['path']}
    try:
        normalize_request({'configuration': default_config(op), 'hardware_ids': ['h200'], 'method_ids': ['roofline']})
    except ValueError as exc:
        return {**row, 'status': 'blocked_input', 'reason': str(exc)}
    source = root / op['source']['path']
    row['asset_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    spec = json.loads(source.read_text())
    ns, chip_cls, execute = helpers
    req = SimpleNamespace(operator=op['key'], inputs=[SimpleNamespace(**t) for t in op['inputs']])
    with contextlib.redirect_stdout(io.StringIO()) as log, contextlib.redirect_stderr(log):
        try:
            result = execute(ns['_build_model'](spec, req), ns['_build_context'](spec, req), chip_cls.from_name(hardware))[1]
            row.update(status='succeeded' if result.bound_type != 'none' else 'failed',
                       latency_us=result.total_cost_us, compute_us=result.compute_cost_us,
                       memory_us=result.bw_cost_us, flops=result.compute_flops, bound=result.bound_type,
                       outputs=[{'shape': x.shape, 'dtype': x.dtype} for x in result.outputs_info])
        except Exception as exc:
            row.update(status='failed', reason=f'{type(exc).__name__}: {exc}')
        if row['status'] != 'succeeded':
            row['log_tail'] = log.getvalue()[-4000:]
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modeling-root', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    args = parser.parse_args()
    helpers = load_helpers(args.modeling_root.resolve())
    templates = json.loads((args.audit_dir / 'templates.json').read_text())
    with (args.audit_dir / 'upstream-roofline.jsonl').open('w') as output:
        for op in templates:
            if op['domain'] != 'infer' or not op['configurable']:
                continue
            for hardware in ['Adevice03_Server', 'H200_Server']:
                row = probe(op, hardware, args.modeling_root, helpers)
                output.write(json.dumps(row, ensure_ascii=False) + '\n')
                print(op['id'], hardware, row['status'], row.get('reason', ''), flush=True)


if __name__ == '__main__':
    main()
