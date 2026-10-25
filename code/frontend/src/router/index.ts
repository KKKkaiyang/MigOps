import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import Home from '@/views/Home.vue'
import Login from '@/views/Login.vue'
import SpaceList from '@/views/space/SpaceList.vue'
import SpaceLayout from '@/views/space/SpaceLayout.vue'
import SpaceOverview from '@/views/space/SpaceOverview.vue'
import MaterialList from '@/views/material/MaterialList.vue'
import DataMigrationList from '@/views/data-migration/DataMigrationList.vue'
import DataCheckList from '@/views/data-check/DataCheckList.vue'
import TaskMigrationList from '@/views/task-migration/TaskMigrationList.vue'
import CustomViewList from '@/views/task-migration/CustomViewList.vue'
import TaskViewList from '@/views/task-migration/TaskViewList.vue'
import LineageView from '@/views/lineage/LineageView.vue'
import TagManage from '@/views/tag/TagManage.vue'
import UserList from '@/views/user/UserList.vue'
import SkillMarket from '@/views/skill/SkillMarket.vue'
import ProfileCenter from '@/views/profile/ProfileCenter.vue'

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
        // 数据校验（b05）：校验结果导入 + 校验概览（最新/近7天）
        path: 'data-checks',
        name: 'space-data-checks',
        component: DataCheckList,
        meta: { title: '数据校验', module: 'b05' },
      },
      {
        // 任务视图清单（原「任务台账」，2026-10-25 重构更名为任务视图；交互评审 I6）
        path: 'tasks/views',
        name: 'space-task-views',
        component: TaskViewList,
        meta: { title: '任务视图', module: 'b04' },
      },
      {
        // 自定义视图详情（原「自定义台账」）
        path: 'tasks/views/:viewId',
        name: 'space-custom-view',
        component: CustomViewList,
        meta: { title: '任务视图', module: 'b04' },
      },
      {
        // 标签管理（收纳为任务迁移子导航）
        path: 'tasks/tags',
        name: 'space-tags',
        component: TagManage,
        meta: { title: '标签管理', module: 'b06' },
      },
      {
        path: 'lineage',
        name: 'space-lineage',
        component: LineageView,
        meta: { title: '血缘管理', module: 'b07' },
      },
    ],
  },
  {
    path: '/common/users',
    name: 'user-list',
    component: UserList,
    meta: { title: '用户管理', module: 'common', requireL0: true },
  },
  {
    path: '/b08/skills',
    name: 'skill-market',
    component: SkillMarket,
    meta: { title: 'skill 市场', module: 'b08' },
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfileCenter,
    meta: { title: '个人中心' },
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
