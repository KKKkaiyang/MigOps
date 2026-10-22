<template>
  <el-card class="user-card" shadow="never">
    <template #header>
      <div class="header">
        <span class="title">用户管理</span>
        <el-button type="primary" @click="openCreate">新建用户</el-button>
      </div>
    </template>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按用户名/姓名搜索"
        clearable
        style="width: 240px"
        @keyup.enter="load"
        @clear="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
      <span class="scope-tip">用户管理仅系统管理员可操作</span>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="margin-top: 12px">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="130">
        <template #default="{ row }">
          <span class="mono">{{ row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="姓名" width="110" />
      <el-table-column label="归属" width="100">
        <template #default="{ row }">
          <span v-if="row.org_type">{{ row.org_type }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.email">{{ row.email }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="120">
        <template #default="{ row }">
          <span v-if="row.phone">{{ row.phone }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small" effect="light">
            {{ row.status === 'enabled' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近登录" width="160">
        <template #default="{ row }">
          {{ formatTime(row.last_login_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRoles(row as UserOut)">角色</el-button>
          <el-button link type="primary" @click="openEdit(row as UserOut)">编辑</el-button>
          <el-button link type="primary" @click="resetPassword(row as UserOut)">重置密码</el-button>
          <el-button
            v-if="row.status === 'enabled'"
            link
            type="danger"
            @click="disable(row as UserOut)"
          >
            停用
          </el-button>
          <el-button v-else link type="success" @click="enable(row as UserOut)">启用</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span class="muted">暂无用户</span>
      </template>
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @current-change="onPage"
    />
  </el-card>

  <UserFormDialog
    v-model="formVisible"
    :user="current"
    @created="onPasswordReady"
    @saved="onSaved"
  />
  <TempPasswordDialog v-model="pwdResultVisible" :password="tempPassword" :scene="pwdScene" />
  <UserRoleDialog v-model="roleVisible" :user="current" @saved="onSaved" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  disableUser,
  enableUser,
  listUsers,
  resetUserPassword,
} from '@/api/user'
import UserFormDialog from './components/UserFormDialog.vue'
import TempPasswordDialog from './components/TempPasswordDialog.vue'
import UserRoleDialog from './components/UserRoleDialog.vue'
import type { UserOut } from '@/types'

const list = ref<UserOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)

const formVisible = ref(false)
const roleVisible = ref(false)
const current = ref<UserOut | null>(null)

const pwdResultVisible = ref(false)
const tempPassword = ref('')
const pwdScene = ref<'created' | 'reset'>('created')

function formatTime(t?: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const data = await listUsers(page.value, pageSize.value, keyword.value || undefined)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  load()
}

function openCreate() {
  current.value = null
  formVisible.value = true
}

function openEdit(row: UserOut) {
  current.value = row
  formVisible.value = true
}

function openRoles(row: UserOut) {
  current.value = row
  roleVisible.value = true
}

function onSaved() {
  load()
}

function onPasswordReady(password: string) {
  tempPassword.value = password
  pwdScene.value = 'created'
  pwdResultVisible.value = true
  load()
}

async function disable(row: UserOut) {
  await ElMessageBox.confirm(
    `确认停用用户「${row.name}」？停用后不可登录，数据保留。`,
    '停用用户',
    { type: 'warning', confirmButtonText: '停用' }
  )
  await disableUser(row.id)
  ElMessage.success('已停用')
  await load()
}

async function enable(row: UserOut) {
  await ElMessageBox.confirm(`确认启用用户「${row.name}」？`, '启用用户', { type: 'warning' })
  await enableUser(row.id)
  ElMessage.success('已启用')
  await load()
}

async function resetPassword(row: UserOut) {
  await ElMessageBox.confirm(
    `确认为用户「${row.name}」重置密码？将生成新的临时密码。`,
    '重置密码',
    { type: 'warning' }
  )
  const res = await resetUserPassword(row.id)
  tempPassword.value = res.temp_password
  pwdScene.value = 'reset'
  pwdResultVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.user-card {
  border-color: var(--color-border);
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.scope-tip {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-left: auto;
}
.pager {
  margin-top: 12px;
  justify-content: flex-end;
}
.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
