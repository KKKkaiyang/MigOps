<template>
  <!-- 数据迁移场景选择栏（需求 §5.2.1） -->
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
        :label="`${s.name}（${s.table_count} 张表）`"
        :value="s.id"
      />
    </el-select>
    <el-button @click="emit('create')">+ 创建新场景</el-button>
    <el-button v-if="scenarioId" link type="danger" @click="emit('delete')">删除当前场景</el-button>
  </div>
</template>

<script setup lang="ts">
import type { DataMigrationScenarioOut } from '@/types'

defineProps<{
  scenarios: DataMigrationScenarioOut[]
  scenarioId: number | null
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
</style>
