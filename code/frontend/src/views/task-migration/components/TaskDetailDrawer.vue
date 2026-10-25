<template>
  <!-- 任务详情抽屉：基础字段 + 5 维独立状态 + 排查备注（需求 §6.2.7 / §6.3，D1/D3） -->
  <el-drawer
    v-model="visible"
    :title="task ? `任务详情：${task.task_name}` : '任务详情'"
    size="680px"
  >
    <div v-loading="loading" class="detail-drawer">
      <template v-if="task">
        <!-- 基础信息：项目名称/工作流名称/任务名称各占一行（B04-09） -->
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目名称" :span="2">{{ task.project_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="工作流名称" :span="2">
            <span class="mono">{{ task.workflow_name || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="任务名称" :span="2">
            <span class="mono">{{ task.task_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="迁移负责人">{{ task.migration_owner || '—' }}</el-descriptions-item>
          <el-descriptions-item label="归属环境">{{ task.env || '—' }}</el-descriptions-item>
          <el-descriptions-item label="归属业务">{{ task.business || '—' }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ task.task_type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="数据校验结果" :span="2">
            <CheckResultTag :value="task.check_result" />
          </el-descriptions-item>
          <el-descriptions-item label="任务URI" :span="2">
            <span class="mono uri">{{ task.task_uri }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ task.remark || '—' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ formatTime(task.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 任务输出表（B04-10：血缘正式输出表，实时查询，非表模型字段；可点击弹出血缘对话框） -->
        <div v-if="!hideOutputTables" class="output-block">
          <div class="block-title">
            任务输出表（血缘·正式表）
            <span v-if="outputTables.length" class="count-badge">{{ outputTables.length }}</span>
          </div>
          <div v-loading="outputLoading" class="output-body">
            <div v-if="outputTables.length" class="output-list">
              <span
                v-for="t in outputTables"
                :key="t"
                class="output-table mono"
                @click="openLineage(t)"
                >{{ t }}</span
              >
            </div>
            <el-empty v-else description="暂无输出表（血缘中无该任务的正式输出表记录）" :image-size="60" />
          </div>
        </div>

        <!-- 5 维状态：各自独立流转（D1） -->
        <div class="status-block">
          <div class="block-title">状态维度</div>
          <div v-for="dim in STATUS_DIMENSIONS" :key="dim.key" class="status-line">
            <span class="dim-label">{{ dim.label }}</span>
            <TaskStatusCell
              :dimension="dim.key"
              :value="(task as Record<string, any>)[dim.key]"
              @change="(v: string) => changeStatus(dim.key, v)"
            />
          </div>
        </div>

        <!-- 标签编辑 -->
        <div class="tag-row">
          <span class="status-label">任务标签：</span>
          <TaskTagSelect v-model="taskTags" placeholder="选择标签" style="flex: 1" />
          <el-button size="small" type="primary" :loading="tagSaving" @click="saveTags">保存标签</el-button>
        </div>

        <!-- 排查备注时间线 -->
        <div class="notes-section">
          <div class="notes-head">
            <span class="notes-title">排查备注时间线</span>
            <el-button size="small" type="primary" @click="noteVisible = true">+ 添加排查备注</el-button>
          </div>
          <el-timeline v-if="notes.length" class="notes-timeline">
            <el-timeline-item
              v-for="n in notes"
              :key="n.id"
              :type="n.note_kind === 'check_result' ? 'success' : 'primary'"
              :timestamp="formatTime(n.created_at)"
              placement="top"
            >
              <div class="note-author">{{ n.created_by || '—' }}</div>
              <div v-if="n.note_kind === 'check_result'" class="note-result">
                校验结果：{{ n.problem_desc || '—' }}
              </div>
              <template v-else>
                <div v-if="n.problem_desc" class="note-line">
                  <strong>问题描述：</strong>{{ n.problem_desc }}
                </div>
                <div v-if="n.cause_analysis" class="note-line">
                  <strong>原因分析：</strong>{{ n.cause_analysis }}
                </div>
                <div v-if="n.fix_plan" class="note-line">
                  <strong>修复方案：</strong>{{ n.fix_plan }}
                </div>
              </template>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无排查备注" :image-size="60" />
        </div>
      </template>
    </div>

    <NoteFormDialog v-model="noteVisible" :task="task" @success="onNoteAdded" />
    <LineageDialog v-model="lineageVisible" :space-id="spaceId" :focus-table="focusTable" />
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import TaskStatusCell from './TaskStatusCell.vue'
import CheckResultTag from '@/components/common/CheckResultTag.vue'
import NoteFormDialog from './NoteFormDialog.vue'
import TaskTagSelect from './TaskTagSelect.vue'
import LineageDialog from '@/views/lineage/components/LineageDialog.vue'
import { getTaskTags, listNotes, setTaskTags, updateTaskStatus } from '@/api/task-migration'
import { getLineageByTask } from '@/api/lineage'
import { formatTime } from '@/utils/format'
import { STATUS_DIMENSIONS } from '@/utils/task-status'
import type { StatusDimensionKey, TaskNoteOut, TaskOut } from '@/types'

const props = defineProps<{ modelValue: boolean; task?: TaskOut | null; hideOutputTables?: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'changed'): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const notes = ref<TaskNoteOut[]>([])
const noteVisible = ref(false)
const taskTags = ref<number[]>([])
const tagSaving = ref(false)

// 任务输出表（B04-10）：血缘正式输出表，按 project_name+task_name 实时查询
const outputTables = ref<string[]>([])
const outputLoading = ref(false)
// 血缘对话框
const lineageVisible = ref(false)
const focusTable = ref('')

watch(
  () => props.modelValue,
  (open) => {
    if (open && props.task) load()
  }
)

async function load() {
  if (!props.task) return
  loading.value = true
  outputTables.value = []
  try {
    notes.value = await listNotes(spaceId.value, props.task.id)
    const tags = await getTaskTags(spaceId.value, props.task.id)
    taskTags.value = tags.map((t) => t.id)
    // 血缘上下文复用时不展示「任务输出表」区块，跳过查询（D5）
    if (!props.hideOutputTables) {
      await loadOutputTables()
    }
  } finally {
    loading.value = false
  }
}

/** 拉取该任务的血缘输出表，仅保留正式表（B04-10：过滤临时表） */
async function loadOutputTables() {
  if (!props.task) return
  outputLoading.value = true
  try {
    const data = await getLineageByTask(
      spaceId.value,
      props.task.project_name,
      props.task.task_name
    )
    outputTables.value = (data.output_tables || [])
      .filter((t) => (t.type ?? '正式表') === '正式表')
      .map((t) => t.table)
  } catch {
    /* 错误提示由请求拦截器统一处理 */
  } finally {
    outputLoading.value = false
  }
}

/** 点击输出表 → 打开血缘对话框并聚焦该表（B04-10） */
function openLineage(table: string) {
  focusTable.value = table
  lineageVisible.value = true
}

async function changeStatus(dimension: StatusDimensionKey, value: string) {
  if (!props.task) return
  await updateTaskStatus(spaceId.value, props.task.id, { [dimension]: value })
  ;(props.task as Record<string, any>)[dimension] = value
  ElMessage.success(`已更新为「${value}」`)
  emit('changed')
}

async function onNoteAdded() {
  noteVisible.value = false
  await load()
  emit('changed')
}

async function saveTags() {
  if (!props.task) return
  tagSaving.value = true
  try {
    await setTaskTags(spaceId.value, props.task.id, taskTags.value)
    ElMessage.success('标签已更新')
    emit('changed')
  } finally {
    tagSaving.value = false
  }
}
</script>

<style scoped>
.detail-drawer {
  padding: 0 16px 16px;
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}

.uri {
  font-size: 11px;
  color: var(--color-text-regular);
  word-break: break-all;
}

.output-block {
  margin-top: 16px;
}

.count-badge {
  display: inline-block;
  margin-left: 6px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  padding: 0 5px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  color: #fff;
  background: #1a73e8;
  border-radius: 9px;
}

.output-body {
  min-height: 48px;
}

.output-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.output-table {
  display: inline-block;
  padding: 3px 8px;
  font-size: 12px;
  color: #1a73e8;
  background: #eef4ff;
  border: 1px solid #d6e4ff;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.output-table:hover {
  background: #d6e4ff;
}

.status-block {
  margin-top: 16px;
}

.block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 10px;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.dim-label {
  font-size: 13px;
  color: var(--color-text-regular);
  width: 110px;
}

.status-label {
  font-size: 13px;
  color: var(--color-text-regular);
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}

.notes-section {
  margin-top: 20px;
}

.notes-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.notes-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.note-author {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.note-line {
  font-size: 13px;
  color: var(--color-text-regular);
  line-height: 1.7;
}

.note-result {
  font-size: 13px;
  color: var(--color-success);
  line-height: 1.7;
}
</style>
