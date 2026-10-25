<template>
  <!-- 批量任务状态流转：选择某一维度与目标准值，整体更新（D1：维度独立） -->
  <el-dialog
    v-model="visible"
    title="批量流转状态"
    width="440px"
    :close-on-click-modal="false"
  >
    <p class="dialog-tip">将已选 {{ ids.length }} 个任务的「{{ dimLabel }}」统一流转为「{{ value }}」。</p>
    <el-form label-width="96px" label-position="right">
      <el-form-item label="状态维度">
        <el-select v-model="dimension" placeholder="选择维度" style="width: 100%" @change="onDimChange">
          <el-option v-for="d in STATUS_DIMENSIONS" :key="d.key" :label="d.label" :value="d.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="目标取值">
        <el-select v-model="value" placeholder="选择目标取值" style="width: 100%" :disabled="!dimension">
          <el-option v-for="s in valueOptions" :key="s" :label="s" :value="s" />
        </el-select>
      </el-form-item>
    </el-form>
    <div class="dialog-note">
      各状态维度相互独立、互不约束；所选任务原值可不同，将被统一覆盖为目标取值。
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="!dimension || !value"
        @click="submit"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { batchUpdateTaskStatus } from '@/api/task-migration'
import { STATUS_DIMENSION_MAP, STATUS_DIMENSIONS } from '@/utils/task-status'
import type { StatusDimensionKey } from '@/types'

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

const dimension = ref<StatusDimensionKey | ''>('')
const value = ref('')
const submitting = ref(false)

const dimLabel = computed(() => (dimension.value ? STATUS_DIMENSION_MAP[dimension.value]?.label ?? '' : ''))
const valueOptions = computed(() =>
  dimension.value ? STATUS_DIMENSION_MAP[dimension.value]?.options ?? [] : []
)

function onDimChange() {
  value.value = ''
}

async function submit() {
  if (!dimension.value || !value.value) return
  submitting.value = true
  try {
    const result = await batchUpdateTaskStatus(spaceId.value, props.scenarioId, {
      ids: props.ids,
      dimension: dimension.value,
      value: value.value,
    })
    ElMessage.success(`已更新 ${result.affected} 条`)
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}

watch(visible, (open) => {
  if (open) {
    dimension.value = ''
    value.value = ''
  }
})
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
