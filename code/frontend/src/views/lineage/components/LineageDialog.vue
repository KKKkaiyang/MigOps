<template>
  <el-dialog
    v-model="visible"
    :destroy-on-close="true"
    :close-on-click-modal="true"
    width="calc(100vw - 32px)"
    top="24px"
    class="lineage-dialog"
    append-to-body
  >
    <!-- 自定义蓝色头部（对齐 CODEBUDDY.md §6.4.6） -->
    <template #header>
      <div class="ld-header">
        <span class="ld-title">数据血缘</span>
        <span class="ld-sub">当前表 · <span class="mono">{{ focusTable }}</span>（受限视图：固定根表，可上下钻取）</span>
      </div>
    </template>

    <div class="ld-body">
      <div v-if="loading" v-loading="true" class="ld-loading"></div>
      <LineageGraph
        v-else
        :graph="graphData"
        :focus-table="focusTable"
        :space-id="spaceId"
        :check-results="checkResults"
        @open-task="onOpenTask"
      />
    </div>

    <!-- D5：血缘内任务名直达任务详情（隐藏任务输出表区块，其余与任务迁移一致） -->
    <TaskDetailDrawer
      v-model="taskVisible"
      :space-id="spaceId"
      :task="detailTask"
      hide-output-tables
      @changed="onTaskChanged"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import LineageGraph from './LineageGraph.vue'
import TaskDetailDrawer from '@/views/task-migration/components/TaskDetailDrawer.vue'
import { listLineages } from '@/api/lineage'
import { getCheckResultsByTables } from '@/api/data-check'
import { getTaskByKey } from '@/api/task-migration'
import { buildGraph, type BuildEdge, type LineageGraphData } from '@/utils/lineage-graph'
import type { LineageOut, TaskOut } from '@/types'

const props = defineProps<{
  modelValue: boolean
  spaceId: number
  focusTable: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const edges = ref<LineageOut[]>([])
const loading = ref(false)
// D4：血缘节点校验□数据（key = db.table）
const checkResults = ref<Record<string, Array<{ data_date: string; result?: string | null; src_volume?: number | null; dst_volume?: number | null }>>>({})
// D5：任务详情抽屉
const taskVisible = ref(false)
const detailTask = ref<TaskOut | null>(null)
const taskLoading = ref(false)

/** 与 LineageView 一致的构图逻辑，但根表固定为传入表、不渲染检索栏 */
const graphData = computed<LineageGraphData>(() =>
  buildGraph(
    edges.value.map(
      (e): BuildEdge => ({
        source: e.input_table,
        target: e.output_table,
        sourceType: e.input_table_type,
        targetType: e.output_table_type,
        workflow: e.workflow_name,
        task: e.task_name,
        taskType: e.task_type,
        project: e.project_name,
        script: e.script_name,
      })
    )
  )
)

/** 打开弹层时拉取当前空间全部血缘边并构图，并批量取节点表的校验结果（D4） */
watch(visible, async (open) => {
  if (!open) return
  loading.value = true
  edges.value = []
  checkResults.value = {}
  try {
    edges.value = await listLineages(props.spaceId)
    // 构图后立即取本空间全部节点表的最近校验结果（省略 tables：后端整空间返回，避免超长 URL 被拒）
    checkResults.value = (await getCheckResultsByTables(props.spaceId)).tables
  } catch {
    /* 错误提示由请求拦截器统一处理 */
  } finally {
    loading.value = false
  }
})

/** D5：血缘「查看详情」内任务名 → 按 项目名称+任务名称 查任务并打开详情面板 */
async function onOpenTask(p: { project: string; task: string }) {
  taskLoading.value = true
  try {
    detailTask.value = await getTaskByKey(props.spaceId, p.project, p.task)
    taskVisible.value = true
  } catch {
    /* 未找到或请求失败：拦截器已提示 */
  } finally {
    taskLoading.value = false
  }
}

/** 任务详情内状态/标签/备注变更后刷新血缘图（保持与源数据一致） */
function onTaskChanged() {
  // 血缘节点本身不缓存任务详情，无需额外刷新；预留钩子
}
</script>

<style scoped>
.lineage-dialog :deep(.el-dialog__header) {
  padding: 0;
  background: #1a73e8;
  border-radius: 10px 10px 0 0;
}
.lineage-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.ld-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 14px 18px;
}
.ld-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}
.ld-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}
.ld-sub .mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.ld-body {
  height: calc(100vh - 160px);
  min-height: 420px;
  background: #eef2f7;
  position: relative;
}
.ld-loading {
  height: 100%;
}
.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
</style>
