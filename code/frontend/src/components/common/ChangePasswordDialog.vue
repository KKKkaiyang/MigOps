<template>
  <el-dialog
    :model-value="modelValue"
    title="修改密码"
    width="440px"
    :close-on-click-modal="!forced"
    :close-on-press-escape="!forced"
    :show-close="!forced"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <el-alert
      v-if="forced"
      type="warning"
      :closable="false"
      show-icon
      class="pwd-alert"
    >
      <template #title>当前为临时密码，请设置新密码后继续使用</template>
    </el-alert>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
      <el-form-item v-if="!forced" label="原密码" prop="old_password">
        <el-input
          v-model="form.old_password"
          type="password"
          show-password
          placeholder="请输入当前密码"
          autocomplete="off"
        />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input
          v-model="form.new_password"
          type="password"
          show-password
          placeholder="至少 8 位，含大写/小写/数字/特殊字符中的三类"
          autocomplete="new-password"
        />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input
          v-model="form.confirm_password"
          type="password"
          show-password
          placeholder="请再次输入新密码"
          autocomplete="new-password"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button v-if="!forced" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { changePassword } from '@/api/auth'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    /** 强制改密模式：原密码由登录态注入、不可见，弹窗不可关闭 */
    forced?: boolean
    /** 强制改密模式下的原密码（临时密码） */
    oldPassword?: string
  }>(),
  { forced: false, oldPassword: '' },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function complexityScore(value: string): number {
  let score = 0
  if (/[a-z]/.test(value)) score++
  if (/[A-Z]/.test(value)) score++
  if (/[0-9]/.test(value)) score++
  if (/[^a-zA-Z0-9]/.test(value)) score++
  return score
}

const rules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少 8 位', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!value) return callback()
        if (complexityScore(value) < 3) {
          return callback(new Error('新密码须至少包含大写、小写、数字、特殊字符中的三类'))
        }
        if (!props.forced && value === form.old_password) {
          return callback(new Error('新密码不能与当前密码相同'))
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

// 打开时初始化表单：强制模式注入原密码（临时密码），自愿模式清空原密码
watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      form.old_password = props.forced ? props.oldPassword || '' : ''
      form.new_password = ''
      form.confirm_password = ''
      formRef.value?.clearValidate?.()
    }
  },
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await changePassword({
        old_password: props.forced ? props.oldPassword || '' : form.old_password,
        new_password: form.new_password,
      })
      ElMessage.success('密码修改成功')
      emit('success')
      close()
    } catch {
      // 错误提示由请求拦截器统一处理
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.pwd-alert {
  margin-bottom: 12px;
}
</style>
