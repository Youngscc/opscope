"""Compare two retained model-prediction runs without inventing missing metrics."""
from opscope.offline.matrix_data import nice_ceiling


def comparison_issues(left, right):
    if left is None or right is None:
        return ['一侧未选择此组合']
    if not left['available'] or not right['available']:
        return ['一侧或两侧没有预测结果']
    a, b = left.get('provenance', {}), right.get('provenance', {})
    issues = []
    if not a.get('configuration_hash') or a['configuration_hash'] != b.get('configuration_hash'):
        issues.append('算子配置不同')
    if not a.get('hardware_hash') or a['hardware_hash'] != b.get('hardware_hash'):
        issues.append('硬件规格不同')
    if not a.get('engine') or a['engine'] != b.get('engine'):
        issues.append('引擎或校准身份不同')
    if left.get('synthetic') or right.get('synthetic'):
        issues.append('示例与预测不可混比')
    return issues


def compact(row):
    if row is None:
        return None
    return {'id': row['id'], 'available': row['available'], 'status': row['task']['status'],
            'reason': row.get('reason'), 'latency_us': row.get('latency_us'),
            'latency': row.get('latency'), 'source_label': row.get('source_label')}


def paired_rows(left, right):
    a = {(r['hardware'], r['method']): r for r in left['results']
         if r['task']['status'] != 'not_run'}
    b = {(r['hardware'], r['method']): r for r in right['results']
         if r['task']['status'] != 'not_run'}
    names = {r['id']: r['name'] for r in left['hardware'] + left['methods']}
    rows = []
    for hardware, method in sorted(a.keys() | b.keys()):
        first, second = a.get((hardware, method)), b.get((hardware, method))
        issues = comparison_issues(first, second)
        x, y = (first or {}).get('latency_us'), (second or {}).get('latency_us')
        delta = (y - x) / x * 100 if not issues and x is not None and x > 0 else None
        rows.append({'hardware': hardware, 'method': method,
                     'name': f'{names.get(hardware, hardware)} · {names.get(method, method)}',
                     'left': compact(first), 'right': compact(second), 'issues': issues,
                     'delta_percent': delta, 'delta_label': f'{delta:+.1f}%' if delta is not None else '—'})
    return rows


def compare_payload(left, right):
    rows = paired_rows(left, right)
    valid = [r for r in rows if not r['issues']]
    maximum = nice_ceiling(max((side['latency_us'] for r in valid
                                for side in (r['left'], r['right'])), default=0) * 1.08)
    for row in rows:
        row['bars'] = [round(side['latency_us'] / maximum * 100, 5) for side in
                       (row['left'], row['right'])] if not row['issues'] else None
    faster = sum(r['right']['latency_us'] < r['left']['latency_us'] for r in valid)
    slower = sum(r['right']['latency_us'] > r['left']['latency_us'] for r in valid)
    return {'left': left['evaluation'], 'right': right['evaluation'], 'rows': rows,
            'scale_us': maximum, 'summary': {'comparable': len(valid), 'faster': faster,
                                           'slower': slower, 'equal': len(valid) - faster - slower,
                                           'not_comparable': len(rows) - len(valid)},
            'notice': 'B 相对 A；数值为模型预测，不代表设备实测。'}
