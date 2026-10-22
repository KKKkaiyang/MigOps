<template>
  <el-card class="space-card" shadow="never">
    <template #header>
      <div class="header">
        <span class="title">项目空间管理</span>
        <el-button v-if="canCreateSpace" type="primary" @click="openCreate">新建空间</el-button>
      </div>
    </template>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按项目名称搜索"
        clearable
        style="width: 240px"
        @keyup.enter="load"
        @clear="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
      <span class="scope-tip">{{ scopeTip }}</span>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="margin-top: 12px">
      <el-table-column prop="space_code" label="空间编码" width="130">
        <template #default="{ row }">
          <span class="mono">{{ row.space_code }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="space_name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="customer_name" label="客户" min-width="110" show-overflow-tooltip />
      <el-table-column prop="source_platform" label="源端" width="100" />
      <el-table-column prop="target_platform" label="目标端" width="100" />
      <el-table-column label="我的角色" width="110">
        <template #default="{ row }">
          <RoleLevelTag v-if="row.my_role" :level="row.my_role" />
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <SpaceStatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column label="绑定数据库" min-width="150">
        <template #default="{ row }">
          <span class="mono">{{ row.db_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.updated_at || row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openMembers(row as SpaceOut)">成员</el-button>
          <el-button v-if="canEdit(row as SpaceOut)" link type="primary" @click="openEdit(row as SpaceOut)">编辑</el-button>
          <el-dropdown v-if="nextStatuses(row as SpaceOut).length" trigger="click" @command="(c) => changeStatus(row as SpaceOut, c)">
            <el-button link type="primary">状态<el-icon><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="s in nextStatuses(row as SpaceOut)"
                  :key="s"
                  :command="s"
                >
                  转为「{{ s }}」
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
      <template #empty>
        <span class="muted">暂无项目空间</span>
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

  <SpaceFormDialog v-model="formVisible" :space="current" @success="load" />
  <SpaceMemberDialog v-model="memberVisible" :space="current" @changed="load" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { changeSpaceStatus, listSpaces } from '@/api/space'
import SpaceFormDialog from './components/SpaceFormDialog.vue'
import SpaceMemberDialog from './components/SpaceMemberDialog.vue'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import RoleLevelTag from '@/components/common/RoleLevelTag.vue'
import { useUserStore } from '@/store/user'
import type { SpaceOut, SpaceStatus } from '@/types'

const userStore = useUserStore()

const list = ref<SpaceOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)

const formVisible = ref(false)
const memberVisible = ref(false)
const current = ref<SpaceOut | null>(null)

/** L0 或任一空间的 L1 均可创建空间 */
const canCreateSpace = computed(
  () => userStore.isL0 || userStore.user?.roles.some((r) => r.role_level === 'L1')
)

const scopeTip = computed(() =>
  userStore.isL0 ? '系统管理员：可见全部项目空间' : '仅显示您参与的项目空间'
)

/** 状态机：初始化 → 交付中 → 已验收 */
const TRANSITIONS: Record<string, SpaceStatus[]> = {
  初始化: ['交付中'],
  交付中: ['已验收'],
  已验收: [],
}

function nextStatuses(row: SpaceOut): SpaceStatus[] {
  if (!canEdit(row)) return []
  return (TRANSITIONS[row.status] ?? []) as SpaceStatus[]
}

/** L0 或该空间 L1 可编辑/改状态 */
function canEdit(row: SpaceOut): boolean {
  return row.my_role === 'L0' || row.my_role === 'L1'
}

function formatTime(t?: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const data = await listSpaces(page.value, pageSize.value, keyword.value || undefined)
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

function openEdit(row: SpaceOut) {
  current.value = row
  formVisible.value = true
}

function openMembers(row: SpaceOut) {
  current.value = row
  memberVisible.value = true
}

async function changeStatus(row: SpaceOut, status: SpaceStatus) {
  try {
    await changeSpaceStatus(row.id, status)
    ElMessage.success(`状态已更新为「${status}」`)
    await load()
  } catch {
    // 错误提示由请求拦截器统一处理
  }
}

onMounted(load)
</script>

<style scoped>
.space-card {
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
