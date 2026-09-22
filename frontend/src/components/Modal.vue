<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
const props = defineProps<{open:boolean; title:string; className?:string}>()
const emit = defineEmits<{close:[]}>()
const dialog = ref<HTMLDialogElement>()
let origin: HTMLElement | null = null
watch(() => props.open, async open => {
  await nextTick()
  if (open) { origin = document.activeElement as HTMLElement; dialog.value?.showModal() }
  else { dialog.value?.close(); if (origin?.isConnected) origin.focus({preventScroll:true}) }
}, {immediate:true})
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const b = dialog.value!.getBoundingClientRect()
  if (event.clientX < b.left || event.clientX > b.right || event.clientY < b.top || event.clientY > b.bottom) emit('close')
}
</script>
<template><dialog ref="dialog" :class="className" :aria-label="title" @cancel.prevent="emit('close')" @click="backdrop"><slot /></dialog></template>
