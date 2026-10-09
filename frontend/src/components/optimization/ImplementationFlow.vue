<script setup lang="ts">
import type { Candidate } from '../../data/optimization'
import OptIcon from './OptIcon.vue'
defineProps<{candidate:Candidate; baseline:Candidate}>()
</script>
<template>
  <section class="opt-panel fusion-panel" aria-labelledby="fusion-title">
    <div class="opt-panel-heading"><div><span class="opt-kicker">执行结构</span><h2 id="fusion-title">融合边界</h2></div><OptIcon name="layers" :size="24"/></div>
    <div class="fusion-flow baseline-flow"><div class="flow-caption"><strong>基线</strong><span>{{baseline.launches}} 次启动</span></div><div class="flow-nodes"><template v-for="(node,i) in baseline.chain" :key="i"><OptIcon v-if="i" name="arrow" :size="16"/><span>{{node}}</span></template></div></div>
    <div class="fusion-flow candidate-flow"><div class="flow-caption"><strong>{{candidate.name}}</strong><span>{{candidate.launches}} 次启动</span></div><div class="flow-nodes"><template v-for="(node,i) in candidate.chain" :key="i"><OptIcon v-if="i" name="arrow" :size="16"/><span>{{node}}</span></template></div></div>
    <div class="flow-traffic"><span>中间结果与数据复用</span><strong>{{baseline.traffic_mib}}<OptIcon name="arrow" :size="16"/>{{candidate.traffic_mib}}<small>MiB 访存量</small></strong></div>
  </section>
</template>
