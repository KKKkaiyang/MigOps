<template>
  <!-- 保存筛选条件为任务台账 / 编辑台账 / 勾选任务创建固定名单（需求 R3，交互评审 I5 引导式） -->
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="480px"
    :close-on-click-modal="false"
  >
    <!-- 勾选任务创建：直接锁定为固定名单 -->
    <div v-if="taskIds?.length" class="filter-summary">
      <div class="filter-note">
        将把选中的 <b>{{ taskIds.length }}</b> 个任务锁定为<b>固定名单</b>：{{ VIEW_MODE_NOTE.fixed }}。
      </div>
    </div>

    <!-- 筛选保存：引导式二选一（而非直接暴露模式单选） -->
    <template v-else-if="!isEdit">
      <div class="filter-summary">
        <div class="filter-title">当前筛选条件</div>
        <div class="filter-tags">
          <el-tag v-for="(v, k) in filters" :key="k" size="small" type="info" class="filter-tag">
            {{ FILTER_LABELS[k as string] || k }}：{{ v }}
          </el-tag>
        </div>
      </div>
      <div class="guide-q">这份台账的名单，后续如何维护？</div>
      <div class="mode-cards">
        <div
          class="mode-card"
          :class="{ active: form.view_mode === 'dynamic' }"
          @click="form.view_mode = 'dynamic'"
        >
          <div class="mc-title">自动更新 <el-tag size="small" type="success" effect="plain">推荐</el-tag></div>
          <div class="mc-desc">{{ VIEW_MODE_NOTE.dynamic }}</div>
        </div>
        <div
          class="mode-card"
          :class="{ active: form.view_mode === 'fixed' }"
          @click="form.view_mode = 'fixed'"
        >
          <div class="mc-title">固定名单</div>
          <div class="mc-desc">{{ VIEW_MODE_NOTE.fixed }}</div>
        </div>
      </div>
    </template>

    <el-form :model="form" label-width="72px" style="margin-top: 14px">
      <el-form-item label="台账名称">
        <el-input v-model="form.name" placeholder="如：第一批次" maxlength="128" />
      </el-form-item>
      <el-form-item label="台账描述">
        <el-input v-model="form.description" type="textarea" :rows="2" maxlength="512" show-word-limit />
      </el-form-item>
    </el-form>

    <div class="dialog-note">任务台账数据引用原任务（非副本）；台账内的状态变更会直接回写原任务。</div>

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
import { createSavedView, updateSavedView } from '@/api/task-migration'
import { VIEW_MODE_NOTE } from '@/types'
import type { SavedViewOut } from '@/types'

const props = defineProps<{
  modelValue: boolean
  scenarioId: number
  filters?: Record<string, unknown>
  /** 编辑态：传入已有台账 */
  view?: SavedViewOut
  /** R3：勾选任务创建台账（强制固定名单，直接落成员） */
  taskIds?: number[]
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

const FILTER_LABELS: Record<string, string> = {
  keyword: '任务名称',
  workflow_name: '工作流',
  migration_status: '迁移状态',
  schedule_status: '调度状态',
  check_status: '校验状态',
  owner: 'Owner',
}

const isEdit = computed(() => !!props.view)
const dialogTitle = computed(() => {
  if (isEdit.value) return '编辑台账'
  if (props.taskIds?.length) return '创建台账（固定名单）'
  return '保存为台账'
})

const submitting = ref(false)
const form = reactive<{ name: string; description: string; view_mode: 'dynamic' | 'fixed' }>({
  name: '',
  description: '',
  view_mode: 'dynamic',
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.view) {
      form.name = props.view.name
      form.description = props.view.description || ''
      form.view_mode = (props.view.view_mode as 'dynamic' | 'fixed') || 'dynamic'
    } else {
      form.name = ''
      form.description = ''
      // 勾选任务创建 → 固定名单；筛选保存默认「自动更新」（引导式默认项）
      form.view_mode = props.taskIds?.length ? 'fixed' : 'dynamic'
    }
  }
)

async function submit() {
  submitting.value = true
  try {
    if (props.view) {
      await updateSavedView(spaceId.value, props.view.id, {
        name: form.name,
        description: form.description || undefined,
        view_mode: form.view_mode,
      })
      ElMessage.success('台账已更新')
    } else if (props.taskIds?.length) {
      await createSavedView(spaceId.value, props.scenarioId, {
        name: form.name,
        description: form.description || undefined,
        member_ids: props.taskIds,
        view_mode: 'fixed',
      })
      ElMessage.success('台账已创建（固定名单）')
    } else {
      await createSavedView(spaceId.value, props.scenarioId, {
        name: form.name,
        description: form.description || undefined,
        filter_config: props.filters || {},
        view_mode: form.view_mode,
      })
      ElMessage.success('台账已创建')
    }
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
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.7;
}

.guide-q {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.mode-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.mode-card:hover {
  border-color: var(--color-primary);
}

.mode-card.active {
  border-color: var(--color-primary);
  background: var(--el-color-primary-light-9);
}

.mc-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.mc-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.dialog-note {
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
