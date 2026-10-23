<template>
  <!-- 批量打标签 / 去标签（需求 §3.2） -->
  <el-dialog
    v-model="visible"
    title="批量打标签"
    width="440px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form label-width="80px">
      <el-form-item label="操作">
        <el-radio-group v-model="action">
          <el-radio value="add">打标签</el-radio>
          <el-radio value="remove">移除标签</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="选择标签">
        <TaskTagSelect v-model="tagIds" placeholder="选择要操作的标签" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!tagIds.length" @click="submit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchTaskTags } from '@/api/task-migration'
import TaskTagSelect from './TaskTagSelect.vue'

const props = defineProps<{
  modelValue: boolean
  scenarioId: number
  ids: number[]
}>()
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

const action = ref<'add' | 'remove'>('add')
const tagIds = ref<number[]>([])
const submitting = ref(false)

async function submit() {
  submitting.value = true
  try {
    const res = await batchTaskTags(spaceId.value, props.scenarioId, {
      ids: props.ids,
      tag_ids: tagIds.value,
      action: action.value,
    })
    ElMessage.success(`已为 ${res.affected} 个任务${action.value === 'add' ? '打标签' : '移除标签'}`)
    visible.value = false
    tagIds.value = []
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>
