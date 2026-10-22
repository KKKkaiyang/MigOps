<template>
  <!-- 数据迁移管理（b03）：按场景管理库表清单与迁移状态（需求 §5） -->
  <div class="dm-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">数据迁移管理</span>
          <div class="head-actions">
            <el-button :disabled="!scenarioId" @click="openImport('items')">导入库表清单</el-button>
            <el-button :disabled="!scenarioId" @click="openImport('records')">导入迁移记录</el-button>
            <el-button :disabled="!scenarioId" @click="exportItems">导出</el-button>
            <el-button :disabled="!scenarioId" type="primary" @click="openCreateItem">+ 新增库表</el-button>
          </div>
        </div>
      </template>

      <ScenarioBar
        :scenarios="scenarios"
        :scenario-id="scenarioId"
        @change="onScenarioChange"
        @create="scenarioVisible = true"
        @delete="removeScenario"
      />

      <template v-if="scenarioId">
        <FilterBar :filters="filters" @update="onFilterUpdate" @search="search" @reset="resetFilters" />

        <!-- 批量操作栏 -->
        <div v-if="selection.length" class="batch-bar">
          <span>已选 {{ selection.length }} 条</span>
          <el-button size="small" type="primary" @click="batchVisible = true">批量更新状态</el-button>
          <el-button size="small" @click="clearSelection">清除选择</el-button>
        </div>

        <el-table
          v-loading="loading"
          :data="list"
          border
          stripe
          style="margin-top: 12px"
          @selection-change="(rows: TableItemOut[]) => (selection = rows)"
        >
          <el-table-column type="selection" width="42" />
          <el-table-column label="库表" min-width="200">
            <template #default="{ row }">
              <span class="mono">{{ row.db_name }}.{{ row.table_name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="目标库表" min-width="180">
            <template #default="{ row }">
              <span v-if="row.target_db_name || row.target_table_name" class="mono">
                {{ row.target_db_name || '—' }}.{{ row.target_table_name || '—' }}
              </span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="表类型" width="90">
            <template #default="{ row }">{{ row.table_type || '—' }}</template>
          </el-table-column>
          <el-table-column label="元数据状态" width="110">
            <template #default="{ row }">
              <MigrationStatusTag :status="row.metadata_status" />
            </template>
          </el-table-column>
          <el-table-column label="全量迁移状态" width="115">
            <template #default="{ row }">
              <MigrationStatusTag :status="row.full_sync_status" />
            </template>
          </el-table-column>
          <el-table-column label="全量截止日期" width="120">
            <template #default="{ row }">{{ formatDate(row.full_sync_cutoff_date) }}</template>
          </el-table-column>
          <el-table-column label="增量状态" width="105">
            <template #default="{ row }">
              <MigrationStatusTag :status="row.incr_sync_status" />
            </template>
          </el-table-column>
          <el-table-column label="迁移记录" width="95" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRecords(row as TableItemOut)">
                {{ row.record_count }} 条
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEditItem(row as TableItemOut)">编辑</el-button>
              <el-button link type="danger" @click="removeItem(row as TableItemOut)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <span class="muted">暂无库表，点击右上角「导入库表清单」或「新增库表」</span>
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

    <!-- 场景创建 -->
    <ScenarioDialog v-model="scenarioVisible" @success="onScenarioCreated" />

    <!-- 库表新增/编辑 -->
    <ItemFormDialog
      v-model="itemVisible"
      :scenario-id="scenarioId ?? 0"
      :item="currentItem"
      @success="load"
    />

    <!-- 批量状态 -->
    <BatchStatusDialog
      v-model="batchVisible"
      :scenario-id="scenarioId ?? 0"
      :count="selection.length"
      :ids="selection.map((s) => s.id)"
      @success="onBatchDone"
    />

    <!-- 迁移记录抽屉 -->
    <RecordDrawer v-model="recordVisible" :item="recordItem" @changed="load" />

    <!-- 导入对话框（库表清单 / 迁移记录） -->
    <ImportDialog
      v-model="importVisible"
      :kind="importKind"
      :scenario-id="scenarioId ?? 0"
      @success="load"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MigrationStatusTag from '@/components/common/MigrationStatusTag.vue'
import ScenarioBar from './components/ScenarioBar.vue'
import FilterBar from './components/FilterBar.vue'
import ScenarioDialog from './components/ScenarioDialog.vue'
import ItemFormDialog from './components/ItemFormDialog.vue'
import BatchStatusDialog from './components/BatchStatusDialog.vue'
import RecordDrawer from './components/RecordDrawer.vue'
import ImportDialog from './components/ImportDialog.vue'
import {
  deleteScenario,
  deleteTableItem,
  listScenarios,
  listTableItems,
} from '@/api/data-migration'
import { downloadFile } from '@/utils/download'
import { formatDate } from '@/utils/format'
import type { DataMigrationScenarioOut, TableItemOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const scenarios = ref<DataMigrationScenarioOut[]>([])
const scenarioId = ref<number | null>(null)

const list = ref<TableItemOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selection = ref<TableItemOut[]>([])

const filters = ref<Record<string, string>>({
  keyword: '',
  table_type: '',
  metadata_status: '',
  full_sync_status: '',
  incr_sync_status: '',
})

const scenarioVisible = ref(false)
const itemVisible = ref(false)
const currentItem = ref<TableItemOut | null>(null)
const batchVisible = ref(false)
const recordVisible = ref(false)
const recordItem = ref<TableItemOut | null>(null)
const importVisible = ref(false)
const importKind = ref<'items' | 'records'>('items')

async function loadScenarios() {
  scenarios.value = await listScenarios(spaceId.value)
  if (!scenarioId.value && scenarios.value.length) {
    scenarioId.value = scenarios.value[0].id
  }
}

async function load() {
  if (!scenarioId.value) return
  loading.value = true
  try {
    const data = await listTableItems(spaceId.value, scenarioId.value, page.value, pageSize.value, {
      keyword: filters.value.keyword || undefined,
      table_type: filters.value.table_type || undefined,
      metadata_status: filters.value.metadata_status || undefined,
      full_sync_status: filters.value.full_sync_status || undefined,
      incr_sync_status: filters.value.incr_sync_status || undefined,
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
    table_type: '',
    metadata_status: '',
    full_sync_status: '',
    incr_sync_status: '',
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

function openCreateItem() {
  currentItem.value = null
  itemVisible.value = true
}

function openEditItem(row: TableItemOut) {
  currentItem.value = row
  itemVisible.value = true
}

async function removeItem(row: TableItemOut) {
  await ElMessageBox.confirm(`确认删除库表「${row.db_name}.${row.table_name}」？`, '删除确认', {
    type: 'warning',
  })
  await deleteTableItem(spaceId.value, row.id)
  ElMessage.success('删除成功')
  await load()
  await loadScenarios()
}

async function removeScenario() {
  await ElMessageBox.confirm('删除场景将级联删除其下全部库表与迁移记录，确认删除？', '删除场景', {
    type: 'warning',
  })
  await deleteScenario(spaceId.value, scenarioId.value!)
  ElMessage.success('场景已删除')
  scenarioId.value = null
  await loadScenarios()
}

function onBatchDone() {
  batchVisible.value = false
  clearSelection()
  load()
}

function openRecords(row: TableItemOut) {
  recordItem.value = row
  recordVisible.value = true
}

function openImport(kind: 'items' | 'records') {
  importKind.value = kind
  importVisible.value = true
}

async function exportItems() {
  await downloadFile(
    `/b03/scenarios/${scenarioId.value}/table-items/export`,
    {
      space_id: spaceId.value,
      keyword: filters.value.keyword || undefined,
      table_type: filters.value.table_type || undefined,
      metadata_status: filters.value.metadata_status || undefined,
      full_sync_status: filters.value.full_sync_status || undefined,
      incr_sync_status: filters.value.incr_sync_status || undefined,
    },
    '库表清单.xlsx'
  )
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

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
