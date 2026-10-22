<template>
  <!-- 我的项目空间 Panel 区（需求 §3：概览页主体最上方） -->
  <section class="spaces-section">
    <div class="spaces-toolbar">
      <div class="spaces-title">
        我的项目空间
        <span class="spaces-count">共 {{ total }} 个</span>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="keyword"
          placeholder="搜索项目名称/简称..."
          clearable
          style="width: 220px"
          @keyup.enter="onSearch"
          @clear="onSearch"
        />
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 130px" @change="onSearch">
          <el-option label="初始化" value="初始化" />
          <el-option label="交付中" value="交付中" />
          <el-option label="已验收" value="已验收" />
        </el-select>
        <el-button v-if="canCreate" type="primary" @click="formVisible = true">+ 创建迁移空间</el-button>
      </div>
    </div>

    <div v-loading="loading" class="panel-grid">
      <div v-for="s in list" :key="s.id" class="space-panel">
        <div class="panel-head">
          <span class="panel-title" :title="s.space_name">{{ s.space_name }}</span>
          <SpaceStatusTag :status="s.status" />
        </div>
        <div class="panel-sub">
          <span class="mono">{{ s.space_code }}</span>
          <span class="dot">·</span>
          <span>{{ routeLine(s) }}</span>
        </div>
        <p v-if="s.remark" class="panel-remark" :title="s.remark">{{ s.remark }}</p>
        <p v-else class="panel-remark panel-remark--empty">暂无项目空间说明</p>
        <div class="panel-progress">
          <span class="progress-label">整体进展</span>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${s.overall_progress}%` }" />
          </div>
          <span class="progress-num">{{ s.overall_progress }}%</span>
        </div>
        <div class="panel-meta">
          <RoleLevelTag :level="s.my_role || ''" />
          <span class="meta-item">成员 {{ s.member_count }} 人</span>
          <span class="meta-item">最近更新：{{ formatDate(s.updated_at) }}</span>
        </div>
        <div class="panel-foot">
          <el-button type="primary" size="small" @click="enterSpace(s.id)">进入空间</el-button>
        </div>
      </div>

      <div v-if="!loading && list.length === 0" class="panel-empty">
        <el-empty :description="emptyText">
          <el-button v-if="canCreate" type="primary" @click="formVisible = true">创建迁移空间</el-button>
        </el-empty>
      </div>
    </div>

    <SpaceFormDialog v-model="formVisible" @success="load" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import RoleLevelTag from '@/components/common/RoleLevelTag.vue'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import SpaceFormDialog from '@/views/space/components/SpaceFormDialog.vue'
import { listSpaces } from '@/api/space'
import { useUserStore } from '@/store/user'
import { formatDate } from '@/utils/format'
import type { SpaceOut } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const list = ref<SpaceOut[]>([])
const total = ref(0)
const keyword = ref('')
const status = ref('')
const loading = ref(true)
const formVisible = ref(false)

/** 创建空间权限：L0 全局，或在任一空间担任 L1（与公共业务需求 §5.3 一致） */
const canCreate = computed(
  () => userStore.isL0 || (userStore.user?.roles ?? []).some((r) => r.role_level === 'L1')
)

const emptyText = computed(() =>
  canCreate.value
    ? '暂无项目空间，点击下方按钮创建第一个空间'
    : '暂无加入的空间，请联系项目管理员将您加入'
)

function routeLine(s: SpaceOut): string {
  if (!s.source_platform && !s.target_platform) return '源/目标平台未维护'
  return `${s.source_platform || '未知源端'} → ${s.target_platform || '未知目标端'}`
}

async function load() {
  loading.value = true
  try {
    const data = await listSpaces(1, 100, keyword.value || undefined, status.value || undefined)
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  load()
}

function enterSpace(id: number) {
  router.push({ name: 'space-overview', params: { spaceId: id } })
}

onMounted(load)
</script>

<style scoped>
.spaces-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px 18px;
}

.spaces-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.spaces-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.spaces-count {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
  min-height: 80px;
}

.space-panel {
  position: relative;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px 16px 12px;
  background: var(--color-surface);
  transition: box-shadow 0.15s, border-color 0.15s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.space-panel:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-medium);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-sub {
  font-size: 12px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dot {
  color: var(--color-border-strong);
}

.panel-remark {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 38px;
}

.panel-remark--empty {
  color: var(--color-text-muted);
}

.panel-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-label {
  font-size: 12px;
  color: var(--color-text-regular);
  white-space: nowrap;
}

.progress-track {
  flex: 1;
  height: 6px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.2s;
}

.progress-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  min-width: 36px;
  text-align: right;
}

.panel-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--color-text-muted);
}

.meta-item {
  white-space: nowrap;
}

.panel-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 2px;
}

.panel-empty {
  grid-column: 1 / -1;
  padding: 24px 0;
}
</style>
