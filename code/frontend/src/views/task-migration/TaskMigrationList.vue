<template>
  <!-- 任务迁移管理（b04）：任务列表（场景上下文由空间头切换器维护，交互评审 I1/I2） -->
  <div class="tm-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">
            任务迁移
            <span v-if="scenario" class="page-scenario">{{ scenario.name }}</span>
          </span>
          <div class="head-actions">
            <el-button :disabled="!scenarioId" @click="importVisible = true">导入任务台账</el-button>
            <el-button :disabled="!scenarioId" @click="exportTasks">导出</el-button>
            <el-button :disabled="!scenarioId" @click="openSaveView">保存为台账</el-button>
            <el-button :disabled="!scenarioId || selection.length === 0" @click="createFromTasksVisible = true">
              创建台账（{{ selection.length }}）
            </el-button>
            <el-button :disabled="!scenarioId || selection.length === 0" type="success" plain @click="addToLedgerVisible = true">
              添加到台账（{{ selection.length }}）
            </el-button>
          </div>
        </div>
      </template>

      <template v-if="scenarioId">
        <TaskFilterBar
          :filters="filters"
          :tags="allTags"
          @update="onFilterUpdate"
          @search="search"
          @reset="resetFilters"
        />

        <!-- 批量操作栏 -->
        <div v-if="selection.length" class="batch-bar">
          <span>已选 {{ selection.length }} 条</span>
          <el-button size="small" type="primary" @click="batchVisible = true">批量流转状态</el-button>
          <el-button size="small" type="primary" @click="batchTagVisible = true">批量打标签</el-button>
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
          <el-table-column label="标签" min-width="180">
            <template #default="{ row }">
              <TaskTagCell
                :tags="row.tags || []"
                :all-tags="allTags"
                :space-id="spaceId"
                :task-id="row.id"
                editable
                @updated="load"
              />
            </template>
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

      <el-empty v-else description="请先在空间头部选择或创建迁移场景" />
    </el-card>

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
    <SaveViewDialog
      v-model="createFromTasksVisible"
      :scenario-id="scenarioId ?? 0"
      :task-ids="selection.map((s) => s.id)"
      @success="onCreatedFromTasks"
    />
    <AddToLedgerDialog
      v-model="addToLedgerVisible"
      :scenario-id="scenarioId ?? 0"
      :task-ids="selection.map((s) => s.id)"
      @success="onAddedToLedger"
    />
    <ImportDialog v-model="importVisible" :scenario-id="scenarioId ?? 0" @success="load" />
    <BatchTagDialog
      v-model="batchTagVisible"
      :scenario-id="scenarioId ?? 0"
      :ids="selection.map((s) => s.id)"
      @success="onBatchTagDone"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ScheduleStatusTag from '@/components/common/ScheduleStatusTag.vue'
import CheckStatusTag from '@/components/common/CheckStatusTag.vue'
import TaskFilterBar from './components/TaskFilterBar.vue'
import TaskStatusCell from './components/TaskStatusCell.vue'
import BatchStatusDialog from './components/BatchStatusDialog.vue'
import TaskDetailDrawer from './components/TaskDetailDrawer.vue'
import SaveViewDialog from './components/SaveViewDialog.vue'
import ImportDialog from './components/ImportDialog.vue'
import BatchTagDialog from './components/BatchTagDialog.vue'
import TaskTagCell from './components/TaskTagCell.vue'
import AddToLedgerDialog from './components/AddToLedgerDialog.vue'
import { listTasks, updateTaskStatus } from '@/api/task-migration'
import { useTagStore } from '@/store/tags'
import { useScenarioStore } from '@/store/scenario'
import { downloadFile } from '@/utils/download'
import { formatTime } from '@/utils/format'
import type { TaskOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

/** 场景上下文：空间级 store 维护（跨导航保持，I2） */
const scenarioStore = useScenarioStore()
const scenario = computed(() => scenarioStore.b04)
const scenarioId = computed(() => scenarioStore.b04?.id ?? null)

const tagStore = useTagStore()
const allTags = computed(() => tagStore.tags)

const list = ref<TaskOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selection = ref<TaskOut[]>([])

interface TaskFilters {
  keyword: string
  workflow_name: string
  migration_status: string
  schedule_status: string
  check_status: string
  owner: string
  tag_ids: number[]
  tag_match: string
}

const filters = ref<TaskFilters>({
  keyword: '',
  workflow_name: '',
  migration_status: '',
  schedule_status: '',
  check_status: '',
  owner: '',
  tag_ids: [],
  tag_match: 'all',
})

const batchVisible = ref(false)
const detailVisible = ref(false)
const detailTask = ref<TaskOut | null>(null)
const saveViewVisible = ref(false)
const createFromTasksVisible = ref(false)
const importVisible = ref(false)
const batchTagVisible = ref(false)
const addToLedgerVisible = ref(false)

/** 当前生效的筛选条件（保存为台账时使用） */
const activeFilters = computed<Record<string, unknown>>(() => {
  const f = filters.value
  const out: Record<string, unknown> = {}
  if (f.keyword) out.keyword = f.keyword
  if (f.workflow_name) out.workflow_name = f.workflow_name
  if (f.migration_status) out.migration_status = f.migration_status
  if (f.schedule_status) out.schedule_status = f.schedule_status
  if (f.check_status) out.check_status = f.check_status
  if (f.owner) out.owner = f.owner
  if (f.tag_ids.length) out.tag_ids = f.tag_ids
  if (f.tag_match !== 'all') out.tag_match = f.tag_match
  return out
})

async function load() {
  if (!scenarioId.value) {
    list.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const data = await listTasks(spaceId.value, scenarioId.value, page.value, pageSize.value, {
      keyword: filters.value.keyword || undefined,
      workflow_name: filters.value.workflow_name || undefined,
      migration_status: filters.value.migration_status || undefined,
      schedule_status: filters.value.schedule_status || undefined,
      check_status: filters.value.check_status || undefined,
      owner: filters.value.owner || undefined,
      tag_ids:
        Array.isArray(filters.value.tag_ids) && filters.value.tag_ids.length
          ? (filters.value.tag_ids as number[])
          : undefined,
      tag_match: filters.value.tag_match !== 'all' ? (filters.value.tag_match as 'all' | 'any') : undefined,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onFilterUpdate(payload: { key: string; value: string | number[] }) {
  ;(filters.value as Record<string, string | number[]>)[payload.key] = payload.value
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
    tag_ids: [],
    tag_match: 'all',
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

function onBatchTagDone() {
  batchTagVisible.value = false
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
}

function onCreatedFromTasks() {
  createFromTasksVisible.value = false
  ElMessage.success('已基于勾选任务创建固定名单台账')
  clearSelection()
}

/** 勾选任务加入已有台账（目标台账在对话框内选择） */
function onAddedToLedger() {
  addToLedgerVisible.value = false
  clearSelection()
}

async function exportTasks() {
  const params: Record<string, unknown> = { space_id: spaceId.value }
  const f = filters.value
  if (f.keyword) params.keyword = f.keyword
  if (f.workflow_name) params.workflow_name = f.workflow_name
  if (f.migration_status) params.migration_status = f.migration_status
  if (f.schedule_status) params.schedule_status = f.schedule_status
  if (f.check_status) params.check_status = f.check_status
  if (f.owner) params.owner = f.owner
  // 标签维度纳入导出筛选，与列表查询保持一致
  if (Array.isArray(f.tag_ids) && f.tag_ids.length) params.tag_ids = (f.tag_ids as number[]).join(',')
  if (f.tag_match && f.tag_match !== 'all') params.tag_match = f.tag_match
  await downloadFile(`/b04/scenarios/${scenarioId.value}/tasks/export`, params, '任务台账.xlsx')
}

/** 场景切换（空间头切换器）→ 重置分页与选择并重载 */
watch(
  () => scenarioStore.b04,
  () => {
    page.value = 1
    clearSelection()
    load()
  }
)

onMounted(async () => {
  await scenarioStore.ensureB04(spaceId.value)
  await tagStore.ensure(spaceId.value)
  await load()
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

.page-scenario {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
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
