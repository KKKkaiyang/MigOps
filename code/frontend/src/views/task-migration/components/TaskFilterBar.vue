<template>
  <!-- 任务台账筛选行（标签筛选待二期标签管理上线后扩展，确认决策 D6） -->
  <div class="filter-row">
    <el-input
      :model-value="filters.keyword"
      placeholder="搜索 任务名称..."
      clearable
      style="width: 180px"
      @update:model-value="(v: string) => emit('update', { key: 'keyword', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-input
      :model-value="filters.workflow_name"
      placeholder="工作流"
      clearable
      style="width: 130px"
      @update:model-value="(v: string) => emit('update', { key: 'workflow_name', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-select
      :model-value="filters.migration_status"
      placeholder="迁移状态"
      clearable
      style="width: 140px"
      @update:model-value="(v: string) => emit('update', { key: 'migration_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in TASK_MIGRATION_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-select
      :model-value="filters.schedule_status"
      placeholder="调度状态"
      clearable
      style="width: 120px"
      @update:model-value="(v: string) => emit('update', { key: 'schedule_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in SCHEDULE_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-select
      :model-value="filters.check_status"
      placeholder="校验状态"
      clearable
      style="width: 120px"
      @update:model-value="(v: string) => emit('update', { key: 'check_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in CHECK_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-input
      :model-value="filters.owner"
      placeholder="Owner"
      clearable
      style="width: 110px"
      @update:model-value="(v: string) => emit('update', { key: 'owner', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-button @click="emit('reset')">重置</el-button>
  </div>
</template>

<script setup lang="ts">
import { CHECK_STATUS_OPTIONS, SCHEDULE_STATUS_OPTIONS, TASK_MIGRATION_STATUS_OPTIONS } from '@/types'

defineProps<{ filters: Record<string, string> }>()

const emit = defineEmits<{
  (e: 'update', payload: { key: string; value: string }): void
  (e: 'search'): void
  (e: 'reset'): void
}>()
</script>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
