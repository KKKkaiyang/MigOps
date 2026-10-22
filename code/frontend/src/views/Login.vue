<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">迁移管家 <span class="logo-en">MigOps</span></div>
        <p class="slogan">面向公有云大数据迁移项目的管理平台</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @keyup.enter="submit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>

        <el-form-item v-if="captchaRequired" label="验证码" prop="captcha_code">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha_code"
              placeholder="不包含 1/I/0/O"
              autocomplete="off"
              maxlength="4"
              @keyup.enter="submit"
            />
            <div class="captcha-img" v-html="captchaSvg" @click="refreshCaptcha" title="点击刷新验证码" />
          </div>
        </el-form-item>

        <el-button type="primary" class="submit-btn" :loading="submitting" @click="submit">
          登 录
        </el-button>
      </el-form>

      <div class="login-tip">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            默认管理员账号：<span class="mono">admin</span> / 初始密码：<span class="mono">Admin@1234</span>
          </template>
        </el-alert>
      </div>
    </div>

    <!-- 临时密码登录后强制修改密码 -->
    <el-dialog
      v-model="pwdDialogVisible"
      title="修改密码"
      width="440px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <el-alert type="warning" :closable="false" show-icon class="pwd-alert">
        <template #title>当前为临时密码，请设置新密码后继续使用</template>
      </el-alert>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="88px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，含三类字符" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitNewPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { changePassword, getCaptcha } from '@/api/auth'
import { BizError, CODE_CAPTCHA } from '@/api/request'
import { useUserStore } from '@/store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const captchaRequired = ref(false)
const captchaSvg = ref('')
const captchaId = ref('')

const form = reactive({
  username: '',
  password: '',
  captcha_code: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 强制改密对话框
const pwdDialogVisible = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdSubmitting = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const pwdRules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少 8 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function refreshCaptcha() {
  try {
    const data = await getCaptcha()
    captchaId.value = data.captcha_id
    captchaSvg.value = data.svg
    form.captcha_code = ''
  } catch {
    // 错误提示由请求拦截器统一处理
  }
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const result = await userStore.login({
        username: form.username,
        password: form.password,
        captcha_id: captchaRequired.value ? captchaId.value : undefined,
        captcha_code: captchaRequired.value ? form.captcha_code : undefined,
      })

      // 临时密码登录：强制修改密码
      if (result.must_change_password) {
        pwdForm.old_password = form.password
        pwdDialogVisible.value = true
        return
      }

      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || '/'
      router.replace(redirect)
    } catch (err) {
      // 后端提示需要验证码：展示验证码区并刷新
      if (err instanceof BizError && err.code === CODE_CAPTCHA) {
        captchaRequired.value = true
        await refreshCaptcha()
      }
    } finally {
      submitting.value = false
    }
  })
}

async function submitNewPassword() {
  await pwdFormRef.value?.validate(async (valid) => {
    if (!valid) return
    pwdSubmitting.value = true
    try {
      await changePassword({
        old_password: pwdForm.old_password,
        new_password: pwdForm.new_password,
      })
      ElMessage.success('密码修改成功')
      pwdDialogVisible.value = false
      // 令牌与密码无关，改密后直接带登录态进入目标页
      const redirect = (route.query.redirect as string) || '/'
      router.replace(redirect)
    } finally {
      pwdSubmitting.value = false
    }
  })
}

onMounted(() => {
  // 已登录用户访问登录页时由路由守卫拦截，此处无需处理
})
</script>

<style scoped>
.login-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  width: 400px;
  max-width: calc(100vw - 32px);
  background: var(--color-surface);
  border-radius: 10px;
  box-shadow: var(--shadow-medium);
  padding: 28px 32px 24px;
}

.login-header {
  text-align: center;
  margin-bottom: 20px;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: 0.5px;
}

.logo-en {
  color: var(--color-primary);
}

.slogan {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.captcha-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.captcha-img {
  flex: none;
  width: 120px;
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: var(--el-border-radius-base);
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f6fb;
}

.captcha-img :deep(svg) {
  display: block;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.login-tip {
  margin-top: 16px;
}

.pwd-alert {
  margin-bottom: 12px;
}
</style>
