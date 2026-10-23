<template>
  <!-- 任务标签展示 + 内联添加（需求优化：在标签列直接以 + 号入口添加已有标签） -->
  <span v-if="tags?.length || editable" class="tag-cell">
    <span
      v-for="t in tags"
      :key="t.id"
      class="tag-pill"
      :class="{ removable: editable }"
      :style="pillStyle(t.color)"
    >
      {{ t.name }}
      <button
        v-if="editable"
        type="button"
        class="rm"
        title="移除标签"
        @click.stop="removeTag(t)"
      >
        ×
      </button>
    </span>

    <el-popover
      v-if="editable"
      v-model:visible="popVisible"
      placement="bottom"
      :width="240"
      trigger="click"
      popper-class="tag-add-popover"
      @show="onShow"
    >
      <template #reference>
        <button
          class="add-btn"
          :class="{ disabled: !canAdd }"
          :disabled="!canAdd"
          :title="canAdd ? '添加标签' : '请先到「标签管理」创建标签'"
        >
          <span class="plus">+</span>
        </button>
      </template>
      <div class="pop-body">
        <el-select
          v-model="selectedIds"
          multiple
          filterable
          :teleported="false"
          placeholder="选择已有标签"
          style="width: 100%"
        >
          <el-option
            v-for="t in candidateTags"
            :key="t.id"
            :label="t.tag_name"
            :value="t.id"
          >
            <span class="opt">
              <span class="dot" :style="{ backgroundColor: t.color }" />
              {{ t.tag_name }}
            </span>
          </el-option>
        </el-select>
        <div class="pop-actions">
          <el-button size="small" @click="popVisible = false">取消</el-button>
          <el-button size="small" type="primary" :loading="submitting" @click="apply">
            确定
          </el-button>
        </div>
      </div>
    </el-popover>
  </span>
  <span v-else class="tag-empty">—</span>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { setTaskTags } from '@/api/task-migration'
import type { TagOut, TaskTagBrief } from '@/types'

const props = defineProps<{
  tags?: TaskTagBrief[]
  allTags?: TagOut[]
  spaceId?: number
  taskId?: number
  editable?: boolean
}>()
const emit = defineEmits<{ (e: 'updated'): void }>()

const popVisible = ref(false)
const selectedIds = ref<number[]>([])
const submitting = ref(false)

const canAdd = computed(() => !!props.allTags && props.allTags.length > 0)
const currentIds = computed(() => (props.tags ?? []).map((t) => t.id))
const candidateTags = computed(() =>
  (props.allTags ?? []).filter((t) => !currentIds.value.includes(t.id))
)

function pillStyle(color: string): Record<string, string> {
  const c = color || '#1a73e8'
  return { color: c, borderColor: c, backgroundColor: `${c}22` }
}

function onShow() {
  selectedIds.value = []
}

async function apply() {
  if (!props.spaceId || !props.taskId) return
  const union = Array.from(new Set([...currentIds.value, ...selectedIds.value]))
  submitting.value = true
  try {
    await setTaskTags(props.spaceId, props.taskId, union)
    ElMessage.success('标签已更新')
    popVisible.value = false
    emit('updated')
  } finally {
    submitting.value = false
  }
}

async function removeTag(t: TaskTagBrief) {
  if (!props.spaceId || !props.taskId) return
  const remaining = currentIds.value.filter((id) => id !== t.id)
  try {
    await setTaskTags(props.spaceId, props.taskId, remaining)
    ElMessage.success('已移除标签')
    emit('updated')
  } catch {
    /* 错误由请求拦截器统一提示 */
  }
}
</script>

<style scoped>
.tag-cell {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  border: 1px solid;
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}

.tag-pill.removable {
  padding-right: 2px;
}

.rm {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  margin-left: 2px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.55;
  transition: opacity 0.15s, background 0.15s;
}

.rm:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.12);
}

.add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px dashed var(--color-border-strong, #c7d2e0);
  border-radius: 10px;
  background: transparent;
  color: var(--color-primary, #1a73e8);
  cursor: pointer;
  transition: all 0.15s;
}

.add-btn:hover {
  border-color: var(--color-primary, #1a73e8);
  background: var(--color-primary-light, #eef4ff);
}

.add-btn.disabled {
  color: var(--color-text-muted, #9aa7b5);
  border-color: var(--color-border, #d7dee7);
  cursor: not-allowed;
}

.plus {
  font-size: 14px;
  line-height: 1;
}

.pop-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: visible;
}

.pop-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.tag-empty {
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
