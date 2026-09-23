"""Standalone, escaped HTML reports for retained OpScope predictions."""
from collections import defaultdict
import html
import json
import re

from .tilesim_details import union_time
from .time_comparison import compare_payload
from opscope.offline.matrix_data import TABS, pair_summary


STYLE = """
:root{--ink:#202c3e;--muted:#58667a;--line:#dce3ec;--blue:#315ac2;--green:#228879}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f7fa;color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}
a{color:#24479f;text-decoration:none}a:hover{text-decoration:underline}h1,h2,h3,p{margin:0}
header{background:#fff;border-bottom:1px solid var(--line);padding:28px max(32px,calc((100vw - 1360px)/2))}
.brand{font-size:12px;font-weight:700;color:#24479f;letter-spacing:.12em}.eyebrow{font-size:10px;font-weight:700;letter-spacing:.16em;color:var(--muted)}
h1{font-size:28px;letter-spacing:-.04em;margin:8px 0 4px}header p{font-size:12px;color:var(--muted)}
.layout{display:grid;grid-template-columns:180px minmax(0,1fr);gap:30px;max-width:1480px;margin:auto;padding:28px 32px 70px}
nav{position:sticky;top:20px;align-self:start;display:grid;gap:4px;font-size:12px}nav a{padding:8px 10px;border-radius:6px}nav a:hover{background:#eaf0fc;text-decoration:none}
main{min-width:0}.panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px 24px;margin-bottom:18px;overflow:hidden}
.panel h2{font-size:18px;letter-spacing:-.02em;margin-bottom:8px}.panel h3{font-size:13px;margin:20px 0 9px}.note{font-size:12px;color:var(--muted);line-height:1.65}.warning{color:#8b5d23;background:#fff8e9;border:1px solid #ebdfc8;border-radius:6px;padding:10px 12px;margin:12px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px;margin-top:18px}.card{background:#f8fafc;border:1px solid var(--line);border-radius:7px;padding:13px}.card strong{display:block;font-size:22px;font-variant-numeric:tabular-nums;line-height:1.2}.card span{font-size:11px;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:12px;table-layout:fixed}th,td{padding:8px 10px;border-bottom:1px solid #e9edf3;text-align:left;vertical-align:top;overflow-wrap:anywhere}thead th{background:#f8fafc;color:var(--muted);font-weight:600}tbody th{font-weight:500;color:var(--muted)}td{font-variant-numeric:tabular-nums}
.pair th:first-child{width:24%}.pair th:not(:first-child){width:38%}.pair-group{padding-top:14px;border-top:1px solid var(--line);margin-top:16px}.pair-group:first-of-type{border:0;padding-top:0}
.chart-head,.chart-row{display:grid;grid-template-columns:220px minmax(0,1fr) 80px;gap:14px;align-items:center}.chart-head{color:var(--muted);font-size:11px;margin:12px 0}.chart-row{border-top:1px solid #e9edf3;padding:10px 0;font-size:12px}.chart-row strong{font-variant-numeric:tabular-nums}.bars{display:grid;gap:5px}.barline{height:17px;display:flex;align-items:center;background:linear-gradient(90deg,#e9edf3 1px,transparent 1px) 0 0/25%}.bar{height:9px;border-radius:2px;display:block;flex-shrink:0}.bar.a{background:var(--blue)}.bar.b{background:var(--green)}.barline em{font-size:10px;font-style:normal;margin-left:6px;white-space:nowrap;color:var(--muted)}
.badge{display:inline-grid;place-items:center;width:21px;height:21px;border-radius:4px;color:#fff;font-size:11px;margin-right:8px}.badge.a{background:var(--blue)}.badge.b{background:var(--green)}
details{border-top:1px solid var(--line);margin-top:14px}summary{cursor:pointer;padding:12px 0;font-weight:650;font-size:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;background:#f8fafc;border:1px solid var(--line);border-radius:6px;padding:12px;font-size:10px}
.lane{display:grid;grid-template-columns:145px minmax(0,1fr) 80px;gap:12px;align-items:center;padding:7px 0;border-bottom:1px solid #e9edf3;font-size:11px}.lane svg{width:100%;height:22px;background:#f8fafc}.lane small{text-align:right;color:var(--muted)}
.event-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0}.event-controls input{border:1px solid var(--line);border-radius:6px;padding:8px 10px;min-width:240px}.event-controls button{border:1px solid var(--line);border-radius:6px;background:#fff;padding:7px 11px;cursor:pointer}.event-controls button:disabled{opacity:.45}.event-controls span{font-size:11px;color:var(--muted)}
.events th:nth-child(1){width:30%}.events th:nth-child(2){width:16%}.events th:nth-child(3){width:18%}.events th:nth-child(4){width:10%}.events th:nth-child(5),.events th:nth-child(6){width:13%}
footer{max-width:1480px;margin:auto;padding:0 32px 28px;color:var(--muted);font-size:11px}
@media(max-width:900px){.layout{display:block;padding:16px}nav{position:static;display:flex;flex-wrap:wrap;margin-bottom:12px}.chart-head,.chart-row{grid-template-columns:130px minmax(0,1fr) 60px}.panel{padding:16px}header{padding:20px}}
"""


def esc(value):
    return html.escape('—' if value is None else str(value), quote=True)


def document(title, subtitle, navigation, sections, script=''):
    nav = ''.join(f'<a href="#{esc(anchor)}">{esc(label)}</a>' for anchor, label in navigation)
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} · OpScope</title><style>{STYLE}</style></head><body>'
            f'<header><div class="brand">OPSCOPE / MODEL REPORT</div><h1>{esc(title)}</h1>'
            f'<p>{esc(subtitle)}</p></header><div class="layout"><nav aria-label="报告目录">{nav}</nav>'
            f'<main>{sections}</main></div><footer>OpScope · 数据性质以结果来源标记为准 · 本报告离线可读</footer>'
            f'{script}</body></html>')


def panel(anchor, title, content):
    return f'<section class="panel" id="{esc(anchor)}"><h2>{esc(title)}</h2>{content}</section>'


def cards(items):
    return '<div class="cards">' + ''.join(
        f'<div class="card"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>'
        for label, value in items) + '</div>'


def table(headers, rows, css=''):
    head = ''.join(f'<th scope="col">{esc(value)}</th>' for value in headers)
    body = ''.join('<tr>' + ''.join(
        f'<th scope="row">{esc(value)}</th>' if index == 0 else f'<td>{esc(value)}</td>'
        for index, value in enumerate(row)) + '</tr>' for row in rows)
    return f'<table class="{esc(css)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def section_facts(first, second=None):
    left = (first or {}).get('facts', []) + (first or {}).get('metadata_facts', [])
    right = (second or {}).get('facts', []) + (second or {}).get('metadata_facts', [])
    labels = dict.fromkeys(item['label'] for item in left + right)
    find = lambda facts, label: next((item['value'] for item in facts if item['label'] == label), '—')
    return [(label, find(left, label), find(right, label)) for label in labels]


def extra_text(item):
    # Detail fragments are presentation HTML; keep their words without trusting their markup.
    fragment = (item or {}).get('extra', '')
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def detail_blocks(left, right=None):
    tabs = [tab for tab, _, _ in TABS if (left and left.get('sections', {}).get(tab))
            or (right and right.get('sections', {}).get(tab))]
    content = []
    for tab in tabs:
        name = next(label for key, label, _ in TABS if key == tab)
        content.append(f'<h3>{esc(name)}</h3>')
        a, b = (left or {}).get('sections', {}).get(tab, []), (right or {}).get('sections', {}).get(tab, [])
        for key in dict.fromkeys(item['key'] for item in a + b):
            first = next((item for item in a if item['key'] == key), None)
            second = next((item for item in b if item['key'] == key), None)
            rows = section_facts(first, second)
            note_a, note_b = extra_text(first), extra_text(second)
            if note_a or note_b:
                rows.append(('补充说明', note_a or '—', note_b or '—'))
            if not rows:
                continue
            content.append(f'<div class="pair-group"><h3>{esc((first or second)["title"])}</h3>'
                           + table(['指标', 'A' if right else '结果', 'B'] if right else ['指标', '结果'],
                                   rows if right else [(label, x) for label, x, _ in rows], 'pair' if right else '')
                           + '</div>')
    return ''.join(content) or '<p class="note">此结果没有结构化指标。</p>'


def row_at(payload, pair):
    return next((row for row in payload['results'] if row['hardware'] == pair['hardware']
                 and row['method'] == pair['method'] and row['task']['status'] != 'not_run'), None)


def chart_rows(summary):
    rows = []
    for pair in summary['rows']:
        if pair['bars'] is None:
            continue
        bars = ''.join(f'<div class="barline"><i class="bar {letter}" style="width:{width}%"></i>'
                       f'<em>{esc(side["latency"])} μs</em></div>'
                       for letter, width, side in zip('ab', pair['bars'], (pair['left'], pair['right'])))
        rows.append(f'<div class="chart-row"><span>{esc(pair["name"])}</span>'
                    f'<div class="bars">{bars}</div><strong>{esc(pair["delta_label"])}</strong></div>')
    return (f'<div class="chart-head"><span>硬件 · 方法</span><span>A 基准 / B 对比 · '
            f'统一刻度 {esc(summary["scale_us"])} μs</span><span>变化率</span></div>'
            + ''.join(rows)) if rows else '<p class="note">没有可绘制的同口径组合。</p>'


def comparison_report(left_job, right_job):
    first, second = left_job['payload'], right_job['payload']
    summary = compare_payload(first, second)
    counts = summary['summary']
    names = [('同口径组合', counts['comparable']), ('B 更短', counts['faster']),
             ('B 更长', counts['slower']), ('相同', counts['equal']),
             ('仅并排展示', counts['not_comparable'])]
    context = table(['时间', 'A 基准', 'B 对比'], [
        ('任务 ID', left_job['id'], right_job['id']),
        ('提交时间', left_job.get('created_at'), right_job.get('created_at')),
        ('完成时间', first['evaluation'].get('completed_at'), second['evaluation'].get('completed_at')),
        ('算子', first['initial_configuration']['operator'], second['initial_configuration']['operator']),
        ('配置摘要', first['evaluation']['configuration_hash'], second['evaluation']['configuration_hash'])], 'pair')
    sections = [panel('overview', '结论与范围', '<p class="note">B 相对 A；仅同口径组合计算变化率。'
                      '更短表示模型预测耗时更小，不代表真机加速或预测精度。</p>' + cards(names) + context),
                panel('chart', '总耗时对照', chart_rows(summary))]
    for index, pair in enumerate(summary['rows'], 1):
        a, b = row_at(first, pair), row_at(second, pair)
        values = table(['', 'A 基准', 'B 对比'], [
            ('状态', (a or {}).get('task', {}).get('status', '未选择'),
             (b or {}).get('task', {}).get('status', '未选择')),
            ('总耗时 / μs', (a or {}).get('latency_us'), (b or {}).get('latency_us')),
            ('缺失原因', (a or {}).get('reason'), (b or {}).get('reason'))], 'pair')
        reason = '；'.join(pair['issues']) if pair['issues'] else f'B 相对 A：{pair["delta_label"]}'
        sections.append(panel(f'pair-{index}', pair['name'],
                              f'<p class="note">{esc(reason)}</p>{values}{detail_blocks(a, b)}'))
    nav = [('overview', '结论与范围'), ('chart', '总耗时对照')]
    nav += [(f'pair-{i}', pair['name']) for i, pair in enumerate(summary['rows'], 1)]
    return document('两次评估对比报告', '独立 HTML · 模型预测结果 · 非设备实测', nav, ''.join(sections))


def event_groups(events):
    groups = defaultdict(list)
    for event in events:
        groups[(event['pid'], event['tid'])].append(event)
    return [(core, lane, len(items), f'{union_time(items):,.6g}')
            for (core, lane), items in sorted(groups.items())]


def trace_lanes(row):
    view = row.get('execution', {}).get('trace_view')
    if not view:
        return '<p class="note">此方法没有提供事件流水；不能据分项成本推导事件顺序。</p>'
    cores = []
    for core in view['cores']:
        lanes = ''.join(f'<div class="lane"><span>{esc(lane["label"])}</span>'
                        f'<svg viewBox="0 -10 800 20" preserveAspectRatio="none" role="img" '
                        f'aria-label="{esc(lane["label"])}，活动 {esc(lane["active_us"])} 微秒">'
                        f'<path d="{esc(lane["path"])}" stroke="{esc(lane["color"])}" '
                        f'stroke-width="12" fill="none"/></svg><small>{esc(lane["active_us"])} μs</small></div>'
                        for lane in core['lanes'])
        cores.append(f'<details{" open" if core["id"] == view["default_core"] else ""}>'
                     f'<summary>{esc(core["id"])} · {esc(core["count"])} 个事件 · '
                     f'活动区间占比 {esc(core["active_percent"])}%</summary>{lanes}</details>')
    return ''.join(cores) + '<p class="note">同一核内通道可重叠；活动占比不是峰值算力利用率。</p>'


def event_script(events):
    data = json.dumps(events, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return '<script type="application/json" id="event-data">' + data + '</script>' + """<script>
const all=JSON.parse(document.getElementById('event-data').textContent);let page=0;
const input=document.getElementById('event-search'),body=document.getElementById('event-body');
function draw(){const q=input.value.trim().toLowerCase();
 const rows=q?all.filter(e=>`${e.name} ${e.pid} ${e.tid}`.toLowerCase().includes(q)):all;
 const count=Math.max(1,Math.ceil(rows.length/100));page=Math.min(page,count-1);
 body.replaceChildren();for(const e of rows.slice(page*100,(page+1)*100)){
  const tr=document.createElement('tr');for(const key of ['name','pid','tid','ph','ts','dur']){
   const td=document.createElement('td');td.textContent=String(e[key]??'—');tr.appendChild(td)}body.appendChild(tr)}
 document.getElementById('event-count').textContent=`${rows.length} 个事件 · 第 ${page+1}/${count} 页`;
 document.getElementById('event-prev').disabled=page===0;
 document.getElementById('event-next').disabled=page>=count-1}
input.addEventListener('input',()=>{page=0;draw()});
document.getElementById('event-prev').addEventListener('click',()=>{page--;draw()});
document.getElementById('event-next').addEventListener('click',()=>{page++;draw()});draw();
</script>"""


def event_table(events):
    if not events:
        return '<p class="note">没有事件明细。Roofline 与多数成本模型仅提供汇总预测。</p>', ''
    controls = ('<div class="event-controls"><label for="event-search">筛选操作 / 核 / 通道</label>'
                '<input id="event-search" type="search" autocomplete="off"></div>'
                '<div class="event-controls"><button id="event-prev" type="button">上一页</button>'
                '<button id="event-next" type="button">下一页</button><span id="event-count"></span></div>')
    placeholder = table(['操作', '核', '通道', '类型', '开始 / μs', '持续 / μs'], [], 'events')
    placeholder = placeholder.replace('<tbody></tbody>', '<tbody id="event-body"></tbody>')
    return controls + placeholder + '<noscript><p class="warning">启用本地 JavaScript 可查看完整事件明细。</p></noscript>', event_script(events)


def single_report(job, row):
    payload = job['payload']
    events = row.get('execution', {}).get('events') or []
    report = [("总耗时 / μs", row.get('latency_us')), ('状态', row['task']['status']),
              ('事件数', len(events)), ('数据性质', '模型预测 · 非设备实测')]
    identity = table(['字段', '值'], [
        ('任务 ID', job['id']), ('提交时间', job.get('created_at')),
        ('完成时间', payload['evaluation'].get('completed_at')),
        ('方法', row['method']), ('硬件', row['hardware']),
        ('实际执行后端', row['task'].get('actual_backend')),
        ('结果 ID', row['id']), ('配置摘要', row.get('provenance', {}).get('configuration_hash'))])
    status = f'<p class="warning">{esc(row.get("reason"))}</p>' if not row['available'] else ''
    sections = [panel('summary', '结果摘要', cards(report) + status + identity),
                panel('details', '各项预测与依据', detail_blocks(row)),
                panel('trace', '核活动与时间轴', trace_lanes(row))]
    event_html, script = event_table(events)
    sections.append(panel('events', '完整事件明细',
                          f'<p class="note">共 {len(events)} 个原始模拟事件。开始和持续时间均为 μs；'
                          '此处不推断同步等待或真机 kernel。</p>'
                          + (table(['核', '通道', '事件数', '活动区间并集 / μs'], event_groups(events)) if events else '')
                          + event_html))
    raw = {key: value for key, value in row.items() if key not in {'details', 'sections', 'matrix'}}
    raw['execution'] = {key: value for key, value in raw.get('execution', {}).items()
                        if key not in {'events', 'trace_view'}}
    sections.append(panel('raw', '原始预测字段', '<pre>' + esc(json.dumps(raw, ensure_ascii=False, indent=2)) + '</pre>'))
    nav = [('summary', '结果摘要'), ('details', '逐项详情'), ('trace', '核活动'),
           ('events', '事件明细'), ('raw', '原始字段')]
    name = next((h['name'] for h in payload['hardware'] if h['id'] == row['hardware']), row['hardware'])
    method = next((m['name'] for m in payload['methods'] if m['id'] == row['method']), row['method'])
    return document(f'{name} · {method} 单项报告',
                    f'{payload["initial_configuration"]["operator"]} · 独立 HTML · 模型预测',
                    nav, ''.join(sections), script)


def pair_report(payload, left, right):
    """Compare exactly the two matrix cells selected, including demo provenance."""
    summary = pair_summary(left, right)
    names = [{item['id']: item['name'] for item in payload[key]}
             for key in ('hardware', 'methods')]
    labels = [f"{names[0][row['hardware']]} · {names[1][row['method']]}" for row in (left, right)]
    sources = ['示例数据 · synthetic=true' if row.get('synthetic') else '模型预测，非设备实测'
               for row in (left, right)]
    chart = ''
    if summary['chart']:
        for index, row in enumerate((left, right)):
            slot = 'B' if index else 'A'
            width = summary['chart']['widths'][index]
            chart += (f'<div class="chart-row"><span>{slot} · {esc(labels[index])}</span>'
                      f'<div class="barline"><span class="bar {slot.lower()}" style="width:{width}%"></span></div>'
                      f'<strong>{esc(row["latency"])} μs</strong></div>')
        chart += f'<p class="note">同一尺度：0 — {esc(summary["chart"]["scale_us"])} μs</p>'
    overview = table(['项目', '结果 A', '结果 B'], [
        ('对象', *labels), ('数据来源', *sources), ('结果 ID', left['id'], right['id'])], 'pair')
    overview += f'<p class="warning">{esc(summary["text"])}</p>' + chart
    body = panel('overview', '总耗时对比', overview)
    body += panel('details', '逐项指标', detail_blocks(left, right))
    raw = json.dumps({'synthetic': any(row.get('synthetic') for row in (left, right)),
                      'results': [left, right]}, ensure_ascii=False, indent=2)
    body += panel('raw', '结果数据', f'<details><summary>展开原始 JSON</summary><pre>{esc(raw)}</pre></details>')
    return document('双结果对比报告', 'A / B · ' + ' ↔ '.join(labels),
                    [('overview', '总耗时'), ('details', '逐项指标'), ('raw', '结果数据')], body)
