<template>
  <!-- 空间级标签管理（任务迁移内嵌入口；独立模块页面见 /space/:spaceId/tags） -->
  <el-dialog
    v-model="visible"
    title="标签管理"
    width="680px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <TagManagePanel :space-id="spaceId" @updated="onUpdated" />
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import TagManagePanel from './TagManagePanel.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'updated'): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function onUpdated() {
  emit('updated')
}
</script>
