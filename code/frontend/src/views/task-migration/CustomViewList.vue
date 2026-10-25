<template>
  <!-- 任务视图详情：引用原任务数据，可搜索/状态流转/批量操作/移除/补充任务（需求 R2/D2，交互评审 I4/I5） -->
  <div class="sv-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <div class="head-left">
            <el-button link type="primary" class="back-btn" @click="goBack">‹ 返回任务视图</el-button>
            <span class="page-title">{{ view?.name || '任务视图' }}</span>
            <el-tag v-if="view" size="small" :type="view.view_mode === 'fixed' ? 'warning' : 'info'">
              {{ modeLabel }}
            </el-tag>
            <span v-if="view" class="member-count">成员 {{ view.task_count }}</span>
          </div>
          <div class="head-actions">
            <el-button type="primary" @click="addTasksVisible = true">补充任务</el-button>
            <el-button :disabled="!tasks.length" @click="exportTasks">导出</el-button>
            <el-button @click="templateVisible = true">配置字段模板</el-button>
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
            {{ FILTER_LABELS[k as string] || k }}：{{ formatFilterValue(k, v) }}
          </el-tag>
          <span v-if="!Object.keys(view.filter_config || {}).length" class="muted">无条件</span>
        </div>
        <div class="view-mode-note">
          <template v-if="view.view_mode === 'fixed'">
            固定名单：成员为锁定的任务集合，任务改标签/状态不会移出；状态变更仍回写原任务。
          </template>
          <template v-else>
            自动更新：名单随筛选条件实时变化，任务改标签/状态后自动移出或加入；移除或补充任务后将转为固定名单。
          </template>
        </div>
      </div>

      <div class="batch-bar">
        <el-button :disabled="!selection.length" @click="batchVisible = true">批量状态流转</el-button>
        <el-button :disabled="!selection.length" @click="batchTagVisible = true">批量打标签</el-button>
        <el-button
          type="danger"
          plain
          :disabled="!selection.length"
          @click="removeFromLedger"
        >
          从视图移除
        </el-button>
        <el-button :disabled="!selection.length" @click="clearSelection">清除选择</el-button>
      </div>

      <TaskFilterBar
        :filters="filters"
        :tags="allTags"
        @update="onFilterUpdate"
        @search="search"
        @reset="resetFilters"
      />

      <el-table
        v-loading="loading"
        :data="tasks"
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
        <el-table-column label="标签" min-width="160">
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
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as TaskOut)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span class="muted">该视图暂无命中任务</span>
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

    <BatchStatusDialog
      v-model="batchVisible"
      :scenario-id="view?.scenario_id ?? 0"
      :ids="selectionIds"
      @success="onBatchDone"
    />
    <BatchTagDialog
      v-model="batchTagVisible"
      :scenario-id="view?.scenario_id ?? 0"
      :ids="selectionIds"
      @success="onBatchTagDone"
    />
    <TaskDetailDrawer v-model="detailVisible" :task="detailTask" @changed="load" />
    <AddTasksDrawer
      v-model="addTasksVisible"
      :space-id="spaceId"
      :scenario-id="view?.scenario_id ?? 0"
      :view-id="viewId"
      :view-name="view?.name || ''"
      @added="onTasksAdded"
    />
    <TemplateConfigDialog
      v-model="templateVisible"
      :space-id="spaceId"
      @saved="onTemplateSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskStatusCell from './components/TaskStatusCell.vue'
import CheckResultTag from '@/components/common/CheckResultTag.vue'
import TaskTagCell from './components/TaskTagCell.vue'
import TaskFilterBar from './components/TaskFilterBar.vue'
import BatchStatusDialog from './components/BatchStatusDialog.vue'
import BatchTagDialog from './components/BatchTagDialog.vue'
import TaskDetailDrawer from './components/TaskDetailDrawer.vue'
import AddTasksDrawer from './components/AddTasksDrawer.vue'
import TemplateConfigDialog from './components/TemplateConfigDialog.vue'
import {
  listSavedViewTasks,
  getSavedView,
  updateTaskStatus,
  removeSavedViewMembers,
} from '@/api/task-migration'
import { downloadFile } from '@/utils/download'
import { useTagStore } from '@/store/tags'
import { useTemplate } from '@/composables/useTemplate'
import { VIEW_MODE_LABEL } from '@/types'
import type { SavedViewOut, StatusDimensionKey, TaskOut } from '@/types'

const route = useRoute()
const router = useRouter()
const spaceId = computed(() => Number(route.params.spaceId))
const viewId = computed(() => Number(route.params.viewId))

const FILTER_LABELS: Record<string, string> = {
  keyword: '任务名称',
  workflow_name: '工作流',
  project_name: '项目名称',
  migration_owner: '迁移负责人',
  active_status: '任务活跃状态',
  migration_status: '迁移状态',
  dualrun_status: '双跑调度状态',
  check_status: '数据校验状态',
  acceptance_status: '客户验收状态',
  tag_ids: '标签',
  tag_match: '标签匹配',
}

function formatFilterValue(key: string, value: unknown): string {
  if (key === 'tag_ids' && Array.isArray(value)) return `${value.length} 个标签`
  if (key === 'tag_match') return value === 'any' ? '含任一标签' : '含全部标签'
  return String(value)
}

const tagStore = useTagStore()
const allTags = computed(() => tagStore.tags)

const tpl = useTemplate(spaceId.value)

const view = ref<SavedViewOut | null>(null)
const tasks = ref<TaskOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selection = ref<TaskOut[]>([])
const selectionIds = computed(() => selection.value.map((t) => t.id))

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
const batchTagVisible = ref(false)
const detailVisible = ref(false)
const detailTask = ref<TaskOut | null>(null)
const addTasksVisible = ref(false)
const templateVisible = ref(false)

const modeLabel = computed(() =>
  view.value ? VIEW_MODE_LABEL[view.value.view_mode] || view.value.view_mode : ''
)

function goBack() {
  router.push({ name: 'space-task-views', params: { spaceId: spaceId.value } })
}

function clearSelection() {
  selection.value = []
}

async function loadView() {
  view.value = await getSavedView(spaceId.value, viewId.value)
}

function buildFilters(): Record<string, unknown> {
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
}

async function load() {
  loading.value = true
  try {
    const data = await listSavedViewTasks(spaceId.value, viewId.value, page.value, pageSize.value, buildFilters())
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
  page.value = 1
  load()
}

async function changeStatus(row: TaskOut, dimension: StatusDimensionKey, value: string) {
  await updateTaskStatus(spaceId.value, row.id, { [dimension]: value })
  ElMessage.success(`已更新为「${value}」`)
  await load()
}

function openDetail(row: TaskOut) {
  detailTask.value = row
  detailVisible.value = true
}

async function removeFromLedger() {
  const willConvert = view.value?.view_mode !== 'fixed'
  await ElMessageBox.confirm(
    willConvert
      ? `将从视图移除选中的 ${selection.value.length} 个任务。此操作会将本视图转为「固定名单」（锁定剩余成员，之后不再自动更新），确认？`
      : `将从视图移除选中的 ${selection.value.length} 个任务（仅解除成员关系，不删除原任务），确认？`,
    '从视图移除任务',
    { type: 'warning' }
  )
  await removeSavedViewMembers(spaceId.value, viewId.value, selectionIds.value)
  ElMessage.success(willConvert ? '已移除，视图已转为固定名单' : '已移除')
  if (view.value) view.value.view_mode = 'fixed'
  clearSelection()
  await load()
  await loadView()
}

async function onTasksAdded() {
  const wasDynamic = view.value?.view_mode !== 'fixed'
  clearSelection()
  await loadView()
  await load()
  if (wasDynamic && view.value?.view_mode === 'fixed') {
    ElMessage.success('已加入任务，本视图已转为「固定名单」（锁定当前成员，之后不再自动更新）')
  }
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

function onTemplateSaved() {
  templateVisible.value = false
  tpl.load(true)
  load()
}

async function exportTasks() {
  await downloadFile(
    `/b04/saved-views/${viewId.value}/tasks/export`,
    { space_id: spaceId.value },
    `${view.value?.name ?? '自定义视图'}.xlsx`
  )
}

onMounted(async () => {
  await tagStore.ensure(spaceId.value)
  await tpl.load()
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
  flex-wrap: wrap;
}

.back-btn {
  font-size: 13px;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.member-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.head-actions {
  display: flex;
  gap: 8px;
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

.view-mode-note {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--color-page-bg, #eef2f7);
  border-radius: 6px;
  font-size: 11px;
  color: var(--color-text-muted);
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

.batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
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

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}

.cell-text {
  font-size: 13px;
  color: var(--color-text-regular);
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
