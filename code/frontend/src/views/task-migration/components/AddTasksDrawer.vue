<template>
  <!-- 补充任务抽屉（交互评审 I4）：在视图详情页内嵌完成，不离开当前页面 -->
  <el-drawer
    v-model="visible"
    :title="`补充任务 · ${viewName}`"
    size="640px"
    :close-on-click-modal="false"
  >
    <div class="add-tasks">
      <div class="drawer-note">
        默认展示当前场景中<b>尚未加入本视图</b>的任务；重复加入会自动去重。
        <span v-if="excludeIncomplete" class="warn">视图成员较多，未能完整预排除，请自行勾选。</span>
      </div>

      <TaskFilterBar
        :filters="filters"
        :tags="tags"
        @update="onFilterUpdate"
        @search="search"
        @reset="resetFilters"
      />

      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="margin-top: 12px"
        @selection-change="(rows: TaskOut[]) => (selection = rows)"
      >
        <el-table-column type="selection" width="42" :selectable="isSelectable" />
        <el-table-column label="任务" min-width="200">
          <template #default="{ row }">
            <div class="task-cell">
              <span class="mono task-name">{{ row.task_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="工作流" prop="workflow_name" width="120" />
        <el-table-column label="迁移负责人" prop="migration_owner" width="110" />
        <el-table-column label="迁移状态" width="140">
          <template #default="{ row }">
            <TaskStatusCell
              dimension="migration_status"
              :value="row.migration_status"
            />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="inLedger(row.id)" size="small" type="info">已在视图</el-tag>
          </template>
        </el-table-column>
        <template #empty><span class="muted">暂无匹配任务</span></template>
      </el-table>

      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        @current-change="onPage"
      />
    </div>

    <template #footer>
      <div class="drawer-footer">
        <span class="sel-count">已选 <b>{{ selection.length }}</b> 项</span>
        <div class="footer-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" :disabled="!selection.length" @click="submit">
            加入视图
          </el-button>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import TaskFilterBar from './TaskFilterBar.vue'
import TaskStatusCell from './TaskStatusCell.vue'
import { listSavedViewTasks, listTasks, addSavedViewMembers } from '@/api/task-migration'
import { useTagStore } from '@/store/tags'
import type { TaskOut } from '@/types'

const props = defineProps<{
  modelValue: boolean
  spaceId: number
  scenarioId: number
  viewId: number
  viewName: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'added', count: number): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const tagStore = useTagStore()
const tags = computed(() => tagStore.tags)

const list = ref<TaskOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selection = ref<TaskOut[]>([])

const memberIds = ref<Set<number>>(new Set())
const excludeIncomplete = ref(false)

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

const submitting = ref(false)

function inLedger(id: number): boolean {
  return memberIds.value.has(id)
}

function isSelectable(row: TaskOut): boolean {
  return !inLedger(row.id)
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

async function loadMembers() {
  memberIds.value = new Set()
  excludeIncomplete.value = false
  try {
    const data = await listSavedViewTasks(props.spaceId, props.viewId, 1, 200)
    memberIds.value = new Set(data.list.map((t) => t.id))
    excludeIncomplete.value = data.total > data.list.length
  } catch {
    /* 排除失败不阻断补充流程（加入接口幂等） */
  }
}

async function load() {
  loading.value = true
  try {
    const data = await listTasks(props.spaceId, props.scenarioId, page.value, pageSize.value, buildFilters())
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
  page.value = 1
  load()
}

function onPage(p: number) {
  page.value = p
  load()
}

async function submit() {
  if (!selection.value.length) return
  submitting.value = true
  try {
    const count = selection.value.length
    await addSavedViewMembers(props.spaceId, props.viewId, selection.value.map((t) => t.id))
    ElMessage.success(`已加入 ${count} 个任务`)
    visible.value = false
    emit('added', count)
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    selection.value = []
    page.value = 1
    await tagStore.ensure(props.spaceId)
    await Promise.all([loadMembers(), load()])
  }
)
</script>

<style scoped>
.drawer-note {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.6;
}

.warn {
  color: var(--color-warning, #e6a23c);
}

.task-cell {
  display: flex;
  flex-direction: column;
}

.task-name {
  font-size: 13px;
  font-weight: 600;
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.sel-count {
  font-size: 12px;
  color: var(--color-text-regular);
}

.sel-count b {
  color: var(--color-primary);
}
</style>
