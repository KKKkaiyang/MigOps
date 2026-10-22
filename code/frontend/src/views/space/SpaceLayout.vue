<template>
  <!-- 项目空间视图框架：空间头部信息 + 模块导航 + 子页面（需求 §2.1） -->
  <div class="space-view">
    <el-card class="space-header" shadow="never" v-loading="loading">
      <template #header>
        <div class="space-head">
          <div class="space-title-row">
            <span class="space-title">{{ space?.space_name }}</span>
            <SpaceStatusTag v-if="space" :status="space.status" />
            <span class="space-code mono">{{ space?.space_code }}</span>
          </div>
          <div class="space-sub">
            <span v-if="routeLine">{{ routeLine }}</span>
            <span v-else>源/目标端平台未维护</span>
            <span class="dot">·</span>
            <span>我的角色：{{ roleLabel }}</span>
            <span class="dot">·</span>
            <span>成员 {{ space?.member_count ?? 0 }} 人</span>
          </div>
        </div>
      </template>
      <div class="progress-row" v-if="space">
        <span class="progress-label">整体进展</span>
        <el-progress
          :percentage="space.overall_progress"
          :stroke-width="10"
          :show-text="false"
          class="progress-bar"
        />
        <span class="progress-num">{{ space.overall_progress }}%</span>
      </div>
      <p v-if="space?.remark" class="space-remark">{{ space.remark }}</p>
    </el-card>

    <nav class="space-nav">
      <router-link :to="{ name: 'space-overview', params: { spaceId } }">空间概览</router-link>
      <router-link :to="{ name: 'space-materials', params: { spaceId } }">项目资料索引</router-link>
      <router-link :to="{ name: 'space-data-migrations', params: { spaceId } }">数据迁移</router-link>
      <router-link :to="{ name: 'space-tasks', params: { spaceId } }">任务迁移</router-link>
    </nav>

    <router-view v-if="!loading" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getSpace } from '@/api/space'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import { ROLE_LEVEL_MAP } from '@/types'
import type { SpaceOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const space = ref<SpaceOut | null>(null)
const loading = ref(true)

const routeLine = computed(() => {
  const s = space.value
  if (!s?.source_platform && !s?.target_platform) return ''
  return `${s.source_platform || '未知源端'} → ${s.target_platform || '未知目标端'}`
})

const roleLabel = computed(() => {
  const role = space.value?.my_role
  return role ? ROLE_LEVEL_MAP[role as keyof typeof ROLE_LEVEL_MAP] || role : '—'
})

onMounted(async () => {
  loading.value = true
  try {
    space.value = await getSpace(spaceId.value)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.space-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.space-header {
  border-color: var(--color-border);
}

.space-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.space-title-row {
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

.space-sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-regular);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dot {
  color: var(--color-border-strong);
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.progress-label {
  font-size: 12px;
  color: var(--color-text-regular);
  white-space: nowrap;
}

.progress-bar {
  flex: 1;
}

.progress-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  min-width: 40px;
  text-align: right;
}

.space-remark {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.space-nav {
  display: flex;
  gap: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 4px;
}

.space-nav a {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-regular);
  text-decoration: none;
  transition: all 0.15s;
}

.space-nav a:hover {
  color: var(--color-primary);
  background: var(--color-primary-light, #eef4ff);
}

.space-nav a.router-link-active {
  background: var(--color-primary);
  color: #fff;
  font-weight: 600;
}
</style>
