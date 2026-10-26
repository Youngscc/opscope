<script setup lang="ts">
import type { Candidate, Pair } from '../../data/optimization'
import OptIcon from './OptIcon.vue'
defineProps<{candidate:Candidate; baseline:Candidate; comparison:Pair}>()
</script>
<template>
  <section class="opt-panel fusion-panel" aria-labelledby="fusion-title">
    <div class="opt-panel-heading"><h2 id="fusion-title">实现与开销对比</h2><OptIcon name="layers" :size="24"/></div>
    <div class="fusion-flow baseline-flow"><div class="flow-caption"><strong>基线</strong><span>{{baseline.launches}} 次启动</span></div><div class="flow-nodes"><template v-for="(node,i) in baseline.chain" :key="i"><OptIcon v-if="i" name="arrow" :size="16"/><span>{{node}}</span></template></div></div>
    <div class="fusion-flow candidate-flow"><div class="flow-caption"><strong>{{candidate.name}}</strong><span>{{candidate.launches}} 次启动</span></div><div class="flow-nodes"><template v-for="(node,i) in candidate.chain" :key="i"><OptIcon v-if="i" name="arrow" :size="16"/><span>{{node}}</span></template></div></div>
    <div class="cost-summary"><div><span>加速比</span><strong>{{comparison.speedup_label}}</strong></div><div><span>节省时间</span><strong>{{comparison.saved_label}}</strong></div></div>
    <table class="implementation-cost-table"><thead><tr><th scope="col">指标</th><th scope="col">基线</th><th scope="col">当前实现</th></tr></thead><tbody><tr v-for="(metric,i) in baseline.cost_view" :key="metric.label"><th scope="row">{{metric.label}}<small>{{metric.unit}}</small></th><td>{{metric.value ?? '—'}}</td><td>{{candidate.cost_view[i]?.value ?? '—'}}</td></tr></tbody></table>
  </section>
</template>
