<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import Modal from '../Modal.vue'
import { parseDimensions, type DiagnosticOperator } from '../../data/optimization'
const props = defineProps<{open:boolean; operator:DiagnosticOperator; dimensions:number[]}>()
const emit = defineEmits<{close:[]; apply:[dimensions:number[]]}>()
const draft = ref<string[]>([]), attempted = ref(false), fields = ref<HTMLInputElement[]>([])
watch(()=>props.open, open=>{if(open){draft.value=props.dimensions.map(String);attempted.value=false}})
function preset(dimensions:number[]) { draft.value=dimensions.map(String);attempted.value=false }
async function apply() {
  attempted.value=true
  const dimensions=parseDimensions(draft.value)
  if (!dimensions) { await nextTick();fields.value.find(field=>field.getAttribute('aria-invalid')==='true')?.focus();return }
  emit('apply',dimensions)
}
</script>
<template>
  <Modal :open="open" title="配置输入 Size" class-name="diagnosis-size-dialog" @close="emit('close')">
    <header class="config-header"><div><span class="eyebrow">INPUT CONFIGURATION</span><h2>{{operator.name}} 输入配置</h2></div><button class="button icon-button" aria-label="关闭输入配置" @click="emit('close')">×</button></header>
    <form id="diagnosis-size-form" class="diagnosis-size-form" novalidate @submit.prevent="apply">
      <div class="tensor-editor-heading"><h3>常用 Size</h3><span>{{operator.dtype}}</span></div>
      <div class="diagnosis-size-presets" role="group" aria-label="常用输入尺寸"><button v-for="size in operator.sizes" :key="size.id" type="button" :aria-pressed="draft.join('×')===size.dimensions.join('×')" @click="preset(size.dimensions)">{{size.shape}}</button></div>
      <div class="diagnosis-dimensions"><label v-for="(axis,index) in operator.axes" :key="axis">{{axis}}<input ref="fields" v-model="draft[index]" :aria-label="`${axis} 维度`" :aria-invalid="attempted && !parseDimensions([draft[index] || ''])" :aria-describedby="attempted && !parseDimensions(draft)?'dimension-error':undefined" inputmode="numeric" autocomplete="off"></label></div>
      <p v-if="attempted && !parseDimensions(draft)" id="dimension-error" class="field-error" role="alert">每个维度都需要填写有效的正整数。</p>
      <p class="diagnosis-input-template">{{operator.input_template}}</p>
    </form>
    <footer class="config-footer"><span class="diagnosis-demo-note">示例数据</span><button class="button" @click="emit('close')">取消</button><button class="button primary" type="submit" form="diagnosis-size-form">应用配置</button></footer>
  </Modal>
</template>
