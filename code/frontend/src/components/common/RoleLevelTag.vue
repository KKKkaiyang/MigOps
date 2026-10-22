<template>
  <!-- 角色等级标签：颜色编码 + 文字标签双标识（§6.4.2） -->
  <span class="role-tag" :class="`role-tag--${variant}`">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ROLE_LEVEL_MAP } from '@/types'

const props = defineProps<{ level: 'L0' | 'L1' | 'L2' | string }>()

const MAP: Record<string, string> = {
  L0: 'l0',
  L1: 'l1',
  L2: 'l2',
}

const label = computed(() => ROLE_LEVEL_MAP[props.level as 'L0'] || props.level || '未知')
const variant = computed(() => MAP[props.level] ?? 'unknown')
</script>

<style scoped>
.role-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

/* L0 系统管理员 = 主色蓝 */
.role-tag--l0 {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

/* L1 项目管理员 = 项目紫 */
.role-tag--l1 {
  background: #f0e8ff;
  color: #6a3fb5;
  border: 1px solid #6a3fb5;
}

/* L2 项目成员 = 任务类型青 */
.role-tag--l2 {
  background: #e0f2fe;
  color: #075985;
  border: 1px solid #075985;
}

.role-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
