<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑用户' : '新建用户'"
    width="480px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" :disabled="isEdit" placeholder="登录用户名" maxlength="64" />
      </el-form-item>
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="姓名" maxlength="64" />
      </el-form-item>
      <el-form-item label="用户归属">
        <el-select v-model="form.org_type" placeholder="请选择归属" clearable style="width: 100%">
          <el-option v-for="o in ORG_TYPE_OPTIONS" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="邮箱（选填）" maxlength="128" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" placeholder="手机号（选填）" maxlength="32" />
      </el-form-item>
      <el-form-item v-if="!isEdit" label="初始密码">
        <el-input v-model="form.password" placeholder="留空则由系统生成临时密码" maxlength="128" />
        <div class="field-tip">至少 8 位，需包含大写字母、小写字母、数字、特殊字符中的三类</div>
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
import type { FormInstance, FormRules } from 'element-plus'
import { createUser, updateUser } from '@/api/user'
import { ORG_TYPE_OPTIONS } from '@/types'
import type { OrgType, UserOut } from '@/types'

const props = defineProps<{ modelValue: boolean; user?: UserOut | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  /** 创建成功时抛出一次性明文密码（系统生成临时密码时） */
  (e: 'created', password: string): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.user)

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  username: '',
  name: '',
  org_type: '' as OrgType | '',
  email: '',
  phone: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  }
)

function reset() {
  const u = props.user
  form.username = u?.username ?? ''
  form.name = u?.name ?? ''
  form.org_type = (u?.org_type as OrgType) ?? ''
  form.email = u?.email ?? ''
  form.phone = u?.phone ?? ''
  form.password = ''
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && props.user) {
        await updateUser(props.user.id, {
          name: form.name,
          org_type: (form.org_type || undefined) as OrgType | undefined,
          email: form.email || undefined,
          phone: form.phone || undefined,
        })
        visible.value = false
        emit('saved')
      } else {
        const res = await createUser({
          username: form.username,
          name: form.name,
          org_type: (form.org_type || undefined) as OrgType | undefined,
          email: form.email || undefined,
          phone: form.phone || undefined,
          password: form.password || undefined,
        })
        visible.value = false
        if (res.password) {
          emit('created', res.password)
        } else {
          emit('saved')
        }
      }
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
</style>
