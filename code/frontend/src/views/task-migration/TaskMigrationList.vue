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
            <el-button @click="templateVisible = true">配置字段模板</el-button>
            <el-button :disabled="!scenarioId" @click="importVisible = true">导入基础数据</el-button>
            <el-button :disabled="!scenarioId" @click="exportTasks">导出</el-button>
            <el-button :disabled="!scenarioId" @click="openSaveView">保存为视图</el-button>
            <el-button :disabled="!scenarioId || selection.length === 0" @click="createFromTasksVisible = true">
              创建视图（{{ selection.length }}）
            </el-button>
            <el-button :disabled="!scenarioId || selection.length === 0" type="success" plain @click="addToLedgerVisible = true">
              添加到视图（{{ selection.length }}）
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
                <span class="mono task-name" @click="openDetail(row as TaskOut)">{{ row.task_name }}</span>
              </div>
            </template>
          </el-table-column>
          <template v-for="field in tpl.listFields.value" :key="field.field_key">
            <el-table-column :label="field.field_label" min-width="140">
              <template #default="{ row }">
                <TaskStatusCell
                  v-if="tpl.isStatusField(field)"
                  :dimension="field.field_key as StatusDimensionKey"
                  :value="tpl.cellValue(row as TaskOut, field)"
                  @change="(v: string) => changeStatus(row as TaskOut, field.field_key as StatusDimensionKey, v)"
                />
                <CheckResultTag
                  v-else-if="field.field_key === 'check_result'"
                  :value="tpl.cellValue(row as TaskOut, field)"
                />
                <span v-else class="cell-text">{{ tpl.cellValue(row as TaskOut, field) || '—' }}</span>
              </template>
            </el-table-column>
          </template>
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
            <span class="muted">暂无任务，点击「导入基础数据」开始</span>
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
    <TemplateConfigDialog
      v-model="templateVisible"
      :space-id="spaceId"
      @saved="onTemplateSaved"
    />
    <BatchTagDialog
      v-model="batchTagVisible"
      :scenario-id="scenarioId ?? 0"
      :ids="selection.map((s) => s.id)"
      @success="onBatchTagDone"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import TaskFilterBar from './components/TaskFilterBar.vue'
import TaskStatusCell from './components/TaskStatusCell.vue'
import CheckResultTag from '@/components/common/CheckResultTag.vue'
import BatchStatusDialog from './components/BatchStatusDialog.vue'
import TaskDetailDrawer from './components/TaskDetailDrawer.vue'
import SaveViewDialog from './components/SaveViewDialog.vue'
import ImportDialog from './components/ImportDialog.vue'
import BatchTagDialog from './components/BatchTagDialog.vue'
import TaskTagCell from './components/TaskTagCell.vue'
import AddToLedgerDialog from './components/AddToLedgerDialog.vue'
import TemplateConfigDialog from './components/TemplateConfigDialog.vue'
import { listTasks, updateTaskStatus } from '@/api/task-migration'
import { useTagStore } from '@/store/tags'
import { useScenarioStore } from '@/store/scenario'
import { useTemplate } from '@/composables/useTemplate'
import { downloadFile } from '@/utils/download'
import { formatTime } from '@/utils/format'
import type { StatusDimensionKey, TaskOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const tpl = useTemplate(spaceId.value)

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

const filters = reactive<Record<string, any>>({
  keyword: '',
  workflow_name: '',
  project_name: '',
  migration_owner: '',
  active_status: '',
  migration_status: '',
  dualrun_status: '',
  check_status: '',
  acceptance_status: '',
  tag_ids: [] as number[],
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
const templateVisible = ref(false)

/** 当前生效的筛选条件（保存为视图时使用） */
const activeFilters = computed<Record<string, unknown>>(() => {
  const f = filters
  const out: Record<string, unknown> = {}
  if (f.keyword) out.keyword = f.keyword
  if (f.workflow_name) out.workflow_name = f.workflow_name
  if (f.project_name) out.project_name = f.project_name
  if (f.migration_owner) out.migration_owner = f.migration_owner
  for (const k of ['active_status', 'migration_status', 'dualrun_status', 'check_status', 'acceptance_status']) {
    if (f[k]) out[k] = f[k]
  }
  if (Array.isArray(f.tag_ids) && f.tag_ids.length) out.tag_ids = f.tag_ids
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
      keyword: filters.keyword || undefined,
      workflow_name: filters.workflow_name || undefined,
      project_name: filters.project_name || undefined,
      migration_owner: filters.migration_owner || undefined,
      active_status: filters.active_status || undefined,
      migration_status: filters.migration_status || undefined,
      dualrun_status: filters.dualrun_status || undefined,
      check_status: filters.check_status || undefined,
      acceptance_status: filters.acceptance_status || undefined,
      tag_ids:
        Array.isArray(filters.tag_ids) && filters.tag_ids.length
          ? (filters.tag_ids as number[])
          : undefined,
      tag_match: filters.tag_match !== 'all' ? (filters.tag_match as 'all' | 'any') : undefined,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onFilterUpdate(payload: { key: string; value: string | number[] }) {
  filters[payload.key] = payload.value
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  Object.assign(filters, {
    keyword: '',
    workflow_name: '',
    project_name: '',
    migration_owner: '',
    active_status: '',
    migration_status: '',
    dualrun_status: '',
    check_status: '',
    acceptance_status: '',
    tag_ids: [],
    tag_match: 'all',
  })
  search()
}

function clearSelection() {
  selection.value = []
}

function onPage(p: number) {
  page.value = p
  load()
}

async function changeStatus(row: TaskOut, dimension: StatusDimensionKey, value: string) {
  await updateTaskStatus(spaceId.value, row.id, { [dimension]: value })
  ElMessage.success(`已更新为「${value}」`)
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
    ElMessage.warning('请先设置筛选条件，再保存为视图')
    return
  }
  saveViewVisible.value = true
}

function onViewSaved() {
  saveViewVisible.value = false
}

function onCreatedFromTasks() {
  createFromTasksVisible.value = false
  ElMessage.success('已基于勾选任务创建固定名单视图')
  clearSelection()
}

/** 勾选任务加入已有视图（目标视图在对话框内选择） */
function onAddedToLedger() {
  addToLedgerVisible.value = false
  clearSelection()
}

function onTemplateSaved() {
  templateVisible.value = false
  tpl.load(true)
  load()
}

async function exportTasks() {
  const params: Record<string, unknown> = { space_id: spaceId.value }
  const f = filters
  if (f.keyword) params.keyword = f.keyword
  if (f.workflow_name) params.workflow_name = f.workflow_name
  if (f.project_name) params.project_name = f.project_name
  if (f.migration_owner) params.migration_owner = f.migration_owner
  for (const k of ['active_status', 'migration_status', 'dualrun_status', 'check_status', 'acceptance_status']) {
    if (f[k]) params[k] = f[k]
  }
  if (Array.isArray(f.tag_ids) && f.tag_ids.length) params.tag_ids = (f.tag_ids as number[]).join(',')
  if (f.tag_match && f.tag_match !== 'all') params.tag_match = f.tag_match
  await downloadFile(`/b04/scenarios/${scenarioId.value}/tasks/export`, params, '任务视图.xlsx')
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

/**
 * 从血缘管理（b07）临时表上下文跳转而来时，按 工作流 + 任务 预置筛选并定位（R3 跨模块联动）。
 */
function applyLineageJump() {
  const q = route.query
  const workflow = typeof q.workflow === 'string' ? q.workflow : ''
  const task = typeof q.task === 'string' ? q.task : ''
  if (!workflow && !task) return
  if (workflow) filters.workflow_name = workflow
  if (task) filters.keyword = task
  search()
}

watch(
  () => route.query,
  (q) => {
    if (typeof q.workflow === 'string' || typeof q.task === 'string') applyLineageJump()
  },
  { deep: true }
)

onMounted(async () => {
  await scenarioStore.ensureB04(spaceId.value)
  await tagStore.ensure(spaceId.value)
  await tpl.load()
  await load()
  applyLineageJump()
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
  cursor: pointer;
  color: var(--color-primary);
}

.task-name:hover {
  text-decoration: underline;
}

.cell-text {
  font-size: 13px;
  color: var(--color-text-regular);
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
