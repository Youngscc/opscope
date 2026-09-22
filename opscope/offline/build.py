"""Build a standalone, offline operator comparison prototype."""
import html
import json
from pathlib import Path

from .fixtures import HARDWARE, METHODS, RESOURCE_STATS, VALUES
from .execution_data import execution_record
from .task_details import hardware_detail, input_detail, task_context, task_overview, workload_record
from .matrix_data import prepare_matrix
from .virtual_data import virtual_result

ROOT = Path(__file__).resolve().parents[2]
FLOPS = 2 * 4096 ** 3
LOGICAL_BYTES = 3 * 4096 ** 2 * 2
MAX_TIME = 320.0


def deviation(value, reference):
    if value is None or reference is None or reference <= 0:
        return None
    return (value - reference) / reference * 100


def kv(rows):
    return '<dl class="facts">' + ''.join(
        f'<div><dt>{html.escape(key)}</dt><dd>{html.escape(str(value))}</dd></div>'
        for key, value in rows
    ) + '</dl>'


def notice(message):
    return f'<div class="empty-detail"><span class="empty-mark">—</span><p>{html.escape(message)}</p></div>'


def svg_wrap(contents, label, height=185):
    return (f'<svg viewBox="0 0 500 {height}" role="img" aria-label="{html.escape(label)}">'
            f'<title>{html.escape(label)}</title>{contents}</svg>')


def resource_bars(rows):
    parts = []
    for label, value, color in rows:
        parts.append(f'<div class="resource-row"><div><span>{label}</span><b>{value}%</b></div><div class="resource-track"><i style="width:{value}%;background:{color}"></i></div></div>')
    return '<div class="resource-bars">' + ''.join(parts) + '</div>'


def timeline(record):
    contents = ''
    for tick in range(0, 321, 80):
        x = 100 + tick
        contents += f'<path d="M{x} 25V139" stroke="#e2e8f0"/><text x="{x}" y="161" text-anchor="middle">{tick}</text>'
    colors = ['#60a5fa', '#2563eb', '#0f766e']
    for event in record['events']:
        lane = event['lane_index']
        y = 32 + lane * 36
        if event['tile'] == 0:
            contents += f'<text x="0" y="{y + 16}">{event["lane"]}</text>'
        start, end = event['start_us'], event['end_us']
        contents += f'<rect x="{100 + start:.1f}" y="{y}" width="{end - start:.1f}" height="24" rx="3" fill="{colors[lane]}"><title>{event["lane"]} tile {event["tile"]}: {start:.1f}–{end:.1f} μs</title></rect>'
    contents += '<text x="448" y="161">μs</text>'
    return svg_wrap(contents, '局部 tile 流水示意，三条并行资源泳道，横轴0至320微秒', 175)


def heatmap_text_color(value):
    # Select readable text after the translucent cell is composited on white.
    rgb = [(channel * value / 100 + 255 * (1 - value / 100)) / 255
           for channel in (37, 99, 235)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    luminance = sum(x * weight for x, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    return '#fff' if luminance < 0.179 else '#000'


def heatmap(hardware, record):
    resource = 'Core' if hardware == 'ascend' else 'SM'
    cells = []
    for index, value in enumerate(record['instances']):
        cells.append(f'<span style="background:rgba(37,99,235,{value / 100:.2f});color:{heatmap_text_color(value)}" title="{resource} {index}: {value}%（示意）">{value}</span>')
    return f'<p class="chart-caption">{resource} 活动比例 · 24 个示意实例</p><div class="heatmap">' + ''.join(cells) + '</div>'


def phase_bars(record):
    if record['compute_us'] is None:
        return notice('回归仅提供总耗时，无计算 / 访存分项。')
    qualifier = '估算' if record['kind'] == 'analytic' else '活动'
    rows = [(f'计算{qualifier}', record['compute_us'], '#2563eb'),
            (f'访存{qualifier}', record['memory_us'], '#0f766e')]
    if record['wait_us'] is not None:
        rows.append(('同步等待', record['wait_us'], '#b45309'))
    output = []
    for label, value, color in rows:
        output.append(f'<div class="cost-row"><span>{label}</span><b>{value:.1f} μs</b><div class="resource-track"><i style="width:{value / MAX_TIME * 100:.3f}%;background:{color}"></i></div></div>')
    return '<div class="cost-bars">' + ''.join(output) + '</div><p class="note">计算、访存与等待可重叠，不相加。</p>'


def latency_detail(hardware, method, latency):
    reference = VALUES[hardware]['profile']
    delta = deviation(latency, reference)
    record = execution_record(hardware, method, latency)
    rows = [('总时延', f'{latency:.2f} μs'), ('边界', '设备侧单 kernel')]
    if method != 'profile':
        rows += [('Profiling 参考', f'{reference:.2f} μs'), ('偏差', f'{delta:+.1f}%')]
    return kv(rows) + phase_bars(record)


def summary_metrics(hardware, method, latency):
    throughput = FLOPS / latency / 1e6
    metrics = {'throughput': f'{throughput:.1f}',
               'throughput_width': round(throughput / 2400 * 100, 3),
               'memory': None, 'activity': []}
    stats = RESOURCE_STATS.get((hardware, method))
    if stats is None:
        return metrics
    traffic, hit, matrix, auxiliary, hbm = stats
    names = ('Cube', 'Vector') if hardware == 'ascend' else ('Tensor', 'SIMT')
    metrics['memory'] = {'traffic': traffic, 'hit': hit,
                         'bandwidth': f'{traffic * 1024 ** 2 / latency / 1e6:.2f}',
                         'hbm_activity': hbm}
    metrics['activity'] = [
        {'label': names[0], 'value': matrix, 'color': '#2563eb'},
        {'label': names[1], 'value': auxiliary, 'color': '#0f766e'},
    ]
    return metrics


def compute_detail(hardware, method, latency):
    common = kv([('逻辑工作量', '137.44 GFLOPs'), ('计算公式', '2 × M × N × K'), ('输入 / 累加精度', 'FP16 / FP32'), ('有效算力（FLOPs / 总时延）', f'{FLOPS / latency / 1e6:.1f} TFLOP/s')])
    metrics = summary_metrics(hardware, method, latency)
    if metrics['activity']:
        rows = [(item['label'], item['value'], item['color']) for item in metrics['activity']]
        return common + '<h4>资源活动比例</h4>' + resource_bars(rows) + '<p class="note">各硬件计数器口径不同。</p>'
    record = execution_record(hardware, method, latency)
    if record['compute_us'] is None:
        return common + notice('回归仅预测总耗时，不提供计算分项。')
    bound = FLOPS / record['compute_us'] / 1e6
    return common + kv([('计算成本', f"{record['compute_us']:.1f} μs"), ('模型有效计算上界', f'{bound:.1f} TFLOP/s'), ('参数来源', record['calibration']['source_label'])]) + '<p class="note">解析估算，不是硬件活动计数器。</p>'


def memory_detail(hardware, method, latency):
    common = kv([('逻辑读取 A + B', '64 MiB'), ('逻辑写入 C', '32 MiB'), ('逻辑算术强度', '1365.33 FLOP/Byte')])
    memory = summary_metrics(hardware, method, latency)['memory']
    if memory:
        return common + kv([('HBM 实际流量', f"{memory['traffic']} MiB"), ('HBM 平均带宽', f"{memory['bandwidth']} TB/s"), ('L2 命中率', f"{memory['hit']}%")]) + resource_bars([('HBM 带宽活动比例 · 示意', memory['hbm_activity'], '#0f766e')]) + '<p class="note">逻辑字节与实际流量口径不同。</p>'
    record = execution_record(hardware, method, latency)
    if record['memory_us'] is None:
        return common + notice('回归仅预测总耗时，不提供访存分项。')
    bandwidth = LOGICAL_BYTES / record['memory_us'] / 1e6
    return common + kv([('访存成本', f"{record['memory_us']:.1f} μs"), ('模型有效带宽', f'{bandwidth:.2f} TB/s'), ('流量假设', '输入读取一次、输出写入一次')]) + '<p class="note">模型假设；不提供实际流量与 L2 命中率。</p>'


def roofline_evidence(record):
    calibration = record['calibration']
    rows = [('评估状态', calibration['label']), ('参数来源', calibration['source_label']),
            ('参数版本', calibration['version'] + '（虚构）'),
            ('匹配条件', calibration['match'])]
    if calibration['source'] == 'regression':
        rows += [('预测方式', '特征回归 · 仅总耗时'), ('计算 / 访存分项', '未提供')]
    else:
        rows += [('模型', 'max(计算成本, 访存成本)'), ('计算公式', '2 × M × N × K'),
                 ('访存公式', '(MK + KN + MN) × 2 bytes')]
    if calibration['factor'] is not None:
        rows += [('时间修正系数（示例）', f"{calibration['factor']:.3f}×")]
    return rows + [('执行内核 / Tiling', '解析模型不指定')]


def evidence_detail(hardware, method, result_id):
    record = execution_record(hardware, method, VALUES[hardware][method])
    rows = [('结果 ID', result_id), ('数据性质', record['source']),
            ('配置版本', 'ui-demo-v3（虚构配置）'),
            ('输入', '4096 × 4096 × 4096 · FP16 / FP32'),
            ('边界', '单 kernel；不含 Host、H2D/D2H')]
    if record['kind'] == 'analytic':
        rows += roofline_evidence(record)
    else:
        rows += [('内核标识', record['kernel']),
                 ('Tile M / N / K', ' × '.join(map(str, record['tile']))),
                 ('Block 数 / K 迭代', f"{record['blocks']} / {record['k_iterations']}"),
                 ('Buffer stages / Split-K', f"{record['stages']} / {record['split_k']}"),
                 ('片上缓冲', f"{record['buffer_kib']} KiB"),
                 ('时钟（示例）', f"{record['clock_mhz']} MHz"),
                 ('版本 / 编译参数', 'demo-toolchain · -O3 · FP32 accumulate')]
    rows += [('原始报告', '未导入；数据由本地 fixtures 生成')]
    message = 'Tilesim 详情是待接入的扩展字段示例。' if method == 'tilesim' else '合成示例，未运行真实评估。'
    return kv(rows) + f'<p class="note">{message}</p>'


def pipeline_detail(hardware, method, latency):
    record = execution_record(hardware, method, latency)
    if record['kind'] == 'analytic':
        return '<h4>计算 / 访存成本</h4>' + phase_bars(record) + '<p class="note">Roofline 不生成指令级流水。</p>'
    tiles = ' × '.join(map(str, record['tile']))
    rows = [('Tile M / N / K', tiles), ('Buffer stages', str(record['stages'])),
            ('同步等待', f"{record['wait_us']:.1f} μs"),
            ('等效周期（示例时钟）', f"{record['cycles']:,} cycles")]
    note = '扩展字段示例 · 当前适配器尚未输出' if method == 'tilesim' else '局部 tile 片段 · 非完整 trace'
    return kv(rows) + f'<p class="note">{note}</p>' + timeline(record) + heatmap(hardware, record)


def result_details(hardware, method, latency, result_id):
    return {'latency': latency_detail(hardware, method, latency),
            'compute': compute_detail(hardware, method, latency),
            'memory': memory_detail(hardware, method, latency),
            'pipeline': pipeline_detail(hardware, method, latency),
            'evidence': evidence_detail(hardware, method, result_id)}


def missing_reason(hardware, method):
    if hardware == 'r200':
        return '正式 SKU 待确认'
    if hardware in {'b200', 'b300'}:
        return '暂无结果'
    return '尚未评估'


def component_label(value, qualifier):
    return '—' if value is None else f'{value:.1f} μs · {qualifier}'


def make_result(hardware, method):
    latency = VALUES.get(hardware, {}).get(method)
    result_id = f'demo-{hardware}-{method}'
    row = {'id': result_id, 'hardware': hardware, 'method': method, 'available': latency is not None, 'synthetic': True}
    context = task_context(hardware, method, result_id, latency is not None)
    row.update(context)
    if latency is None:
        return {**row, 'reason': missing_reason(hardware, method)}
    error = deviation(latency, VALUES[hardware]['profile'])
    if method in {'method3', 'method4'}:
        return virtual_result(row, latency, VALUES[hardware]['profile'], summary_metrics(hardware, method, latency), MAX_TIME)
    record = execution_record(hardware, method, latency)
    qualifier = '估算' if record['kind'] == 'analytic' else '活动'
    source_label = next(item[2] for item in METHODS if item[0] == method)
    if method == 'tilesim':
        source_label = '扩展字段示例'
    if method == 'roofline':
        source_label = record['calibration']['label']
        row['source_class'] = 'estimate-status ' + record['calibration']['status']
    row.update({'latency_us': latency, 'latency': f'{latency:.2f}', 'bar_width': round(latency / MAX_TIME * 100, 3), 'deviation_percent': error, 'deviation': '参考基线' if method == 'profile' else f'{error:+.1f}%', 'error_class': 'baseline' if method == 'profile' else ('near' if abs(error) <= 5 else 'far'), 'compute': component_label(record['compute_us'], qualifier), 'memory': component_label(record['memory_us'], qualifier), 'bound': record['bound'], 'execution': record, 'source_label': source_label, 'summary': summary_metrics(hardware, method, latency), 'details': result_details(hardware, method, latency, result_id)})
    row['details'].update({'overview': task_overview(context, row),
                           'inputs': input_detail(context['workload']),
                           'hardware': hardware_detail(context['hardware_snapshot'])})
    return row


def build_payload():
    from .catalog_data import all_hardware, catalog_payload, pending_results
    catalog = catalog_payload()
    hardware = all_hardware(catalog)
    results = [make_result(hw[0], method[0]) for hw in HARDWARE for method in METHODS]
    pending = pending_results(hardware)
    demo_ids = {item[0] for item in HARDWARE}
    results.extend({**row, 'workload': workload_record()} for row in pending if row['hardware'] not in demo_ids)
    matrix = prepare_matrix(results)
    return {'schema': 'operator-ui-demo-v1', 'synthetic': True, 'notice': '合成 UI 示例，非实测或实际仿真结果', 'workload': {'operator': 'MatMul', 'm': 4096, 'n': 4096, 'k': 4096, 'dtype': 'FP16', 'flops': FLOPS, 'logical_bytes': LOGICAL_BYTES, 'boundary': 'device kernel only'}, 'hardware': hardware, 'methods': [{'id': item[0], 'name': item[1], 'source': item[2], 'color': item[3]} for item in METHODS], 'results': results, 'matrix': matrix, 'catalog': catalog, 'pending_results': pending}


def render_page(data):
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    output = ROOT.joinpath('shell.html').read_text().replace('/* INLINE_CSS */', ROOT.joinpath('styles.css').read_text())
    scripts = '\n'.join(ROOT.joinpath(name).read_text() for name in ('configuration.js', 'catalog-ui.js', 'evaluation-ui.js', 'trace-ui.js', 'app.js'))
    output = output.replace('/* INLINE_DATA */', payload).replace('/* INLINE_JS */', scripts)
    return output


def build():
    output = render_page(build_payload())
    ROOT.joinpath('index.html').write_text(output)
    print(f'Built {ROOT / "index.html"} ({len(output.encode()):,} bytes)')


if __name__ == '__main__':
    build()
