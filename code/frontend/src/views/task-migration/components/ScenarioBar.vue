<template>
  <!-- 场景选择栏 + 自定义台账入口（需求 §6.2.1 / §6.4） -->
  <div class="scenario-row">
    <span class="scenario-label">迁移场景</span>
    <el-select
      :model-value="scenarioId"
      placeholder="选择或创建迁移场景"
      style="width: 280px"
      @update:model-value="(v: number) => emit('change', v)"
    >
      <el-option
        v-for="s in scenarios"
        :key="s.id"
        :label="`${s.name}（${s.task_count} 个任务）`"
        :value="s.id"
      />
    </el-select>
    <el-button @click="emit('create')">+ 创建新场景</el-button>
    <el-button v-if="scenarioId" link type="danger" @click="emit('delete')">删除当前场景</el-button>
    <span v-if="savedViews.length" class="saved-views">
      自定义台账：
      <router-link
        v-for="v in savedViews"
        :key="v.id"
        :to="{ name: 'space-saved-view', params: { spaceId, viewId: v.id } }"
        class="view-link"
      >
        {{ v.name }}（{{ v.task_count }}）
      </router-link>
    </span>
  </div>
</template>

<script setup lang="ts">
import type { SavedViewOut, TaskScenarioOut } from '@/types'

defineProps<{
  scenarios: TaskScenarioOut[]
  scenarioId: number | null
  savedViews: SavedViewOut[]
  spaceId: number
}>()

const emit = defineEmits<{
  (e: 'change', scenarioId: number): void
  (e: 'create'): void
  (e: 'delete'): void
}>()
</script>

<style scoped>
.scenario-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.scenario-label {
  font-size: 13px;
  color: var(--color-text-regular);
}

.saved-views {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.view-link {
  color: var(--color-primary);
  text-decoration: none;
}

.view-link:hover {
  text-decoration: underline;
}
</style>
