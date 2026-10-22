<template>
  <!-- 任务迁移状态标签（BRD 4.2 状态机 §6.4.2 语义配色） -->
  <span class="task-tag" :class="`task-tag--${variant}`">{{ status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const VARIANT_MAP: Record<string, string> = {
  未开始: 'pending',
  改造完成: 'running',
  调度成功: 'running',
  数据校验通过: 'passed',
  数据校验不通过: 'failed',
  客户验收通过: 'accepted',
  客户验收不通过: 'failed',
  挂起: 'suspended',
  废弃: 'discarded',
}

const variant = computed(() => VARIANT_MAP[props.status] ?? 'unknown')
</script>

<style scoped>
.task-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

/* 未开始 = 中性灰 */
.task-tag--pending {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #c7d2e0;
}

/* 改造完成 / 调度成功 = 蓝（进行中） */
.task-tag--running {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

/* 数据校验通过 = 绿 */
.task-tag--passed {
  background: #e6f4ea;
  color: #188038;
  border: 1px solid #188038;
}

/* 数据校验不通过 / 客户验收不通过 = 红 */
.task-tag--failed {
  background: #fdecea;
  color: #c62828;
  border: 1px solid #e53935;
}

/* 客户验收通过 = 深绿 */
.task-tag--accepted {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #10b981;
}

/* 挂起 = 琥珀 */
.task-tag--suspended {
  background: #fef7e0;
  color: #b06a00;
  border: 1px solid #f2a100;
}

/* 废弃 = 灰（终态） */
.task-tag--discarded {
  background: #f1f5f9;
  color: #94a3b8;
  border: 1px solid #c7d2e0;
}

/* 未知 = 灰 */
.task-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
