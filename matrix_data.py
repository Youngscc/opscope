"""Prepare matrix geometry and comparison semantics before browser rendering."""
import html
import math
import re


TABS = [
    ('overview', '结果概览', [('overview', '结果摘要'), ('latency', '耗时分析')]),
    ('cost', '计算与访存', [('compute', '计算'), ('memory', '访存')]),
    ('execution', '执行过程', [('pipeline', '各核活动与流水')]),
    ('context', '输入与硬件', [('inputs', '输入输出'), ('hardware', '硬件配置')]),
    ('source', '依据与数据', [('evidence', '执行依据')]),
]
UNKNOWN = {'—', '未采集', '未创建', '未导入', '未提供', '未执行 · 示例数据'}


def nice_ceiling(value):
    """Use a shared, zero-based scale independent of the visible filters."""
    if value <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 2.5, 3, 4, 5, 10):
        if step * magnitude >= value:
            return step * magnitude


def chart_scales(results):
    times = [r['latency_us'] for r in results if r['available']]
    errors = [abs(r['deviation_percent']) for r in results
              if r['available'] and r.get('deviation_percent') is not None]
    latency = nice_ceiling(max(times, default=0) * 1.08)
    error = nice_ceiling(max(errors, default=0) * 1.15)
    return {
        'latency_max': latency, 'error_max': error,
        'latency_ticks': [{'position': i * 25, 'label': f'{latency * i / 4:g}'}
                          for i in range(5)],
        'error_ticks': [{'position': i * 25, 'label': f'{error * (i / 2 - 1):g}%'}
                        for i in range(5)],
    }


def parsed_facts(fragment):
    """Extract our generated scalar labels once; keep visual markup separate."""
    facts = []
    for label, value in re.findall(r'<dt>(.*?)</dt><dd>(.*?)</dd>', fragment, re.S):
        label, value = (html.unescape(re.sub('<[^>]+>', '', x)) for x in (label, value))
        facts.append({'label': label, 'value': value, 'known': value not in UNKNOWN})
    return facts


def detail_sections(result):
    if not result['available']:
        return {}
    sections = {}
    for tab, _, groups in TABS:
        sections[tab] = []
        for key, title in groups:
            body = result['details'][key]
            extra = re.sub(r'<dl class="facts">.*?</dl>', '', body, flags=re.S)
            # Empty headings and run wrappers add noise once their scalar rows are aligned.
            extra = re.sub(r'<details.*?</details>|<h4>.*?</h4>', '', extra, flags=re.S)
            facts = parsed_facts(body)
            metadata = facts[4:] if key == 'overview' else []
            if key == 'overview':
                facts, extra = facts[:4], ''
            elif key == 'latency':
                facts = [item for item in facts if item['label'] not in {'总时延', '偏差'}]
            sections[tab].append({'title': title, 'key': key, 'metadata_facts': metadata,
                                  'facts': facts, 'extra': extra})
    return sections


def comparison_issues(left, right):
    if not left['available'] or not right['available']:
        return ['结果缺失']
    issues = []
    for key, name in [('operator', '算子'), ('tensors', '输入输出'), ('layout', '布局'),
                      ('transpose_a', 'A转置'), ('transpose_b', 'B转置'),
                      ('accumulator_dtype', '累加精度'), ('boundary', '计时边界')]:
        a, b = left.get('workload', {}).get(key), right.get('workload', {}).get(key)
        if a is None or b is None:
            issues.append(name + '未提供')
        elif a != b:
            issues.append(name + '不同')
    if left['hardware'] != right['hardware'] and left['method'] != right['method']:
        issues.append('硬件与方法同时变化')
    demo = all(r.get('synthetic') and r.get('task', {}).get('source') == 'synthetic_fixture'
               for r in (left, right))
    if not demo:
        issues.append('真实来源与硬件/引擎契约尚未校验')
    return issues


def pair_summary(left, right):
    issues = comparison_issues(left, right)
    base = {'ids': [left['id'], right['id']], 'issues': issues, 'delta_percent': None,
            'text': '无法直接计算差值：' + '；'.join(issues)}
    if issues:
        return base
    a, b = left['latency_us'], right['latency_us']
    if a == 0:
        return {**base, 'text': 'A 耗时为 0，相对变化未定义；保留原始值。'}
    delta = (b - a) / a * 100
    return {**base, 'delta_percent': delta,
            'text': f'B 相对 A 耗时 {delta:+.1f}% · 仅合成示例，不代表准确性或真实性能结论。'}


def prepare_matrix(results):
    scales = chart_scales(results)
    for row in results:
        available = row['available']
        delta = row.get('deviation_percent')
        row['matrix'] = {
            'latency_width': round(row['latency_us'] / scales['latency_max'] * 100, 5) if available else None,
            'error_position': round(50 + delta / scales['error_max'] * 50, 5) if delta is not None else None,
            'error_label': f'{delta:+.1f}%' if delta is not None else '—',
            'note': row.get('bound') or ('瓶颈未提供' if available else row['reason']),
        }
        row['sections'] = detail_sections(row)
    pairs = {a['id'] + '|' + b['id']: pair_summary(a, b)
             for a in results for b in results if a['available'] and b['available'] and a['id'] != b['id']}
    return {'scales': scales, 'tabs': [{'id': key, 'name': name} for key, name, _ in TABS],
            'pairs': pairs}
