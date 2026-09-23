<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
import type { Result } from '../types'
const s = useOpScopeStore()
const emit = defineEmits<{detail:[ids:string[]]; export:[rows:Result[]]}>()
const search = ref('')
const hardware = computed(() => s.data!.hardware.filter(h => s.hardware.includes(h.id)))
const methods = computed(() => s.data!.methods.filter(m => s.methods.includes(m.id)))
const selected = computed(() => s.selected.map(id => s.data!.results.find(r => r.id === id)!).filter(Boolean))
const options = computed(() => s.data!.hardware.filter(h => `${h.name} ${h.note} ${h.family}`.toLowerCase().includes(search.value.toLowerCase())))
const rows = computed(() => hardware.value.map(hw => ({hw, cells:methods.value.map(m => s.visible.find(r => r.hardware === hw.id && r.method === m.id)!)})))
watch(() => [s.hardware, s.methods], () => {
  s.selected = s.selected.filter(id => s.visible.some(r => r.id === id && r.available))
  if (s.scope && ((s.scope.hardware && !s.hardware.includes(s.scope.hardware)) || (s.scope.method && !s.methods.includes(s.scope.method)))) s.scope = null
}, {deep:true})
function select(id:string) {
  if (s.selected.includes(id)) s.selected = s.selected.filter(value => value !== id)
  else if (s.selected.length < 2) s.selected.push(id)
}
function secondary(r:Result) {
  if (!r.available) return r.reason
  if (s.metric === 'error') return r.latency + ' μs'
  return r.method === 'profile' ? '同硬件参考' : r.deviation_percent === null ? '模型预测 · 无实测参考' : `较参考 ${r.matrix.error_label}`
}
</script>
<template>
<section class="workspace" aria-label="结果比较">
<div class="matrix-toolbar"><div class="filter-controls">
<details id="hardware-filter" class="filter-menu"><summary>硬件 <span>{{s.hardware.length}}</span></summary><fieldset class="filter-popover"><legend>选择硬件</legend><label class="search-field"><span class="sr-only">搜索硬件</span><input v-model="search" type="search" placeholder="搜索型号、Server / POD"></label><div class="filter-bulk"><button class="text-button" @click="s.hardware = [...new Set([...s.hardware,...options.map(h=>h.id)])]">全选当前搜索</button><button class="text-button" @click="s.hardware=[]">清空选择</button></div><label v-for="h in options" :key="h.id" class="filter-option" :title="h.note"><input v-model="s.hardware" type="checkbox" :value="h.id"><span>{{h.name}}</span><small>{{h.family}}</small></label><p class="filter-note">目录配置不代表所有方法均已适配。</p></fieldset></details>
<details class="filter-menu"><summary>方法 <span>{{s.methods.length}}</span></summary><fieldset class="filter-popover"><legend>选择方法</legend><label v-for="m in s.data!.methods" :key="m.id" class="filter-option"><input v-model="s.methods" type="checkbox" :value="m.id"><i class="method-dot" :class="m.id"></i><span>{{m.name}}</span></label></fieldset></details>
<button class="text-button" @click="s.reset()">重置</button><span class="result-count">{{s.visible.filter(r=>r.available).length}} / {{s.visible.length}} 有结果</span></div>
<div class="view-controls"><div class="segmented" aria-label="矩阵主指标"><button :aria-pressed="s.metric==='latency'" @click="s.metric='latency'">总耗时</button><button :aria-pressed="s.metric==='error'" @click="s.metric='error'">参考偏差</button></div><span class="compare-hint">选两张卡片进行对比</span><button class="button" @click="emit('export',s.visible)">导出 JSON</button></div></div>
<div v-if="s.selected.length" class="compare-tray" aria-live="polite"><div class="compare-picks"><button v-for="(r,i) in selected" :key="r.id" class="compare-pick" :aria-label="`取消选择 ${s.name(r)}`" @click="select(r.id)"><span class="detail-result-badge" :class="i?'result-b':'result-a'">{{i?'B':'A'}}</span>{{s.name(r)}}<span aria-hidden="true">×</span></button><span v-if="selected.length===1" class="compare-hint">再选一张卡片</span></div><div><button class="text-button" @click="s.selected=[]">清空</button><button class="button primary" :disabled="s.selected.length!==2" @click="emit('detail',[...s.selected])">对比所选 ↗</button></div></div>
<div v-if="s.visible.length" class="matrix-wrap" role="region" aria-label="结果矩阵，可横向滚动" tabindex="0"><table class="result-matrix" :style="{'--method-count': methods.length}"><thead><tr><th class="axis-corner" scope="col">硬件 ↓ / 方法 →</th><th v-for="m in methods" :key="m.id" scope="col" class="method-column" :class="{'reference-cell':m.id==='profile'}"><button class="axis-button" :aria-pressed="s.scope?.method===m.id" @click="s.scope={method:m.id}"><i class="method-dot" :class="m.id"></i>{{m.name}} ↗</button><small>{{m.source}}</small></th></tr></thead>
<tbody><tr v-for="{hw,cells} in rows" :key="hw.id"><th class="hardware-column" scope="row"><button class="axis-button" :aria-pressed="s.scope?.hardware===hw.id" @click="s.scope={hardware:hw.id}">{{hw.name}} ↗</button><small>{{hw.family}} · {{s.data!.synthetic && hw.group==='demo'?'示例':'规格配置'}}</small></th><td v-for="r in cells" :key="r.id" class="matrix-cell" :class="{'is-missing':!r.available,'is-selected':s.selected.includes(r.id),'reference-cell':r.method==='profile'}"><div class="cell-inner"><button v-if="r.available" class="cell-compare" :aria-pressed="s.selected.includes(r.id)" :disabled="s.selected.length===2 && !s.selected.includes(r.id)" :aria-label="`${s.selected.includes(r.id)?'取消对比':'加入对比'} ${s.name(r)}`" @click="select(r.id)">{{s.selected.includes(r.id)?`${s.selected.indexOf(r.id)?'B':'A'} · 已选 ×`:'+ 加入对比'}}</button><button class="cell-result" aria-haspopup="dialog" :aria-label="`${s.name(r)}，${r.available?r.latency+' 微秒':r.reason}，查看详情`" @click="emit('detail',[r.id])"><span class="cell-value">{{!r.available?'—':s.metric==='error'?(r.method==='profile'?'参考':r.matrix.error_label):r.latency}}<small v-if="r.available && s.metric==='latency'">μs</small></span><span class="cell-secondary">{{secondary(r)}}</span><span v-if="r.available" class="cell-meta"><span>{{r.matrix.note}}</span><span v-if="r.method==='roofline'" class="calibration generic">{{r.source_label}}</span></span><span class="cell-arrow">↗</span></button></div></td></tr></tbody></table></div>
<div v-else class="empty-state"><h2>没有选中的比较组合</h2><p>选择至少一种硬件和一种方法。</p><button class="button" @click="s.reset()">恢复全部</button></div>
<div class="matrix-footer"><span>点击结果查看详情 / 点击行列名称聚焦图表</span><span>{{s.data!.synthetic?'全部为合成示例':'未接入实测参考 · 不计算参考偏差'}}</span></div>
</section>
</template>
