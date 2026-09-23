'use strict';

function catalog_operator(id) {
  return data.catalog.operators.find(op => op.id === id);
}

function initialize_catalog() {
  state.config = Configuration.clone(data.initial_configuration || data.catalog.default_config);
  state.baseline = data.demo_results || data.results;
  state.baselineWorkload = data.demo_workload || data.workload;
  state.baselineMatrix = data.demo_matrix || data.matrix;
  state.demoMethods = Configuration.clone(data.demo_methods || data.methods);
  if (data.evaluation) {
    state.hardware = new Set(data.evaluation.hardware_ids);
    state.methods = new Set(data.evaluation.method_ids);
    state.chart = 'latency';
  }
  const categories = [...new Set(data.catalog.groups.map(op => op.category))].sort();
  by_id('operator-category').innerHTML += categories.map(name => `<option value="${escape_html(name)}">${escape_html(name)}</option>`).join('');
  ['operator-search', 'operator-category'].forEach(id => by_id(id).addEventListener(id === 'operator-search' ? 'input' : 'change', render_operator_list));
  by_id('input-form-select').addEventListener('change', event => select_operator(event.target.value));
  by_id('hardware-search').addEventListener('input', render_hardware_options);
  by_id('operator-list').addEventListener('click', event => {
    const button = event.target.closest('[data-operator]');
    if (button) {
      const group = data.catalog.groups.find(item => item.id === button.dataset.operator);
      select_operator(group.variants.includes(state.draft.operator_id) ? state.draft.operator_id : group.variants[0]);
    }
  });
  by_id('restore-demo').addEventListener('click', () => {
    by_id('operator-search').value = '';
    by_id('operator-category').value = 'all';
    select_operator('demo:matmul');
    by_id('operator-list').scrollTop = 0;
  });
  by_id('configuration-form').addEventListener('submit', event => {event.preventDefault(); apply_configuration();});
  by_id('configuration-form').addEventListener('focusout', event => {
    if (event.target.matches('input,select')) validate_editor(false);
  });
  by_id('hardware-filter').addEventListener('click', event => {
    const button = event.target.closest('[data-hardware-bulk]');
    if (!button) return;
    if (button.dataset.hardwareBulk === 'none') state.hardware.clear();
    else by_id('hardware-options').querySelectorAll('[data-hardware]').forEach(input => state.hardware.add(input.dataset.hardware));
    render_hardware_options();
    update_filters();
  });
  render_workload_heading();
}

function render_hardware_options() {
  const search = by_id('hardware-search').value.toLowerCase().trim();
  const items = data.hardware.filter(hw => `${hw.name} ${hw.note} ${hw.family}`.toLowerCase().includes(search));
  by_id('hardware-options').innerHTML = items.map(hw => `<label class="filter-option" title="${escape_html(hw.note)}"><input type="checkbox" data-hardware="${hw.id}" ${state.hardware.has(hw.id) ? 'checked' : ''}><span>${escape_html(hw.name)}</span><small>${hw.family}</small></label>`).join('') || '<p class="catalog-empty">没有匹配的硬件。</p>';
}

function render_operator_list() {
  const search = by_id('operator-search').value.toLowerCase().trim();
  const category = by_id('operator-category').value;
  const items = data.catalog.groups.filter(group => (category === 'all' || group.category === category) && `${group.name} ${group.category}`.toLowerCase().includes(search));
  by_id('catalog-count').textContent = `${items.length} / ${data.catalog.groups.length} 个算子`;
  by_id('operator-list').innerHTML = items.map(group => `<button type="button" class="operator-item" data-operator="${escape_html(group.id)}" aria-pressed="${group.variants.includes(state.draft.operator_id)}"><span>${escape_html(group.name)}</span><small>${escape_html(group.category)}${group.variants.length > 1 ? ` · ${group.variants.length} 种输入形式` : ''}${catalog_operator(group.variants[0]).configurable ? '' : ' · 仅目录'}</small></button>`).join('') || '<p class="catalog-empty">未找到算子，试试其他名称或分类。</p>';
}

function open_configuration() {
  state.draft = Configuration.clone(state.config);
  by_id('operator-search').value = '';
  by_id('operator-category').value = 'all';
  render_operator_list();
  render_configuration();
  by_id('workload-dialog').showModal();
  by_id('operator-search').focus();
}

function select_operator(id) {
  const from_list = Boolean(document.activeElement?.dataset.operator);
  state.draft = id === 'demo:matmul' ? Configuration.clone(data.catalog.default_config) : Configuration.from_operator(catalog_operator(id));
  render_operator_list();
  render_configuration();
  by_id('config-editor').scrollTop = 0;
  if (from_list) [...by_id('operator-list').querySelectorAll('[data-operator]')].find(button => button.dataset.operator === catalog_operator(id).group_id)?.focus({preventScroll: true});
}

function tensor_editor(tensor, index, op) {
  const template = op.inputs[index];
  const shape = (tensor.shape || []).map(value => value ?? '?').join(', ');
  const error_id = `tensor-error-${index}`;
  return `<fieldset class="tensor-input"><legend><b>${escape_html(tensor.name)}</b><span>${tensor.role === 'parameter' ? '参数张量' : '输入'}</span></legend><div class="tensor-fields"><label>形状<input id="shape-${index}" name="shape-${index}" value="${escape_html(shape)}" autocomplete="off" spellcheck="false" aria-describedby="template-${index} ${error_id}"></label><label>dtype<select id="dtype-${index}" aria-describedby="${error_id}">${data.catalog.dtypes.map(dtype => `<option value="${dtype}" ${dtype === tensor.dtype ? 'selected' : ''}>${dtype.toUpperCase()}</option>`).join('')}</select></label></div><p id="template-${index}" class="tensor-template">模板 ${escape_html(template.expression)}</p><p id="${error_id}" class="field-error" hidden></p></fieldset>`;
}

function render_configuration() {
  const op = catalog_operator(state.draft.operator_id);
  by_id('editor-name').textContent = op.display_name;
  by_id('editor-category').textContent = op.category;
  const group = data.catalog.groups.find(item => item.id === op.group_id);
  by_id('input-form-control').hidden = group.variants.length < 2;
  by_id('input-form-select').innerHTML = group.variants.map(id => `<option value="${id}" ${id === op.id ? 'selected' : ''}>${escape_html(catalog_operator(id).template_label)}</option>`).join('');
  const missing = op.inputs.some(t => t.shape.includes(null));
  by_id('operator-note').textContent = op.reason || (op.category === 'Flow' ? '流程标记，不是独立计算内核。' : missing ? '模板含未定义维度，请将 ? 替换为实际大小。' : '按张量设置形状与精度。');
  by_id('tensor-inputs').innerHTML = state.draft.inputs.map((tensor, index) => tensor_editor(tensor, index, op)).join('');
  by_id('operator-attributes').hidden = !(op.parameters || []).length;
  by_id('attribute-inputs').innerHTML = (op.parameters || []).map(field => {
    const current = state.draft.attributes?.[field.name];
    const display = Array.isArray(current) ? current.join(',') : current ?? '';
    return `<label>${escape_html(field.label)}<input id="attribute-${field.name}" data-attribute="${field.name}" value="${escape_html(String(display))}" inputmode="numeric" autocomplete="off"></label>`;
  }).join('');
  by_id('demo-options').hidden = op.domain !== 'demo';
  by_id('accumulator-dtype').value = state.draft.options.accumulator_dtype || 'fp32';
  by_id('tensor-layout').value = state.draft.options.layout || 'row-major';
  by_id('transpose-a').checked = !!state.draft.options.transpose_a;
  by_id('transpose-b').checked = !!state.draft.options.transpose_b;
  by_id('output-templates').innerHTML = op.outputs.length ? '<h4>输出模板 · 尚未推导实际形状</h4>' + op.outputs.map(tensor => `<p><b>${escape_html(tensor.name)}</b> · ${escape_html(tensor.dtype)}<br><code>${escape_html(typeof tensor.shape === 'string' ? tensor.shape : JSON.stringify(tensor.shape))}</code></p>`).join('') : '<p>实际输出形状待评估后端返回。</p>';
  by_id('config-error').hidden = true;
  by_id('apply-config').disabled = !op.configurable;
  by_id('apply-hint').textContent = op.configurable ? '应用配置后可运行评估' : op.reason;
}

function read_configuration() {
  const config = Configuration.clone(state.draft);
  config.inputs = config.inputs.map((tensor, index) => ({...tensor,
    shape: Configuration.parse_shape(by_id(`shape-${index}`).value), dtype: by_id(`dtype-${index}`).value}));
  config.attributes = Object.fromEntries((catalog_operator(config.operator_id).parameters || []).map(field => {
    const text = by_id(`attribute-${field.name}`).value.trim();
    const parsed = field.type === 'permutation' ? text.split(',').map(value => Number(value.trim())) : (text === '' ? null : Number(text));
    return [field.name, parsed];
  }));
  if (config.domain === 'demo') config.options = {layout: by_id('tensor-layout').value,
    accumulator_dtype: by_id('accumulator-dtype').value,
    transpose_a: by_id('transpose-a').checked, transpose_b: by_id('transpose-b').checked};
  return config;
}

function validate_editor(focus) {
  const config = read_configuration();
  const errors = Configuration.validate(config, catalog_operator(config.operator_id), data.catalog.dtypes);
  document.querySelectorAll('.field-error').forEach(node => {node.hidden = true; node.textContent = '';});
  by_id('configuration-form').querySelectorAll('[aria-invalid]').forEach(node => node.removeAttribute('aria-invalid'));
  errors.forEach(error => {
    const input = by_id(error.field);
    input?.setAttribute('aria-invalid', 'true');
    const inline = by_id(`tensor-error-${error.field.split('-').pop()}`);
    if (inline) {inline.textContent += error.message + ' '; inline.hidden = false;}
  });
  by_id('config-error').hidden = !errors.length;
  by_id('config-error').innerHTML = errors.map(error => `<a href="#${error.field}">${escape_html(error.message)}</a>`).join('');
  if (focus && errors.length) by_id('config-error').focus();
  return {config, errors};
}

function apply_configuration() {
  const {config, errors} = validate_editor(true);
  if (errors.length) return;
  const previous = state.config.domain;
  state.config = config;
  reset_evaluation();
  const demo = Configuration.matches_demo(config, data.catalog.default_config);
  data.results = Configuration.project(config, state.baseline, data.pending_results, data.catalog.default_config);
  data.workload = demo ? state.baselineWorkload : Configuration.workload(config);
  if (previous === 'demo' && config.domain !== 'demo' && ![...state.hardware].some(id => id.startsWith('modeling:') || id.startsWith('tilesim:'))) {
    state.hardware = new Set(['modeling:Adevice03_Server', 'modeling:H100_Server', 'modeling:H200_Server'].filter(id => hardware_by_id(id)));
  } else if (previous !== 'demo' && demo) state.hardware = new Set(data.hardware.filter(hw => hw.group === 'demo').map(hw => hw.id));
  state.selected = [];
  state.selecting = false;
  state.scope = null;
  by_id('workload-dialog').close();
  render_workload_heading();
  render_filters();
  update_filters();
  render_evaluation_controls();
  announce('配置已应用。' + (demo ? '展示合成示例。' : '当前配置尚未评估。'));
}

function workload_summary() {
  const config = state.config;
  const dtypes = [...new Set(config.inputs.map(tensor => tensor.dtype.toUpperCase()))].join(' / ');
  return `${config.inputs.length} 个输入张量 · ${dtypes}`;
}

function render_workload_heading() {
  const demo = Configuration.matches_demo(state.config, data.catalog.default_config);
  by_id('workload-name').textContent = state.config.operator;
  const shape = state.config.inputs.map(tensor => `${tensor.name} [${tensor.shape.join(' × ')}]`).join(' · ');
  by_id('workload-shape').textContent = demo ? '4096 × 4096 × 4096' : `${state.config.inputs[0]?.name || ''} [${state.config.inputs[0]?.shape.join(' × ') || '—'}]` + (state.config.inputs.length > 1 ? ` +${state.config.inputs.length - 1} 张量` : '');
  by_id('workload-shape').title = shape;
  by_id('workload-summary').textContent = demo ? '输入输出 FP16 · 累加 FP32 · 设备侧单 kernel' : workload_summary();
  if (data.evaluation || !data.synthetic) {
    by_id('workload-summary').textContent = workload_summary() + ' · 单算子性能预测';
    by_id('workload-status').textContent = state.evaluating ? '正在评估当前配置…' : data.evaluation ? '已运行评估 · 模型预测，非设备实测' : '暂无预测结果 · 可重新运行';
    by_id('matrix-data-note').textContent = '未接入实测参考 · 不计算参考偏差';
    return;
  }
  by_id('workload-status').textContent = demo ? '界面示例 · 未执行真实评估' : '配置已就绪 · 尚未评估';
  by_id('matrix-data-note').textContent = demo ? '参考：同硬件 Profiling · 全部为合成示例' : '当前配置尚无结果 · 点击运行评估';
}

function pending_detail(record) {
  const config = state.config;
  const device = hardware_by_id(record.hardware);
  const profile = '硬件配置';
  return `<div class="missing-detail"><span class="empty-mark">—</span><h3>${escape_html(record.reason)}</h3><p>此组合暂无可用性能数值。</p><p class="note">${escape_html(device.note)} · ${data.synthetic && device.group === 'demo' ? '合成示例配置' : profile}</p></div><div class="pending-inputs"><h3>${escape_html(config.operator)} · 输入配置</h3><dl class="facts">${config.inputs.map(t => `<div><dt>${escape_html(t.name)}</dt><dd>[${t.shape.join(', ')}] · ${escape_html(t.dtype.toUpperCase())}</dd></div>`).join('')}</dl></div>`;
}
