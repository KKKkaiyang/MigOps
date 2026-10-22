<template>
  <!-- 创建任务迁移场景 -->
  <el-dialog v-model="visible" title="创建任务迁移场景" width="480px" :close-on-click-modal="false">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="场景名称" prop="name">
        <el-input v-model="form.name" placeholder="如：hive→hive" maxlength="128" />
      </el-form-item>
      <el-form-item label="场景说明">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="512" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createScenario } from '@/api/task-migration'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success', scenario: { id: number; name: string }): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ name: '', remark: '' })

const rules: FormRules = {
  name: [{ required: true, message: '请输入场景名称', trigger: 'blur' }],
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const scenario = await createScenario(spaceId.value, {
        name: form.name,
        remark: form.remark || undefined,
      })
      ElMessage.success('场景已创建')
      visible.value = false
      emit('success', scenario)
      form.name = ''
      form.remark = ''
    } finally {
      submitting.value = false
    }
  })
}
</script>
