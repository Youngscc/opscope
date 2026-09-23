'use strict';

async function evaluation_request(path, body) {
  const response = await fetch(path.replace('/api/', '/api/opscope/'), {method: body ? 'POST' : 'GET',
    headers: body ? {'Content-Type': 'application/json'} : {},
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '评估服务暂不可用');
  return result;
}

function evaluation_label() {
  return data.evaluation ? '模型预测 · 非实测' : data.synthetic ? '示例数据' : '待评估';
}

function render_evaluation_controls() {
  const busy = Boolean(state.evaluating);
  by_id('run-evaluation').disabled = busy || !state.serviceReady || !state.hardware.size || !state.methods.size;
  by_id('run-evaluation').textContent = busy ? '评估中…' : '运行评估';
  by_id('snapshot-link').hidden = !data.evaluation || state.evaluating || data.evaluation.status === 'failed' || !state.serviceReady;
  if (data.evaluation) by_id('snapshot-link').href = `/api/opscope/evaluations/${data.evaluation.id}/snapshot`;
  by_id('data-kind').textContent = evaluation_label();
  document.querySelector('.detail-demo').textContent = '/ ' + evaluation_label();
}

function reset_evaluation() {
  state.evaluationToken = (state.evaluationToken || 0) + 1;
  state.evaluating = false;
  delete data.evaluation;
  data.schema = 'operator-ui-demo-v1';
  data.synthetic = true;
  data.notice = '合成 UI 示例，非实测或实际仿真结果';
  data.methods = Configuration.clone(state.demoMethods);
  data.matrix = state.baselineMatrix;
  by_id('evaluation-message').textContent = state.serviceMessage || '';
  render_evaluation_controls();
}

function show_evaluation_pending() {
  data.synthetic = false;
  data.schema = 'opscope-evaluation-v1';
  data.notice = '评估尚未完成';
  delete data.evaluation;
  data.results = Configuration.project(state.config, [], data.pending_results, {}).map(row => {
    const selected = state.hardware.has(row.hardware) && state.methods.has(row.method);
    return {...row, synthetic: false, workload: {...row.workload, synthetic: false}, reason: selected ? '等待评估' : '本批次未选择此组合',
      task: {...row.task, synthetic: false, status: selected ? 'queued' : 'not_run'}};
  });
  data.workload = {...Configuration.workload(state.config), synthetic: false};
  state.selected = []; state.scope = null;
  by_id('detail-panel').close();
  render_workload_heading(); update_filters(); render_evaluation_controls();
}

function accept_evaluation(payload, status = 'completed') {
  Object.assign(data, payload);
  state.config = Configuration.clone(payload.initial_configuration);
  state.evaluating = status === 'running';
  const info = payload.evaluation;
  by_id('evaluation-message').textContent = state.evaluating
    ? `已处理 ${info.finished_count} / ${info.total} 个组合 · 已有 ${info.success_count} 个预测，结果持续更新中…`
    : `${info.success_count} / ${info.total} 个组合完成预测；其余组合可点开查看原因。`;
  render_workload_heading(); render_filters(); update_filters(); render_evaluation_controls();
  if (by_id('detail-panel').open) render_detail_content();
  if (!state.evaluating) announce('评估完成，矩阵与图表已更新。');
}

async function run_evaluation() {
  if (state.evaluating || !state.serviceReady) return;
  const token = state.evaluationToken = (state.evaluationToken || 0) + 1;
  const request = {configuration: Configuration.clone(state.config),
    hardware_ids: [...state.hardware], method_ids: [...state.methods]};
  state.evaluating = true; state.chart = 'latency'; state.metric = 'latency';
  show_evaluation_pending();
  by_id('evaluation-message').textContent = '正在计算所选组合，结果将逐个显示…';
  try {
    const job = await evaluation_request('/api/evaluations', request);
    let revision = -1;
    while (token === state.evaluationToken) {
      const current = await evaluation_request(`/api/evaluations/${job.id}?since_revision=${revision}`);
      if (token !== state.evaluationToken) return;
      if (current.payload) {accept_evaluation(current.payload, current.status); revision = current.revision ?? revision;}
      if (current.status === 'failed') throw new Error(current.reason);
      if (current.status === 'completed') return;
      await new Promise(resolve => setTimeout(resolve, 700));
    }
  } catch (error) {
    if (token !== state.evaluationToken) return;
    state.evaluating = false;
    const message = error.name === 'TimeoutError' ? '服务响应超时，请稍后重新运行。' : error.message;
    by_id('evaluation-message').textContent = message;
    data.results.filter(row => ['queued', 'running'].includes(row.task.status)).forEach(row => {
      row.task.status = 'failed'; row.reason = message;
    });
    render_workload_heading(); update_filters(); render_evaluation_controls();
    announce(message);
  }
}

async function initialize_evaluation() {
  state.evaluationToken = 0;
  by_id('run-evaluation').addEventListener('click', run_evaluation);
  render_evaluation_controls();
  if (location.protocol === 'file:') {
    state.serviceMessage = '离线查看 · 重新计算请使用本地评估服务';
  } else {
    try {
      const info = await evaluation_request('/api/capabilities');
      state.serviceReady = info.ready;
      state.serviceMessage = info.ready ? (info.tilesim ? 'Roofline / TileSim 已就绪 · 支持范围按算子与硬件配置判定' : 'Roofline 已就绪 · ' + (info.tilesim_reason || 'TileSim 待接入')) : info.reason;
      if (info.tilesim && data.synthetic && !data.evaluation) {
        info.tilesim_hardware.forEach(id => state.hardware.add(id));
        render_filters(); update_filters();
      }
    } catch (_) {state.serviceMessage = '当前为静态页面 · 运行评估需启动本地服务';}
  }
  by_id('evaluation-message').textContent = state.serviceMessage;
  render_evaluation_controls();
}
