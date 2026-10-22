<template>
  <!-- 调度状态标签（b04） -->
  <span class="sched-tag" :class="`sched-tag--${variant}`">{{ status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const VARIANT_MAP: Record<string, string> = {
  未提交: 'pending',
  已提交: 'running',
  调度中: 'running',
  调度成功: 'success',
  调度失败: 'failed',
}

const variant = computed(() => VARIANT_MAP[props.status] ?? 'unknown')
</script>

<style scoped>
.sched-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

.sched-tag--pending {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #c7d2e0;
}

.sched-tag--running {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

.sched-tag--success {
  background: #e6f4ea;
  color: #188038;
  border: 1px solid #188038;
}

.sched-tag--failed {
  background: #fdecea;
  color: #c62828;
  border: 1px solid #e53935;
}

.sched-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
