"""Presentation-only samples shaped like Hanguang analysis fields, never engine output."""
import html

METRICS = [('l2_cache_hit_rate', 'L2 命中率'), ('mfu', 'MFU'), ('ub_utilization', 'UB 利用率')]
PIPES = [('aic_mac', 'AIC MAC'), ('aic_mte1', 'AIC MTE1'), ('aic_mte2', 'AIC MTE2'),
         ('fixpipe', 'FIXPIPE'), ('aiv_vec', 'AIV VEC'), ('aiv_mte2', 'AIV MTE2'), ('aiv_mte3', 'AIV MTE3')]
# Authored UI examples, not inferred from timings, active ratios or an assumed device clock.
PROFILES = {
    'memory': ((.62, .46, .72), (58, 30, 86, 15, 35, 40, 25)),
    'compute': ((.86, .81, .64), (88, 24, 48, 18, 28, 30, 20)),
    'waiting': ((.78, .52, .82), (62, 26, 58, 15, 71, 44, 32)),
    'balanced': ((.86, .61, .72), (80, 30, 65, 15, 35, 40, 25)),
}


def sample_analysis(latency, profile='balanced', npu=True, l2=None, clock_mhz=None):
    metrics, pipes = PROFILES[profile]
    return {'performance': {'latency_us': latency, 'cycles': round(latency * clock_mhz) if clock_mhz is not None else None},
            'sample_clock_mhz': clock_mhz,
            'metrics': {'l2_cache_hit_rate': metrics[0] if l2 is None else l2,
                        'mfu': metrics[1], 'ub_utilization': metrics[2] if npu else None},
            'pipe_cycles': {'components': dict(zip((key for key, _ in PIPES), pipes)) if npu else None},
            'trace': {'format': None, 'file': None}}


def analysis_view(analysis=None):
    analysis = analysis or {}
    metrics = analysis.get('metrics') or {}
    components = (analysis.get('pipe_cycles') or {}).get('components') or {}
    cycles = (analysis.get('performance') or {}).get('cycles')
    return {'metrics': [dict(key=key, label=label, value=metrics.get(key),
                            display='—' if metrics.get(key) is None else f'{metrics[key] * 100:.1f}%',
                            width=None if metrics.get(key) is None else round(metrics[key] * 100, 3))
                        for key, label in METRICS],
            'pipes': [dict(key=key, label=label, value=components.get(key),
                          display='—' if components.get(key) is None else f'{components[key]:g}')
                      for key, label in PIPES],
            'cycles': '—' if cycles is None else f'{cycles:,}',
            'cycle_label': '等效周期' if analysis.get('sample_clock_mhz') else '总周期',
            'latency': '—' if (analysis.get('performance') or {}).get('latency_us') is None else f"{analysis['performance']['latency_us']:.1f} μs"}


def analysis_detail(analysis, section):
    view = analysis_view(analysis)
    if section == 'analysis':
        rows = [(row['label'], row['display']) for row in view['metrics']] + [(view['cycle_label'], view['cycles'])]
    else:
        rows = [(row['label'], row['display']) for row in view['pipes']]
        trace = (analysis or {}).get('trace') or {}
        rows += [('Trace 格式', trace.get('format') or '—'),
                 ('Trace 文件', '已提供' if trace.get('file') else '未提供')]
    facts = ''.join(f'<div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>' for label, value in rows)
    return f'<dl class="facts">{facts}</dl>'


def attach_matrix_samples(results):
    for row in results:
        if not row['available']:
            continue
        # Lookup-only and analytic examples retain missing analysis fields.
        if row['method'] not in ('profile', 'tilesim'):
            continue
        memory = row.get('summary', {}).get('memory')
        hit = memory['hit'] / 100 if memory else None
        row['analysis'] = sample_analysis(row['latency_us'], npu=row['hardware'] == 'ascend', l2=hit, clock_mhz=1500 if row['hardware'] == 'ascend' else None)
