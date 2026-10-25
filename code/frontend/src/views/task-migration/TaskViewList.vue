<template>
  <!-- 任务视图清单：空间内独立的视图列表入口（需求 R1 / D1；场景由空间头切换器维护） -->
  <div class="ledger-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">
            任务视图
            <span v-if="scenario" class="page-scenario">{{ scenario.name }}</span>
          </span>
          <el-button type="primary" :disabled="!scenarioId" @click="openCreate">新建视图</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="savedViews" border stripe style="margin-top: 12px">
        <el-table-column prop="name" label="视图名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="模式" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.view_mode === 'fixed' ? 'warning' : 'info'">
              {{ VIEW_MODE_LABEL[row.view_mode] || row.view_mode }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="task_count" label="任务数" width="90" align="center" />
        <el-table-column prop="created_by" label="创建人" width="110" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ row.created_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openView(row as SavedViewOut)">打开</el-button>
            <el-button link type="primary" @click="openEdit(row as SavedViewOut)">编辑</el-button>
            <el-button link type="danger" @click="remove(row as SavedViewOut)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><span class="muted">当前场景暂无视图，可在任务列表勾选任务或保存筛选条件创建</span></template>
      </el-table>

      <el-empty v-if="!scenarioId" description="请先在空间头部选择或创建迁移场景" />
    </el-card>

    <SaveViewDialog
      v-model="saveViewVisible"
      :scenario-id="scenarioId ?? 0"
      :view="editingView"
      @success="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import SaveViewDialog from './components/SaveViewDialog.vue'
import { deleteSavedView, listSavedViews } from '@/api/task-migration'
import { useScenarioStore } from '@/store/scenario'
import { VIEW_MODE_LABEL } from '@/types'
import type { SavedViewOut } from '@/types'

const route = useRoute()
const router = useRouter()
const spaceId = computed(() => Number(route.params.spaceId))

/** 场景上下文：空间级 store 维护（跨导航保持，交互评审 I2） */
const scenarioStore = useScenarioStore()
const scenario = computed(() => scenarioStore.b04)
const scenarioId = computed(() => scenarioStore.b04?.id ?? null)

const savedViews = ref<SavedViewOut[]>([])
const loading = ref(false)

const saveViewVisible = ref(false)
const editingView = ref<SavedViewOut | undefined>(undefined)

async function loadSavedViews() {
  if (!scenarioId.value) {
    savedViews.value = []
    return
  }
  loading.value = true
  try {
    savedViews.value = await listSavedViews(spaceId.value, scenarioId.value)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingView.value = undefined
  saveViewVisible.value = true
}

function openEdit(row: SavedViewOut) {
  editingView.value = row
  saveViewVisible.value = true
}

function openView(row: SavedViewOut) {
  router.push({
    name: 'space-custom-view',
    params: { spaceId: spaceId.value, viewId: row.id },
  })
}

async function remove(row: SavedViewOut) {
  await ElMessageBox.confirm(`删除视图「${row.name}」仅移除该视图（不影响原任务），确认删除？`, '删除视图', {
    type: 'warning',
  })
  await deleteSavedView(spaceId.value, row.id)
  ElMessage.success('视图已删除')
  await loadSavedViews()
}

function onSaved() {
  saveViewVisible.value = false
  editingView.value = undefined
  loadSavedViews()
}

/** 场景切换（空间头切换器）→ 重载视图列表 */
watch(
  () => scenarioStore.b04,
  () => {
    loadSavedViews()
  }
)

onMounted(async () => {
  await scenarioStore.ensureB04(spaceId.value)
  await loadSavedViews()
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

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
