<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import OptIcon from '../components/optimization/OptIcon.vue'
import PipelineChart from '../components/optimization/PipelineChart.vue'
import DiagnosisSizeConfig from '../components/optimization/DiagnosisSizeConfig.vue'
import { findDiagnosis, diagnosticOperators, diagnosticHardware, exportDemo } from '../data/optimization'
const operatorId = ref(diagnosticOperators[0].id), hardwareId = ref(diagnosticHardware[0].id), exported = ref(false)
const workload = computed(()=>diagnosticOperators.find(item=>item.id===operatorId.value)!)
const dimensions = ref([...workload.value.sizes.find(size=>size.id===workload.value.default_size)!.dimensions])
const configOpen = ref(false)
const selectedSize = computed(()=>workload.value.sizes.find(size=>size.dimensions.join('×')===dimensions.value.join('×')))
const scenario = computed(()=>findDiagnosis(operatorId.value, hardwareId.value, dimensions.value))
watch(operatorId, ()=>{dimensions.value=[...workload.value.sizes.find(size=>size.id===workload.value.default_size)!.dimensions]}, {flush:'sync'})
watch([operatorId,hardwareId,dimensions], ()=>{exported.value=false})
function selectSize(id:string) {
  const size=workload.value.sizes.find(item=>item.id===id)
  if (size) dimensions.value=[...size.dimensions]
}
function applyDimensions(value:number[]) { dimensions.value=[...value];configOpen.value=false }
function download() {
  if (!scenario.value) return
  exportDemo('diagnosis', {operator:operatorId.value,hardware:hardwareId.value,size:scenario.value.size_id,dimensions:dimensions.value}, scenario.value)
  exported.value=true
}
</script>
<template>
  <a class="skip" href="#optimization-main">跳到性能诊断</a>
  <WorkspaceHeader />
  <main id="optimization-main" class="optimization-workspace" tabindex="-1">
    <section class="opt-page-heading">
      <div><div class="eyebrow">OPERATOR OPTIMIZATION</div><h1>算子性能优化</h1><p>定位瓶颈，明确优化方向。</p></div>
      <button class="button" :disabled="!scenario" @click="download"><OptIcon name="download"/>导出诊断</button>
    </section>
    <section class="diagnosis-configuration" aria-label="诊断配置">
      <div class="diagnosis-control-grid">
        <label>算子<select v-model="operatorId" aria-label="诊断算子"><option v-for="item in diagnosticOperators" :key="item.id" :value="item.id">{{item.name}}</option></select></label>
        <label>硬件<select v-model="hardwareId" aria-label="诊断硬件"><option v-for="item in diagnosticHardware" :key="item.id" :value="item.id">{{item.name}}</option></select></label>
        <label>输入 Size<select :value="selectedSize?.id ?? 'custom'" aria-label="诊断 Size" @change="selectSize(($event.target as HTMLSelectElement).value)"><option v-for="item in workload.sizes" :key="item.id" :value="item.id">{{item.shape}}</option><option v-if="!selectedSize" value="custom">自定义 · {{dimensions.join(' × ')}}</option></select></label>
        <button class="button primary diagnosis-configure" aria-haspopup="dialog" :aria-expanded="configOpen" @click="configOpen=true"><OptIcon name="sliders"/>配置输入</button>
      </div>
      <div class="diagnosis-selection-summary"><span class="opt-shape">{{workload.axes.join(' × ')}}<b>{{workload.dtype}}</b></span><span class="diagnosis-latency">任务耗时 <strong>{{scenario?.latency ?? '—'}}</strong><span v-if="scenario">μs</span></span></div>
    </section>
    <template v-if="scenario">
    <div class="diagnosis-overview" :key="scenario.id">
      <section class="diagnosis-verdict">
        <div class="verdict-tag"><OptIcon name="target"/>诊断结论</div>
        <h2>{{scenario.bound}}<span class="verdict-rule"></span></h2>
        <h3>{{scenario.title}}</h3><p>{{scenario.summary}}</p>
        <div class="verdict-bottom"><span><OptIcon name="target" :size="15"/>{{scenario.location}}</span><a href="#optimization-actions">查看优化方向 <OptIcon name="arrow" :size="16"/></a></div>
      </section>
      <section class="diagnosis-pressure" aria-label="资源压力示例">
        <div class="pressure-heading"><span>资源压力</span></div>
        <div v-for="gauge in scenario.gauges" :key="gauge.label" class="pressure-metric">
          <div><span>{{gauge.label}}</span><strong>{{gauge.value}}<small>%</small></strong></div>
          <div class="pressure-track"><i :class="gauge.kind" :style="{width:gauge.value+'%'}"></i></div>
        </div>
      </section>
    </div>
    <div class="diagnosis-lower">
      <PipelineChart :scenario="scenario"/>
      <section id="optimization-actions" class="opt-panel optimization-actions" aria-labelledby="actions-title">
        <div class="opt-panel-heading"><div><span class="opt-kicker">下一步</span><h2 id="actions-title">优化方向</h2></div><span class="opt-count">03</span></div>
        <details v-for="(action,i) in scenario.actions" :key="scenario.id+action.title" :open="i===0" class="optimization-action">
          <summary><span class="action-index">0{{i+1}}</span><strong>{{action.title}}</strong><span class="action-priority" :class="{'is-first':i===0}">{{action.priority}}</span><OptIcon name="chevron" :size="14"/></summary>
          <div class="action-body"><p>{{action.detail}}</p><span><OptIcon name="target" :size="14"/>{{action.check}}</span></div>
        </details>
      </section>
    </div>
    </template>
    <section v-else class="opt-panel diagnosis-empty" aria-label="暂无诊断" role="status"><OptIcon name="chip" :size="28"/><h2>暂无该配置的示例诊断</h2><p>选择常用 Size，或调整算子与硬件。</p></section>
    <footer class="opt-footer"><span>OpScope / 性能优化</span><span role="status">{{exported?'已导出示例诊断 JSON':'示例数据 · 诊断与流水均为预设展示'}}</span></footer>
    <DiagnosisSizeConfig :open="configOpen" :operator="workload" :dimensions="dimensions" @close="configOpen=false" @apply="applyDimensions"/>
  </main>
</template>
