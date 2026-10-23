<template>
  <!-- 资料新增/编辑：按类型切换表单；markdown 用 md-editor-v3（确认决策 D7，非富文本） -->
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑资料' : '新增资料索引'"
    width="720px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="资料名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入资料名称" maxlength="255" />
      </el-form-item>
      <el-form-item label="类型" prop="type">
        <el-radio-group v-model="form.type" :disabled="isEdit">
          <el-radio value="external_link">外部链接</el-radio>
          <el-radio value="markdown">markdown</el-radio>
          <el-radio value="platform_ledger">平台台账</el-radio>
        </el-radio-group>
        <div v-if="isEdit" class="field-tip">类型创建后不可修改</div>
      </el-form-item>
      <el-form-item label="所属分类">
        <el-select v-model="form.category_id" placeholder="未分类" clearable style="width: 100%">
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>

      <!-- 外部链接 -->
      <el-form-item v-if="form.type === 'external_link'" label="链接地址" prop="url">
        <el-input v-model="form.url" placeholder="https://..." maxlength="1024" />
      </el-form-item>

      <!-- 平台台账 -->
      <el-form-item v-else-if="form.type === 'platform_ledger'" label="跳转目标" prop="target_module">
        <el-select v-model="form.target_module" placeholder="选择平台内模块" style="width: 100%">
          <el-option
            v-for="opt in PLATFORM_LEDGER_TARGET_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <!-- markdown -->
      <el-form-item v-else-if="form.type === 'markdown'" label="资料内容" prop="content">
        <MdEditor v-model="form.content" :theme="editorTheme" style="height: 320px" />
        <div class="field-tip">使用 Markdown 编辑器维护，支持实时预览；保存后可下载为 .md 文件</div>
      </el-form-item>

      <el-form-item label="描述信息">
        <el-input v-model="form.description" type="textarea" :rows="2" maxlength="512" show-word-limit />
      </el-form-item>

      <!-- 查看密码：仅 markdown 类型可设置（确认决策 D4/D10） -->
      <el-form-item v-if="form.type === 'markdown'" label="查看密码">
        <el-input
          v-model="form.view_password"
          type="password"
          show-password
          :placeholder="isEdit ? '不修改请留空；输入新密码可更换；清空并保存可移除密码' : '选填，默认无需密码'"
          maxlength="64"
          @input="passwordTouched = true"
        />
        <div class="field-tip">
          设置后，查看与下载需验证密码（编辑免密）；连续 5 次错误锁定 10 分钟
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createMaterial, listCategories, updateMaterial } from '@/api/material'
import { PLATFORM_LEDGER_TARGET_OPTIONS } from '@/types'
import type { MaterialCategoryOut, MaterialOut } from '@/types'

// md-editor-v3（PrismJS + CodeMirror，体积大）按需异步加载，避免拖累主包（样式已在 main.ts 全局引入）
const MdEditor = defineAsyncComponent(() => import('md-editor-v3').then((m) => m.MdEditor))

const props = defineProps<{ modelValue: boolean; material?: MaterialOut | null }>()
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

const isEdit = computed(() => !!props.material)

const formRef = ref<FormInstance>()
const submitting = ref(false)
const passwordTouched = ref(false)
const categories = ref<MaterialCategoryOut[]>([])
const editorTheme = ref<'light' | 'dark'>('light')

const form = reactive({
  name: '',
  type: 'external_link',
  category_id: null as number | null,
  url: '',
  target_module: '',
  content: '',
  description: '',
  view_password: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入资料名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  url: [{ required: true, message: '请输入链接地址', trigger: 'blur' }],
  target_module: [{ required: true, message: '请选择跳转目标', trigger: 'change' }],
  content: [{ required: true, message: '请输入资料内容', trigger: 'blur' }],
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    passwordTouched.value = false
    categories.value = await listCategories(spaceId.value)
    reset()
  }
)

function reset() {
  const m = props.material
  form.name = m?.name ?? ''
  form.type = m?.type ?? 'external_link'
  form.category_id = m?.category_id ?? null
  form.url = m?.url ?? ''
  form.target_module = m?.target_module ?? ''
  form.content = m?.content ?? ''
  form.description = m?.description ?? ''
  form.view_password = ''
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const typed: Record<string, unknown> = {
        name: form.name,
        type: form.type,
        category_id: form.category_id,
        description: form.description || undefined,
      }
      if (form.type === 'external_link') typed.url = form.url
      if (form.type === 'markdown') typed.content = form.content
      if (form.type === 'platform_ledger') typed.target_module = form.target_module
      if (form.type === 'markdown' && form.view_password) {
        typed.view_password = form.view_password
      }

      if (isEdit.value && props.material) {
        const payload: Parameters<typeof updateMaterial>[2] = {
          ...(typed as Parameters<typeof updateMaterial>[2]),
        }
        // view_password：未触碰不传；空串=清除；非空=更换
        if (form.type === 'markdown' && passwordTouched.value) {
          payload.view_password = form.view_password
        }
        await updateMaterial(spaceId.value, props.material.id, payload)
        ElMessage.success('更新成功')
      } else {
        await createMaterial(spaceId.value, typed as Parameters<typeof createMaterial>[1])
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
</style>
