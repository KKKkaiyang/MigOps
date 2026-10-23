<template>
  <!-- 空间概览：空间信息 + 真实统计（交互评审 I8）+ 项目自评 + 模块入口 -->
  <div class="space-overview" v-loading="loading">
    <template v-if="space">
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span class="card-title">空间信息</span>
            <el-button link type="primary" @click="$router.push('/b01/spaces')">前往空间管理</el-button>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目名称">{{ space.space_name }}</el-descriptions-item>
          <el-descriptions-item label="项目简称">
            <span class="mono">{{ space.space_code }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ space.customer_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="空间状态">
            <SpaceStatusTag :status="space.status" />
          </el-descriptions-item>
          <el-descriptions-item label="源端平台">{{ space.source_platform || '—' }}</el-descriptions-item>
          <el-descriptions-item label="目标端平台">{{ space.target_platform || '—' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ space.owner || '—' }}</el-descriptions-item>
          <el-descriptions-item label="整体进展（自评）">{{ space.overall_progress }}%</el-descriptions-item>
          <el-descriptions-item label="项目周期">
            {{ formatDate(space.start_date) }} ~ {{ formatDate(space.end_date) }}
          </el-descriptions-item>
          <el-descriptions-item label="绑定数据库">
            <span class="mono">{{ space.db_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="项目空间说明" :span="2">
            {{ space.remark || '—' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 业务进展（真实数据聚合，替代单一手工进展口径） -->
      <div v-if="stats" class="section-title">业务进展（真实数据）</div>
      <div v-if="stats" class="stats-grid">
        <el-card class="stat-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-title">数据迁移（b03）</span>
              <span class="card-sub">{{ stats.b03_scenario_count }} 个场景</span>
            </div>
          </template>
          <div class="dist-row" v-for="row in b03Rows" :key="row.k">
            <span class="dist-k">{{ row.k }}</span>
            <div class="dist-bar"><i :style="{ width: row.pct + '%', background: row.color }" /></div>
            <span class="dist-n">{{ row.n }}</span>
          </div>
          <div class="stat-kv">库表合计 <b>{{ stats.b03_table_total }}</b> · 迁移记录 <b>{{ stats.b03_record_count }}</b> 条</div>
        </el-card>

        <el-card class="stat-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-title">任务迁移（b04）</span>
              <span class="card-sub">{{ stats.b04_scenario_count }} 个场景</span>
            </div>
          </template>
          <div class="dist-row" v-for="row in b04Rows" :key="row.k">
            <span class="dist-k">{{ row.k }}</span>
            <div class="dist-bar"><i :style="{ width: row.pct + '%', background: row.color }" /></div>
            <span class="dist-n">{{ row.n }}</span>
          </div>
          <div class="stat-kv">任务合计 <b>{{ stats.b04_task_total }}</b> · 排查备注 <b>{{ stats.b04_note_count }}</b> 条</div>
        </el-card>
      </div>

      <!-- 项目自评（手工维护，与真实统计并列） -->
      <div class="section-title">项目自评（手工维护）</div>
      <el-card class="self-card" shadow="never">
        <div class="self-row">
          <div class="self-bar"><i :style="{ width: `${space.overall_progress}%` }" /></div>
          <span class="self-num">{{ space.overall_progress }}%</span>
          <span class="self-note">与上方真实统计并列展示；二期可切换为按任务完成率自动计算（保留手工覆盖）</span>
          <el-button v-if="canEdit" size="small" @click="editVisible = true">编辑</el-button>
        </div>
      </el-card>

      <div class="section-title">模块入口</div>
      <div class="module-grid">
        <el-card
          v-for="m in modules"
          :key="m.route"
          class="module-card"
          shadow="never"
          @click="$router.push({ name: m.route, params: { spaceId } })"
        >
          <div class="module-icon" :style="{ background: m.bg }">
            <el-icon :size="20" :color="m.color"><component :is="m.icon" /></el-icon>
          </div>
          <div class="module-name">{{ m.name }}</div>
          <div class="module-desc">{{ m.desc }}</div>
        </el-card>
      </div>
    </template>

    <SpaceFormDialog v-model="editVisible" :space="space" @success="reloadSpace" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Document, DataLine, Notebook, Tickets, PriceTag, Share } from '@element-plus/icons-vue'
import { getSpace, getSpaceStats } from '@/api/space'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import SpaceFormDialog from '@/views/space/components/SpaceFormDialog.vue'
import { useUserStore } from '@/store/user'
import { formatDate } from '@/utils/format'
import type { SpaceOut, SpaceStatsOut } from '@/types'

const route = useRoute()
const userStore = useUserStore()
const spaceId = computed(() => Number(route.params.spaceId))

const space = ref<SpaceOut | null>(null)
const stats = ref<SpaceStatsOut | null>(null)
const loading = ref(true)
const editVisible = ref(false)

/** 空间信息编辑（整体进展等）：L0 或本空间 L1 */
const canEdit = computed(() => userStore.isL0 || space.value?.my_role === 'L1')

/** 全局状态色板（交互评审 I9：同义状态跨模块同色） */
const STATUS_COLORS: Record<string, string> = {
  未开始: '#bdc3c7',
  未迁移: '#bdc3c7',
  未提交: '#bdc3c7',
  未校验: '#bdc3c7',
  迁移中: '#1a73e8',
  进行中: '#1a73e8',
  调度中: '#1a73e8',
  改造完成: '#1a73e8',
  已完成: '#188038',
  调度成功: '#188038',
  校验通过: '#188038',
  数据校验通过: '#188038',
  客户验收通过: '#188038',
  成功: '#188038',
  异常: '#e53935',
  失败: '#e53935',
  校验不通过: '#e53935',
  数据校验不通过: '#e53935',
  客户验收不通过: '#e53935',
  已停止: '#f2a100',
  挂起: '#f2a100',
  废弃: '#8a96a3',
}

const B03_ORDER = ['未迁移', '迁移中', '已完成', '异常']
const B04_ORDER = [
  '未开始',
  '改造完成',
  '调度成功',
  '数据校验通过',
  '数据校验不通过',
  '客户验收通过',
  '挂起',
  '废弃',
]

interface DistRow {
  k: string
  n: number
  pct: number
  color: string
}

function buildRows(statsMap: Record<string, number>, order: string[], total: number): DistRow[] {
  return order
    .map((k) => ({
      k,
      n: statsMap[k] || 0,
      pct: total ? Math.round(((statsMap[k] || 0) / total) * 100) : 0,
      color: STATUS_COLORS[k] || '#8a96a3',
    }))
    .filter((r) => r.n > 0)
}

const b03Rows = computed<DistRow[]>(() =>
  buildRows(stats.value?.b03_metadata_stats ?? {}, B03_ORDER, stats.value?.b03_table_total ?? 0)
)
const b04Rows = computed<DistRow[]>(() =>
  buildRows(stats.value?.b04_migration_stats ?? {}, B04_ORDER, stats.value?.b04_task_total ?? 0)
)

const modules = computed(() => [
  {
    route: 'space-materials',
    name: '项目资料索引',
    desc: stats.value ? `${stats.value.b02_material_count} 条资料 · ${stats.value.b02_category_count} 个分类` : '集中维护外部链接、Markdown 资料与平台内台账入口',
    icon: Document,
    bg: '#e8f0fe',
    color: '#1a73e8',
  },
  {
    route: 'space-data-migrations',
    name: '数据迁移管理',
    desc: stats.value ? `${stats.value.b03_scenario_count} 个场景 · ${stats.value.b03_table_total} 张库表` : '按场景管理库表清单的元数据 / 全量 / 增量迁移状态',
    icon: DataLine,
    bg: '#e6f4ea',
    color: '#188038',
  },
  {
    route: 'space-tasks',
    name: '任务迁移管理',
    desc: stats.value ? `${stats.value.b04_scenario_count} 个场景 · ${stats.value.b04_task_total} 个任务` : '任务全生命周期状态、排查备注时间线与自定义台账',
    icon: Notebook,
    bg: '#f0e8ff',
    color: '#6a3fb5',
  },
  {
    route: 'space-ledgers',
    name: '任务台账',
    desc: stats.value ? `${stats.value.b04_view_count} 个台账 · 固定名单 ${stats.value.b04_fixed_view_count}` : '任务清单视角：自动更新 / 固定名单',
    icon: Tickets,
    bg: '#e0f2fe',
    color: '#075985',
  },
  {
    route: 'space-tags',
    name: '标签管理',
    desc: stats.value ? `${stats.value.b06_tag_count} 个标签 · 管理 ${stats.value.b06_manage_tag_count} / 技术 ${stats.value.b06_tech_tag_count}` : '空间级标签维护与查看',
    icon: PriceTag,
    bg: '#fef7e0',
    color: '#b06a00',
  },
  {
    route: 'space-lineage',
    name: '血缘管理',
    desc: stats.value ? `${stats.value.b07_workflow_count} 个工作流 · ${stats.value.b07_edge_count} 条血缘边` : '检索驱动的上下游可视化',
    icon: Share,
    bg: '#e6f4ea',
    color: '#188038',
  },
])

async function reloadSpace() {
  space.value = await getSpace(spaceId.value)
}

onMounted(async () => {
  loading.value = true
  try {
    const [s, st] = await Promise.all([getSpace(spaceId.value), getSpaceStats(spaceId.value)])
    space.value = s
    stats.value = st
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.space-overview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-card {
  border-color: var(--color-border);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.card-sub {
  font-size: 12px;
  color: var(--color-text-muted);
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title::before {
  content: '';
  width: 3px;
  height: 13px;
  background: var(--color-primary);
  border-radius: 2px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  border-color: var(--color-border);
}

.dist-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
}

.dist-k {
  width: 96px;
  text-align: right;
  color: var(--color-text-regular);
  flex-shrink: 0;
}

.dist-bar {
  flex: 1;
  height: 12px;
  background: #eef1f5;
  border-radius: 3px;
  overflow: hidden;
}

.dist-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
}

.dist-n {
  width: 32px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary);
  font-weight: 600;
}

.stat-kv {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.stat-kv b {
  color: var(--color-text-primary);
}

.self-card {
  border-color: var(--color-border);
}

.self-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.self-bar {
  flex: 1;
  height: 10px;
  background: #eef1f5;
  border-radius: 5px;
  overflow: hidden;
}

.self-bar i {
  display: block;
  height: 100%;
  background: var(--color-primary);
  border-radius: 5px;
}

.self-num {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
  min-width: 44px;
}

.self-note {
  flex: 2;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.module-card {
  border-color: var(--color-border);
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.module-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-medium);
}

.module-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.module-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.module-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
</style>
