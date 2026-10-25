<template>
  <!-- 数据校验管理（b05）：数据迁移清单全部库表 + 最新校验结果 + 近7天校验结果（需求 B05-01） -->
  <div class="dc-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">
            数据校验
            <span v-if="scenario" class="page-scenario">{{ scenario.name }}</span>
          </span>
          <div class="head-actions">
            <el-button
              type="success"
              :disabled="!scenarioId"
              :loading="refreshing"
              @click="refreshStatus"
            >
              刷新任务状态
            </el-button>
            <el-button type="primary" :disabled="!scenarioId" @click="importVisible = true">
              导入校验结果
            </el-button>
          </div>
        </div>
      </template>

      <template v-if="scenarioId">
        <div class="filter-row">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索 库名/表名..."
            clearable
            style="width: 220px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-select
            v-model="filters.result"
            placeholder="最新校验结果"
            clearable
            style="width: 150px"
            @change="search"
          >
            <el-option v-for="r in RESULT_OPTIONS" :key="r" :label="r" :value="r" />
          </el-select>
          <el-button @click="resetFilters">重置</el-button>
        </div>

        <el-table v-loading="loading" :data="list" border stripe style="margin-top: 12px">
          <el-table-column label="库表" min-width="200">
            <template #default="{ row }">
              <span class="mono link" :title="`${row.db_name}.${row.table_name}`" @click="openLineage(row.db_name, row.table_name)">
                {{ row.db_name }}.{{ row.table_name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="表类型" width="90">
            <template #default="{ row }">{{ row.table_type || '—' }}</template>
          </el-table-column>
          <el-table-column label="最新校验结果" width="130" align="center">
            <template #default="{ row }">
              <CheckResultTag :value="row.latest_result" />
            </template>
          </el-table-column>
          <el-table-column label="近7天校验结果" min-width="140">
            <template #default="{ row }">
              <WeekCheckDots :days="row.recent_days || []" />
            </template>
          </el-table-column>
          <template #empty>
            <span class="muted">暂无库表，请先在「数据迁移」中维护库表清单</span>
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

    <!-- 校验结果导入 -->
    <CheckResultImportDialog
      v-model="importVisible"
      :scenario-id="scenarioId"
      @success="load"
    />

    <!-- 库表 → 数据血缘（D3：点击库表弹出血缘并聚焦该表） -->
    <LineageDialog v-model="lineageVisible" :space-id="spaceId" :focus-table="focusTable" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useScenarioStore } from '@/store/scenario'
import CheckResultTag from '@/components/common/CheckResultTag.vue'
import WeekCheckDots from './components/WeekCheckDots.vue'
import CheckResultImportDialog from './components/CheckResultImportDialog.vue'
import LineageDialog from '@/views/lineage/components/LineageDialog.vue'
import { listChecks, refreshChecks } from '@/api/data-check'
import { useRoute } from 'vue-router'
import type { CheckOverviewOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const scenarioStore = useScenarioStore()
const scenario = computed(() => scenarioStore.b03)
const scenarioId = computed(() => scenarioStore.b03?.id ?? null)

const list = ref<CheckOverviewOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const filters = ref<{ keyword: string; result: string }>({ keyword: '', result: '' })

/** 最新校验结果筛选项（含无校验结果） */
const RESULT_OPTIONS = ['通过', '不通过', '无校验结果']

const importVisible = ref(false)
const refreshing = ref(false)

// D3：点击「库表」打开血缘并聚焦该表
const lineageVisible = ref(false)
const focusTable = ref('')

function openLineage(dbName: string, tableName: string) {
  focusTable.value = `${dbName}.${tableName}`
  lineageVisible.value = true
}

/** B05-04：全空间重跑任务级数据校验结果刷新 */
async function refreshStatus() {
  if (!scenarioId.value) return
  refreshing.value = true
  try {
    const res = await refreshChecks(spaceId.value)
    ElMessage.success(`已刷新 ${res.refreshed_tasks} 个任务的数据校验结果`)
    await load()
  } finally {
    refreshing.value = false
  }
}

async function load() {
  if (!scenarioId.value) return
  loading.value = true
  try {
    const data = await listChecks(spaceId.value, page.value, pageSize.value, {
      scenario_id: scenarioId.value ?? undefined,
      keyword: filters.value.keyword || undefined,
      result: filters.value.result || undefined,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.value = { keyword: '', result: '' }
  search()
}

function onPage(p: number) {
  page.value = p
  load()
}

onMounted(async () => {
  await scenarioStore.ensureB03(spaceId.value)
  await load()
})

/** 空间头场景切换器（b03 场景，D2）切换 → 重置分页并重载列表 */
watch(
  () => scenarioStore.b03,
  () => {
    page.value = 1
    load()
  }
)
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

.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pager {
  margin-top: 12px;
  justify-content: flex-end;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.link {
  color: #1a73e8;
  cursor: pointer;
}

.link:hover {
  text-decoration: underline;
}
</style>
