<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import Configuration from 'virtual:opscope-configuration'
import { useOpScopeStore } from '../stores/opscope'
import type { Result } from '../types'
import Modal from './Modal.vue'
const props=defineProps<{rows:Result[]|null}>(), emit=defineEmits<{close:[]}>()
const s=useOpScopeStore(), text=ref(''), url=ref(''), textarea=ref<HTMLTextAreaElement>(), copied=ref(false), copyError=ref(false)
watch(()=>props.rows, rows=>{
  if(!rows)return
  copied.value=false;copyError.value=false
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
async function copy() {
  try {
    await navigator.clipboard.writeText(text.value);copied.value=true;copyError.value=false
  } catch {
    textarea.value?.focus();textarea.value?.select()
    copied.value=document.execCommand('copy');copyError.value=!copied.value
  }
}
onBeforeUnmount(()=>{if(url.value)URL.revokeObjectURL(url.value)})
</script>
<template><Modal :open="rows!==null" title="导出 JSON" class-name="export-dialog" @close="emit('close')"><div class="dialog-header"><h2>导出 JSON</h2><button class="button icon-button" aria-label="关闭导出" @click="emit('close')">×</button></div><div class="export-body"><p class="export-info">ⓘ 共 {{rows?.length}} 条结果 · {{s.label}} · UTF-8 编码</p><div class="json-toolbar"><span>JSON</span><button class="text-button" @click="copy">{{copied?'已复制':'复制代码'}}</button></div><textarea ref="textarea" class="export-json" :value="text" readonly aria-label="导出 JSON"></textarea><p v-if="copyError" role="status">已选中文本，请按 Ctrl / ⌘ + C 复制。</p></div><div class="export-actions"><button class="button" @click="emit('close')">取消</button><a class="button primary" :href="url" download="opscope-results.json">下载 JSON</a></div></Modal></template>
