<template>
  <div class="lineage-view">
    <!-- 头部 -->
    <header class="lv-header">
      <div class="lv-title">
        <span class="lv-brand">数据血缘</span>
        <span class="lv-sub">b07 · 检索驱动的上下游可视化</span>
      </div>
      <div class="lv-tools">
        <SearchBar
          :tables="searchTables"
          :type-map="searchTypeMap"
          :project-map="searchProjectMap"
          :task-type-map="searchTaskTypeMap"
          :workflows="workflows"
          @select="focusTable = $event"
        />
        <el-button type="primary" @click="openAdd">新增血缘</el-button>
        <el-button @click="manageOpen = true">工作流管理</el-button>
      </div>
    </header>

    <!-- 当前定位表信息条 -->
    <div v-if="focusTable" class="lv-focus">
      <span class="lv-focus-tag">当前表</span>
      <span class="mono">{{ focusTable }}</span>
      <el-button link type="primary" size="small" @click="focusTable = ''">取消定位</el-button>
    </div>

    <!-- 图区 -->
    <main class="lv-body">
      <LineageGraph :graph="graphData" :focus-table="focusTable" />
    </main>

    <!-- 工作流管理抽屉 -->
    <el-drawer v-model="manageOpen" title="工作流管理" size="380px" :append-to-body="false">
      <div v-if="!workflows.length" class="muted">暂无工作流，请先新增血缘。</div>
      <div v-for="w in workflows" :key="w.name" class="wf-item">
        <div class="wf-head">
          <span class="mono">{{ w.name }}</span>
          <el-tag size="small" effect="plain">{{ w.count }} 条</el-tag>
        </div>
        <div class="wf-actions">
          <el-button size="small" @click="rebuild(w.name)">重建</el-button>
          <el-button size="small" type="danger" plain @click="delWorkflow(w.name)">删除全部</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 新增 / 重建对话框 -->
    <WorkflowDialog
      v-model="wfVisible"
      :space-id="spaceId"
      :mode="wfMode"
      :default-workflow="wfDefault"
      @success="onImported"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import LineageGraph from './components/LineageGraph.vue'
import SearchBar from './components/SearchBar.vue'
import WorkflowDialog from './components/WorkflowDialog.vue'
import { deleteWorkflow, listLineages, listWorkflows } from '@/api/lineage'
import { buildGraph, type BuildEdge, type LineageGraphData } from '@/utils/lineage-graph'
import type { LineageOut, LineageWorkflowOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const edges = ref<LineageOut[]>([])
const workflows = ref<LineageWorkflowOut[]>([])
const focusTable = ref<string>('')
const loading = ref(false)

const manageOpen = ref(false)
const wfVisible = ref(false)
const wfMode = ref<'add' | 'rebuild'>('add')
const wfDefault = ref<string>('')

/** 由后端返回的边构建血缘图（up/down/tempUp/tempDown 邻接 + typeMap 等） */
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

/** 检索建议所需的派生结构 */
const searchTables = computed(() => Array.from(graphData.value.tables))
const searchTypeMap = computed(() => Object.fromEntries(graphData.value.typeMap))
const searchProjectMap = computed(() =>
  Object.fromEntries([...graphData.value.projectMap.entries()].map(([k, v]) => [k, [...v]]))
)
const searchTaskTypeMap = computed(() =>
  Object.fromEntries([...graphData.value.taskTypeMap.entries()].map(([k, v]) => [k, [...v]]))
)

async function reload() {
  loading.value = true
  try {
    const [list, wf] = await Promise.all([listLineages(spaceId.value), listWorkflows(spaceId.value)])
    edges.value = list
    workflows.value = wf
    // 由任务详情「查看血缘」携带 table 参数跳入时，预置聚焦表（交互评审 I7）
    if (route.query.table) focusTable.value = String(route.query.table)
  } catch {
    /* 错误提示由拦截器统一处理 */
  } finally {
    loading.value = false
  }
}

function openAdd() {
  wfMode.value = 'add'
  wfDefault.value = ''
  wfVisible.value = true
}

function rebuild(name: string) {
  manageOpen.value = false
  wfMode.value = 'rebuild'
  wfDefault.value = name
  wfVisible.value = true
}

async function delWorkflow(name: string) {
  try {
    await ElMessageBox.confirm(`确认逻辑删除工作流「${name}」的全部血缘边？`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    const res = await deleteWorkflow(spaceId.value, name)
    ElMessage.success(`已删除工作流「${name}」共 ${res.deleted} 条血缘`)
    reload()
  } catch {
    /* ignore */
  }
}

function onImported() {
  reload()
}

onMounted(reload)

/** 同页带不同 table 参数跳入（如从另一任务详情进入）时，更新聚焦表（I7） */
watch(
  () => route.query.table,
  (t) => {
    if (t) focusTable.value = String(t)
  }
)
</script>

<style scoped>
.lineage-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-page-bg, #eef2f7);
}
.lv-header {
  height: 64px;
  flex: 0 0 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e3e9f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.lv-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.lv-brand {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
}
.lv-sub {
  font-size: 12px;
  color: #8a96a3;
}
.lv-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  justify-content: flex-end;
}
.lv-focus {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: #e6f4ea;
  border-bottom: 1px solid #d7e8dd;
  font-size: 13px;
  color: #188038;
}
.lv-focus-tag {
  background: #188038;
  color: #fff;
  border-radius: 10px;
  padding: 1px 10px;
  font-size: 11px;
}
.lv-body {
  flex: 1 1 auto;
  position: relative;
  min-height: 0;
}
.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  word-break: break-all;
}
.muted {
  color: #9aa7b5;
}
.wf-item {
  border: 1px solid #e3e9f0;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.wf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.wf-actions {
  display: flex;
  gap: 8px;
}
</style>
