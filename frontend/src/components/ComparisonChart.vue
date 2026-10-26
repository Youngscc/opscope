<script setup lang="ts">
import { computed } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
const s = useOpScopeStore()
const emit = defineEmits<{detail:[ids:string[]]}>()
const hardware = computed(() => s.data!.hardware.filter(h => s.hardware.includes(h.id)))
const methods = computed(() => s.data!.methods.filter(m => s.methods.includes(m.id)))
const hardwareId = computed(() => hardware.value.find(h => h.id === s.scope?.hardware)?.id ?? hardware.value[0]?.id ?? '')
const methodId = computed(() => methods.value.find(m => m.id === s.scope?.method)?.id ?? methods.value[0]?.id ?? '')
const ticks = computed(() => s.data!.matrix.scales.latency_ticks)
const panels = computed(() => [
  {id:'hardware', title:'同平台 · 不同方法', label:'对比平台', value:hardwareId.value, options:hardware.value,
    rows:methods.value.map(m => ({label:m.name, result:s.visible.find(r => r.hardware === hardwareId.value && r.method === m.id)}))},
  {id:'method', title:'同方法 · 不同平台', label:'对比方法', value:methodId.value, options:methods.value,
    rows:hardware.value.map(h => ({label:h.name, result:s.visible.find(r => r.method === methodId.value && r.hardware === h.id)}))},
])
function select(axis:string, event:Event) {
  s.scope = {...s.scope, [axis]:(event.target as HTMLSelectElement).value}
}
</script>
<template>
<section class="analysis-section" aria-labelledby="chart-heading">
  <div class="analysis-heading">
    <div><h2 id="chart-heading">性能对比</h2><p class="chart-description">点击柱条可查看详情<br>统一刻度，图形长度表示耗时。</p></div>
    <span class="comparison-unit">总耗时 · μs</span>
  </div>
  <div class="comparison-panels">
    <section v-for="panel in panels" :key="panel.id" class="comparison-panel" :aria-labelledby="`comparison-${panel.id}-heading`">
      <div class="comparison-panel-heading">
        <h3 :id="`comparison-${panel.id}-heading`">{{panel.title}}</h3>
        <label class="comparison-select"><span>{{panel.label}}</span>
          <select :value="panel.value" :disabled="!panel.options.length" @change="select(panel.id,$event)">
            <option v-if="!panel.options.length" value="">未选择</option>
            <option v-for="option in panel.options" :key="option.id" :value="option.id">{{option.name}}</option>
          </select>
        </label>
      </div>
      <div v-if="panel.value && panel.rows.length" class="comparison-bars">
        <div class="comparison-axis" aria-hidden="true"><span>μs</span><div>
          <span v-for="(tick,i) in ticks" :key="i" class="axis-tick" :class="{first:i===0,last:i===ticks.length-1}" :style="{left:tick.position+'%'}">{{tick.label}}</span>
        </div><span></span></div>
        <div v-for="row in panel.rows" :key="row.label" class="comparison-row">
          <button v-if="row.result" class="comparison-bar-button" :class="[row.result.method,{'is-missing':!row.result.available}]" :aria-label="`${s.name(row.result)} · ${row.result.available?row.result.latency+' μs':row.result.reason}，查看详情`" @click="emit('detail',[row.result.id])">
            <span class="comparison-label">{{row.label}}</span>
            <span class="comparison-track"><span v-if="row.result.available" class="comparison-bar" :style="{width:row.result.matrix.latency_width+'%'}"></span><span v-else class="comparison-missing">{{row.result.reason}}</span></span>
            <strong class="comparison-value">{{row.result.available?row.result.latency:'—'}}</strong>
          </button>
          <div v-else class="comparison-bar-button is-missing"><span class="comparison-label">{{row.label}}</span><span class="comparison-missing">暂无结果</span><strong class="comparison-value">—</strong></div>
        </div>
      </div>
      <div v-else class="empty-state"><h3>暂无比较组合</h3><p>选择平台和方法后展示对比。</p></div>
    </section>
  </div>
</section>
</template>
