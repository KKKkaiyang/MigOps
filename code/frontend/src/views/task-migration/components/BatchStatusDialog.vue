<template>
  <!-- 批量任务状态流转（先全部校验，任一非法整体拒绝） -->
  <el-dialog
    v-model="visible"
    title="批量流转状态"
    width="420px"
    :close-on-click-modal="false"
  >
    <p class="dialog-tip">将已选 {{ ids.length }} 个任务统一流转为指定迁移状态。</p>
    <el-select v-model="status" placeholder="选择目标状态" style="width: 100%">
      <el-option v-for="s in TASK_MIGRATION_STATUS_OPTIONS" :key="s" :label="s" :value="s" />
    </el-select>
    <div class="dialog-note">
      流转须符合状态机规则；若所选任务中存在不允许该流转的状态，整体将被拒绝并提示。
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!status" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchUpdateTaskStatus } from '@/api/task-migration'
import { TASK_MIGRATION_STATUS_OPTIONS } from '@/types'

const props = defineProps<{ modelValue: boolean; scenarioId: number; ids: number[] }>()
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

const status = ref('')
const submitting = ref(false)

async function submit() {
  submitting.value = true
  try {
    const result = await batchUpdateTaskStatus(spaceId.value, props.scenarioId, {
      ids: props.ids,
      status: status.value,
    })
    ElMessage.success(`已更新 ${result.affected} 条`)
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-tip {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--color-text-regular);
}

.dialog-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
