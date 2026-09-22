<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Result, Fields } from '../types'
const props = defineProps<{row:Result}>()
const core_id = ref(props.row.execution.trace_view.default_core), page = ref(0)
const view = computed(() => props.row.execution.trace_view)
const core = computed(() => view.value.cores.find((c:Fields)=>c.id===core_id.value) || view.value.cores.find((c:Fields)=>c.id===view.value.default_core))
const events = computed(() => props.row.execution.events.filter((e:Fields)=>e.pid===core.value.id))
const number = (value:number) => new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(value)
watch(() => props.row.id, () => {core_id.value=props.row.execution.trace_view.default_core;page.value=0})
watch(core_id, () => page.value=0)
</script>
<template><div class="trace-view"><div class="trace-toolbar"><label>查看计算核 <select v-model="core_id" aria-label="查看计算核"><option v-for="c in view.cores" :key="c.id" :value="c.id">{{c.id}} · {{c.active_percent}}% 活动</option></select></label><span>{{core.count}} 个事件 · 活动区间并集 {{core.active_percent}}%</span></div>
<div class="trace-lanes"><div v-for="lane in core.lanes" :key="lane.id" class="trace-lane"><span>{{lane.label}}<small>{{number(lane.active_us)}} μs</small></span><svg viewBox="0 -10 800 20" preserveAspectRatio="none" role="img" :aria-label="`${lane.label}，活动 ${number(lane.active_us)} 微秒`"><path :d="lane.path" :stroke="lane.color" stroke-width="12" fill="none" /></svg></div></div>
<div class="trace-axis"><span>时间 / μs</span><div><span v-for="tick in view.ticks" :key="tick">{{tick}}</span></div></div><p class="note">时间轴覆盖本次模拟；空白表示该通道无活动事件，不直接解释为同步等待。</p>
<details class="trace-events"><summary>查看事件明细</summary><div class="trace-pager"><button class="button" :disabled="page===0" @click="page--">上一页</button><span>{{page*40+1}}–{{Math.min((page+1)*40,events.length)}} / {{events.length}} 个事件</span><button class="button" :disabled="(page+1)*40>=events.length" @click="page++">下一页</button></div><table class="tensor-table"><thead><tr><th>操作</th><th>通道</th><th>开始 / μs</th><th>持续 / μs</th></tr></thead><tbody><tr v-for="(e,i) in events.slice(page*40,(page+1)*40)" :key="i"><td>{{e.name}}</td><td>{{e.tid}}</td><td>{{number(e.ts)}}</td><td>{{number(e.dur)}}</td></tr></tbody></table></details></div></template>
