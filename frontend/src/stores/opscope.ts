import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import Configuration from 'virtual:opscope-configuration'
import { request, api_base } from '../api/client'
import { EvaluationSession } from './evaluation-session'
import { initialHardwareIds } from './hardware-selection'
import type { Payload, Configuration as Config, Fields, Result } from '../types'

export const useOpScopeStore = defineStore('opscope', () => {
  const data = shallowRef<Payload>()
  const baseline = shallowRef<Payload>()
  const config = ref<Config>()
  const hardware = ref<string[]>([]), methods = ref<string[]>([]), selected = ref<string[]>([])
  const metric = ref('latency'), chart = ref('error'), scope = ref<Fields | null>(null)
  const busy = ref(false), ready = ref(false), message = ref('正在连接本地服务…')
  const session = new EvaluationSession()
  const visible = computed(() => data.value?.results.filter(r => hardware.value.includes(r.hardware) && methods.value.includes(r.method)) || [])
  const label = computed(() => data.value?.evaluation ? '模型预测 · 非实测' : data.value?.synthetic && config.value && baseline.value && Configuration.matches_demo(config.value, baseline.value.catalog.default_config) ? '示例数据' : '待评估')
  const snapshot = computed(() => data.value?.evaluation && !busy.value && data.value.evaluation.status === 'completed' ? `${api_base}/evaluations/${data.value.evaluation.id}/snapshot` : '')

  async function initialize() {
    const signal = session.begin()
    try {
      const [payload, caps] = await Promise.all([request<Payload>('/bootstrap', undefined, signal), request<Fields>('/capabilities', undefined, signal)])
      if (!session.current(signal)) return
      baseline.value = payload; data.value = payload
      config.value = Configuration.clone(payload.catalog.default_config)
      hardware.value = initialHardwareIds(payload.hardware, Boolean(caps.tilesim))
      methods.value = payload.methods.map(m => m.id)
      ready.value = caps.ready
      message.value = caps.ready ? (caps.tilesim ? 'Roofline / TileSim 已就绪 · 支持范围按算子与硬件配置判定' : 'Roofline 已就绪 · ' + caps.tilesim_reason) : caps.reason
    } catch (error) { if (!signal.aborted) message.value = String(error) }
  }

  function apply(next: Config) {
    session.cancel(); busy.value = false
    config.value = next
    const base = baseline.value!
    data.value = { ...base, results: Configuration.project(next, base.results, base.pending_results, base.catalog.default_config),
      workload: Configuration.workload(next) }
    selected.value = []; scope.value = null
    message.value = Configuration.matches_demo(next, base.catalog.default_config) ? '已载入示例数据' : '配置已应用，请运行评估'
  }

  function pending() {
    const base = baseline.value!
    const workload = {...Configuration.workload(config.value!), synthetic:false}
    const rows = base.pending_results.map(row => {
      const included = hardware.value.includes(row.hardware) && methods.value.includes(row.method)
      return {...row, synthetic:false, workload,
        reason:included ? '等待评估' : '本批次未选择此组合',
        task:{...row.task, synthetic:false, status:included ? 'queued' : 'not_run'}}
    })
    data.value = {...base, synthetic:false, results:rows, workload}
    selected.value = []; scope.value = null
  }

  async function run() {
    if (busy.value || !ready.value || !hardware.value.length || !methods.value.length) return
    const signal = session.begin()
    busy.value = true; pending(); metric.value = 'latency'; chart.value = 'latency'
    message.value = '正在计算所选组合，结果将逐个显示…'
    try {
      const job = await request<Fields>('/evaluations', {configuration:config.value, hardware_ids:hardware.value, method_ids:methods.value}, signal)
      let revision = -1
      while (session.current(signal)) {
        const result = await request<Fields>(`/evaluations/${job.id}?since_revision=${revision}`, undefined, signal)
        if (!session.current(signal)) return
        if (result.payload) {
          data.value = result.payload; config.value = result.payload.initial_configuration
          revision = result.revision ?? revision
          const info = result.payload.evaluation
          message.value = result.status === 'running'
            ? `已处理 ${info.finished_count} / ${info.total} 个组合 · 已有 ${info.success_count} 个预测，结果持续更新中…`
            : `${info.success_count} / ${info.total} 个组合完成预测；其余组合可查看原因。`
        }
        if (result.status === 'failed') throw new Error(result.reason)
        if (result.status === 'completed') return
        await new Promise(resolve => setTimeout(resolve, 700))
      }
    } catch (error) {
      if (session.current(signal)) {
        message.value = error instanceof Error ? error.message : '评估失败'
        data.value = {...data.value!, results:data.value!.results.map(row => ['queued', 'running'].includes(row.task.status)
          ? {...row, reason:message.value, task:{...row.task, status:'failed'}} : row)}
      }
    } finally { if (session.current(signal)) busy.value = false }
  }

  function reset() {
    hardware.value = initialHardwareIds(baseline.value!.hardware, ready.value)
    methods.value = baseline.value!.methods.map(m => m.id); selected.value = []; scope.value = null
  }
  function name(row: Result) {
    return `${data.value!.hardware.find(h => h.id === row.hardware)?.name} · ${data.value!.methods.find(m => m.id === row.method)?.name}`
  }
  function cancel() { session.cancel(); busy.value = false }
  return {data, config, hardware, methods, selected, metric, chart, scope, busy, ready, message, visible, label, snapshot, initialize, apply, run, reset, name, cancel}
})
