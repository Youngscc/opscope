<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
import type { Fact, Result, Section } from '../types'
import Modal from './Modal.vue'
import TraceView from './TraceView.vue'
const props = defineProps<{ids:string[]}>()
const emit = defineEmits<{close:[]; export:[rows:Result[]]; change:[ids:string[]]}>()
const s = useOpScopeStore(), tab = ref('overview'), differences = ref(false)
const scroll = ref<HTMLElement>()
const records = computed(() => props.ids.map(id=>s.data!.results.find(r=>r.id===id)!).filter(Boolean))
const paired = computed(() => records.value.length===2)
const available = computed(() => records.value.every(r=>r.available))
const sections = computed(() => available.value ? records.value[0]?.sections[tab.value] || [] : [])
const notice = computed(() => s.data!.matrix.pairs[props.ids.join('|')])
watch(() => props.ids, () => {tab.value='overview';differences.value=false})
function facts(left:Fact[], right:Fact[]) {
  return [...new Set([...left,...right].map(f=>f.label))].map(label=>{
    const a=left.find(f=>f.label===label), b=right.find(f=>f.label===label)
    return {label,a:a?.value || '—',b:b?.value || '—',same:!!(a?.known && b?.known && a.value===b.value)}
  }).filter(row=>!differences.value || !row.same)
}
function body(row:Result, section:Section, extra=false) {
  let text = extra ? section.extra : row.synthetic && section.key==='latency' ? section.extra : row.details[section.key]
  return text.replace(/<div class="trace-view" data-trace-result="[^"]*"><\/div>/g,'')
}
function change_slot(index:number,event:Event) {
  const ids=[...props.ids];ids[index]=(event.target as HTMLSelectElement).value;emit('change',ids)
}
async function select_tab(id:string) {
  tab.value=id;await nextTick();scroll.value?.scrollTo(0,0)
}
function keyboard(event:KeyboardEvent) {
  const tabs=s.data!.matrix.tabs.map((t:{id:string})=>t.id), i=tabs.indexOf(tab.value)
  if (!['ArrowRight','ArrowLeft','Home','End'].includes(event.key)) return
  event.preventDefault()
  const id=tabs[event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:tabs.length-1))%tabs.length]
  select_tab(id).then(()=>document.getElementById('tab-'+id)?.focus())
}
</script>
<template><Modal :open="!!records.length" title="结果详情" :class-name="`detail-dialog ${paired?'paired':''}`" @close="emit('close')"><div v-if="records.length" class="detail-shell">
<header class="detail-header"><div><span class="eyebrow">RESULT DETAILS / {{s.label}}</span><h2>{{paired?'双结果对照':s.name(records[0]!)}}</h2><p>{{s.config!.operator}} · {{s.config!.inputs.length}} 个输入张量</p></div><div class="detail-actions"><button class="button" @click="emit('export',records)">导出 JSON</button><button class="button icon-button" aria-label="关闭结果详情" @click="emit('close')">×</button></div></header>
<div v-if="paired" class="detail-selectors"><label v-for="(r,i) in records" :key="i">结果 {{i?'B':'A'}}<select :value="r.id" @change="change_slot(i,$event)"><option v-for="v in s.visible.filter(v=>v.available && (v.id===r.id || !ids.includes(v.id)))" :key="v.id" :value="v.id">{{s.name(v)}}</option></select></label></div>
<div v-if="available" class="detail-nav"><div class="detail-tabs" role="tablist" aria-label="性能详情" @keydown="keyboard"><button v-for="t in s.data!.matrix.tabs" :id="'tab-'+t.id" :key="t.id" role="tab" aria-controls="detail-content" :aria-selected="tab===t.id" :tabindex="tab===t.id?0:-1" @click="select_tab(t.id)">{{t.name}}</button></div><label v-if="paired" class="diff-control"><input v-model="differences" type="checkbox">仅看差异</label></div>
<div ref="scroll" class="detail-scroll"><div v-if="paired" class="comparison-notice" :class="{'has-issues':notice?.issues.length}">{{notice?.text}}</div><div id="detail-content" class="detail-content" role="tabpanel" :aria-labelledby="available?'tab-'+tab:undefined" :data-detail-tab="tab" tabindex="0">
<template v-if="!available"><div class="missing-detail"><span class="empty-mark">—</span><h3>{{records[0]!.reason}}</h3><p>此组合暂无可用性能数值。</p></div><h3>{{s.config!.operator}} · 输入配置</h3><dl class="facts"><div v-for="t in s.config!.inputs" :key="t.name"><dt>{{t.name}}</dt><dd>{{t.shape}} · {{t.dtype}}</dd></div></dl></template>
<section v-for="(section,i) in sections" v-else :key="section.key" class="detail-section"><h3>{{section.title}}</h3>
<template v-if="paired"><div class="pair-table-wrap"><table class="pair-table"><thead><tr><th>指标</th><th>结果 A</th><th>结果 B</th></tr></thead><tbody><tr v-for="f in facts(section.facts,records[1]!.sections[tab]![i]!.facts)" :key="f.label" :class="f.same?'same-value':'different-value'"><th scope="row">{{f.label}}</th><td>{{f.a}}</td><td>{{f.b}}</td></tr></tbody></table></div><div class="pair-visuals"><div v-for="(r,j) in records" :key="r.id"><h4 class="visual-result-name">结果 {{j?'B':'A'}} · {{s.name(r)}}</h4><div v-html="body(r,r.sections[tab]![i]!,true)"></div><TraceView v-if="section.key==='pipeline' && r.execution.trace_view" :row="r" /></div></div></template>
<template v-else><div v-html="body(records[0]!,section)"></div><TraceView v-if="section.key==='pipeline' && records[0]!.execution.trace_view" :row="records[0]!" /></template>
</section>
<details v-if="paired && sections[0]?.metadata_facts.length" class="task-run"><summary>任务、来源与运行记录</summary><table class="pair-table"><tbody><tr v-for="f in facts(sections[0].metadata_facts,records[1]!.sections[tab]![0]!.metadata_facts)" :key="f.label"><th>{{f.label}}</th><td>{{f.a}}</td><td>{{f.b}}</td></tr></tbody></table></details>
</div></div></div></Modal></template>
