import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import OpScopePage from './pages/OpScopePage.vue'
import '../../styles.css'
const router = createRouter({ history: createWebHistory(import.meta.env.BASE_URL), routes: [
  { path: '/', component: OpScopePage }, { path: '/opscope', component: OpScopePage },
  { path: '/:pathMatch(.*)*', redirect: '/' }
] })
createApp(App).use(createPinia()).use(router).mount('#app')
