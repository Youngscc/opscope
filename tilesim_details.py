"""Prepare trace geometry and honest TileSim details on the server."""
from collections import defaultdict
import html

from task_details import facts

LANES = {'CUBE': ('Cube 计算', '#2563eb'), 'AIC_MTE2': ('MTE2 搬入', '#0f766e'),
         'AIC_MTE1': ('MTE1 片上搬运', '#7c3aed'), 'AIC_FIXPIPE': ('FIXPIPE 写回', '#b45309'),
         'VEC': ('Vector 计算', '#2563eb'), 'AIV_MTE2': ('MTE2 向量搬入', '#0f766e'),
         'AIV_MTE3': ('MTE3 向量搬出', '#b45309')}


def union_time(events):
    end, total = 0, 0
    for start, stop in sorted((e['ts'], e['ts'] + e['dur']) for e in events):
        total += max(0, stop - max(start, end))
        end = max(end, stop)
    return total


def trace_geometry(events, latency):
    grouped = defaultdict(list)
    for event in events:
        grouped[event['pid']].append(event)
    cores = []
    for name, entries in sorted(grouped.items(), key=lambda pair: int(pair[0].rsplit('_', 1)[-1])):
        lanes = []
        for lane in dict.fromkeys(e['tid'] for e in entries):
            selected = [e for e in entries if e['tid'] == lane]
            segments = ' '.join(f'M {e["ts"] / latency * 800:.4f} 0 h {e["dur"] / latency * 800:.4f}' for e in selected)
            label, color = LANES.get(lane, (lane, '#64748b'))
            lanes.append({'id': lane, 'label': label, 'color': color, 'path': segments,
                          'active_us': union_time(selected), 'count': len(selected)})
        busy = union_time(entries)
        cores.append({'id': name, 'lanes': lanes, 'count': len(entries),
                      'active_percent': round(busy / latency * 100, 2),
                      'last_end_us': max(e['ts'] + e['dur'] for e in entries)})
    return {'cores': cores, 'ticks': [f'{latency * i / 4:.3f}' for i in range(5)],
            'default_core': max(cores, key=lambda c: c['last_end_us'])['id']}


def num(value, unit=''):
    return '—' if value is None else f'{value:,.6g}{unit}'


def component_facts(model):
    mapping = [('Cube 计算', 'aic_cube_time'), ('MTE2 搬入', 'aic_mte2_time'),
               ('MTE1 片上搬运', 'aic_mte1_time'), ('FIXPIPE 写回', 'aic_fixpipe_time'),
               ('Vector 计算', 'aiv_vec_time'), ('MTE2 向量搬入', 'aiv_mte2_time'),
               ('MTE3 向量搬出', 'aiv_mte3_time')]
    return facts([(label, num(model[key], ' μs')) for label, key in mapping])


def tile_details(row):
    r, work = row['raw_result'], row['workload']
    model, hw = r['model_result'], r['hardware_spec']
    spec, view = hw['model_spec'], row['execution']['trace_view']
    rate = row['summary']['throughput']
    inputs = [(t['name'], f"{t['shape']} · {t['dtype']}") for t in work['tensors']]
    outputs = [(t['name'], f"{t['shape']} · {t['dtype']}") for t in r['outputs']]
    return {
        'overview': facts([('总时延', num(r['latency_us'], ' μs')), ('有效算力', rate + ' TFLOP/s'),
                           ('相对参考偏差', '—'), ('主要瓶颈', '—'), ('实际执行后端', 'TileSim · DSL 工程模式'),
                           ('数据性质', '模型预测 · 非设备实测'), ('结果 ID', row['id']), ('执行时间', row['task']['finished_at'])]),
        'latency': component_facts(model) + '<p class="note">分项为最晚结束核的通道工作时间，可重叠；不相加为总耗时。未推断同步等待与瓶颈。</p>',
        'compute': facts([('逻辑工作量', num(r['flops'] / 1e9, ' GFLOPs')), ('计算公式', '2 × M × N × K'),
                          ('有效算力', rate + ' TFLOP/s'), ('统计核', view['default_core']),
                          ('Cube 工作周期', num(model['aic_cycles'])), ('Vector 工作周期', num(model['aiv_cycles']))]),
        'memory': facts([('预测 L2 字节命中率', num(model['l2_access_rate'] * 100, '%')),
                         ('逻辑读取', num(r['read_bytes'] / 1048576, ' MiB')), ('逻辑写入', num(r['write_bytes'] / 1048576, ' MiB')),
                         ('逻辑算术强度', num(r['arithmetic_intensity'], ' FLOP/B'))]) +
                  '<h4>模拟搬运路径</h4>' + facts([(k.replace('_2_', ' → '), num(v / 1048576, ' MiB')) for k, v in model['data_transfer'].items()]) +
                  '<p class="note">按模拟路径累计的数据量，包含复用与重复搬运；不等于真机 HBM 计数器。</p>',
        'pipeline': facts([('流水事件', str(len(row['execution']['events']))), ('有活动的核', str(len(view['cores']))),
                           ('流水类型', 'Tile 操作级模拟')]) + f'<div class="trace-view" data-trace-result="{html.escape(row["id"], quote=True)}"></div>',
        'inputs': facts([('算子', work['operator']), ('边界', '单算子 Tile 模拟，不含 Host / H2D / D2H'),
                         ('累加精度', '未单独建模')]) + '<h4>输入</h4>' + facts(inputs) + '<h4>输出</h4>' + facts(outputs),
        'hardware': facts([('实际规格', hw['name']), ('模型时钟', num(spec['clock_freq'], ' MHz')),
                           ('AIC / AIV 核数', f"{spec['core_config']['cube_core_num']} / {spec['core_config']['vec_core_num']}"),
                           ('模型 L1 / L0C', f"{spec['local_mem']['L1']} / {spec['local_mem']['L0C']} KiB"),
                           ('模型 L2', num(spec['share_mem']['L2'] / 1024, ' MiB')), ('配置摘要', r['hardware_hash'])]),
        'evidence': facts([('实际方法', 'TileSim · DSL 工程模式'), ('方法回退', '无'), ('引擎版本', r['engine']['revision']),
                           ('输入分块 M / N / K1 / K0', ' / '.join(str(r['tiling_input'][k]) for k in ('tm', 'tn', 'tk1', 'tk0'))),
                           ('分块选择', '固定候选 · 非自动寻优'), ('配置摘要', row['provenance']['configuration_hash']),
                           ('评估程序墙钟耗时', num(r['wall_time_ms'], ' ms'))]) + '<p class="note">耗时、分项和流水来自同一次模拟；不代表真实内核或设备测量。</p>',
    }
