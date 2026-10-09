<script setup lang="ts">
import { useRoute } from 'vue-router'
import OptIcon from './optimization/OptIcon.vue'
withDefaults(defineProps<{label?:string}>(), {label:'示例数据'})
const route = useRoute()
const links = [
  {path:'/', label:'性能矩阵', icon:'matrix'},
  {path:'/optimization', label:'性能优化', icon:'pulse'},
  {path:'/megakernel', label:'MegaKernel', icon:'layers'},
]
function active(path:string) { return route.path === path || (path === '/' && route.path === '/opscope') }
</script>
<template>
  <header class="topbar workspace-header">
    <RouterLink class="brand" to="/" aria-label="OpScope 性能矩阵">
      <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="7" fill="currentColor"/><path d="M7 19V13M14 19V7M21 19V10" stroke="white" stroke-width="2.5"/></svg>
      OpScope
    </RouterLink>
    <nav class="workspace-nav" aria-label="工作台导航">
      <RouterLink v-for="link in links" :key="link.path" :to="link.path" :class="{'is-current':active(link.path)}" :aria-current="active(link.path)?'page':undefined">
        <OptIcon :name="link.icon" />{{link.label}}
      </RouterLink>
    </nav>
    <span class="demo-pill"><i></i>{{label}}</span>
  </header>
</template>
