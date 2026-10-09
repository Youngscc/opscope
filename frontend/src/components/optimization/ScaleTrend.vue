<script setup lang="ts">
import { computed } from 'vue'
import type { MegaCase } from '../../data/optimization'
const props = defineProps<{scenario:MegaCase; selected:string; baseline:string}>()
const series = computed(()=>props.scenario.trend.series.filter(row=>row.id===props.selected || row.id===props.baseline))
</script>
<template>
  <section class="opt-panel scale-panel" aria-labelledby="scale-title">
    <div class="opt-panel-heading"><div><span class="opt-kicker">规模敏感性</span><h2 id="scale-title">换个规模，还快吗？</h2></div><span class="opt-subtle">耗时 / μs</span></div>
    <svg class="scale-chart" viewBox="0 0 570 202" role="img" :aria-label="`${scenario.semantic} 不同输入规模的耗时趋势`">
      <g v-for="(tick,i) in scenario.trend.ticks" :key="i"><line x1="40" x2="520" :y1="25+i*70" :y2="25+i*70" class="trend-grid"/><text x="28" :y="29+i*70" text-anchor="end" class="trend-label">{{tick}}</text></g>
      <text v-for="(label,i) in scenario.trend.labels" :key="label" :x="40+i*160" y="191" text-anchor="middle" class="trend-label">{{label}}</text>
      <g v-for="row in series" :key="row.id" :class="row.id===selected?'trend-selected':'trend-baseline'">
        <polyline :points="row.path" fill="none" stroke-width="2.5"/>
        <circle v-for="(point,i) in row.points" :key="i" :cx="point.x" :cy="point.y" r="4" tabindex="0" :aria-label="`${row.name}，规模 ${scenario.trend.labels[i]}：${point.value}`"><title>{{row.name}} · {{scenario.trend.labels[i]}}：{{point.value}}</title></circle>
      </g>
    </svg>
    <div class="trend-legend"><span v-for="row in series" :key="row.id" :class="row.id===selected?'selected':'baseline'"><i></i>{{row.name}}</span><span class="trend-axis-label">{{scenario.trend.axis_label}}</span></div>
    <details class="trend-values"><summary>查看图表数据</summary><table><thead><tr><th>实现</th><th v-for="n in scenario.trend.labels" :key="n">{{n}}</th></tr></thead><tbody><tr v-for="row in series" :key="row.id"><th>{{row.name}}</th><td v-for="(point,i) in row.points" :key="i">{{point.value}}</td></tr></tbody></table></details>
  </section>
</template>
