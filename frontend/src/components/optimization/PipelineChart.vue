<script setup lang="ts">
import type { Diagnosis } from '../../data/optimization'
defineProps<{scenario:Diagnosis}>()
</script>
<template>
  <section class="opt-panel pipeline-panel" aria-labelledby="pipeline-title">
    <div class="opt-panel-heading">
      <div><span class="opt-kicker">关键路径</span><h2 id="pipeline-title">{{scenario.timeline_title}}</h2></div>
    </div>
    <div class="pipeline-meta"><span>{{scenario.window}}</span><span class="legend-dot memory">搬运</span><span class="legend-dot compute">计算</span><span class="legend-dot" :class="scenario.timeline[2].kind">{{scenario.timeline[2].label}}</span></div>
    <div class="pipeline-chart" :key="scenario.id">
      <div class="pipeline-axis"><span></span><div><span v-for="tick in scenario.ticks" :key="tick">{{tick}}</span></div></div>
      <div class="pipeline-body">
        <div v-for="lane in scenario.timeline" :key="lane.name" class="pipeline-row">
          <div class="pipeline-label"><strong>{{lane.name}}</strong><span>{{lane.label}}</span></div>
          <div class="pipeline-track">
            <span v-for="(segment,i) in lane.segments" :key="i" class="pipeline-block" :class="lane.kind" :style="{left:segment.left+'%',width:segment.width+'%'}" tabindex="0" :aria-label="`${lane.name}：${segment.detail}`" :title="segment.detail">{{segment.label}}</span>
          </div>
        </div>
        <div class="pipeline-overlay" aria-hidden="true"><span class="pipeline-focus" :style="{left:scenario.focus_region.left+'%',width:scenario.focus_region.width+'%'}"></span></div>
      </div>
    </div>
    <div class="pipeline-callout"><span class="opt-status-dot"></span><strong>{{scenario.focus_range}}</strong><span>{{scenario.focus}}</span><span class="opt-subtle">局部流水示意</span></div>
  </section>
</template>
