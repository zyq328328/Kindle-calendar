import { createRouter, createWebHistory } from 'vue-router'
import ManageView from './views/ManageView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ManageView },
  ]
})

export default router
