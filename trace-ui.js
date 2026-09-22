'use strict';

function trace_number(value) {
  return new Intl.NumberFormat('en-US', {maximumFractionDigits: 6}).format(value);
}

function render_trace(container, coreId) {
  const row = result_by_id(container.dataset.traceResult);
  const view = row?.execution?.trace_view;
  if (!view) return;
  const core = view.cores.find(item => item.id === coreId) || view.cores.find(item => item.id === view.default_core);
  container.dataset.core = core.id;
  container.innerHTML = `<div class="trace-toolbar"><label>查看计算核 <select data-trace-core>${view.cores.map(item => `<option value="${escape_html(item.id)}" ${item.id === core.id ? 'selected' : ''}>${escape_html(item.id)} · ${item.active_percent}% 活动</option>`).join('')}</select></label><span>${core.count} 个事件 · 活动区间并集 ${core.active_percent}%</span></div>
    <div class="trace-lanes">${core.lanes.map(lane => `<div class="trace-lane"><span>${escape_html(lane.label)}<small>${trace_number(lane.active_us)} μs</small></span><svg viewBox="0 -10 800 20" preserveAspectRatio="none" role="img" aria-label="${escape_html(lane.label)}，活动 ${trace_number(lane.active_us)} 微秒"><path d="${lane.path}" stroke="${lane.color}" stroke-width="12" fill="none"/></svg></div>`).join('')}</div>
    <div class="trace-axis"><span>时间 / μs</span><div>${view.ticks.map(tick => `<span>${tick}</span>`).join('')}</div></div>
    <p class="note">统一时间轴覆盖本次模拟；空白仅表示该通道没有活动事件，不直接解释为同步等待。</p>
    <details class="trace-events"><summary>查看事件明细</summary><div class="trace-event-content"></div></details>`;
  render_trace_events(container, 0);
}

function render_trace_events(container, page) {
  const row = result_by_id(container.dataset.traceResult);
  const events = row.execution.events.filter(event => event.pid === container.dataset.core);
  const offset = page * 40;
  container.dataset.page = page;
  container.querySelector('.trace-event-content').innerHTML = `<div class="trace-pager"><button type="button" data-trace-page="${page - 1}" ${page === 0 ? 'disabled' : ''}>上一页</button><span>${offset + 1}–${Math.min(offset + 40, events.length)} / ${events.length} 个事件</span><button type="button" data-trace-page="${page + 1}" ${offset + 40 >= events.length ? 'disabled' : ''}>下一页</button></div><table class="tensor-table"><thead><tr><th>操作</th><th>通道</th><th>开始 / μs</th><th>持续 / μs</th></tr></thead><tbody>${events.slice(offset, offset + 40).map(e => `<tr><td>${escape_html(e.name)}</td><td>${escape_html(e.tid)}</td><td>${trace_number(e.ts)}</td><td>${trace_number(e.dur)}</td></tr>`).join('')}</tbody></table>`;
}

function render_traces() {
  document.querySelectorAll('[data-trace-result]').forEach(container => render_trace(container));
}

document.addEventListener('change', event => {
  if (event.target.matches('[data-trace-core]')) {
    const container = event.target.closest('[data-trace-result]');
    render_trace(container, event.target.value);
    container.querySelector('[data-trace-core]').focus();
  }
});
document.addEventListener('click', event => {
  const button = event.target.closest('[data-trace-page]');
  if (button) render_trace_events(button.closest('[data-trace-result]'), Number(button.dataset.tracePage));
});
