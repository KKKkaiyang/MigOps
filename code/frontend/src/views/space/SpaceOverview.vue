<template>
  <!-- 空间概览：空间信息 + 模块导航入口（确认决策 D15：不含量化统计） -->
  <div class="space-overview" v-loading="loading">
    <template v-if="space">
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-head">
            <span class="card-title">空间信息</span>
            <el-button link type="primary" @click="$router.push('/b01/spaces')">
              前往空间管理
            </el-button>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目名称">{{ space.space_name }}</el-descriptions-item>
          <el-descriptions-item label="项目简称">
            <span class="mono">{{ space.space_code }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="客户名称">
            {{ space.customer_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="空间状态">
            <SpaceStatusTag :status="space.status" />
          </el-descriptions-item>
          <el-descriptions-item label="源端平台">
            {{ space.source_platform || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="目标端平台">
            {{ space.target_platform || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="负责人">{{ space.owner || '—' }}</el-descriptions-item>
          <el-descriptions-item label="整体进展">
            {{ space.overall_progress }}%
          </el-descriptions-item>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Document, DataLine, Notebook } from '@element-plus/icons-vue'
import { getSpace } from '@/api/space'
import SpaceStatusTag from '@/components/common/SpaceStatusTag.vue'
import { formatDate } from '@/utils/format'
import type { SpaceOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const space = ref<SpaceOut | null>(null)
const loading = ref(true)

const modules = [
  {
    route: 'space-materials',
    name: '项目资料索引',
    desc: '集中维护外部链接、Markdown 资料与平台内台账入口',
    icon: Document,
    bg: '#e8f0fe',
    color: '#1a73e8',
  },
  {
    route: 'space-data-migrations',
    name: '数据迁移管理',
    desc: '按场景管理库表清单的元数据 / 全量 / 增量迁移状态',
    icon: DataLine,
    bg: '#e6f4ea',
    color: '#188038',
  },
  {
    route: 'space-tasks',
    name: '任务迁移管理',
    desc: '任务全生命周期状态、排查备注时间线与自定义台账',
    icon: Notebook,
    bg: '#f0e8ff',
    color: '#6a3fb5',
  },
]

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
.space-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
</style>
