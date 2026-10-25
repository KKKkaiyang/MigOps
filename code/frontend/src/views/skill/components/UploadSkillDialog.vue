<template>
  <!-- skill 上传对话框：手工上传（名称 / 简介 / 是否公开 + zip 包） -->
  <el-dialog
    v-model="visible"
    title="上传 skill"
    width="520px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="skill 名称（平台级唯一）" maxlength="128" />
      </el-form-item>
      <el-form-item label="简介" prop="intro">
        <el-input
          v-model="form.intro"
          type="textarea"
          :rows="3"
          placeholder="一句话描述这个 skill 的用途"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>
      <el-form-item label="是否公开" prop="is_public">
        <el-switch
          v-model="form.is_public"
          :active-value="1"
          :inactive-value="0"
          active-text="公开"
          inactive-text="私有"
        />
        <span class="form-hint">私有仅本人与系统管理员可见</span>
      </el-form-item>
      <el-form-item label="文件" prop="file" :rules="fileRule">
        <el-upload
          ref="uploadRef"
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".zip"
          :on-change="onFileChange"
          :on-exceed="onExceed"
          :file-list="fileList"
        >
          <div class="upload-inner">
            <el-icon :size="32" color="#8a96a3"><UploadFilled /></el-icon>
            <div class="upload-text">将 skill 压缩包拖到此处，或<em>点击上传</em></div>
            <div class="upload-sub">仅支持 .zip，单个文件 ≤ 50MB</div>
          </div>
        </el-upload>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!file" @click="submit">
        上传
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { FormInstance, FormRules, UploadFile, UploadFiles, UploadInstance } from 'element-plus'
import { uploadSkill } from '@/api/skill'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref<FormInstance>()
const uploadRef = ref<UploadInstance>()
const form = ref({ name: '', intro: '', is_public: 1 as number })
const file = ref<File | null>(null)
const fileList = ref<UploadFiles>([])
const submitting = ref(false)

const rules: FormRules = {
  name: [{ required: true, message: '请输入 skill 名称', trigger: 'blur' }],
}

const fileRule = [
  {
    required: true,
    validator: (_r: unknown, _v: unknown, cb: (msg?: Error) => void) => {
      if (!file.value) cb(new Error('请选择上传的 zip 文件'))
      else cb()
    },
    trigger: 'change',
  },
]

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

function reset() {
  form.value = { name: '', intro: '', is_public:1 }
  file.value = null
  fileList.value = []
  uploadRef.value?.clearFiles()
  formRef.value?.clearValidate()
}

async function submit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid || !file.value) return
    submitting.value = true
    try {
      await uploadSkill(file.value, {
        name: form.value.name,
        intro: form.value.intro || undefined,
        is_public: form.value.is_public,
      })
      ElMessage.success('上传成功')
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.upload-area {
  width: 100%;
}

.upload-inner {
  padding: 16px 0;
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
</style>
