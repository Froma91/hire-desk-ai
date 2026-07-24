import { createRouter, createWebHistory } from 'vue-router'
import BoardView from '@/views/BoardView.vue'
import DashboardView from '@/views/DashboardView.vue'
import NewApplicationView from '@/views/NewApplicationView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/board', name: 'board', component: BoardView },
    { path: '/dashboard', name: 'dashboard', component: DashboardView },
    { path: '/new', name: 'new', component: NewApplicationView },
    { path: '/:pathMatch(.*)*', redirect: '/board' },
  ],
})

export default router
