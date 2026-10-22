<template>
  <!-- 资料类型标签：外部链接=蓝 / markdown=紫 / 平台台账=青（§6.4.2 语义配色） -->
  <span class="type-tag" :class="`type-tag--${variant}`">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MaterialType } from '@/types'

const props = defineProps<{ type: string }>()

const MAP: Record<string, { label: string; variant: string }> = {
  external_link: { label: '外部链接', variant: 'link' },
  markdown: { label: 'markdown', variant: 'markdown' },
  platform_ledger: { label: '平台台账', variant: 'ledger' },
}

const current = computed(
  () => MAP[props.type as MaterialType] ?? { label: props.type || '未知', variant: 'unknown' }
)
const label = computed(() => current.value.label)
const variant = computed(() => current.value.variant)
</script>

<style scoped>
.type-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

/* 外部链接 = 蓝 */
.type-tag--link {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

/* markdown = 紫 */
.type-tag--markdown {
  background: #f0e8ff;
  color: #6a3fb5;
  border: 1px solid #6a3fb5;
}

/* 平台台账 = 青 */
.type-tag--ledger {
  background: #e0f2fe;
  color: #075985;
  border: 1px solid #075985;
}

/* 未知 = 灰 */
.type-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
