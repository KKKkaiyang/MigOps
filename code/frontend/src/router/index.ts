import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'
import SpaceList from '@/views/space/SpaceList.vue'
import SpaceLayout from '@/views/space/SpaceLayout.vue'
import SpaceOverview from '@/views/space/SpaceOverview.vue'
import MaterialList from '@/views/material/MaterialList.vue'
import DataMigrationList from '@/views/data-migration/DataMigrationList.vue'
import TaskMigrationList from '@/views/task-migration/TaskMigrationList.vue'
import SavedViewList from '@/views/task-migration/SavedViewList.vue'
import UserList from '@/views/user/UserList.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: { title: '登录', public: true },
  },
  { path: '/', name: 'home', component: Home, meta: { title: '概览' } },
  {
    path: '/b01/spaces',
    name: 'space-list',
    component: SpaceList,
    meta: { title: '项目空间管理', module: 'b01' },
  },
  {
    // 项目空间视图：空间头部 + 模块导航 + 子页面（资料索引/数据迁移/任务迁移）
    path: '/space/:spaceId',
    component: SpaceLayout,
    meta: { title: '项目空间', module: 'space' },
    children: [
      {
        path: '',
        name: 'space-overview',
        component: SpaceOverview,
        meta: { title: '空间概览' },
      },
      {
        path: 'materials',
        name: 'space-materials',
        component: MaterialList,
        meta: { title: '项目资料索引', module: 'b02' },
      },
      {
        path: 'data-migrations',
        name: 'space-data-migrations',
        component: DataMigrationList,
        meta: { title: '数据迁移', module: 'b03' },
      },
      {
        path: 'tasks',
        name: 'space-tasks',
        component: TaskMigrationList,
        meta: { title: '任务迁移', module: 'b04' },
      },
      {
        path: 'tasks/views/:viewId',
        name: 'space-saved-view',
        component: SavedViewList,
        meta: { title: '自定义台账', module: 'b04' },
      },
    ],
  },
  {
    path: '/common/users',
    name: 'user-list',
    component: UserList,
    meta: { title: '用户管理', module: 'common', requireL0: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const store = useUserStore()
  const isLoginPage = to.path === '/login'

  // 未登录：跳转登录页并携带来源地址
  if (!store.token && !isLoginPage) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 已登录访问登录页：回首页
  if (isLoginPage && store.token) {
    return { path: '/' }
  }

  // 系统管理员专属页面：非 L0 不允许进入
  if (to.meta.requireL0 && !store.isL0) {
    return { path: '/' }
  }

  return true
})

export default router
