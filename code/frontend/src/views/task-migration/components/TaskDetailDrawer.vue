<template>
  <!-- 任务详情抽屉：全部字段 + 排查备注时间线（需求 §6.2.7 / §6.3） -->
  <el-drawer
    v-model="visible"
    :title="task ? `任务详情：${task.task_name}` : '任务详情'"
    size="680px"
  >
    <div v-loading="loading" class="detail-drawer">
      <template v-if="task">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务名称">
            <span class="mono">{{ task.task_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="工作流">
            <span class="mono">{{ task.workflow_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="脚本名称">
            <span class="mono">{{ task.script_name || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="Owner">{{ task.owner || '—' }}</el-descriptions-item>
          <el-descriptions-item label="任务URI" :span="2">
            <span class="mono uri">{{ task.task_uri }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="输入表" :span="2">
            <span class="mono">{{ task.input_tables || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="输出表" :span="2">
            <span class="mono">{{ task.output_tables || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="迁移状态">
            <TaskStatusTag :status="task.migration_status" />
          </el-descriptions-item>
          <el-descriptions-item label="调度状态">
            <ScheduleStatusTag :status="task.schedule_status" />
          </el-descriptions-item>
          <el-descriptions-item label="校验状态">
            <CheckStatusTag :status="task.check_status" />
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatTime(task.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 状态流转（按状态机可选） -->
        <div class="status-row" v-if="nextStatuses.length">
          <span class="status-label">流转状态：</span>
          <el-dropdown trigger="click" @command="changeStatus">
            <el-button size="small">
              选择目标状态<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="s in nextStatuses" :key="s" :command="s">
                  流转为「{{ s }}」
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 数据血缘联动（交互评审 I7：带任务上下文跳转血缘页预置检索） -->
        <div class="lineage-row">
          <span class="status-label">数据血缘：</span>
          <el-button size="small" @click="viewLineage">查看血缘</el-button>
          <span class="lineage-hint">在血缘图中检索该任务的上下游关联</span>
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
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import TaskStatusTag from '@/components/common/TaskStatusTag.vue'
import ScheduleStatusTag from '@/components/common/ScheduleStatusTag.vue'
import CheckStatusTag from '@/components/common/CheckStatusTag.vue'
import NoteFormDialog from './NoteFormDialog.vue'
import TaskTagSelect from './TaskTagSelect.vue'
import { getTaskTags, listNotes, setTaskTags, updateTaskStatus } from '@/api/task-migration'
import { formatTime } from '@/utils/format'
import { TASK_STATUS_TRANSITIONS } from '@/types'
import type { TaskNoteOut, TaskOut } from '@/types'

const props = defineProps<{ modelValue: boolean; task?: TaskOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'changed'): void
}>()

const route = useRoute()
const router = useRouter()
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

const nextStatuses = computed(() =>
  props.task ? (TASK_STATUS_TRANSITIONS[props.task.migration_status] ?? []) : []
)

watch(
  () => props.modelValue,
  (open) => {
    if (open && props.task) load()
  }
)

async function load() {
  if (!props.task) return
  loading.value = true
  try {
    notes.value = await listNotes(spaceId.value, props.task.id)
    const tags = await getTaskTags(spaceId.value, props.task.id)
    taskTags.value = tags.map((t) => t.id)
  } finally {
    loading.value = false
  }
}

async function changeStatus(status: string) {
  if (!props.task) return
  await updateTaskStatus(spaceId.value, props.task.id, status)
  ElMessage.success(`已流转为「${status}」`)
  emit('changed')
  visible.value = false
}

/** 取首个表名（逗号分隔列表）：优先输出表，其次输入表 */
function firstTable(value?: string | null): string | null {
  if (!value) return null
  const t = value.split(',')[0]?.trim()
  return t || null
}

/** 查看血缘：携带任务的输入输出表名跳入，由血缘页预置聚焦检索（交互评审 I7） */
function viewLineage() {
  if (!props.task) return
  const table = firstTable(props.task.output_tables) || firstTable(props.task.input_tables)
  router.push({
    name: 'space-lineage',
    params: { spaceId: spaceId.value },
    query: table ? { table } : {},
  })
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

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.lineage-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.lineage-hint {
  font-size: 11px;
  color: var(--color-text-muted);
}

.status-label {
  font-size: 13px;
  color: var(--color-text-regular);
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
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
