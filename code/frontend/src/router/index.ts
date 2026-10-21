import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import SpaceList from '@/views/space/SpaceList.vue'

const routes = [
  { path: '/', name: 'home', component: Home, meta: { title: '概览' } },
  {
    path: '/b01/spaces',
    name: 'space-list',
    component: SpaceList,
    meta: { title: '项目空间管理', module: 'b01' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
