import { createRouter, createWebHistory } from 'vue-router'
import ManageView from './views/ManageView.vue'
import CalendarView from './views/CalendarView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ManageView },
    { path: '/calendar', component: CalendarView },
  ]
})

export default router