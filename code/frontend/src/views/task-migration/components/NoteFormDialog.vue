<template>
  <!-- 添加排查备注（需求 §6.3） -->
  <el-dialog v-model="visible" title="添加排查备注" width="560px" :close-on-click-modal="false">
    <el-form :model="form" label-width="84px">
      <el-form-item label="备注类型">
        <el-radio-group v-model="form.note_kind">
          <el-radio value="troubleshoot">排查备注</el-radio>
          <el-radio value="check_result">校验结果</el-radio>
        </el-radio-group>
      </el-form-item>
      <template v-if="form.note_kind === 'troubleshoot'">
        <el-form-item label="问题描述">
          <el-input v-model="form.problem_desc" type="textarea" :rows="2" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="原因分析">
          <el-input v-model="form.cause_analysis" type="textarea" :rows="2" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="修复方案">
          <el-input v-model="form.fix_plan" type="textarea" :rows="2" maxlength="2000" show-word-limit />
        </el-form-item>
      </template>
      <el-form-item v-else label="校验结果">
        <el-input
          v-model="form.problem_desc"
          type="textarea"
          :rows="3"
          placeholder="如：重跑后输出表数据完全对齐，校验通过"
          maxlength="2000"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">添加</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createNote } from '@/api/task-migration'
import type { TaskOut } from '@/types'

const props = defineProps<{ modelValue: boolean; task?: TaskOut | null }>()
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

const submitting = ref(false)
const form = reactive({
  note_kind: 'troubleshoot',
  problem_desc: '',
  cause_analysis: '',
  fix_plan: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.note_kind = 'troubleshoot'
      form.problem_desc = ''
      form.cause_analysis = ''
      form.fix_plan = ''
    }
  }
)

async function submit() {
  if (!props.task) return
  if (!form.problem_desc.trim()) {
    ElMessage.warning(form.note_kind === 'troubleshoot' ? '请填写问题描述' : '请填写校验结果')
    return
  }
  submitting.value = true
  try {
    await createNote(spaceId.value, props.task.id, {
      note_kind: form.note_kind,
      problem_desc: form.problem_desc || undefined,
      cause_analysis: form.cause_analysis || undefined,
      fix_plan: form.fix_plan || undefined,
    })
    ElMessage.success('备注已添加')
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>
