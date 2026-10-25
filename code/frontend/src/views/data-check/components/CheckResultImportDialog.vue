<template>
  <!-- 数据校验结果导入（需求 B05-02）：模版下拉 / 所属日期 / 文件上传 / 列说明 / 结果摘要 -->
  <el-dialog
    v-model="visible"
    title="导入校验结果"
    width="600px"
    :close-on-click-modal="false"
  >
    <div v-if="!result">
      <el-form label-width="110px">
        <el-form-item label="导入模版" required>
          <el-select v-model="template" style="width: 100%">
            <el-option
              v-for="t in CHECK_TEMPLATES"
              :key="t"
              :label="CHECK_TEMPLATE_LABELS[t]"
              :value="t"
            />
          </el-select>
          <div class="field-tip">
            默认模版：库名、表名、源端数据量、目标端数据量、结果(通过/不通过)；
            腾讯数据校验工具模版直接读取 TDM 导出 CSV 字段，无需线下转换。
          </div>
        </el-form-item>
        <el-form-item label="校验结果所属日期" required>
          <el-date-picker
            v-model="dataDate"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
            placeholder="选择日期"
            style="width: 100%"
          />
          <div class="field-tip">所选日期将批量写入本次导入的全部记录；不可晚于今天。</div>
        </el-form-item>
      </el-form>

      <el-alert type="info" :closable="false" show-icon class="cols-alert">
        <template #title>
          <div class="cols-title">{{ CHECK_TEMPLATE_LABELS[template] }}列说明</div>
          <div class="cols-body">
            <span v-for="c in CHECK_TEMPLATE_HEADERS[template]" :key="c" class="col-chip mono">{{ c }}</span>
          </div>
        </template>
      </el-alert>

      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xls,.csv,.xlsx"
        :on-change="onFileChange"
        :on-exceed="onExceed"
        :file-list="fileList"
      >
        <div class="upload-inner">
          <el-icon :size="32" color="#8a96a3"><UploadFilled /></el-icon>
          <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
          <div class="upload-sub">支持 .xls / .csv / .xlsx，单次最多 50000 行</div>
        </div>
      </el-upload>

      <div class="template-row">
        <span>不知道格式？</span>
        <el-button link type="primary" @click="downloadTemplate">下载导入模版</el-button>
      </div>
    </div>

    <div v-else class="import-result">
      <el-result icon="success" title="导入完成">
        <template #sub-title>
          新增 {{ result.inserted }} 条 · 更新 {{ result.updated }} 条 · 跳过 {{ result.skipped }} 条 ·
          已刷新 {{ result.refreshed_tasks }} 个任务的数据校验结果
          <span v-if="result.errors.length"> · 失败 {{ result.errors.length }} 条</span>
        </template>
      </el-result>
      <el-alert
        v-if="result.not_in_list > 0"
        type="warning"
        :closable="false"
        show-icon
        class="not-in-list"
      >
        其中 {{ result.not_in_list }} 条不在当前迁移场景的库表清单中（已正常入库并参与任务刷新，校验列表页不展示）
      </el-alert>
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
        确认导入
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
import { importCheckResults, downloadCheckTemplate } from '@/api/data-check'
import { CHECK_TEMPLATES, CHECK_TEMPLATE_LABELS, CHECK_TEMPLATE_HEADERS } from '@/types'
import type { CheckImportResult, CheckTemplate } from '@/types'

const props = defineProps<{ modelValue: boolean; scenarioId?: number | null }>()
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
const template = ref<CheckTemplate>('default')
const dataDate = ref('')
const submitting = ref(false)
const result = ref<CheckImportResult | null>(null)

watch(
  () => props.modelValue,
  (open) => {
    if (open) resetAll()
  }
)

function resetAll() {
  file.value = null
  fileList.value = []
  template.value = 'default'
  dataDate.value = todayStr()
  result.value = null
  uploadRef.value?.clearFiles()
}

function todayStr(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 不可选未来日期（按日期串比较） */
function disabledDate(d: Date): boolean {
  const pad = (n: number) => String(n).padStart(2, '0')
  const cur = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return cur > todayStr()
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
  await downloadCheckTemplate(spaceId.value, template.value)
}

async function submit() {
  if (!file.value) {
    ElMessage.warning('请先选择导入文件')
    return
  }
  if (!dataDate.value) {
    ElMessage.warning('请选择校验结果所属日期')
    return
  }
  submitting.value = true
  try {
    result.value = await importCheckResults(
      spaceId.value,
      file.value,
      dataDate.value,
      template.value,
      props.scenarioId ?? undefined
    )
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.field-tip {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: 2px;
}

.cols-alert {
  margin: 0 0 14px;
}

.cols-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.cols-body {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.col-chip {
  background: #eef4ff;
  border: 1px solid #c5dbff;
  color: #23527c;
  border-radius: 6px;
  padding: 1px 8px;
  font-size: 12px;
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

.not-in-list {
  margin-top: 12px;
}

.error-table {
  margin-top: 12px;
}
</style>
