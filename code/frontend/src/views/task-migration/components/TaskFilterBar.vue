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
    <el-select
      :model-value="filters.tag_match"
      placeholder="标签匹配"
      style="width: 110px"
      @update:model-value="(v: string) => emit('update', { key: 'tag_match', value: v })"
      @change="emit('search')"
    >
      <el-option label="含全部标签" value="all" />
      <el-option label="含任一标签" value="any" />
    </el-select>
    <el-select
      :model-value="filters.tag_ids"
      multiple
      collapse-tags
      collapse-tags-tooltip
      placeholder="按标签筛选"
      style="width: 200px"
      @update:model-value="(v: number[]) => emit('update', { key: 'tag_ids', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in tags" :key="t.id" :label="t.tag_name" :value="t.id" />
    </el-select>
    <el-button @click="emit('reset')">重置</el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CHECK_STATUS_OPTIONS, SCHEDULE_STATUS_OPTIONS, TASK_MIGRATION_STATUS_OPTIONS } from '@/types'

interface TagOption {
  id: number
  tag_name: string
  tag_category?: string
}

const props = defineProps<{
  filters: Record<string, any>
  tags?: TagOption[]
}>()
const emit = defineEmits<{
  (e: 'update', payload: { key: string; value: string | number[] }): void
  (e: 'search'): void
  (e: 'reset'): void
}>()

const tags = computed(() => props.tags ?? [])
</script>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
