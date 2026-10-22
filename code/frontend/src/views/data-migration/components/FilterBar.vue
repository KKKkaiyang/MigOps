<template>
  <!-- 数据迁移筛选行（需求 §5.2.9） -->
  <div class="filter-row">
    <el-input
      :model-value="filters.keyword"
      placeholder="搜索 库名/表名..."
      clearable
      style="width: 200px"
      @update:model-value="(v: string) => emit('update', { key: 'keyword', value: v })"
      @keyup.enter="emit('search')"
      @clear="emit('search')"
    />
    <el-select
      :model-value="filters.table_type"
      placeholder="全部表类型"
      clearable
      style="width: 130px"
      @update:model-value="(v: string) => emit('update', { key: 'table_type', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in TABLE_TYPE_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-select
      :model-value="filters.metadata_status"
      placeholder="元数据状态"
      clearable
      style="width: 120px"
      @update:model-value="(v: string) => emit('update', { key: 'metadata_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in MIGRATION_LINE_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-select
      :model-value="filters.full_sync_status"
      placeholder="全量迁移状态"
      clearable
      style="width: 130px"
      @update:model-value="(v: string) => emit('update', { key: 'full_sync_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in MIGRATION_LINE_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-select
      :model-value="filters.incr_sync_status"
      placeholder="增量迁移状态"
      clearable
      style="width: 130px"
      @update:model-value="(v: string) => emit('update', { key: 'incr_sync_status', value: v })"
      @change="emit('search')"
    >
      <el-option v-for="t in INCR_SYNC_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
    </el-select>
    <el-button @click="emit('reset')">重置</el-button>
  </div>
</template>

<script setup lang="ts">
import { INCR_SYNC_STATUS_OPTIONS, MIGRATION_LINE_STATUS_OPTIONS, TABLE_TYPE_OPTIONS } from '@/types'

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
