<template>
  <!-- markdown 查看：渲染预览（非富文本）+ 下载（确认决策 D4/D9） -->
  <el-dialog
    v-model="visible"
    :title="material ? `查看资料：${material.name}` : '查看资料'"
    width="760px"
    :close-on-click-modal="false"
    class="material-view-dialog"
  >
    <div v-loading="loading" class="preview-wrap">
      <MdPreview
        v-if="material?.content != null"
        :id="`preview-${material.id}`"
        :model-value="material.content"
        :sanitize="sanitize"
        class="md-preview"
      />
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="downloading" @click="download">下载 .md</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DOMPurify from 'dompurify'
// md-editor-v3（PrismJS + CodeMirror，体积大）按需异步加载，避免拖累主包（样式已在 main.ts 全局引入）
const MdPreview = defineAsyncComponent(() => import('md-editor-v3').then((m) => m.MdPreview))
import { downloadFile } from '@/utils/download'
import { getViewToken } from '@/utils/view-token'
import type { MaterialOut } from '@/types'

const props = defineProps<{ modelValue: boolean; material?: MaterialOut | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const downloading = ref(false)

/** 预览 HTML 经 DOMPurify 净化后再注入（需求 §7 防 XSS） */
const sanitize = (html: string) => DOMPurify.sanitize(html)

async function download() {
  const m = props.material
  if (!m) return
  downloading.value = true
  try {
    await downloadFile(
      `/b02/materials/${m.id}/download`,
      { space_id: spaceId.value, view_token: getViewToken(m.id) },
      `${m.name}.md`
    )
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.preview-wrap {
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}

.md-preview {
  border-radius: 6px;
}
</style>
