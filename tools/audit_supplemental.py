"""Explicit input-change controls; never merge these into default coverage counts."""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from opscope.evaluation.evaluation_contract import normalize_request
from opscope.evaluation.tilesim_contract import OPERATOR_KINDS, unsupported
from tools.audit_evaluations import default_config, run_tile


def check(config, hardware, label):
    row = {'case_id': f"{config['operator_id']}|{hardware}|{label}",
           'configuration': config, 'hardware': hardware, 'control': label}
    try:
        normalized = normalize_request({'configuration': config, 'hardware_ids': [hardware],
                                        'method_ids': ['tilesim']})['configuration']
    except ValueError as exc:
        return {**row, 'status': 'blocked_input', 'reason': str(exc)}
    reason = unsupported(normalized, hardware)
    if reason:
        return {**row, 'status': 'unsupported', 'reason': reason}
    return {**row, **run_tile((row['case_id'], normalized, hardware))}


def jobs(templates):
    for op in templates:
        if op['id'] not in OPERATOR_KINDS or not any(t['dtype'] == 'bf16' for t in op['inputs']):
            continue
        config = default_config(op)
        for tensor in config['inputs']:
            if tensor['dtype'] == 'bf16':
                tensor['dtype'] = 'fp16'
        for hardware in ['h200', 'b200', 'r200']:
            yield config, hardware, 'explicit-fp16'
    op = next(o for o in templates if o['id'] == 'infer:FlashAttentionScore')
    for shape, label in [([1, 32, 2048, 128], 'explicit-head-dim-128'),
                         ([1, 8, 512, 128], 'explicit-small-fa')]:
        config = default_config(op)
        for tensor in config['inputs']:
            tensor['shape'] = shape.copy()
        for hardware in ['tilesim:910B1', 'tilesim:910B4']:
            yield config, hardware, label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir', type=Path, required=True)
    args = parser.parse_args()
    templates = json.loads((args.audit_dir / 'templates.json').read_text())
    with (args.audit_dir / 'supplemental.jsonl').open('w') as output:
        for config, hardware, label in jobs(templates):
            row = check(copy.deepcopy(config), hardware, label)
            output.write(json.dumps(row, ensure_ascii=False) + '\n'); output.flush()
            print(row['case_id'], row['status'], row.get('reason', '')[:160], flush=True)


if __name__ == '__main__':
    main()
