<template>
  <!-- 勾选任务加入已有视图（目标视图在对话框内选择） -->
  <el-dialog
    v-model="visible"
    title="添加到视图"
    width="460px"
    :close-on-click-modal="false"
  >
    <div class="hint">
      将选中的 <b>{{ taskIds.length }}</b> 个任务加入目标视图。
      <span v-if="targetIsDynamic" class="warn">
        该视图为「自动更新」类型，加入后将转为「固定名单」。
      </span>
    </div>

    <el-form label-width="72px">
      <el-form-item label="目标视图" required>
        <el-select
          v-model="viewId"
          placeholder="选择要加入的视图"
          filterable
          style="width: 100%"
        >
          <el-option
            v-for="v in views"
            :key="v.id"
            :value="v.id"
            :label="`${v.name}（${VIEW_MODE_LABEL[v.view_mode] || v.view_mode} · ${v.task_count}）`"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!viewId" @click="submit">
        加入视图
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { addSavedViewMembers, listSavedViews } from '@/api/task-migration'
import { VIEW_MODE_LABEL } from '@/types'
import type { SavedViewOut } from '@/types'

const props = defineProps<{
  modelValue: boolean
  scenarioId: number
  taskIds: number[]
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success', viewId: number): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const views = ref<SavedViewOut[]>([])
const viewId = ref<number | undefined>(undefined)
const submitting = ref(false)

const targetIsDynamic = computed(() => {
  if (!viewId.value) return false
  const v = views.value.find((x) => x.id === viewId.value)
  return v ? v.view_mode !== 'fixed' : false
})

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    viewId.value = undefined
    try {
      views.value = await listSavedViews(spaceId.value, props.scenarioId)
    } catch {
      views.value = []
    }
  }
)

async function submit() {
  if (!viewId.value) return
  submitting.value = true
  try {
    await addSavedViewMembers(spaceId.value, viewId.value, props.taskIds)
    ElMessage.success('已加入视图')
    visible.value = false
    emit('success', viewId.value)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.hint {
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.6;
  margin-bottom: 14px;
}

.warn {
  color: var(--color-warning, #e6a23c);
}
</style>
