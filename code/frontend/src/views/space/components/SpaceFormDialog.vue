<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑空间' : '新建空间'"
    width="520px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="项目简称" prop="space_code">
        <el-input
          v-model="form.space_code"
          :disabled="isEdit"
          placeholder="小写字母开头，可含数字/下划线"
          maxlength="32"
        />
        <div class="field-tip">用于生成独立数据库 mig_&lt;简称&gt;_db，创建后不可修改</div>
      </el-form-item>
      <el-form-item label="项目名称" prop="space_name">
        <el-input v-model="form.space_name" placeholder="请输入项目名称" maxlength="128" />
      </el-form-item>
      <el-form-item label="客户名称">
        <el-input v-model="form.customer_name" placeholder="请输入客户名称" maxlength="128" />
      </el-form-item>
      <el-form-item label="源端平台">
        <el-input v-model="form.source_platform" placeholder="华为云/阿里云/私有云/火山云" maxlength="64" />
      </el-form-item>
      <el-form-item label="目标平台">
        <el-input v-model="form.target_platform" placeholder="腾讯云/AWS/Azure" maxlength="64" />
      </el-form-item>
      <el-form-item label="负责人">
        <el-input v-model="form.owner" placeholder="请输入负责人" maxlength="64" />
      </el-form-item>
      <el-form-item label="整体进展">
        <div class="progress-input">
          <el-slider v-model="form.overall_progress" :min="0" :max="100" style="flex: 1" />
          <el-input-number
            v-model="form.overall_progress"
            :min="0"
            :max="100"
            :step="5"
            size="small"
            controls-position="right"
            style="width: 112px"
          />
        </div>
        <div class="field-tip">手工维护的项目整体进展（0~100%）</div>
      </el-form-item>
      <el-form-item label="项目周期">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="空间说明">
        <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createSpace, updateSpace } from '@/api/space'
import type { SpaceOut } from '@/types'

const props = defineProps<{ modelValue: boolean; space?: SpaceOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.space)

const formRef = ref<FormInstance>()
const submitting = ref(false)
const dateRange = ref<[string, string] | null>(null)

const form = reactive({
  space_code: '',
  space_name: '',
  customer_name: '',
  source_platform: '',
  target_platform: '',
  owner: '',
  remark: '',
  overall_progress: 0,
})

const CODE_PATTERN = /^[a-z][a-z0-9_]{1,30}$/

const rules: FormRules = {
  space_code: [
    { required: true, message: '请输入项目简称', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!CODE_PATTERN.test(value)) {
          callback(new Error('小写字母开头，可含小写字母/数字/下划线，长度 2~32'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  space_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  }
)

function reset() {
  const s = props.space
  form.space_code = s?.space_code ?? ''
  form.space_name = s?.space_name ?? ''
  form.customer_name = s?.customer_name ?? ''
  form.source_platform = s?.source_platform ?? ''
  form.target_platform = s?.target_platform ?? ''
  form.owner = s?.owner ?? ''
  form.remark = s?.remark ?? ''
  form.overall_progress = s?.overall_progress ?? 0
  dateRange.value =
    s?.start_date && s?.end_date ? [s.start_date, s.end_date] : null
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const payload = {
        space_name: form.space_name,
        customer_name: form.customer_name || undefined,
        source_platform: form.source_platform || undefined,
        target_platform: form.target_platform || undefined,
        owner: form.owner || undefined,
        remark: form.remark || undefined,
        overall_progress: form.overall_progress,
        start_date: dateRange.value?.[0],
        end_date: dateRange.value?.[1],
      }
      if (isEdit.value && props.space) {
        await updateSpace(props.space.id, payload)
        ElMessage.success('更新成功')
      } else {
        await createSpace({ ...payload, space_code: form.space_code })
        ElMessage.success('创建成功')
      }
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.field-tip {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.5;
  margin-top: 2px;
}

.progress-input {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
</style>
