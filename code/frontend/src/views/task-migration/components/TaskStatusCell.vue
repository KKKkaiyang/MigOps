<template>
  <!-- 迁移状态单元格：标签 + 按状态机可选的目标状态下拉（BRD 4.2） -->
  <el-dropdown trigger="click" @command="(c: string) => emit('change', c)">
    <span class="status-drop">
      <TaskStatusTag :status="status" />
      <el-icon v-if="nextStatuses.length"><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item v-for="s in nextStatuses" :key="s" :command="s">
          流转为「{{ s }}」
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import TaskStatusTag from '@/components/common/TaskStatusTag.vue'
import { TASK_STATUS_TRANSITIONS } from '@/types'

const props = defineProps<{ status: string }>()

const emit = defineEmits<{ (e: 'change', status: string): void }>()

const nextStatuses = computed(() => TASK_STATUS_TRANSITIONS[props.status] ?? [])
</script>

<style scoped>
.status-drop {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.status-drop .el-icon {
  color: var(--color-text-muted);
}
</style>
