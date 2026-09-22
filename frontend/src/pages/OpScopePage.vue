<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
import type { Result } from '../types'
import ResultMatrix from '../components/ResultMatrix.vue'
import ComparisonChart from '../components/ComparisonChart.vue'
import ResultDetails from '../components/ResultDetails.vue'
import OperatorConfig from '../components/OperatorConfig.vue'
import ExportDialog from '../components/ExportDialog.vue'
const s=useOpScopeStore(), details=ref<string[]>([]), config_open=ref(false), exported=ref<Result[]|null>(null)
onMounted(()=>{s.initialize();document.addEventListener('click',close_filters)})
onBeforeUnmount(()=>{s.cancel();document.removeEventListener('click',close_filters)})
function close_filters(event:MouseEvent) {
  document.querySelectorAll<HTMLDetailsElement>('.filter-menu[open]').forEach(el=>{if(!el.contains(event.target as Node))el.open=false})
}
function run(){details.value=[];s.run()}
</script>
<template>
<a class="skip" href="#main">跳到结果矩阵</a><header class="topbar"><a class="brand" href="#main"><svg width="27" height="27" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="7" fill="currentColor"/><path d="M7 19V13M14 19V7M21 19V10" stroke="white" stroke-width="2.5"/></svg>OpScope</a><span class="brand-caption">算子性能观察台</span><span class="demo-pill"><i></i>{{s.label}}</span></header>
<main v-if="s.data && s.config" id="main" tabindex="-1"><section class="page-heading" aria-label="当前工作负载"><div><div class="eyebrow">OPERATOR / PERFORMANCE</div><div class="heading-line"><h1>{{s.config.operator}}</h1><span class="workload-shape" :title="s.config.inputs.map(t=>`${t.name} [${t.shape?.join(' × ')}]`).join(' · ')">{{s.config.inputs[0]?.name}} [{{s.config.inputs[0]?.shape?.join(' × ')}}] +{{s.config.inputs.length-1}} 张量</span></div><p>{{s.config.inputs.length}} 个输入张量 · {{[...new Set(s.config.inputs.map(t=>t.dtype.toUpperCase()))].join(' / ')}}</p><span class="config-status">{{s.busy?'正在评估当前配置…':s.data.evaluation?'已运行评估 · 模型预测，非设备实测':'配置已就绪'}}</span></div><div class="evaluation-actions"><button class="button" @click="config_open=true">选择算子 / 配置 ↗</button><button class="button primary" :disabled="s.busy || !s.ready || !s.hardware.length || !s.methods.length" @click="run">{{s.busy?'评估中…':'运行评估'}}</button><a v-if="s.snapshot" class="button" :href="s.snapshot" download>保存结果 HTML</a></div></section>
<p class="evaluation-message" role="status" aria-live="polite">{{s.message}}</p><ResultMatrix @detail="details=$event" @export="exported=$event" /><ComparisonChart @detail="details=$event" /><footer class="page-footer"><span>OpScope / 单算子评估工作台</span><span>解析、仿真与测量结果应保留各自的统计口径。</span></footer>
<ResultDetails :ids="details" @close="details=[]" @change="details=$event" @export="exported=$event" /><OperatorConfig :open="config_open" @close="config_open=false" /><ExportDialog :rows="exported" @close="exported=null" /></main>
<main v-else class="empty-state"><p role="status">{{s.message}}</p><button class="button" @click="s.initialize()">重新连接</button></main>
</template>
