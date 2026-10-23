<template>
  <!-- 空间状态标签：颜色编码 + 文字标签双标识（§6.4.2） -->
  <span class="status-tag" :class="`status-tag--${variant}`">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const MAP: Record<string, { label: string; variant: string }> = {
  初始化: { label: '初始化', variant: 'init' },
  交付中: { label: '交付中', variant: 'delivering' },
  已验收: { label: '已验收', variant: 'accepted' },
  已删除: { label: '已删除', variant: 'deleted' },
}

const current = computed(() => MAP[props.status] ?? { label: props.status || '未知', variant: 'unknown' })
const label = computed(() => current.value.label)
const variant = computed(() => current.value.variant)
</script>

<style scoped>
.status-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

/* 初始化 = 中性灰 */
.status-tag--init {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #c7d2e0;
}

/* 交付中 = 主色蓝 */
.status-tag--delivering {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

/* 已验收 = 成功绿 */
.status-tag--accepted {
  background: #e6f4ea;
  color: #188038;
  border: 1px solid #188038;
}

/* 未知 = 灰 */
.status-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}

/* 已删除 = 危险灰红 */
.status-tag--deleted {
  background: #fdecea;
  color: #c62828;
  border: 1px solid #e53935;
}
</style>
