<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import SkipLink from '../components/SkipLink.vue'
import OptIcon from '../components/optimization/OptIcon.vue'
import ScaleTrend from '../components/optimization/ScaleTrend.vue'
import ImplementationFlow from '../components/optimization/ImplementationFlow.vue'
import AnalysisPanel from '../components/AnalysisPanel.vue'
import { findMegaCase, findDimensionCase, optimizationHardware, exportDemo } from '../data/optimization'
import { familyCatalog, parseFamilyImport, familyTemplate, familyResult } from '../data/family-import'
const megaFamilies=familyCatalog, importStatus=ref(''), importError=ref(false), familyFile=ref<HTMLInputElement>()
const context = ref({family:megaFamilies.value[0].id, scope:megaFamilies.value[0].scopes[0].id, size:megaFamilies.value[0].default_size, hardware:optimizationHardware[0].id})
const metric = ref('latency'), exported = ref(false), familySearch=ref(''), familyMenu=ref<HTMLDetailsElement>()
const filteredFamilies=computed(()=>megaFamilies.value.filter(item=>item.name.toLowerCase().includes(familySearch.value.toLowerCase())))
const family = computed(()=>(megaFamilies.value.find(row=>row.id===context.value.family) ?? megaFamilies.value[0])!)
const scope = computed(()=>family.value.scopes.find(row=>row.id===context.value.scope)!)
const calculationType = computed(()=>family.value.calculation_type)
const dimensions = ref([1,4096,4096,4096])
const batched = computed(()=>['bmm','shared'].includes(calculationType.value))
const scenario = computed(()=>familyResult(calculationType.value==='custom'?null:calculationType.value!=='attention' ? findDimensionCase(calculationType.value, context.value.hardware, dimensions.value) : findMegaCase({...context.value,family:family.value.source_family_id ?? family.value.id}),family.value))
const missingMembers=computed(()=>family.value.members.filter(m=>!scenario.value?.candidates.some(c=>c.member_id===m.id)))
async function importFamilies(event:Event) {
  const input=event.target as HTMLInputElement, file=input.files?.[0]
  if(!file) return
  try {
    if(file.size>1024*1024) throw new Error('文件不能超过 1 MB')
    const parsed=parseFamilyImport(await file.text())
    const first=parsed[0]!
    context.value={...context.value,family:first.id,scope:first.scopes[0]!.id,size:first.default_size}
    megaFamilies.value=parsed;dimensions.value=[1,4096,4096,4096]
    importError.value=false;importStatus.value=`已导入 ${parsed.length} 个算子族`
  } catch(error) {importError.value=true;importStatus.value=error instanceof Error?error.message:'导入失败，请检查 JSON 格式'}
  input.value=''
}
function downloadTemplate() {
  const url=URL.createObjectURL(new Blob([JSON.stringify(familyTemplate(),null,2)],{type:'application/json'}))
  const a=document.createElement('a');a.href=url;a.download='opscope-families.json';a.click()
  setTimeout(()=>URL.revokeObjectURL(url),1000)
}



const selectedId = ref(scenario.value?.winner ?? ''), baselineId = ref(scenario.value?.baseline ?? '')
const candidate = computed(()=>scenario.value?.candidates.find(row=>row.id===selectedId.value))
const baseline = computed(()=>scenario.value?.candidates.find(row=>row.id===baselineId.value))
const pairs = computed(()=>scenario.value?.comparisons[baselineId.value] ?? {})
const comparison = computed(()=>pairs.value[selectedId.value])
watch(scenario, value=>{selectedId.value=value?.winner ?? '';baselineId.value=value?.baseline ?? '';exported.value=false}, {flush:'sync'})
watch([selectedId,baselineId,metric], ()=>{exported.value=false})
function selectFamily(id:string) {
  if (familyMenu.value) familyMenu.value.open=false
  if (id===context.value.family) return
  const next = megaFamilies.value.find(row=>row.id===id)!
  dimensions.value=[1,4096,4096,4096]
  context.value = {...context.value, family:next.id, scope:next.scopes[0].id, size:next.default_size}
}
function download() {
  if (!scenario.value || !candidate.value || !baseline.value) return
  exportDemo('megakernel', {...context.value,calculation_type:calculationType.value!=='attention'?calculationType.value:'attention',dimensions:calculationType.value!=='attention'?[...dimensions.value]:undefined,selected:candidate.value.member_id,baseline:baseline.value.member_id}, {family:family.value,result:scenario.value})
  exported.value=true
}
</script>
<template>
  <SkipLink target="megakernel-main">跳到实现对比</SkipLink>
  <WorkspaceHeader />
  <main id="megakernel-main" class="optimization-workspace" tabindex="-1">
    <section class="opt-page-heading">
      <h1>MegaKernel 优化</h1>

    </section>
    <div class="input-result-layout">
    <aside class="mega-configuration input-sidebar" aria-label="MegaKernel输入配置"><h2 class="input-sidebar-title">输入配置</h2><section class="mega-family-picker" aria-labelledby="family-title">
      <div class="family-picker-heading"><h2 id="family-title">算子族</h2></div>
      <details ref="familyMenu" class="family-menu"><summary>{{family.name}}<span class="chevron"></span></summary><div class="family-popover"><input v-model="familySearch" type="search" placeholder="搜索算子族" aria-label="搜索算子族"><div class="family-options" role="group" aria-label="选择算子族">
        <button v-for="item in filteredFamilies" :key="item.id" class="family-option" :aria-pressed="family.id===item.id" @click="selectFamily(item.id)"><OptIcon name="layers"/><strong>{{item.name}}</strong><span>{{item.member_count}} 个成员</span></button>
      </div><p v-if="!filteredFamilies.length" class="family-empty">没有匹配的算子族</p></div></details>
      <div class="family-import-actions"><button class="text-button" @click="familyFile?.click()">导入 JSON</button><button class="text-button" @click="downloadTemplate">下载模板</button></div><input ref="familyFile" type="file" accept=".json,application/json" class="sr-only" aria-label="导入算子族 JSON" @change="importFamilies"><p v-if="importStatus" class="family-import-status" :class="{'is-error':importError}" role="status">{{importStatus}}</p>
    </section>
    <section class="opt-context-bar opt-control-grid mega-context" aria-label="对比配置">
      <label>平台<select v-model="context.hardware" aria-label="对比硬件"><option v-for="item in optimizationHardware" :key="item.id" :value="item.id">{{item.name}}</option></select></label>
      <label v-if="calculationType==='attention'">输入 Size<select v-model="context.size" aria-label="输入规模"><option v-for="item in scope.sizes" :key="item.id" :value="item.id">{{item.label}}</option></select></label><div v-if="calculationType!=='attention' && calculationType!=='custom'" class="dimension-grid"><label v-for="(axis,i) in ['Batch','M','N','K']" :key="axis">{{axis}}<select v-model.number="dimensions[i]" :aria-label="`输入 ${axis}`" :disabled="i===0 && !batched"><option v-for="value in (i===0 ? [1,4] : [1024,4096])" :key="value" :value="value">{{value}}</option></select></label></div>
    </section>
    <label v-if="scenario" class="sidebar-baseline">对比基线<select v-model="baselineId" aria-label="对比基线"><option v-for="row in scenario.candidates" :key="row.id" :value="row.id">{{row.name}}</option></select></label>
    <div class="sidebar-actions"><button class="button primary" @click="dimensions=[1,4096,4096,4096];context.size=family.default_size;baselineId=scenario?.baseline ?? '';selectedId=scenario?.winner ?? ''">恢复默认</button><button class="button" :disabled="!scenario" @click="download">导出对比数据</button></div>
    <div v-if="scenario" class="mega-summary"><span class="opt-equation">{{scenario.semantic}}</span><span class="opt-shape">{{scenario.shape_label}} · {{scenario.shape}}<b>{{scenario.dtype}}</b></span></div>
    </aside><div class="workspace-results"><template v-if="scenario && candidate && baseline && comparison">
    <div class="mega-comparison-layout">
      <section class="opt-panel implementation-ranking" aria-labelledby="ranking-title">
        <div class="opt-panel-heading"><h2 id="ranking-title">族内成员对比</h2><div class="segmented" role="group" aria-label="排名指标"><button :aria-pressed="metric==='latency'" @click="metric='latency'">耗时</button><button :aria-pressed="metric==='speedup'" @click="metric='speedup'">加速比</button></div></div>
        <div class="ranking-toolbar"><span>{{metric==='latency'?'耗时 / μs':'加速比 / ×'}}</span></div>
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
        <div class="spotlight-bottom"><span>MFU<strong>{{candidate.analysis_view.metrics[1]?.display}}</strong></span><span>L2 命中率<strong>{{candidate.analysis_view.metrics[0]?.display}}</strong></span></div>
      </section>
    </div>
    <AnalysisPanel class="mega-analysis-panel" title="性能指标对照" :entries="[{name:`基线 · ${baseline.name}`,view:baseline.analysis_view},{name:`当前 · ${candidate.name}`,view:candidate.analysis_view}]" :show-pipes="true"/>
    <div class="mega-details-layout"><ImplementationFlow :candidate="candidate" :baseline="baseline" :comparison="comparison"/><ScaleTrend :scenario="scenario" :selected="selectedId" :baseline="baselineId"/></div>
    </template>
    <section v-else class="opt-panel diagnosis-empty" aria-label="暂无对比" role="status"><OptIcon name="chip" :size="28"/><h2>暂无该配置的示例对比</h2></section>
    <section v-if="missingMembers.length" class="opt-panel pending-members"><h2>待接入成员</h2><div v-for="member in missingMembers" :key="member.id"><strong>{{member.name}}</strong><span>{{member.kind_label}}</span><span>当前配置暂无结果</span></div></section>
    </div></div>
    <footer class="opt-footer"><span>OpScope / MegaKernel 优化</span><span role="status">{{exported?'已导出对比 JSON':''}}</span></footer>
  </main>
</template>
