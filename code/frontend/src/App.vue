<template>
  <!-- 登录页为独立全屏布局，不渲染应用头部与功能菜单 -->
  <router-view v-if="isLoginPage" />

  <div class="app-layout" v-else>
    <header class="app-header">
      <div class="logo">迁移管家 <span class="logo-en">MigOps</span></div>
      <nav class="nav">
        <router-link to="/">概览</router-link>
        <router-link to="/b01/spaces">项目空间</router-link>
        <router-link v-if="isL0" to="/common/users">用户管理</router-link>
      </nav>
      <div class="header-right">
        <el-dropdown v-if="user" trigger="click" @command="onCommand">
          <div class="user-trigger">
            <span class="user-name">{{ user.name || user.username }}</span>
            <el-tag v-if="isL0" size="small" type="primary" effect="light">系统管理员</el-tag>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                <span class="menu-meta">{{ user.username }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>

  <!-- 用户自助修改密码（复用共用改密组件，自愿模式） -->
  <ChangePasswordDialog v-model="pwdVisible" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { logout as logoutApi } from '@/api/auth'
import ChangePasswordDialog from '@/components/common/ChangePasswordDialog.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

/** 登录页（及强制改密场景）不展示应用头部与功能菜单 */
const isLoginPage = computed(() => route.name === 'login')

const user = computed(() => userStore.user)
const isL0 = computed(() => userStore.isL0)
const pwdVisible = ref(false)

async function onCommand(command: string) {
  if (command === 'change-password') {
    pwdVisible.value = true
    return
  }
  if (command === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
    try {
      await logoutApi()
    } catch {
      // 登出接口失败不影响本地清理
    }
    userStore.logout()
    router.replace('/login')
  }
}

onMounted(async () => {
  // 有 token 但缺少用户信息时补拉（刷新页面场景）
  if (userStore.token && !userStore.user) {
    try {
      await userStore.fetchMe()
    } catch {
      // 401 已由请求拦截器统一跳转登录页
    }
  }
})
</script>

<style scoped>
.app-layout {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  display: flex;
  align-items: center;
  gap: 32px;
  height: 64px;
  padding: 0 24px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-header-border);
  box-shadow: var(--shadow-light);
}

.logo {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: 0.5px;
}

.logo-en {
  color: var(--color-primary);
  font-weight: 600;
}

.nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav a {
  padding: 6px 12px;
  border-radius: var(--el-border-radius-base);
  color: var(--color-text-regular);
  text-decoration: none;
  font-size: 13px;
  transition: color 0.15s, background 0.15s;
}

.nav a:hover {
  color: var(--color-primary);
  background: var(--el-color-primary-light-9);
}

.nav a.router-link-active {
  color: var(--color-primary);
  background: var(--el-color-primary-light-9);
  font-weight: 500;
}

.header-right {
  margin-left: auto;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--el-border-radius-base);
  cursor: pointer;
  outline: none;
}

.user-trigger:hover {
  background: var(--el-color-primary-light-9);
}

.user-name {
  font-size: 13px;
  color: var(--color-text-primary);
}

.caret {
  font-size: 12px;
  color: var(--color-text-muted);
}

.menu-meta {
  font-size: 12px;
  color: var(--color-text-muted);
}

.app-main {
  flex: 1;
  padding: 20px;
}
</style>
