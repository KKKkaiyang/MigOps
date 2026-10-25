<template>
  <!-- 数据校验结果标签：通过=绿 / 不通过=红 / 无校验结果=灰（对齐 CODEBUDDY.md §6.4.2 校验语义色） -->
  <el-tag
    v-if="value === '通过'"
    color="#27ae60"
    size="small"
    style="color: #fff; border: none; border-radius: 10px"
    >通过</el-tag
  >
  <el-tag
    v-else-if="value === '不通过'"
    color="#e74c3c"
    size="small"
    style="color: #fff; border: none; border-radius: 10px"
    >不通过</el-tag
  >
  <span v-else class="cr-none">—</span>
</template>

<script setup lang="ts">
defineProps<{ value?: string | null }>()
</script>

<style scoped>
.cr-none {
  color: var(--color-text-muted);
}
</style>
