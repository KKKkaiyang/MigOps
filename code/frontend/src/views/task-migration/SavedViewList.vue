<template>
  <!-- 自定义台账视图：引用原任务数据，可执行状态流转（需求 §6.4） -->
  <div class="sv-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <div class="head-left">
            <el-button link type="primary" class="back-btn" @click="$router.back()">‹ 返回任务台账</el-button>
            <span class="page-title">{{ view?.name || '自定义台账' }}</span>
            <el-tag v-if="view" size="small" type="info">引用视图</el-tag>
          </div>
          <div class="head-actions">
            <el-button :disabled="!tasks.length" @click="exportTasks">导出</el-button>
          </div>
        </div>
      </template>

      <div v-if="view" class="view-meta">
        <div class="view-desc">{{ view.description || '暂无描述' }}</div>
        <div class="view-filters">
          <span class="filters-label">筛选条件：</span>
          <el-tag
            v-for="(v, k) in view.filter_config"
            :key="k"
            size="small"
            type="info"
            class="filter-tag"
          >
            {{ FILTER_LABELS[k as string] || k }}：{{ v }}
          </el-tag>
          <span v-if="!Object.keys(view.filter_config).length" class="muted">无条件</span>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tasks"
        border
        stripe
        style="margin-top: 12px"
      >
        <el-table-column label="任务" min-width="220">
          <template #default="{ row }">
            <div class="task-cell">
              <span class="mono task-name">{{ row.task_name }}</span>
              <span v-if="row.script_name" class="task-script mono">{{ row.script_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="workflow_name" label="工作流" width="140">
          <template #default="{ row }"><span class="mono">{{ row.workflow_name }}</span></template>
        </el-table-column>
        <el-table-column prop="owner" label="Owner" width="80" />
        <el-table-column label="迁移状态" width="150">
          <template #default="{ row }">
            <TaskStatusCell
              :status="row.migration_status"
              @change="(c: string) => changeStatus(row as TaskOut, c)"
            />
          </template>
        </el-table-column>
        <el-table-column label="调度状态" width="110">
          <template #default="{ row }">
            <ScheduleStatusTag :status="row.schedule_status" />
          </template>
        </el-table-column>
        <el-table-column label="校验状态" width="110">
          <template #default="{ row }">
            <CheckStatusTag :status="row.check_status" />
          </template>
        </el-table-column>
        <el-table-column label="最新备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.latest_note || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="$router.push({ name: 'space-tasks', params: { spaceId } })"
            >
              去台账
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span class="muted">该台账暂无命中任务</span>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ScheduleStatusTag from '@/components/common/ScheduleStatusTag.vue'
import CheckStatusTag from '@/components/common/CheckStatusTag.vue'
import TaskStatusCell from './components/TaskStatusCell.vue'
import { listSavedViewTasks, getSavedView, updateTaskStatus } from '@/api/task-migration'
import { downloadFile } from '@/utils/download'
import type { SavedViewOut, TaskOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))
const viewId = computed(() => Number(route.params.viewId))

const FILTER_LABELS: Record<string, string> = {
  keyword: '任务名称',
  workflow_name: '工作流',
  migration_status: '迁移状态',
  schedule_status: '调度状态',
  check_status: '校验状态',
  owner: 'Owner',
}

const view = ref<SavedViewOut | null>(null)
const tasks = ref<TaskOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

async function loadView() {
  view.value = await getSavedView(spaceId.value, viewId.value)
}

async function load() {
  loading.value = true
  try {
    const data = await listSavedViewTasks(spaceId.value, viewId.value, page.value, pageSize.value)
    tasks.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  load()
}

async function changeStatus(row: TaskOut, status: string) {
  await updateTaskStatus(spaceId.value, row.id, status)
  ElMessage.success(`已流转为「${status}」`)
  await load()
}

async function exportTasks() {
  await downloadFile(
    `/b04/saved-views/${viewId.value}/tasks/export`,
    { space_id: spaceId.value },
    `${view.value?.name ?? '自定义台账'}.xlsx`
  )
}

onMounted(async () => {
  await loadView()
  await load()
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.back-btn {
  font-size: 13px;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.view-meta {
  background: var(--color-page-bg, #eef2f7);
  border-radius: 8px;
  padding: 12px 14px;
}

.view-desc {
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.6;
}

.view-filters {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--color-text-muted);
}

.filter-tag {
  border-radius: 10px;
}

.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.task-cell {
  display: flex;
  flex-direction: column;
}

.task-name {
  font-size: 13px;
  font-weight: 600;
}

.task-script {
  font-size: 11px;
  color: var(--color-text-muted);
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}

.status-drop {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.status-drop .el-icon {
  color: var(--color-text-muted);
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
