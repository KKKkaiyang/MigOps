<template>
  <!-- 任务迁移管理（b04）：任务台账全生命周期（需求 §6） -->
  <div class="tm-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">任务迁移管理</span>
          <div class="head-actions">
            <el-button :disabled="!scenarioId" @click="importVisible = true">导入任务台账</el-button>
            <el-button :disabled="!scenarioId" @click="exportTasks">导出</el-button>
            <el-button :disabled="!scenarioId" @click="openSaveView">保存为台账</el-button>
          </div>
        </div>
      </template>

      <ScenarioBar
        :scenarios="scenarios"
        :scenario-id="scenarioId"
        :saved-views="savedViews"
        :space-id="spaceId"
        @change="onScenarioChange"
        @create="scenarioVisible = true"
        @delete="removeScenario"
      />

      <template v-if="scenarioId">
        <TaskFilterBar :filters="filters" @update="onFilterUpdate" @search="search" @reset="resetFilters" />

        <!-- 批量操作栏 -->
        <div v-if="selection.length" class="batch-bar">
          <span>已选 {{ selection.length }} 条</span>
          <el-button size="small" type="primary" @click="batchVisible = true">批量流转状态</el-button>
          <el-button size="small" @click="clearSelection">清除选择</el-button>
        </div>

        <el-table
          v-loading="loading"
          :data="list"
          border
          stripe
          style="margin-top: 12px"
          @selection-change="(rows: TaskOut[]) => (selection = rows)"
        >
          <el-table-column type="selection" width="42" />
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
          <el-table-column label="更新时间" width="150">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row as TaskOut)">详情</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="muted">暂无任务，点击「导入任务台账」开始</span>
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
      </template>

      <el-empty v-else description="请先选择或创建迁移场景" />
    </el-card>

    <ScenarioDialog v-model="scenarioVisible" @success="onScenarioCreated" />
    <BatchStatusDialog
      v-model="batchVisible"
      :scenario-id="scenarioId ?? 0"
      :ids="selection.map((s) => s.id)"
      @success="onBatchDone"
    />
    <TaskDetailDrawer v-model="detailVisible" :task="detailTask" @changed="load" />
    <SaveViewDialog
      v-model="saveViewVisible"
      :scenario-id="scenarioId ?? 0"
      :filters="activeFilters"
      @success="onViewSaved"
    />
    <ImportDialog v-model="importVisible" :scenario-id="scenarioId ?? 0" @success="load" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ScheduleStatusTag from '@/components/common/ScheduleStatusTag.vue'
import CheckStatusTag from '@/components/common/CheckStatusTag.vue'
import ScenarioBar from './components/ScenarioBar.vue'
import TaskFilterBar from './components/TaskFilterBar.vue'
import TaskStatusCell from './components/TaskStatusCell.vue'
import ScenarioDialog from './components/ScenarioDialog.vue'
import BatchStatusDialog from './components/BatchStatusDialog.vue'
import TaskDetailDrawer from './components/TaskDetailDrawer.vue'
import SaveViewDialog from './components/SaveViewDialog.vue'
import ImportDialog from './components/ImportDialog.vue'
import {
  batchUpdateTaskStatus,
  deleteScenario,
  listSavedViews,
  listScenarios,
  listTasks,
  updateTaskStatus,
} from '@/api/task-migration'
import { downloadFile } from '@/utils/download'
import { formatTime } from '@/utils/format'
import type { SavedViewOut, TaskOut, TaskScenarioOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const scenarios = ref<TaskScenarioOut[]>([])
const scenarioId = ref<number | null>(null)
const savedViews = ref<SavedViewOut[]>([])

const list = ref<TaskOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selection = ref<TaskOut[]>([])

const filters = ref<Record<string, string>>({
  keyword: '',
  workflow_name: '',
  migration_status: '',
  schedule_status: '',
  check_status: '',
  owner: '',
})

const scenarioVisible = ref(false)
const batchVisible = ref(false)
const detailVisible = ref(false)
const detailTask = ref<TaskOut | null>(null)
const saveViewVisible = ref(false)
const importVisible = ref(false)

/** 当前生效的筛选条件（保存为台账时使用） */
const activeFilters = computed(() => {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(filters.value)) {
    if (v) out[k] = v
  }
  return out
})

async function loadScenarios() {
  scenarios.value = await listScenarios(spaceId.value)
  if (!scenarioId.value && scenarios.value.length) {
    scenarioId.value = scenarios.value[0].id
  }
  await loadSavedViews()
}

async function loadSavedViews() {
  if (!scenarioId.value) {
    savedViews.value = []
    return
  }
  savedViews.value = await listSavedViews(spaceId.value, scenarioId.value)
}

async function load() {
  if (!scenarioId.value) return
  loading.value = true
  try {
    const data = await listTasks(spaceId.value, scenarioId.value, page.value, pageSize.value, {
      keyword: filters.value.keyword || undefined,
      workflow_name: filters.value.workflow_name || undefined,
      migration_status: filters.value.migration_status || undefined,
      schedule_status: filters.value.schedule_status || undefined,
      check_status: filters.value.check_status || undefined,
      owner: filters.value.owner || undefined,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onScenarioChange(id: number) {
  scenarioId.value = id
  page.value = 1
  clearSelection()
  load()
  loadSavedViews()
}

function onScenarioCreated(scenario: { id: number; name: string }) {
  scenarioId.value = scenario.id
  loadScenarios().then(load)
}

function onFilterUpdate(payload: { key: string; value: string }) {
  filters.value[payload.key] = payload.value
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.value = {
    keyword: '',
    workflow_name: '',
    migration_status: '',
    schedule_status: '',
    check_status: '',
    owner: '',
  }
  search()
}

function clearSelection() {
  selection.value = []
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

function onBatchDone() {
  batchVisible.value = false
  clearSelection()
  load()
}

function openDetail(row: TaskOut) {
  detailTask.value = row
  detailVisible.value = true
}

function openSaveView() {
  if (Object.keys(activeFilters.value).length === 0) {
    ElMessage.warning('请先设置筛选条件，再保存为台账')
    return
  }
  saveViewVisible.value = true
}

function onViewSaved() {
  saveViewVisible.value = false
  loadSavedViews()
}

async function removeScenario() {
  await ElMessageBox.confirm('删除场景将级联删除其下全部任务、备注与自定义台账，确认删除？', '删除场景', {
    type: 'warning',
  })
  await deleteScenario(spaceId.value, scenarioId.value!)
  ElMessage.success('场景已删除')
  scenarioId.value = null
  await loadScenarios()
}

async function exportTasks() {
  const params: Record<string, unknown> = { space_id: spaceId.value }
  for (const [k, v] of Object.entries(filters.value)) {
    if (v) params[k] = v
  }
  await downloadFile(`/b04/scenarios/${scenarioId.value}/tasks/export`, params, '任务台账.xlsx')
}

onMounted(async () => {
  await loadScenarios()
  if (scenarioId.value) await load()
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--color-primary-light, #eef4ff);
  border-radius: 6px;
  font-size: 12px;
  color: var(--color-text-regular);
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

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
