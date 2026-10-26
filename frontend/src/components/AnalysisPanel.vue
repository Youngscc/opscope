<script setup lang="ts">
interface Indicator { key:string; label:string; display:string; width?:number | null }
interface AnalysisView { metrics:Indicator[]; pipes:Indicator[]; cycles:string; cycle_label:string; latency:string }
defineProps<{title:string; entries:{name:string; view:AnalysisView}[]; showPipes?:boolean}>()
</script>
<template>
<section class="opt-panel analysis-indicators" :aria-label="title">
  <div class="opt-panel-heading"><h2>{{title}}</h2></div>
  <div class="analysis-table-wrap"><table class="analysis-indicator-table">
    <thead><tr><th scope="col">指标</th><th v-for="(entry,i) in entries" :key="i" scope="col">{{entry.name}}</th></tr></thead>
    <tbody><tr v-for="metric in entries[0]?.view.metrics" :key="metric.key">
      <th scope="row">{{metric.label}}</th><td v-for="(entry,i) in entries" :key="i">
        <strong>{{entry.view.metrics.find(item=>item.key===metric.key)?.display ?? '—'}}</strong>
        <span class="analysis-metric-track"><i v-if="entry.view.metrics.find(item=>item.key===metric.key)?.width != null" :class="i?'analysis-current':'analysis-baseline'" :style="{width:entry.view.metrics.find(item=>item.key===metric.key)?.width+'%'}"></i></span>
      </td>
    </tr></tbody>
  </table></div>
  <details v-if="showPipes" class="analysis-pipe-details">
    <summary title="多核平均周期，各组件可重叠，不求和">流水组件周期 · cycles</summary>
    <div class="analysis-table-wrap"><table class="analysis-indicator-table">
      <thead><tr><th scope="col">组件</th><th v-for="(entry,i) in entries" :key="i" scope="col">{{entry.name}}</th></tr></thead>
      <tbody><tr><th scope="row">总耗时</th><td v-for="(entry,i) in entries" :key="i"><strong>{{entry.view.latency}}</strong></td></tr><tr><th scope="row" title="示例按 1.5 GHz 换算；真实结果使用返回的周期">{{entries[0]?.view.cycle_label}}</th><td v-for="(entry,i) in entries" :key="i"><strong>{{entry.view.cycles}}</strong></td></tr>
      <tr v-for="pipe in entries[0]?.view.pipes" :key="pipe.key"><th scope="row">{{pipe.label}}</th><td v-for="(entry,i) in entries" :key="i">{{entry.view.pipes.find(item=>item.key===pipe.key)?.display ?? '—'}}</td></tr></tbody>
    </table></div>
  </details>
</section>
</template>
