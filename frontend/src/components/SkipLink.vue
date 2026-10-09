<script setup lang="ts">
const props = defineProps<{target:string}>()
function focusContent() {
  // Keep the workspace hash route intact when jumping within a standalone page.
  const content = document.getElementById(props.target)
  content?.focus(); content?.scrollIntoView({block:'start'})
}
</script>
<template><a class="skip" :href="'#'+target" @click.prevent="focusContent"><slot /></a></template>
