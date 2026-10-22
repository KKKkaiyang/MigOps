<template>
  <!-- 数据校验状态标签（b04） -->
  <span class="check-tag" :class="`check-tag--${variant}`">{{ status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const VARIANT_MAP: Record<string, string> = {
  未校验: 'pending',
  校验中: 'running',
  校验通过: 'passed',
  校验不通过: 'failed',
}

const variant = computed(() => VARIANT_MAP[props.status] ?? 'unknown')
</script>

<style scoped>
.check-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

.check-tag--pending {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #c7d2e0;
}

.check-tag--running {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

.check-tag--passed {
  background: #e6f4ea;
  color: #188038;
  border: 1px solid #188038;
}

.check-tag--failed {
  background: #fdecea;
  color: #c62828;
  border: 1px solid #e53935;
}

.check-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
