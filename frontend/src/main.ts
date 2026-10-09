import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import { STATIC_DEMO } from './demo-mode'
import App from './App.vue'
import OpScopePage from './pages/OpScopePage.vue'
import OptimizationPage from './pages/OptimizationPage.vue'
import MegaKernelPage from './pages/MegaKernelPage.vue'
import '../../styles.css'
import './optimization.css'
const router = createRouter({ history: STATIC_DEMO ? createWebHashHistory() : createWebHistory(import.meta.env.BASE_URL),
scrollBehavior: STATIC_DEMO ? () => ({top:0}) : undefined, routes: [
  { path: '/', component: OpScopePage }, { path: '/opscope', component: OpScopePage },
  { path: '/optimization', component: OptimizationPage, meta:{title:'算子性能优化'} },
  { path: '/megakernel', component: MegaKernelPage, meta:{title:'MegaKernel 优化'} },
  { path: '/:pathMatch(.*)*', redirect: '/' }
] })
router.afterEach(to=>{document.title = `OpScope · ${to.meta.title || '算子性能观察台'}`})
createApp(App).use(createPinia()).use(router).mount('#app')
