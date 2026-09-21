'use strict';
const data = JSON.parse(document.getElementById('result-data').textContent);
const state = {hardware: new Set(['ascend', 'h100']), methods: new Set(data.methods.map(item => item.id)), view: 'hardware', selected: [], details: [], tab: 'latency', origin: null};
const by_id = id => document.getElementById(id);
const hardware_by_id = id => data.hardware.find(item => item.id === id);
const method_by_id = id => data.methods.find(item => item.id === id);
const result_by_id = id => data.results.find(item => item.id === id);

function visible_results() {
  return data.results.filter(item => state.hardware.has(item.hardware) && state.methods.has(item.method));
}

function render_filters() {
  by_id('hardware-options').innerHTML = data.hardware.map(item => `<label class="hardware-option"><input type="checkbox" data-hardware="${item.id}" ${state.hardware.has(item.id) ? 'checked' : ''}><span><b>${item.name}</b></span><span class="family">${item.family}</span></label>`).join('');
  by_id('method-options').innerHTML = data.methods.map(item => `<label class="method-chip"><input type="checkbox" data-method="${item.id}" ${state.methods.has(item.id) ? 'checked' : ''}><span class="method-dot ${item.color}"></span>${item.name}</label>`).join('');
}

function result_heading(result) {
  const method = method_by_id(result.method);
  const name = state.view === 'hardware' ? method.name : hardware_by_id(result.hardware).name;
  const checked = state.selected.includes(result.id) ? 'checked' : '';
  const checkbox = result.available ? `<input type="checkbox" data-select="${result.id}" ${checked} aria-label="选择 ${hardware_by_id(result.hardware).name} ${method.name} 进行比较">` : '';
  return `<th scope="col"><div class="method-head">${checkbox}<span class="method-dot ${method.color}"></span><span>${name}</span></div><span class="source-label ${result.source_class || ''}">${result.available ? result.source_label : '未提供'}</span></th>`;
}

function detail_button(result, tab, content, class_name) {
  return `<button class="${class_name}" data-open="${result.id}" data-open-tab="${tab}" aria-expanded="${state.details.includes(result.id)}" aria-controls="detail-panel">${content}</button>`;
}

function throughput_summary(result) {
  const item = result.summary;
  const color = method_by_id(result.method).color;
  return detail_button(result, 'compute', `<span class="metric-value">${item.throughput}<small>TFLOP/s</small></span><span class="mini-track"><i class="${color}" style="width:${item.throughput_width}%"></i></span>`, 'visual-metric');
}

function memory_summary(result) {
  const item = result.summary.memory;
  if (!item) return '<span class="metric-missing" title="此方法未提供实际流量与缓存指标">—</span>';
  return detail_button(result, 'memory', `<span class="memory-value"><b>${item.traffic}<small>MiB</small></b><span>${item.bandwidth}<small>TB/s</small></span></span><span class="mini-label"><span>L2 命中</span><b>${item.hit}%</b></span><span class="mini-track"><i class="cache-bar" style="width:${item.hit}%"></i></span>`, 'visual-metric');
}

function activity_summary(result) {
  const rows = result.summary.activity;
  if (!rows.length) return '<span class="metric-missing" title="此方法未提供资源活动计数器">—</span>';
  const chart = rows.map(item => `<span class="activity-line"><span>${item.label}</span><span class="mini-track"><i style="width:${item.value}%;background:${item.color}"></i></span><b>${item.value}%</b></span>`).join('');
  return detail_button(result, 'compute', chart, 'visual-metric activity-metric');
}

function result_cell(result, metric) {
  if (!result.available) return `<td class="missing-cell">${metric === 'latency' ? `<span class="missing-value">—</span><div class="unavailable">${result.reason}</div>` : '<span class="unavailable">—</span>'}</td>`;
  const method = method_by_id(result.method);
  const cells = {
    latency: `<span class="latency-number">${result.latency}<small>μs</small></span><div class="latency-track"><i class="${method.color}" style="width:${result.bar_width}%"></i></div>`,
    deviation: `<span class="delta ${result.error_class}">${result.deviation}</span>`,
    components: `<div class="component">${detail_button(result, 'compute', '<span>计算</span>' + result.compute, 'component-link')}${detail_button(result, 'memory', '<span>访存</span>' + result.memory, 'component-link')}</div>`,
    throughput: throughput_summary(result),
    traffic: memory_summary(result),
    activity: activity_summary(result),
    bound: result.bound ? detail_button(result, 'latency', result.bound, 'bound-button') : '<span class="metric-missing" title="此结果未提供瓶颈分类">—</span>',
    action: detail_button(result, 'latency', '查看详情 <span aria-hidden="true">↗</span>', 'details-button')
  };
  return `<td>${cells[metric]}</td>`;
}

function render_group(group, results) {
  const is_hardware = state.view === 'hardware';
  const family = is_hardware ? `<span class="family ${group.family === 'NPU' ? 'npu' : ''}">${group.family}</span>` : `<span class="method-dot ${group.color}"></span>`;
  const metrics = [['latency', '总时延'], ['deviation', '偏差'], ['components', '计算 / 访存'], ['throughput', '有效算力<span class="row-hint">FLOPs / 总时延</span>'], ['traffic', 'HBM / 缓存<span class="row-hint">实际流量与命中率</span>'], ['activity', '资源活动<span class="row-hint">各硬件原生口径</span>'], ['bound', '主要瓶颈'], ['action', '']];
  const rows = metrics.map(([key, label]) => `<tr class="metric-row-${key}"><th scope="row">${label}</th>${results.map(item => result_cell(item, key)).join('')}</tr>`).join('');
  return `<section class="group" aria-label="${group.name} 比较"><div class="group-heading"><div><div class="group-title">${family}<h2>${group.name}</h2></div></div></div><div class="table-scroll" tabindex="0" role="region" aria-label="${group.name} 对比表，可横向滚动"><table class="comparison"><thead><tr><th scope="col">性能指标</th>${results.map(result_heading).join('')}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
}

function render_groups() {
  const results = visible_results();
  const groups = state.view === 'hardware' ? data.hardware : data.methods;
  const selected_groups = state.view === 'hardware' ? state.hardware : state.methods;
  const output = groups.filter(item => selected_groups.has(item.id)).map(group => {
    const members = results.filter(item => item[state.view] === group.id);
    return members.length ? render_group(group, members) : '';
  }).join('');
  by_id('groups').after(by_id('detail-panel'));
  by_id('groups').innerHTML = output;
  by_id('empty-state').hidden = results.length > 0;
  by_id('result-count').textContent = `${state.hardware.size} 种硬件 / ${state.methods.size} 种方法`;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
}

function render_tray() {
  by_id('compare-tray').hidden = state.selected.length === 0;
  by_id('selection-label').textContent = `已选择 ${state.selected.length} / 2 个结果`;
  by_id('compare-button').disabled = state.selected.length !== 2;
}

function announce(message) {
  by_id('announcement').textContent = message;
}

function close_details(restore_focus = false) {
  by_id('detail-panel').hidden = true;
  state.details = [];
  render_tray();
  document.querySelectorAll('[data-open]').forEach(button => button.setAttribute('aria-expanded', 'false'));
  if (restore_focus && state.origin) {
    const trigger = document.querySelector(`[data-open="${state.origin}"]`);
    if (trigger) trigger.focus();
  }
}

function update_filters() {
  const visible = new Set(visible_results().filter(item => item.available).map(item => item.id));
  state.selected = state.selected.filter(id => visible.has(id));
  close_details();
  render_groups();
  render_tray();
  announce('比较结果已按筛选条件更新');
}

function reset_filters() {
  state.hardware = new Set(['ascend', 'h100']);
  state.methods = new Set(data.methods.map(item => item.id));
  state.selected = [];
  state.view = 'hardware';
  render_filters();
  update_filters();
}

function result_name(result) {
  return `${hardware_by_id(result.hardware).name} · ${method_by_id(result.method).name}${result.method === 'roofline' ? ' · ' + result.source_label : ''}`;
}

function render_selectors() {
  const options = visible_results().filter(item => item.available);
  const paired = state.details.length === 2;
  by_id('detail-selectors').classList.toggle('paired', paired);
  by_id('detail-selectors').innerHTML = state.details.map((id, index) => {
    const choices = options.filter(item => item.id === id || !state.details.includes(item.id));
    return `<label>${paired ? ('结果 ' + (index === 0 ? 'A' : 'B')) : '评估结果'}<select data-detail-slot="${index}">${choices.map(item => `<option value="${item.id}" ${item.id === id ? 'selected' : ''}>${result_name(item)}</option>`).join('')}</select></label>`;
  }).join('');
}

function render_detail_content() {
  const paired = state.details.length === 2;
  by_id('detail-heading').textContent = paired ? '双结果详情对照' : '结果详情';
  by_id('detail-content').classList.toggle('paired', paired);
  by_id('detail-content').dataset.detailTab = state.tab;
  by_id('detail-content').setAttribute('aria-labelledby', `tab-${state.tab}`);
  by_id('detail-content').innerHTML = state.details.map(id => {
    const result = result_by_id(id);
    return `<article class="detail-card">${paired ? `<h3>${result_name(result)}</h3>` : ''}${result.details[state.tab]}</article>`;
  }).join('');
  document.querySelectorAll('[data-tab]').forEach(button => {
    const selected = button.dataset.tab === state.tab;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
}

function open_details(ids, tab = 'latency') {
  state.details = ids;
  state.tab = tab;
  state.origin = ids[0];
  render_selectors();
  render_detail_content();
  by_id('detail-panel').hidden = false;
  by_id('compare-tray').hidden = true;
  // Keep the selected group's summary immediately above its expanded details.
  const first = result_by_id(ids[0]);
  const group_id = state.view === 'hardware' ? first.hardware : first.method;
  const group = state.view === 'hardware' ? hardware_by_id(group_id) : method_by_id(group_id);
  const section = Array.from(document.querySelectorAll('.group')).find(item => item.getAttribute('aria-label') === `${group.name} 比较`);
  if (section) section.after(by_id('detail-panel'));
  document.querySelectorAll('[data-open]').forEach(button => button.setAttribute('aria-expanded', String(ids.includes(button.dataset.open))));
  by_id('detail-heading').focus({preventScroll: true});
  by_id('detail-panel').scrollIntoView({block: 'start', behavior: 'instant'});
}

function toggle_selection(input) {
  if (input.checked && state.selected.length === 2) {
    input.checked = false;
    announce('最多选择两个结果，请先取消一个已选结果');
    by_id('selection-label').textContent = '已选满 2 个，请先取消一个';
    return;
  }
  if (input.checked) state.selected.push(input.dataset.select);
  else state.selected = state.selected.filter(id => id !== input.dataset.select);
  render_tray();
  announce(`已选择 ${state.selected.length} 个结果，最多两个`);
}

function export_results() {
  const results = visible_results().map(({details, ...fields}) => fields);
  const payload = {schema: data.schema, synthetic: true, notice: data.notice, workload: data.workload, results};
  const json = JSON.stringify(payload, null, 2);
  by_id('export-json').value = json;
  by_id('download-json').href = 'data:application/json;charset=utf-8,' + encodeURIComponent(json);
  by_id('export-dialog').showModal();
  announce('当前筛选结果已准备好，可下载或复制 JSON');
}

function on_change(event) {
  const input = event.target;
  if (input.dataset.hardware || input.dataset.method) {
    const collection = input.dataset.hardware ? state.hardware : state.methods;
    const key = input.dataset.hardware || input.dataset.method;
    if (input.checked) collection.add(key);
    else collection.delete(key);
    update_filters();
  } else if (input.dataset.select) toggle_selection(input);
  else if (input.dataset.detailSlot !== undefined) {
    state.details[Number(input.dataset.detailSlot)] = input.value;
    render_selectors();
    render_detail_content();
  }
}

function on_click(event) {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.view) {
    state.view = button.dataset.view;
    close_details();
    render_groups();
  } else if (button.dataset.open) open_details([button.dataset.open], button.dataset.openTab);
  else if (button.dataset.tab) {
    state.tab = button.dataset.tab;
    render_detail_content();
  }
}

function on_tab_key(event) {
  const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End'];
  if (!keys.includes(event.key)) return;
  const buttons = Array.from(by_id('detail-tabs').querySelectorAll('button'));
  const index = buttons.indexOf(document.activeElement);
  if (index < 0) return;
  let next = event.key === 'ArrowRight' ? (index + 1) % buttons.length : (index + buttons.length - 1) % buttons.length;
  if (event.key === 'Home') next = 0;
  if (event.key === 'End') next = buttons.length - 1;
  event.preventDefault();
  state.tab = buttons[next].dataset.tab;
  render_detail_content();
  buttons[next].focus();
}

function bind_controls() {
  document.addEventListener('change', on_change);
  document.addEventListener('click', on_click);
  by_id('detail-tabs').addEventListener('keydown', on_tab_key);
  by_id('reset-button').addEventListener('click', reset_filters);
  by_id('empty-reset').addEventListener('click', reset_filters);
  by_id('export-button').addEventListener('click', export_results);
  by_id('close-detail').addEventListener('click', () => close_details(true));
  by_id('compare-button').addEventListener('click', () => open_details([...state.selected]));
  by_id('clear-selection').addEventListener('click', () => {state.selected = []; render_groups(); render_tray();});
  by_id('workload-button').addEventListener('click', () => by_id('workload-dialog').showModal());
  by_id('close-workload').addEventListener('click', () => by_id('workload-dialog').close());
  by_id('close-export').addEventListener('click', () => by_id('export-dialog').close());
  by_id('select-json').addEventListener('click', () => by_id('export-json').select());
}

render_filters();
render_groups();
bind_controls();
