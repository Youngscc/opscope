<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useOpScopeStore } from '../stores/opscope'
import type { Result } from '../types'
import ResultMatrix from '../components/ResultMatrix.vue'
import ComparisonChart from '../components/ComparisonChart.vue'
import ResultDetails from '../components/ResultDetails.vue'
import OperatorConfig from '../components/OperatorConfig.vue'
import ExportDialog from '../components/ExportDialog.vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import SkipLink from '../components/SkipLink.vue'
import { STATIC_DEMO } from '../demo-mode'
const s=useOpScopeStore(), details=ref<string[]>([]), config_open=ref(false), exported=ref<Result[]|null>(null)
onMounted(()=>{if(!s.data)s.initialize();document.addEventListener('click',close_filters)})
onBeforeUnmount(()=>{s.cancel();document.removeEventListener('click',close_filters)})
function close_filters(event:MouseEvent) {
  document.querySelectorAll<HTMLDetailsElement>('.filter-menu[open]').forEach(el=>{if(!el.contains(event.target as Node))el.open=false})
}
async function run(){details.value=[];await s.run()}
</script>
<template>
<SkipLink target="main">跳到结果矩阵</SkipLink><WorkspaceHeader :label="s.label" />
<main v-if="s.data && s.config" id="main" tabindex="-1"><section class="page-heading operator-heading" aria-label="性能评估"><div class="heading-line"><h1>性能评估</h1></div></section>
<p class="evaluation-message" role="status" aria-live="polite">{{s.message}}</p><ResultMatrix @configure="config_open=true" @detail="details=$event" @export="exported=$event"><template #actions><div class="evaluation-actions"><button v-if="STATIC_DEMO" class="button primary" @click="s.selected=[];s.scope={};" title="展示当前配置的预设结果">开始评估</button><template v-else><button class="button primary" :disabled="s.busy || !s.ready || !s.hardware.length || !s.methods.length" @click="run">{{s.busy?'评估中…':'运行评估'}}</button><a v-if="s.snapshot" class="button" :href="s.snapshot" download>保存结果 HTML</a></template></div></template><template #results><ComparisonChart @detail="details=$event" /></template></ResultMatrix><footer class="page-footer"><span>OpScope / 单算子评估工作台</span></footer>
<ResultDetails :ids="details" @close="details=[]" @change="details=$event;s.selected=[...$event]" @export="exported=$event" /><OperatorConfig :open="config_open" @close="config_open=false" /><ExportDialog :rows="exported" @close="exported=null" /></main>
<main v-else class="empty-state"><p role="status">{{s.message}}</p><button class="button" @click="s.initialize()">重新连接</button></main>
</template>
