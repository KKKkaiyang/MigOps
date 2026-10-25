<template>
  <!-- 5 维状态统一标签：根据取值语义着色（§6.4.2 语义配色） -->
  <span class="status-pill" :style="style">{{ display }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { statusTagType } from '@/utils/task-status'

const props = defineProps<{ value?: string | null; status?: string | null }>()

const text = computed(() => props.value ?? props.status ?? '')
const type = computed(() => statusTagType(text.value))
const display = computed(() => text.value || '—')

const STYLES: Record<string, { background: string; color: string; border: string }> = {
  success: { background: '#e6f4ea', color: '#188038', border: '#188038' },
  warning: { background: '#fef7e0', color: '#b06a00', border: '#f2a100' },
  danger: { background: '#fdecea', color: '#c62828', border: '#e53935' },
  info: { background: '#f1f5f9', color: '#475569', border: '#c7d2e0' },
}

const style = computed(() => STYLES[type.value])
</script>

<style scoped>
.status-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.5;
  border: 1px solid transparent;
}
</style>
