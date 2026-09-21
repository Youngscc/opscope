'use strict';
const data = JSON.parse(document.getElementById('result-data').textContent);
const state = {hardware: new Set(data.hardware.filter(item => item.group === 'demo').map(item => item.id)), methods: new Set(data.methods.map(item => item.id)), metric: 'latency', chart: 'error', scope: null, selecting: false, selected: [], details: [], tab: 'overview', onlyDifferences: false, origin: null};
const by_id = id => document.getElementById(id);
const hardware_by_id = id => data.hardware.find(item => item.id === id);
const method_by_id = id => data.methods.find(item => item.id === id);
const result_by_id = id => data.results.find(item => item.id === id);
const escape_html = value => String(value ?? '—').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
const method_name = id => id === 'profile' ? 'Profiling' : method_by_id(id).name;

function announce(message) {
  by_id('announcement').textContent = message;
}

function visible_results() {
  return data.results.filter(item => state.hardware.has(item.hardware) && state.methods.has(item.method));
}

function result_name(result) {
  return `${hardware_by_id(result.hardware).name} · ${method_name(result.method)}`;
}

function render_filters() {
  render_hardware_options();
  by_id('method-options').innerHTML = data.methods.map(item => `<label class="filter-option"><input type="checkbox" data-method="${item.id}" ${state.methods.has(item.id) ? 'checked' : ''}><i class="method-dot ${item.id}" aria-hidden="true"></i><span>${method_name(item.id)}</span></label>`).join('');
}

function cell_markup(result) {
  const {available, id, matrix} = result;
  const error = state.metric === 'error';
  const main = !available ? '—' : error ? (result.method === 'profile' ? '参考' : matrix.error_label) : `${result.latency}<small>μs</small>`;
  const secondary = !available ? result.reason : error ? `${result.latency} μs` : result.method === 'profile' ? '同硬件参考' : `较参考 ${matrix.error_label}`;
  const source = available && result.method === 'roofline' ? `<span class="calibration ${result.source_class.includes('generic') ? 'generic' : ''}">${result.source_label}</span>` : '';
  const check = state.selecting && available ? `<label class="cell-check"><input type="checkbox" data-select="${id}" ${state.selected.includes(id) ? 'checked' : ''} aria-label="选择 ${result_name(result)} 进行比较"></label>` : '';
  return `<td class="matrix-cell ${available ? '' : 'is-missing'} ${result.method === 'profile' ? 'reference-cell' : ''} ${state.selected.includes(id) ? 'is-selected' : ''}"><div class="cell-inner">${check}<button class="cell-result" data-open="${id}" aria-haspopup="dialog" aria-controls="detail-panel" aria-label="${result_name(result)}，${available ? result.latency + ' 微秒' : result.reason}，查看详情"><span class="cell-value">${main}</span><span class="cell-secondary">${secondary}</span>${available ? `<span class="cell-meta"><span>${matrix.note}</span>${source}</span>` : ''}<span class="cell-arrow" aria-hidden="true">↗</span></button></div></td>`;
}

function render_matrix() {
  const methods = data.methods.filter(item => state.methods.has(item.id));
  const hardware = data.hardware.filter(item => state.hardware.has(item.id));
  const visible = visible_results();
  by_id('matrix-head').innerHTML = `<tr><th scope="col" class="axis-corner">硬件 <span aria-hidden="true">↓</span> <span class="separator">/</span> 方法 <span aria-hidden="true">→</span></th>${methods.map(item => `<th scope="col" class="method-column ${item.id === 'profile' ? 'reference-cell' : ''}"><button class="axis-button" data-scope-method="${item.id}"><i class="method-dot ${item.id}" aria-hidden="true"></i>${method_name(item.id)}<span aria-hidden="true">↗</span></button><small>${item.id === 'profile' ? '同硬件参考' : item.source}</small></th>`).join('')}</tr>`;
  by_id('matrix-body').innerHTML = methods.length ? hardware.map(hw => `<tr><th scope="row" class="hardware-column"><button class="axis-button" data-scope-hardware="${hw.id}"><span>${hw.name}</span><span aria-hidden="true">↗</span></button><small>${hw.family} · ${hw.group === 'demo' ? '示例' : '目录配置'}</small></th>${methods.map(method => cell_markup(visible.find(row => row.hardware === hw.id && row.method === method.id))).join('')}</tr>`).join('') : '';
  by_id('result-matrix').style.setProperty('--method-count', methods.length || 1);
  by_id('matrix-wrap').hidden = !visible.length;
  by_id('empty-state').hidden = !!visible.length;
  by_id('hardware-count').textContent = state.hardware.size;
  by_id('method-count').textContent = state.methods.size;
  by_id('result-count').textContent = `${visible.filter(item => item.available).length} / ${visible.length} 有结果`;
  document.querySelectorAll('[data-metric]').forEach(button => button.setAttribute('aria-pressed', button.dataset.metric === state.metric));
  render_scope();
}

function render_scope() {
  document.querySelectorAll('[data-scope-method], [data-scope-hardware]').forEach(button => {
    const active = state.scope && ((button.dataset.scopeMethod && button.dataset.scopeMethod === state.scope.method) || (button.dataset.scopeHardware && button.dataset.scopeHardware === state.scope.hardware));
    button.setAttribute('aria-pressed', String(Boolean(active)));
  });
  by_id('chart-reset').hidden = !state.scope;
}

function render_tray() {
  by_id('compare-tray').hidden = !state.selecting;
  by_id('selection-mode').setAttribute('aria-pressed', String(state.selecting));
  by_id('selection-mode').textContent = state.selecting ? '退出选择' : '选择对比';
  by_id('selection-label').textContent = state.selected.length ? state.selected.map(id => result_name(result_by_id(id))).join('  ↔  ') : '勾选两个结果，逐项比较详情';
  by_id('compare-button').disabled = state.selected.length !== 2;
}

function update_filters() {
  const visible = new Set(visible_results().filter(item => item.available).map(item => item.id));
  state.selected = state.selected.filter(id => visible.has(id));
  if (state.scope && ((state.scope.hardware && !state.hardware.has(state.scope.hardware)) || (state.scope.method && !state.methods.has(state.scope.method)))) state.scope = null;
  render_matrix();
  render_tray();
  render_chart();
  announce('矩阵与图表已按筛选更新');
}

function reset_filters() {
  const group = state.config.domain === 'demo' ? 'demo' : 'modeling';
  state.hardware = new Set(data.hardware.filter(item => item.group === group).map(item => item.id));
  by_id('hardware-search').value = '';
  state.methods = new Set(data.methods.map(item => item.id));
  state.selected = [];
  state.scope = null;
  render_filters();
  update_filters();
}

function plot_results() {
  return visible_results().filter(item => !state.scope || (state.scope.hardware ? item.hardware === state.scope.hardware : item.method === state.scope.method));
}

function chart_axis(metric) {
  const ticks = data.matrix.scales[metric === 'error' ? 'error_ticks' : 'latency_ticks'];
  return `<div class="chart-axis"><span>${metric === 'error' ? '偏差 %' : '耗时 μs'}</span><div>${ticks.map((tick, index) => `<span class="axis-tick ${index === 0 ? 'first' : index === ticks.length - 1 ? 'last' : ''}" style="left:${tick.position}%">${tick.label}</span>`).join('')}</div><span></span></div>`;
}

function chart_mark(result, metric) {
  const error = metric === 'error';
  const value = error ? result.matrix.error_label : `${result.latency} μs`;
  const location = error ? `left:${result.matrix.error_position}%` : `width:${result.matrix.latency_width}%`;
  const label = `${result_name(result)} · ${error ? '较同硬件参考 ' : ''}${value}`;
  const side_label = !error ? `${method_name(result.method)}<span class="narrow-chart-value">${value}</span>` : state.scope ? value : '';
  return `<div class="chart-lane"><div class="lane-plot"><button class="chart-mark ${result.method} ${error ? 'point' : 'bar'}" data-open="${result.id}" aria-label="${label}，查看详情" title="${label}" style="${location}">${error ? '<i aria-hidden="true"></i>' : `<span class="bar-number">${result.latency}</span>`}</button></div><span class="lane-value">${side_label}</span></div>`;
}

function chart_group(hw, rows, metric) {
  const valid = rows.filter(row => row.available && (metric !== 'error' || row.matrix.error_position !== null));
  const show_names = Boolean(state.scope);
  const marks = valid.map(row => `<div class="chart-series"><span class="lane-name">${show_names ? method_name(row.method) : ''}</span>${chart_mark(row, metric)}</div>`).join('');
  return `<div class="chart-group"><div class="chart-hardware">${hw.name.replace('NVIDIA ', '')}</div><div class="chart-series-group ${metric}">${marks || '<div class="chart-no-data">— 暂无结果</div>'}</div></div>`;
}

function render_chart() {
  const rows = plot_results();
  const no_reference = rows.some(row => row.available) && !rows.some(row => row.available && row.matrix.error_position !== null);
  const metric = state.chart === 'error' && no_reference ? 'latency' : state.chart;
  const scope = state.scope?.hardware ? hardware_by_id(state.scope.hardware).name + ' · 比较方法' : state.scope?.method ? method_name(state.scope.method) + ' · 比较硬件' : '全局对比';
  by_id('chart-heading').textContent = scope;
  by_id('chart-description').textContent = metric === 'error' ? '参考偏差 · 左侧低估，右侧高估，越接近零越接近本次参考。' : state.scope?.hardware ? '同一硬件 · 比较各方法预测与参考的耗时差异。' : '总耗时 · 固定同一方法后，可以直观比较不同硬件。';
  by_id('chart-footnote').textContent = no_reference ? '暂无可用参考，展示绝对耗时。' : metric === 'error' ? '每行使用该硬件的 Profiling 作为零点；缺失结果不作零值绘制。' : '统一零起点刻度 · 更短的预测不代表更准确。';
  const methods = data.methods.filter(item => state.methods.has(item.id) && rows.some(row => row.method === item.id && row.available) && (!state.scope?.method || item.id === state.scope.method) && (metric !== 'error' || item.id !== 'profile'));
  const plotted = rows.filter(row => metric !== 'error' || row.method !== 'profile');
  by_id('chart-legend').innerHTML = methods.map(item => `<span><i class="legend-mark ${item.id}" aria-hidden="true"></i>${method_name(item.id)}</span>`).join('');
  const groups = data.hardware.filter(hw => state.hardware.has(hw.id) && (!state.scope?.hardware || hw.id === state.scope.hardware));
  const only_reference = rows.length && rows.every(row => row.method === 'profile') && metric === 'error';
  by_id('analysis-chart').innerHTML = only_reference ? '<div class="reference-note">Profiling 是每个硬件的参考基线，偏差为 0%。切换“总耗时”比较硬件。</div>' : chart_axis(metric) + groups.map(hw => chart_group(hw, plotted.filter(row => row.hardware === hw.id), metric)).join('');
  by_id('analysis-chart').classList.toggle('focused', Boolean(state.scope));
  const has_results = rows.some(row => row.available);
  by_id('analysis-chart').hidden = !has_results;
  by_id('chart-empty').hidden = has_results;
  if (!has_results) {
    by_id('chart-description').textContent = '此配置尚无可对比的性能数据。';
    by_id('chart-footnote').textContent = '未运行的组合不作为零值绘制。';
  }
  document.querySelectorAll('[data-chart]').forEach(button => button.setAttribute('aria-pressed', button.dataset.chart === metric));
}

function render_selectors() {
  const paired = state.details.length === 2;
  by_id('detail-selectors').hidden = !paired;
  if (!paired) return;
  const choices = visible_results().filter(item => item.available);
  by_id('detail-selectors').innerHTML = state.details.map((id, index) => `<label>结果 ${index ? 'B' : 'A'}<select data-detail-slot="${index}">${choices.filter(item => item.id === id || !state.details.includes(item.id)).map(item => `<option value="${item.id}" ${item.id === id ? 'selected' : ''}>${result_name(item)}</option>`).join('')}</select></label>`).join('');
}

function paired_facts(left, right) {
  const labels = [...new Set([...left.facts, ...right.facts].map(item => item.label))];
  let count = 0;
  const rows = labels.map(label => {
    const a = left.facts.find(item => item.label === label);
    const b = right.facts.find(item => item.label === label);
    const same = a?.known && b?.known && a.value === b.value;
    if (state.onlyDifferences && same) return '';
    count++;
    const style = same ? 'same-value' : a?.known && b?.known ? 'different-value' : 'unknown-value';
    return `<tr class="${style}"><th scope="row">${escape_html(label)}</th><td>${escape_html(a?.value)}</td><td>${escape_html(b?.value)}</td></tr>`;
  }).join('');
  return count ? `<div class="pair-table-wrap"><table class="pair-table"><thead><tr><th scope="col">指标</th><th scope="col">结果 A</th><th scope="col">结果 B</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="note">已提供的字段一致。</p>';
}

function paired_content(records) {
  const [left, right] = records.map(row => row.sections[state.tab]);
  const sections = left.map((section, index) => `<section class="detail-section"><h3>${section.title}</h3>${paired_facts(section, right[index])}${section.extra || right[index].extra ? `<div class="pair-visuals"><div><h4 class="visual-result-name">结果 A · ${result_name(records[0])}</h4>${section.extra}</div><div><h4 class="visual-result-name">结果 B · ${result_name(records[1])}</h4>${right[index].extra}</div></div>` : ''}</section>`).join('');
  const metadata = left[0].metadata_facts.length ? `<details class="task-run"><summary>任务、来源与运行记录</summary>${paired_facts({facts: left[0].metadata_facts}, {facts: right[0].metadata_facts})}</details>` : '';
  return sections + metadata;
}

function single_content(record) {
  return record.sections[state.tab].map(section => {
    let body = record.details[section.key];
    if (section.key === 'latency') {
      const reference = section.facts.find(item => item.label === 'Profiling 参考');
      body = (reference ? `<p class="note">Profiling 参考：${escape_html(reference.value)}</p>` : '') + section.extra;
    }
    return `<section class="detail-section"><h3>${section.title}</h3>${body}</section>`;
  }).join('');
}

function render_detail_content() {
  const records = state.details.map(result_by_id);
  const paired = records.length === 2;
  const available = records.every(row => row.available);
  by_id('detail-panel').classList.toggle('paired', paired);
  by_id('detail-heading').textContent = paired ? '双结果对照' : result_name(records[0]);
  by_id('detail-subtitle').textContent = state.config.operator + ' · ' + workload_summary();
  by_id('diff-control').hidden = !paired;
  by_id('only-differences').checked = state.onlyDifferences;
  by_id('detail-tabs').hidden = !available;
  by_id('detail-tabs').innerHTML = data.matrix.tabs.map(tab => `<button id="tab-${tab.id}" data-tab="${tab.id}" role="tab" aria-controls="detail-content" aria-selected="${state.tab === tab.id}" tabindex="${state.tab === tab.id ? 0 : -1}">${tab.name}</button>`).join('');
  by_id('detail-content').setAttribute('aria-labelledby', available ? `tab-${state.tab}` : 'detail-heading');
  by_id('detail-content').dataset.detailTab = state.tab;
  const notice = paired ? data.matrix.pairs[state.details.join('|')] : null;
  by_id('comparison-notice').hidden = !paired;
  by_id('comparison-notice').textContent = notice?.text || '';
  by_id('comparison-notice').classList.toggle('has-issues', Boolean(notice?.issues.length));
  if (!available) by_id('detail-content').innerHTML = pending_detail(records[0]);
  else by_id('detail-content').innerHTML = paired ? paired_content(records) : single_content(records[0]);
}

function open_details(ids, origin) {
  state.details = ids;
  state.origin = origin || document.activeElement;
  state.tab = 'overview';
  state.onlyDifferences = false;
  render_selectors();
  render_detail_content();
  by_id('detail-panel').showModal();
  by_id('detail-panel').querySelector('.detail-scroll').scrollTop = 0;
  by_id('close-detail').focus({preventScroll: true});
}

function toggle_selection(input) {
  if (input.checked && state.selected.length === 2) {
    input.checked = false;
    by_id('selection-label').textContent = '已选满两条，请先取消一条再选择';
    announce('最多选择两个结果，请先取消一个');
    return;
  }
  if (input.checked) state.selected.push(input.dataset.select);
  else state.selected = state.selected.filter(id => id !== input.dataset.select);
  input.closest('.matrix-cell').classList.toggle('is-selected', input.checked);
  render_tray();
  announce(`已选择 ${state.selected.length} 个结果`);
}

function export_results(detail_only = false) {
  const records = detail_only ? state.details.map(result_by_id) : visible_results();
  const results = records.map(({details, sections, matrix, ...fields}) => fields);
  const payload = {schema: data.schema, synthetic: true, notice: data.notice, workload: data.workload, configuration: state.config, catalog_revision: data.catalog.revision, results};
  const json = JSON.stringify(Configuration.public_export(payload, data.catalog), null, 2);
  by_id('export-json').value = json;
  by_id('export-scope').textContent = `${detail_only ? '当前详情' : '当前筛选结果'} · ${results.length} 条 · 示例数据`;
  by_id('download-json').href = 'data:application/json;charset=utf-8,' + encodeURIComponent(json);
  by_id('export-dialog').showModal();
  announce('JSON 已准备好，可下载或复制');
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
    document.querySelector(`[data-detail-slot="${input.dataset.detailSlot}"]`).focus();
  } else if (input.id === 'only-differences') {
    state.onlyDifferences = input.checked;
    render_detail_content();
  }
}

function select_tab(tab) {
  state.tab = tab;
  render_detail_content();
  by_id(`tab-${tab}`).focus({preventScroll: true});
  by_id('detail-panel').querySelector('.detail-scroll').scrollTop = 0;
}

function on_click(event) {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.open) open_details([button.dataset.open], button);
  else if (button.dataset.metric) {
    state.metric = button.dataset.metric;
    render_matrix();
  } else if (button.dataset.chart) {
    state.chart = button.dataset.chart;
    render_chart();
  } else if (button.dataset.scopeHardware || button.dataset.scopeMethod) {
    state.scope = button.dataset.scopeHardware ? {hardware: button.dataset.scopeHardware} : {method: button.dataset.scopeMethod};
    render_scope();
    render_chart();
    announce(by_id('chart-heading').textContent + '，图表已更新');
  } else if (button.dataset.tab) select_tab(button.dataset.tab);
}

function on_tab_key(event) {
  if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
  const tabs = data.matrix.tabs.map(tab => tab.id);
  const index = tabs.indexOf(state.tab);
  let next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : (index + tabs.length - 1) % tabs.length;
  if (event.key === 'Home') next = 0;
  if (event.key === 'End') next = tabs.length - 1;
  event.preventDefault();
  select_tab(tabs[next]);
}

function bind_dialogs() {
  for (const dialog of document.querySelectorAll('dialog')) {
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
  }
  by_id('detail-panel').addEventListener('close', () => {
    state.details = [];
    if (state.origin?.isConnected) state.origin.focus({preventScroll: true});
  });
  document.addEventListener('click', event => document.querySelectorAll('.filter-menu[open]').forEach(menu => {
    if (!menu.contains(event.target)) menu.open = false;
  }));
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    const menu = document.querySelector('.filter-menu[open]');
    if (menu) {menu.open = false; menu.querySelector('summary').focus();}
  });
}

function bind_controls() {
  document.addEventListener('change', on_change);
  document.addEventListener('click', on_click);
  by_id('detail-tabs').addEventListener('keydown', on_tab_key);
  by_id('reset-button').addEventListener('click', reset_filters);
  by_id('empty-reset').addEventListener('click', reset_filters);
  by_id('export-button').addEventListener('click', () => export_results());
  by_id('export-detail').addEventListener('click', () => export_results(true));
  by_id('close-detail').addEventListener('click', () => by_id('detail-panel').close());
  by_id('compare-button').addEventListener('click', event => open_details([...state.selected], event.currentTarget));
  by_id('clear-selection').addEventListener('click', () => {state.selected = []; render_matrix(); render_tray();});
  by_id('selection-mode').addEventListener('click', () => {state.selecting = !state.selecting; if (!state.selecting) state.selected = []; render_matrix(); render_tray();});
  by_id('chart-reset').addEventListener('click', () => {state.scope = null; render_scope(); render_chart();});
  by_id('workload-button').addEventListener('click', open_configuration);
  by_id('close-workload').addEventListener('click', () => by_id('workload-dialog').close());
  by_id('close-export').addEventListener('click', () => by_id('export-dialog').close());
  by_id('select-json').addEventListener('click', () => by_id('export-json').select());
  bind_dialogs();
}

initialize_catalog();
render_filters();
render_matrix();
render_tray();
render_chart();
bind_controls();
