<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import OptIcon from '../components/optimization/OptIcon.vue'
import ScaleTrend from '../components/optimization/ScaleTrend.vue'
import ImplementationFlow from '../components/optimization/ImplementationFlow.vue'
import { findMegaCase, megaFamilies, optimizationHardware, exportDemo } from '../data/optimization'
const context = ref({family:megaFamilies[0].id, scope:megaFamilies[0].scopes[0].id, size:megaFamilies[0].default_size, hardware:optimizationHardware[0].id})
const metric = ref('latency'), exported = ref(false)
const family = computed(()=>megaFamilies.find(row=>row.id===context.value.family)!)
const scope = computed(()=>family.value.scopes.find(row=>row.id===context.value.scope)!)
const scenario = computed(()=>findMegaCase(context.value))
const selectedId = ref(scenario.value?.winner ?? ''), baselineId = ref(scenario.value?.baseline ?? '')
const candidate = computed(()=>scenario.value?.candidates.find(row=>row.id===selectedId.value))
const baseline = computed(()=>scenario.value?.candidates.find(row=>row.id===baselineId.value))
const pairs = computed(()=>scenario.value?.comparisons[baselineId.value] ?? {})
const comparison = computed(()=>pairs.value[selectedId.value])
watch(scenario, value=>{selectedId.value=value?.winner ?? '';baselineId.value=value?.baseline ?? '';exported.value=false}, {flush:'sync'})
watch([selectedId,baselineId,metric], ()=>{exported.value=false})
function selectFamily(id:string) {
  if (id===context.value.family) return
  const next = megaFamilies.find(row=>row.id===id)!
  context.value = {...context.value, family:next.id, scope:next.scopes[0].id, size:next.default_size}
}
function download() {
  if (!scenario.value || !candidate.value || !baseline.value) return
  exportDemo('megakernel', {...context.value,selected:candidate.value.member_id,baseline:baseline.value.member_id}, {family:family.value,result:scenario.value})
  exported.value=true
}
</script>
<template>
  <a class="skip" href="#megakernel-main">跳到实现对比</a>
  <WorkspaceHeader />
  <main id="megakernel-main" class="optimization-workspace" tabindex="-1">
    <section class="opt-page-heading">
      <h1>MegaKernel 优化</h1>
      <button class="button" :disabled="!scenario" @click="download"><OptIcon name="download"/>导出对比</button>
    </section>
    <section class="mega-family-picker" aria-labelledby="family-title">
      <div class="family-picker-heading"><h2 id="family-title">算子族</h2></div>
      <div class="family-options" role="group" aria-label="选择算子族">
        <button v-for="item in megaFamilies" :key="item.id" class="family-option" :aria-pressed="family.id===item.id" @click="selectFamily(item.id)"><OptIcon name="layers"/><strong>{{item.name}}</strong><span>{{item.member_count}} 个成员</span></button>
      </div>
    </section>
    <section class="opt-context-bar opt-control-grid mega-context" aria-label="对比配置">
      <label>对比范围<select v-model="context.scope" aria-label="对比范围"><option v-for="item in family.scopes" :key="item.id" :value="item.id">{{item.name}} · {{item.member_count}} 个成员</option></select></label>
      <label>硬件<select v-model="context.hardware" aria-label="对比硬件"><option v-for="item in optimizationHardware" :key="item.id" :value="item.id">{{item.name}}</option></select></label>
      <label>输入 Size<select v-model="context.size" aria-label="输入规模"><option v-for="item in scope.sizes" :key="item.id" :value="item.id">{{item.label}}</option></select></label>
    </section>
    <template v-if="scenario && candidate && baseline && comparison">
    <div class="mega-summary"><span class="opt-equation">{{scenario.semantic}}</span><span class="opt-shape">{{scenario.shape_label}} · {{scenario.shape}}<b>{{scenario.dtype}}</b></span></div>
    <div class="mega-comparison-layout">
      <section class="opt-panel implementation-ranking" aria-labelledby="ranking-title">
        <div class="opt-panel-heading"><h2 id="ranking-title">族内成员对比</h2><div class="segmented" role="group" aria-label="排名指标"><button :aria-pressed="metric==='latency'" @click="metric='latency'">耗时</button><button :aria-pressed="metric==='speedup'" @click="metric='speedup'">加速比</button></div></div>
        <div class="ranking-toolbar"><span>{{metric==='latency'?'耗时 / μs':'加速比 / ×'}}</span><label>基线<select v-model="baselineId" aria-label="对比基线"><option v-for="row in scenario.candidates" :key="row.id" :value="row.id">{{row.name}}</option></select></label></div>
        <div class="ranking-list" :key="scenario.id + metric">
          <button v-for="(row,i) in scenario.candidates" :key="row.id" class="implementation-row" :class="{'is-selected':selectedId===row.id}" :aria-pressed="selectedId===row.id" @click="selectedId=row.id">
            <span class="implementation-index">0{{i+1}}</span>
            <span class="implementation-main"><span class="implementation-name">{{row.name}}<span v-if="row.id===scenario.winner" class="fastest-badge">最快</span><span v-if="row.id===baselineId" class="baseline-badge">基线</span></span><span class="implementation-tag"><span class="member-kind" :class="row.kind">{{row.kind_label}}</span>{{row.tag}}</span><span class="ranking-track"><i :style="{width:(metric==='latency'?row.width:pairs[row.id].speed_width)+'%'}"></i></span></span>
            <span class="implementation-result"><strong>{{metric==='latency'?row.latency:pairs[row.id].speedup_label}}</strong><small>{{metric==='latency'?'μs':'相对基线'}}</small></span>
          </button>
        </div>
      </section>
      <section class="implementation-spotlight" aria-labelledby="candidate-title">
        <div class="spotlight-top"><span>{{family.name}} / 当前成员</span><span :class="candidate.id===scenario.winner?'winner-status':'opt-subtle'">{{candidate.id===scenario.winner?'本组最快':'已选中'}}</span></div>
        <h2 id="candidate-title">{{candidate.name}}</h2><span class="spotlight-tag"><span class="member-kind" :class="candidate.kind">{{candidate.kind_label}}</span>{{candidate.tag}}</span>
        <div class="speedup-hero"><strong>{{comparison.speedup_label}}</strong><span>相对 {{baseline.name}}</span></div>
        <div class="spotlight-metrics"><div><span>任务耗时</span><strong>{{candidate.latency}}<small>μs</small></strong></div><div><span>节省时间</span><strong :class="{'negative-change':comparison.speedup<1}">{{comparison.saved_label}}</strong></div></div>
        <div class="spotlight-bottom"><span>Kernel 启动<strong>{{candidate.launches}}<small>次</small></strong></span><span>访存量<strong>{{candidate.traffic_mib}}<small>MiB</small></strong></span></div>
      </section>
    </div>
    <div class="mega-details-layout"><ImplementationFlow :candidate="candidate" :baseline="baseline"/><ScaleTrend :scenario="scenario" :selected="selectedId" :baseline="baselineId"/></div>
    </template>
    <section v-else class="opt-panel diagnosis-empty" aria-label="暂无对比" role="status"><OptIcon name="chip" :size="28"/><h2>暂无该配置的示例对比</h2></section>
    <footer class="opt-footer"><span>OpScope / MegaKernel 优化</span><span role="status">{{exported?'已导出示例对比 JSON':'示例数据'}}</span></footer>
  </main>
</template>
