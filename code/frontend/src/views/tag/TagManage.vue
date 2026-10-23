<template>
  <!-- 标签管理独立模块（b06）：标签列表维护与查看 -->
  <div class="tag-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">标签管理</span>
          <span class="page-sub">空间级标签维护与查看（b06 标签管理模块）</span>
        </div>
      </template>
      <TagManagePanel :space-id="spaceId" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import TagManagePanel from '@/views/task-migration/components/TagManagePanel.vue'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.page-sub {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
