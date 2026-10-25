<template>
  <!-- 导入基础数据（原名「导入任务台账」，需求优化：功能不变仅改名） -->
  <el-dialog
    v-model="visible"
    title="导入基础数据"
    width="560px"
    :close-on-click-modal="false"
  >
    <div v-if="!result">
      <el-form label-width="84px">
        <el-form-item label="导入模式">
          <el-radio-group v-model="mode">
            <el-radio value="overwrite">覆盖导入</el-radio>
            <el-radio value="incremental">增量导入</el-radio>
          </el-radio-group>
          <div class="mode-tip">
            覆盖导入：按任务URI更新已存在行的导入字段；增量导入：仅插入新任务，已存在行跳过。<br />
            仅「项目名称、任务名称」为必填，其他字段可留空（留空将清空原值）。
          </div>
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false" show-icon class="import-tip">
        <template #title>
          <span>支持 .xlsx / .csv；任务URI（项目名称://任务名称@工作流名称）由系统自动生成。</span>
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
          <div class="upload-sub">仅支持 .xlsx / .csv，单次最多 50000 行</div>
        </div>
      </el-upload>
      <div class="template-row">
        <span>不知道格式？</span>
        <el-button link type="primary" @click="downloadTemplate(spaceId)">下载导入模板</el-button>
      </div>
    </div>

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
import { importTasks, downloadTemplate as downloadTemplateFile } from '@/api/task-migration'
import type { ImportResult } from '@/types'

const props = defineProps<{ modelValue: boolean; scenarioId: number }>()
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
const mode = ref<'overwrite' | 'incremental'>('overwrite')
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
  mode.value = 'overwrite'
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

async function downloadTemplate(spaceId: number) {
  await downloadTemplateFile(spaceId)
}

async function submit() {
  if (!file.value) {
    ElMessage.warning('请先选择导入文件')
    return
  }
  submitting.value = true
  try {
    result.value = await importTasks(spaceId.value, props.scenarioId, file.value, mode.value)
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.mode-tip {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: 2px;
}

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
