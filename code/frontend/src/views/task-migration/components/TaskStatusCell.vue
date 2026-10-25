<template>
  <!-- 5 维状态单元格：标签 + 同维度可选目标值下拉（D1：各维度独立，互不约束） -->
  <el-dropdown trigger="click" @command="(c: string) => emit('change', c)">
    <span class="status-drop">
      <StatusTag :value="value" />
      <el-icon v-if="options.length"><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item v-for="s in options" :key="s" :command="s">
          流转为「{{ s }}」
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { STATUS_DIMENSION_MAP } from '@/utils/task-status'
import type { StatusDimensionKey } from '@/types'

const props = defineProps<{ dimension: StatusDimensionKey; value?: string | null }>()
const emit = defineEmits<{ (e: 'change', value: string): void }>()

const options = computed(() => STATUS_DIMENSION_MAP[props.dimension]?.options ?? [])
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
