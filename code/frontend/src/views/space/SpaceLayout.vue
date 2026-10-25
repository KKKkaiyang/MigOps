<template>
  <!-- 项目空间视图框架：侧边分组导航（支持收起/展开）+ 空间头（分区 + 场景切换器常驻）+ 子页面 -->
  <div class="space-view" v-loading="loading">
    <div class="space-body">
      <!-- 侧边分组导航（交互评审 I1：按业务阶段分组，任务列表/台账/标签收纳为任务迁移子项） -->
      <aside v-if="!collapsed" class="sidebar">
        <!-- 收起按钮（LAYOUT-01/D4：收起后侧边栏完全隐藏，右缘留展开按钮） -->
        <div class="side-toggle">
          <el-tooltip content="收起菜单" placement="right">
            <el-button link class="toggle-btn" @click="toggleCollapsed">
              <span class="toggle-ico">«</span><span class="toggle-text">收起</span>
            </el-button>
          </el-tooltip>
        </div>

        <div class="side-group">
          <router-link class="side-item" :to="{ name: 'space-overview', params: { spaceId } }">
            <span class="ico">🏠</span>空间概览
          </router-link>
        </div>

        <div class="side-group">
          <div class="side-group-title">资料准备</div>
          <router-link class="side-item" :to="{ name: 'space-materials', params: { spaceId } }">
            <span class="ico">📄</span>项目资料索引
            <span v-if="stats" class="side-badge">{{ stats.b02_material_count }}</span>
          </router-link>
        </div>

        <div class="side-group">
          <div class="side-group-title">迁移执行</div>
          <router-link class="side-item" :to="{ name: 'space-data-migrations', params: { spaceId } }">
            <span class="ico">🗄️</span>数据迁移
          </router-link>
          <div class="side-item side-parent" :class="{ on: inTaskModule }" @click="taskGroupOpen = !taskGroupOpen">
            <span class="ico">⚙️</span>任务迁移
            <span class="caret" :class="{ open: taskGroupOpen }">▾</span>
          </div>
          <div class="side-sub" v-show="taskGroupOpen || inTaskModule">
            <router-link class="side-item" :to="{ name: 'space-tasks', params: { spaceId } }">
              任务列表<span v-if="stats" class="side-badge">{{ stats.b04_task_total }}</span>
            </router-link>
            <router-link class="side-item" :to="{ name: 'space-task-views', params: { spaceId } }">
              任务视图<span v-if="stats" class="side-badge">{{ stats.b04_view_count }}</span>
            </router-link>
            <router-link class="side-item" :to="{ name: 'space-tags', params: { spaceId } }">
              标签管理<span v-if="stats" class="side-badge">{{ stats.b06_tag_count }}</span>
            </router-link>
          </div>
        </div>

        <div class="side-group">
          <div class="side-group-title">数据校验</div>
          <router-link class="side-item" :to="{ name: 'space-data-checks', params: { spaceId } }">
            <span class="ico">✅</span>数据校验
          </router-link>
        </div>

        <div class="side-group">
          <div class="side-group-title">数据资产</div>
          <router-link class="side-item" :to="{ name: 'space-lineage', params: { spaceId } }">
            <span class="ico">🕸️</span>血缘管理
          </router-link>
        </div>
      </aside>

      <!-- 收起态：侧边栏完全隐藏，仅留展开按钮窄条，右边面板自适应撑满（LAYOUT-01/D4） -->
      <div v-else class="side-collapsed-bar">
        <el-tooltip content="展开菜单" placement="right">
          <el-button link class="toggle-btn expand" @click="toggleCollapsed">
            <span class="toggle-ico">»</span>
          </el-button>
        </el-tooltip>
      </div>

      <!-- 主内容区 -->
      <div class="space-main">
        <!-- 空间头：左区身份信息 / 右区角色·成员·自评进展 + 场景切换器（I12 分区） -->
        <header class="space-head">
          <div class="head-left">
            <div class="title-row">
              <span class="space-title">{{ space?.space_name }}</span>
              <SpaceStatusTag v-if="space" :status="space.status" />
              <span class="space-code mono">{{ space?.space_code }}</span>
            </div>
            <div class="head-meta">
              <span v-if="routeLine">{{ routeLine }}</span>
              <span v-else class="muted">源/目标端平台未维护</span>
              <template v-if="space?.customer_name">
                <span class="dot">·</span><span>客户：{{ space.customer_name }}</span>
              </template>
            </div>
          </div>
          <div class="head-right">
            <SpaceScenarioPicker
              :module="pickerModule"
              :scenarios="pickerScenarios"
              :scenario-id="pickerScenarioId"
              @change="onScenarioChange"
              @create="openScenarioCreate"
              @delete="removeScenario"
            />
            <div class="head-chip">
              <span class="k">我的角色</span>
              <span class="v">{{ roleLabel }}</span>
            </div>
            <div class="head-chip">
              <span class="k">成员</span>
              <span class="v">{{ space?.member_count ?? 0 }} 人</span>
            </div>
            <div class="head-chip">
              <span class="k">整体进展（自评）</span>
              <div class="progress-mini">
                <div class="bar"><i :style="{ width: (space?.overall_progress ?? 0) + '%' }" /></div>
                <span class="num">{{ space?.overall_progress ?? 0 }}%</span>
                <el-button v-if="canEditSpace" link type="primary" size="small" @click="editVisible = true">编辑</el-button>
              </div>
            </div>
          </div>
        </header>

        <router-view v-if="!loading" />
      </div>
    </div>

    <!-- 场景创建（按当前模块路由到对应弹窗） -->
    <B03ScenarioDialog v-model="b03ScenarioVisible" @success="onB03ScenarioCreated" />
    <B04ScenarioDialog v-model="b04ScenarioVisible" @success="onB04ScenarioCreated" />
    <!-- 空间信息编辑（整体进展等，仅 L0/L1） -->
    <SpaceFormDialog v-model="editVisible" :space="space" @success="reloadSpace" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import SpaceScenarioPicker from './components/SpaceScenarioPicker.vue'
import SpaceFormDialog from './components/SpaceFormDialog.vue'
import B03ScenarioDialog from '@/views/data-migration/components/ScenarioDialog.vue'
import B04ScenarioDialog from '@/views/task-migration/components/ScenarioDialog.vue'
import { getSpace, getSpaceStats } from '@/api/space'
import { deleteScenario as deleteB03Scenario, listScenarios as listB03Scenarios } from '@/api/data-migration'
import { deleteScenario as deleteB04Scenario, listScenarios as listB04Scenarios } from '@/api/task-migration'
import { useScenarioStore } from '@/store/scenario'
import { useUserStore } from '@/store/user'
import { ROLE_LEVEL_MAP } from '@/types'
import type { DataMigrationScenarioOut, SpaceOut, SpaceStatsOut, TaskScenarioOut } from '@/types'

const route = useRoute()
const userStore = useUserStore()
const scenarioStore = useScenarioStore()

const spaceId = computed(() => Number(route.params.spaceId))

const space = ref<SpaceOut | null>(null)
const stats = ref<SpaceStatsOut | null>(null)
const loading = ref(true)

/** b03 / b04 场景清单（供空间头切换器下拉） */
const b03Scenarios = ref<DataMigrationScenarioOut[]>([])
const b04Scenarios = ref<TaskScenarioOut[]>([])

/** 任务迁移子导航：路由在任务模块内或用户手动展开时保持展开 */
const taskGroupOpen = ref(false)
const inTaskModule = computed(() =>
  ['space-tasks', 'space-task-views', 'space-custom-view', 'space-tags'].includes(String(route.name))
)

/**
 * 侧边菜单收起/展开（LAYOUT-01，D4：收起后完全隐藏，留展开按钮，右边面板自适应）。
 * 状态持久化到 localStorage，刷新/切页/切空间后保持；默认展开。
 */
const SIDEBAR_COLLAPSED_KEY = 'migops:space:sidebar-collapsed'
const collapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed.value ? '1' : '0')
  if (!collapsed.value) taskGroupOpen.value = false
}

const routeLine = computed(() => {
  const s = space.value
  if (!s?.source_platform && !s?.target_platform) return ''
  return `${s.source_platform || '未知源端'} → ${s.target_platform || '未知目标端'}`
})

const roleLabel = computed(() => {
  const role = space.value?.my_role
  return role ? ROLE_LEVEL_MAP[role as keyof typeof ROLE_LEVEL_MAP] || role : '—'
})

/** 空间信息编辑（整体进展等）：L0 或本空间 L1 */
const canEditSpace = computed(() => userStore.isL0 || space.value?.my_role === 'L1')

// ── 场景切换器（b03/b04 页面激活；b05 数据校验跟随 b03 场景，D2） ──
const pickerModule = computed<'b03' | 'b04' | null>(() => {
  const m = route.meta.module
  if (m === 'b03' || m === 'b04') return m
  if (m === 'b05') return 'b03' // 数据校验页切换的是 b03 迁移场景（库表清单口径）
  return null
})

const pickerScenarios = computed(() => {
  if (pickerModule.value === 'b03') {
    return b03Scenarios.value.map((s) => ({ id: s.id, label: `${s.name}（${s.table_count} 张表）` }))
  }
  if (pickerModule.value === 'b04') {
    return b04Scenarios.value.map((s) => ({ id: s.id, label: `${s.name}（${s.task_count} 个任务）` }))
  }
  return []
})

const pickerScenarioId = computed(() => {
  if (pickerModule.value === 'b03') return scenarioStore.b03?.id ?? null
  if (pickerModule.value === 'b04') return scenarioStore.b04?.id ?? null
  return null
})

function onScenarioChange(id: number) {
  if (pickerModule.value === 'b03') {
    const s = b03Scenarios.value.find((x) => x.id === id)
    scenarioStore.selectB03(s ? { id: s.id, name: s.name } : null)
  } else if (pickerModule.value === 'b04') {
    const s = b04Scenarios.value.find((x) => x.id === id)
    scenarioStore.selectB04(s ? { id: s.id, name: s.name } : null)
  }
}

// ── 弹窗与场景管理 ──
const b03ScenarioVisible = ref(false)
const b04ScenarioVisible = ref(false)
const editVisible = ref(false)

function openScenarioCreate() {
  if (pickerModule.value === 'b03') b03ScenarioVisible.value = true
  else if (pickerModule.value === 'b04') b04ScenarioVisible.value = true
}

async function reloadScenarios() {
  const [b03List, b04List] = await Promise.all([
    listB03Scenarios(spaceId.value),
    listB04Scenarios(spaceId.value),
  ])
  b03Scenarios.value = b03List
  b04Scenarios.value = b04List
}

function onB03ScenarioCreated(s: { id: number; name: string }) {
  b03ScenarioVisible.value = false
  scenarioStore.selectB03(s)
  reloadScenarios()
}

function onB04ScenarioCreated(s: { id: number; name: string }) {
  b04ScenarioVisible.value = false
  scenarioStore.selectB04(s)
  reloadScenarios()
}

async function removeScenario() {
  if (pickerModule.value === 'b03') {
    if (!scenarioStore.b03) return
    await ElMessageBox.confirm(
      `删除场景将级联删除「${scenarioStore.b03.name}」下全部库表清单与迁移记录，确认删除？`,
      '删除场景',
      { type: 'warning' }
    )
    await deleteB03Scenario(spaceId.value, scenarioStore.b03.id)
    scenarioStore.clearB03()
    ElMessage.success('场景已删除')
  } else if (pickerModule.value === 'b04') {
    if (!scenarioStore.b04) return
    await ElMessageBox.confirm(
      `删除场景将级联删除「${scenarioStore.b04.name}」下全部任务、备注与自定义视图，确认删除？`,
      '删除场景',
      { type: 'warning' }
    )
    await deleteB04Scenario(spaceId.value, scenarioStore.b04.id)
    scenarioStore.clearB04()
    ElMessage.success('场景已删除')
  }
  await reloadScenarios()
}

// ── 数据加载 ──
async function reloadSpace() {
  space.value = await getSpace(spaceId.value)
}

async function loadAll() {
  loading.value = true
  try {
    const [s, st] = await Promise.all([getSpace(spaceId.value), getSpaceStats(spaceId.value)])
    space.value = s
    stats.value = st
  } finally {
    loading.value = false
  }
}

watch(spaceId, () => {
  // 切换空间：重置场景上下文与全部数据，避免串空间
  scenarioStore.clear()
  loadAll()
  reloadScenarios()
})

onMounted(async () => {
  await loadAll()
  await reloadScenarios()
})
</script>

<style scoped>
.space-view {
  min-height: 100%;
}

.space-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* ── 侧边导航 ── */
.sidebar {
  width: 208px;
  flex-shrink: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px 8px;
  position: sticky;
  top: 84px;
}

.side-toggle {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.toggle-btn {
  height: auto;
  padding: 2px 6px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.toggle-btn:hover {
  color: var(--color-primary);
}

.toggle-ico {
  font-weight: 700;
}

.toggle-text {
  margin-left: 4px;
}

/* ── 收起态窄条：仅承载展开按钮 ── */
.side-collapsed-bar {
  flex-shrink: 0;
  width: 28px;
  position: sticky;
  top: 84px;
  display: flex;
  justify-content: center;
  padding-top: 12px;
}

.side-collapsed-bar .toggle-btn.expand {
  padding: 6px 4px;
}

.side-group {
  margin-bottom: 14px;
}

.side-group-title {
  font-size: 11px;
  color: var(--color-text-muted);
  padding: 4px 10px 6px;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-regular);
  text-decoration: none;
  cursor: pointer;
  margin-bottom: 2px;
  transition: all 0.15s;
}

.side-item:hover {
  background: var(--el-color-primary-light-9);
  color: var(--color-primary);
}

.side-item.on,
.side-item.router-link-active {
  background: var(--color-primary);
  color: #fff;
  font-weight: 600;
}

.side-item.on .side-badge,
.side-item.router-link-active .side-badge {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

.side-item .ico {
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.side-parent .caret {
  margin-left: auto;
  font-size: 10px;
  color: var(--color-text-muted);
  transition: transform 0.15s;
}

.side-parent .caret.open {
  transform: rotate(180deg);
}

.side-sub {
  margin: 2px 0 6px 26px;
  border-left: 2px solid var(--color-border-light);
  padding-left: 8px;
}

.side-sub .side-item {
  font-size: 12px;
  padding: 5px 8px;
}

.side-sub .side-item.router-link-active {
  background: var(--el-color-primary-light-9);
  color: var(--color-primary);
}

.side-sub .side-item.router-link-active .side-badge {
  background: var(--color-primary);
  color: #fff;
}

.side-badge {
  margin-left: auto;
  background: #eef1f5;
  color: var(--color-text-muted);
  font-size: 10px;
  border-radius: 9px;
  padding: 0 6px;
  line-height: 16px;
}

/* ── 空间头 ── */
.space-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.space-head {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.head-left {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.space-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.space-code {
  font-size: 12px;
  color: var(--color-text-muted);
}

.head-meta {
  margin-top: 3px;
  font-size: 12px;
  color: var(--color-text-muted);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dot {
  color: var(--color-border-strong);
}

.head-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.head-chip {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.head-chip .k {
  font-size: 11px;
  color: var(--color-text-muted);
}

.head-chip .v {
  font-size: 12px;
  color: var(--color-text-regular);
  font-weight: 600;
}

.progress-mini {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-mini .bar {
  width: 110px;
  height: 8px;
  border-radius: 4px;
  background: #eef1f5;
  overflow: hidden;
}

.progress-mini .bar i {
  display: block;
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
}

.progress-mini .num {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-primary);
}

.muted {
  color: var(--color-text-muted);
}
</style>
