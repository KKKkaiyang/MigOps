<template>
  <!-- 保存筛选条件为自定义台账（需求 §6.4） -->
  <el-dialog
    v-model="visible"
    title="保存为台账"
    width="480px"
    :close-on-click-modal="false"
  >
    <div class="filter-summary">
      <div class="filter-title">当前筛选条件</div>
      <div class="filter-tags">
        <el-tag v-for="(v, k) in filters" :key="k" size="small" type="info" class="filter-tag">
          {{ FILTER_LABELS[k as string] || k }}：{{ v }}
        </el-tag>
      </div>
      <div class="filter-note">
        自定义台账为「保存的筛选视图」，数据引用原任务台账（非副本），原任务更新后自动同步。
      </div>
    </div>
    <el-form :model="form" label-width="72px">
      <el-form-item label="台账名称">
        <el-input v-model="form.name" placeholder="如：第一批次" maxlength="128" />
      </el-form-item>
      <el-form-item label="台账描述">
        <el-input v-model="form.description" type="textarea" :rows="2" maxlength="512" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!form.name" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSavedView } from '@/api/task-migration'

const props = defineProps<{ modelValue: boolean; scenarioId: number; filters: Record<string, string> }>()
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

const FILTER_LABELS: Record<string, string> = {
  keyword: '任务名称',
  workflow_name: '工作流',
  migration_status: '迁移状态',
  schedule_status: '调度状态',
  check_status: '校验状态',
  owner: 'Owner',
}

const submitting = ref(false)
const form = reactive({ name: '', description: '' })

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.name = ''
      form.description = ''
    }
  }
)

async function submit() {
  submitting.value = true
  try {
    await createSavedView(spaceId.value, props.scenarioId, {
      name: form.name,
      description: form.description || undefined,
      filter_config: props.filters,
    })
    ElMessage.success('台账已创建')
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.filter-summary {
  background: var(--color-page-bg, #eef2f7);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 14px;
}

.filter-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-tag {
  border-radius: 10px;
}

.filter-note {
  margin-top: 8px;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
