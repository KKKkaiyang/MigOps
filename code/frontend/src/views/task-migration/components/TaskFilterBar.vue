<template>
  <!-- 任务视图筛选行：5 维状态 + 项目/负责人/工作流 + 标签（D1/D2） -->
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
    <el-input
      :model-value="filters.project_name"
      placeholder="项目名称"
      clearable
      style="width: 140px"
      @update:model-value="(v: string) => emit('update', { key: 'project_name', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-input
      :model-value="filters.migration_owner"
      placeholder="迁移负责人"
      clearable
      style="width: 120px"
      @update:model-value="(v: string) => emit('update', { key: 'migration_owner', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-select
      v-for="dim in STATUS_DIMENSIONS"
      :key="dim.key"
      :model-value="(filters as Record<string, any>)[dim.key]"
      :placeholder="dim.label"
      clearable
      style="width: 140px"
      @update:model-value="(v: string) => emit('update', { key: dim.key, value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in dim.options" :key="t" :label="t" :value="t" />
    </el-select>
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
import { STATUS_DIMENSIONS } from '@/utils/task-status'
import type { TagOut } from '@/types'

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

const tags = computed<TagOut[]>(() => (props.tags as TagOut[]) ?? [])
</script>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
