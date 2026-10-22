<template>
  <!-- 导入对话框：库表清单 / 迁移记录（需求 §5.2.2 / §5.2.6） -->
  <el-dialog
    v-model="visible"
    :title="kind === 'items' ? '导入库表清单' : '导入迁移记录'"
    width="560px"
    :close-on-click-modal="false"
  >
    <div v-if="!result">
      <el-alert type="info" :closable="false" show-icon class="import-tip">
        <template #title>
          <span v-if="kind === 'items'">
            支持 .xlsx / .csv；按「库名.表名」upsert（已存在则更新基础信息）。
          </span>
          <span v-else>
            支持 .xlsx / .csv；按「库名.表名」匹配当前场景下的库表后追加记录。
          </span>
        </template>
      </el-alert>
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.csv"
        :on-change="onFileChange"
        :on-exceed="onExceed"
        :file-list="fileList"
      >
        <div class="upload-inner">
          <el-icon :size="32" color="#8a96a3"><UploadFilled /></el-icon>
          <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
          <div class="upload-sub">仅支持 .xlsx / .csv，单次最多 5000 行</div>
        </div>
      </el-upload>
      <div class="template-row">
        <span>不知道格式？</span>
        <el-button link type="primary" @click="downloadTemplate">下载导入模板</el-button>
      </div>
    </div>

    <!-- 导入结果 -->
    <div v-else class="import-result">
      <el-result icon="success" title="导入完成">
        <template #sub-title>
          新增 {{ result.inserted }} 条 · 更新 {{ result.updated }} 条 · 跳过 {{ result.skipped }} 条
          <span v-if="result.errors.length"> · 失败 {{ result.errors.length }} 条</span>
        </template>
      </el-result>
      <el-table
        v-if="result.errors.length"
        :data="result.errors"
        border
        size="small"
        max-height="220"
        class="error-table"
      >
        <el-table-column prop="row" label="行号" width="70" align="center" />
        <el-table-column prop="message" label="错误原因" min-width="200" show-overflow-tooltip />
      </el-table>
    </div>

    <template #footer>
      <el-button @click="visible = false">{{ result ? '关闭' : '取消' }}</el-button>
      <el-button v-if="!result" type="primary" :loading="submitting" :disabled="!file" @click="submit">
        开始导入
      </el-button>
      <el-button v-else type="primary" @click="resetAll">继续导入</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadFiles, UploadInstance } from 'element-plus'
import { importRecords, importTableItems } from '@/api/data-migration'
import { downloadFile } from '@/utils/download'
import type { ImportResult } from '@/types'

const props = defineProps<{
  modelValue: boolean
  kind: 'items' | 'records'
  scenarioId: number
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const uploadRef = ref<UploadInstance>()
const file = ref<File | null>(null)
const fileList = ref<UploadFiles>([])
const submitting = ref(false)
const result = ref<ImportResult | null>(null)

watch(
  () => props.modelValue,
  (open) => {
    if (open) resetAll()
  }
)

function resetAll() {
  file.value = null
  fileList.value = []
  result.value = null
  uploadRef.value?.clearFiles()
}

function onFileChange(uploadFile: UploadFile) {
  fileList.value = [uploadFile]
  file.value = (uploadFile.raw as File) ?? null
}

function onExceed(files: File[]) {
  uploadRef.value?.clearFiles()
  const f = files[0]
  if (f) {
    fileList.value = [{ name: f.name } as UploadFile]
    file.value = f
  }
}

async function downloadTemplate() {
  const url =
    props.kind === 'items'
      ? `/b03/scenarios/${props.scenarioId}/table-items/template`
      : `/b03/scenarios/${props.scenarioId}/records/template`
  await downloadFile(
    url,
    { space_id: spaceId.value },
    props.kind === 'items' ? '库表清单导入模板.xlsx' : '迁移记录导入模板.xlsx'
  )
}

async function submit() {
  if (!file.value) {
    ElMessage.warning('请先选择导入文件')
    return
  }
  submitting.value = true
  try {
    result.value =
      props.kind === 'items'
        ? await importTableItems(spaceId.value, props.scenarioId, file.value)
        : await importRecords(spaceId.value, props.scenarioId, file.value)
    if (result.value.errors.length === 0) {
      emit('success')
    } else {
      // 有行级错误时也刷新列表（成功行已落库）
      emit('success')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.import-tip {
  margin-bottom: 14px;
}

.upload-area {
  width: 100%;
}

.upload-inner {
  padding: 18px 0;
}

.upload-text {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-regular);
}

.upload-sub {
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.template-row {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

.import-result {
  padding: 0 8px;
}

.error-table {
  margin-top: 12px;
}
</style>
