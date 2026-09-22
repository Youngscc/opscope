<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import Configuration from 'virtual:opscope-configuration'
import { useOpScopeStore } from '../stores/opscope'
import type { Result } from '../types'
import Modal from './Modal.vue'
const props=defineProps<{rows:Result[]|null}>(), emit=defineEmits<{close:[]}>()
const s=useOpScopeStore(), text=ref(''), url=ref(''), textarea=ref<HTMLTextAreaElement>()
watch(()=>props.rows, rows=>{
  if(!rows)return
  const results=rows.map(({details,sections,matrix,...r})=>{
    if(!r.execution)return r
    const {trace_view,...execution}=r.execution;return {...r,execution}
  })
  const payload=Configuration.public_export({schema:s.data!.schema,synthetic:s.data!.synthetic,notice:s.data!.notice,
    workload:s.data!.workload,configuration:s.config,evaluation:s.data!.evaluation,results},s.data!.catalog)
  text.value=JSON.stringify(payload,null,results.some(r=>r.execution?.events?.length>5000)?0:2)
  if(url.value)URL.revokeObjectURL(url.value)
  url.value=URL.createObjectURL(new Blob([text.value],{type:'application/json'}))
})
onBeforeUnmount(()=>{if(url.value)URL.revokeObjectURL(url.value)})
</script>
<template><Modal :open="rows!==null" title="导出 JSON" @close="emit('close')"><div class="dialog-header"><h2>导出 JSON</h2><button class="button" @click="emit('close')">关闭导出</button></div><p>{{rows?.length}} 条 · {{s.label}}</p><textarea ref="textarea" class="export-json" :value="text" readonly aria-label="导出 JSON"></textarea><div class="export-actions"><button class="button" @click="textarea?.select()">选中全部文本</button><a class="button primary" :href="url" download="opscope-results.json">下载 JSON</a></div></Modal></template>
