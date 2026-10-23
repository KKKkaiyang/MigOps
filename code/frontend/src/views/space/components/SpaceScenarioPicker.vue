<template>
  <!-- 空间头场景切换器（交互评审 I2）：仅 b03/b04 页面激活，状态空间级跨导航保持 -->
  <div class="scenario-picker" :class="{ disabled: !module }">
    <span class="sp-label">当前场景</span>
    <el-select
      :model-value="scenarioId"
      :placeholder="module ? '选择迁移场景' : '未选择'"
      :disabled="!module"
      style="width: 220px"
      @update:model-value="(v: number) => emit('change', v)"
    >
      <el-option v-for="s in scenarios" :key="s.id" :label="s.label" :value="s.id" />
    </el-select>
    <el-dropdown v-if="module && scenarioId !== null" trigger="click" @command="onCommand">
      <el-button size="small" :icon="Setting">管理</el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="create">新建场景</el-dropdown-item>
          <el-dropdown-item command="delete" divided>删除当前场景</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <el-button v-else-if="module" size="small" :icon="Plus" @click="emit('create')" />
  </div>
</template>

<script setup lang="ts">
import { Plus, Setting } from '@element-plus/icons-vue'

defineProps<{
  /** 当前路由所属模块：b03 / b04 时激活，其余置灰 */
  module: 'b03' | 'b04' | null
  scenarios: { id: number; label: string }[]
  scenarioId: number | null
}>()

const emit = defineEmits<{
  (e: 'change', scenarioId: number): void
  (e: 'create'): void
  (e: 'delete'): void
}>()

function onCommand(cmd: 'create' | 'delete') {
  if (cmd === 'create') emit('create')
  else emit('delete')
}
</script>

<style scoped>
.scenario-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 8px;
  padding: 4px 10px 4px 12px;
}
.scenario-picker.disabled {
  background: #f5f7fa;
  border-color: var(--color-border);
}
.sp-label {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
}
</style>
