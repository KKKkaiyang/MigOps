<template>
  <!-- 标签多选控件：从空间标签库选择，支持新建标签 -->
  <el-select
    :model-value="modelValue"
    multiple
    filterable
    :placeholder="placeholder"
    :loading="tagStore.loading"
    collapse-tags
    collapse-tags-tooltip
    style="width: 100%"
    @update:model-value="(v: number[]) => emit('update:modelValue', v)"
  >
    <el-option
      v-for="t in tags"
      :key="t.id"
      :label="t.tag_name"
      :value="t.id"
    >
      <span class="opt">
        <span class="dot" :style="{ backgroundColor: t.color }" />
        {{ t.tag_name }}
      </span>
    </el-option>
  </el-select>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTagStore } from '@/store/tags'
import type { TagOut } from '@/types'

const props = defineProps<{
  modelValue: number[]
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: number[]): void
}>()

const route = useRoute()
const spaceId = Number(route.params.spaceId)
const tagStore = useTagStore()

// 标签库由共享 store 统一维护（标签增删改后实时刷新，避免缓存陈旧）
const tags = computed<TagOut[]>(() => tagStore.tags)

onMounted(() => {
  tagStore.ensure(spaceId)
})
</script>

<style scoped>
.opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
</style>
