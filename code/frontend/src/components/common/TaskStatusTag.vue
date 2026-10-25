<template>
  <!-- 任务迁移状态标签（统一语义着色，兼容旧引用） -->
  <StatusTag :value="status" />
</template>

<script setup lang="ts">
import StatusTag from './StatusTag.vue'

defineProps<{ status?: string | null }>()
</script>
