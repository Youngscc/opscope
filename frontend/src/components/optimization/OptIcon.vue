<script setup lang="ts">
withDefaults(defineProps<{name:string; size?:number}>(), {size:18})
const paths:Record<string,string> = {
  matrix:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  pulse:'M2 12h4l3-8 5 16 3-8h5',
  layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',
  arrow:'M5 12h14 m-6-6 6 6-6 6',
  download:'M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5',
  sliders:'M4 7h5 M13 7h7 M4 17h9 M17 17h3 M9 4v6 M17 14v6',
  target:'M21 12a9 9 0 1 1-9-9 M17 12a5 5 0 1 1-5-5 M12 12l9-9 M16 3h5v5',
  check:'m5 12 4 4L19 6',
  chip:'M7 7h10v10H7z M9 2v5 M15 2v5 M9 17v5 M15 17v5 M2 9h5 M2 15h5 M17 9h5 M17 15h5',
  chevron:'m9 5 7 7-7 7',
}
</script>
<template><svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.pulse"/></svg></template>
