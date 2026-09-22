<script setup lang="ts">
import { computed } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
const s = useOpScopeStore()
const emit = defineEmits<{detail:[ids:string[]]}>()
const rows = computed(() => s.visible.filter(r => !s.scope || (s.scope.hardware ? r.hardware===s.scope.hardware : r.method===s.scope.method)))
const no_reference = computed(() => rows.value.some(r=>r.available) && !rows.value.some(r=>r.available && r.matrix.error_position!==null))
const metric = computed(() => s.chart==='error' && no_reference.value ? 'latency' : s.chart)
const groups = computed(() => s.data!.hardware.filter(h=>s.hardware.includes(h.id) && (!s.scope?.hardware || h.id===s.scope.hardware)).map(hw=>({hw,rows:rows.value.filter(r=>r.hardware===hw.id && r.available && (metric.value!=='error' || (r.method!=='profile' && r.matrix.error_position!==null)))})))
const ticks = computed(() => s.data!.matrix.scales[metric.value==='error'?'error_ticks':'latency_ticks'])
const title = computed(() => s.scope?.hardware ? s.data!.hardware.find(h=>h.id===s.scope!.hardware)?.name+' · 比较方法' : s.scope?.method ? s.data!.methods.find(m=>m.id===s.scope!.method)?.name+' · 比较硬件' : '全局对比')
const methods = computed(() => s.data!.methods.filter(m=>rows.value.some(r=>r.method===m.id && r.available) && (metric.value!=='error' || m.id!=='profile')))
</script>
<template>
<section class="analysis-section" aria-labelledby="chart-heading"><div class="analysis-heading"><div><div class="eyebrow">COMPARISON / INSIGHTS</div><h2 id="chart-heading">{{title}}</h2></div><div class="chart-controls"><button v-if="s.scope" class="text-button" @click="s.scope=null">返回全局</button><div class="segmented" aria-label="图表指标"><button :aria-pressed="metric==='error'" @click="s.chart='error'">参考偏差</button><button :aria-pressed="metric==='latency'" @click="s.chart='latency'">总耗时</button></div></div></div>
<div class="chart-meta"><p>{{metric==='error'?'参考偏差 · 左侧低估，右侧高估，越接近零越接近本次参考。':'总耗时 · 固定同一方法后，可以直观比较不同硬件。'}}</p><div class="chart-legend"><span v-for="m in methods" :key="m.id"><i class="legend-mark" :class="m.id"></i>{{m.name}}</span></div></div>
<div v-if="rows.some(r=>r.available)" class="analysis-chart" :class="{focused:!!s.scope}"><div class="chart-axis"><span>{{metric==='error'?'偏差 %':'耗时 μs'}}</span><div><span v-for="(tick,i) in ticks" :key="i" class="axis-tick" :class="{first:i===0,last:i===ticks.length-1}" :style="{left:tick.position+'%'}">{{tick.label}}</span></div><span></span></div>
<div v-for="group in groups" :key="group.hw.id" class="chart-group"><div class="chart-hardware">{{group.hw.name.replace('NVIDIA ','')}}</div><div class="chart-series-group" :class="metric"><div v-for="r in group.rows" :key="r.id" class="chart-series"><span class="lane-name">{{s.scope?s.data!.methods.find(m=>m.id===r.method)?.name:''}}</span><div class="chart-lane"><div class="lane-plot"><button class="chart-mark" :class="[r.method,metric==='error'?'point':'bar']" :style="metric==='error'?{left:r.matrix.error_position+'%'}:{width:r.matrix.latency_width+'%'}" :aria-label="`${s.name(r)} · ${r.latency} μs，查看详情`" @click="emit('detail',[r.id])"><i v-if="metric==='error'"></i><span v-else class="bar-number">{{r.latency}}</span></button></div><span class="lane-value">{{metric==='error'?(s.scope?r.matrix.error_label:''):s.data!.methods.find(m=>m.id===r.method)?.name}}</span></div></div><div v-if="!group.rows.length" class="chart-no-data">— 暂无结果</div></div></div></div>
<div v-else class="empty-state"><h3>暂无可绘制的结果</h3><p>缺失值保留为空，不参与对比。</p></div><p class="chart-footnote">{{no_reference?'暂无可用参考，展示绝对耗时。':'统一刻度 · 缺失结果不作零值绘制，更短的预测不代表更准确。'}}</p>
</section>
</template>
