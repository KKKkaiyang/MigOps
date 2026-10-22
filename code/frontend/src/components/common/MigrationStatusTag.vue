<template>
  <!-- 数据迁移状态标签（元数据/全量/增量三线共用 §6.4.2 语义配色） -->
  <span class="mig-tag" :class="`mig-tag--${variant}`">{{ status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const VARIANT_MAP: Record<string, string> = {
  未迁移: 'pending',
  未开始: 'pending',
  迁移中: 'running',
  进行中: 'running',
  已完成: 'done',
  已停止: 'stopped',
  异常: 'error',
}

const variant = computed(() => VARIANT_MAP[props.status] ?? 'unknown')
</script>

<style scoped>
.mig-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

/* 未迁移 / 未开始 = 中性灰 */
.mig-tag--pending {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #c7d2e0;
}

/* 迁移中 / 进行中 = 蓝 */
.mig-tag--running {
  background: #e8f0fe;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

/* 已完成 = 成功绿 */
.mig-tag--done {
  background: #e6f4ea;
  color: #188038;
  border: 1px solid #188038;
}

/* 已停止 = 琥珀 */
.mig-tag--stopped {
  background: #fef7e0;
  color: #b06a00;
  border: 1px solid #f2a100;
}

/* 异常 = 危险红 */
.mig-tag--error {
  background: #fdecea;
  color: #c62828;
  border: 1px solid #e53935;
}

/* 未知 = 灰 */
.mig-tag--unknown {
  background: #f1f5f9;
  color: #bdc3c7;
  border: 1px solid #bdc3c7;
}
</style>
