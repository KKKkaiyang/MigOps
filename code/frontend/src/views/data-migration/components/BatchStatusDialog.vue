<template>
  <!-- 批量更新迁移状态（需求 §5.2.8） -->
  <el-dialog
    v-model="visible"
    :title="`批量更新状态（已选 ${count} 条）`"
    width="480px"
    :close-on-click-modal="false"
  >
    <el-form label-width="110px">
      <el-form-item label="元数据状态">
        <el-select v-model="form.metadata_status" clearable placeholder="不修改" style="width: 100%">
          <el-option v-for="t in MIGRATION_LINE_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="全量迁移状态">
        <el-select v-model="form.full_sync_status" clearable placeholder="不修改" style="width: 100%">
          <el-option v-for="t in MIGRATION_LINE_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="全量截止日期">
        <el-date-picker
          v-model="form.full_sync_cutoff_date"
          type="date"
          placeholder="不修改"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="增量迁移状态">
        <el-select v-model="form.incr_sync_status" clearable placeholder="不修改" style="width: 100%">
          <el-option v-for="t in INCR_SYNC_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="增量最新时间">
        <el-date-picker
          v-model="form.incr_sync_latest_at"
          type="datetime"
          placeholder="不修改"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>
      <div class="dialog-note">仅勾选的字段会被更新，其余保持原值。</div>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchUpdateStatus } from '@/api/data-migration'
import { INCR_SYNC_STATUS_OPTIONS, MIGRATION_LINE_STATUS_OPTIONS } from '@/types'

const props = defineProps<{
  modelValue: boolean
  scenarioId: number
  count: number
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

const submitting = ref(false)
const form = reactive({
  metadata_status: '',
  full_sync_status: '',
  full_sync_cutoff_date: '',
  incr_sync_status: '',
  incr_sync_latest_at: '',
})

async function submit() {
  const payload: Record<string, unknown> = { ids: props.ids }
  if (form.metadata_status) payload.metadata_status = form.metadata_status
  if (form.full_sync_status) payload.full_sync_status = form.full_sync_status
  if (form.full_sync_cutoff_date) payload.full_sync_cutoff_date = form.full_sync_cutoff_date
  if (form.incr_sync_status) payload.incr_sync_status = form.incr_sync_status
  if (form.incr_sync_latest_at) payload.incr_sync_latest_at = form.incr_sync_latest_at
  if (Object.keys(payload).length === 1) {
    ElMessage.warning('请至少选择一个要更新的字段')
    return
  }
  submitting.value = true
  try {
    await batchUpdateStatus(spaceId.value, props.scenarioId, payload as never)
    ElMessage.success('批量更新成功')
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-note {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
