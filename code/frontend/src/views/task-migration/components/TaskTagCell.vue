<template>
  <!-- 任务标签展示 + 内联添加（需求优化：在标签列直接以 + 号入口添加已有标签） -->
  <span v-if="tags?.length || editable" class="tag-cell">
    <span
      v-for="t in visibleTags"
      :key="t.id"
      class="tag-pill"
      :class="{ removable: editable && expanded }"
      :style="pillStyle(t.color)"
    >
      {{ t.name }}
      <button
        v-if="editable && expanded"
        type="button"
        class="rm"
        title="移除标签"
        @click.stop="removeTag(t)"
      >
        ×
      </button>
    </span>

    <!-- 溢出折叠：标签数超过阈值时折叠，提供 V 展开 / ^ 收起 切换（D1/D3） -->
    <button
      v-if="overflow"
      type="button"
      class="fold-toggle"
      :title="expanded ? '收起' : `展开剩余 ${hiddenCount} 个标签`"
      @click="expanded = !expanded"
    >
      <template v-if="expanded">▲ 收起</template>
      <template v-else>▼ 展开 {{ hiddenCount }}</template>
    </button>

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

const props = withDefaults(
  defineProps<{
    tags?: TaskTagBrief[]
    allTags?: TagOut[]
    spaceId?: number
    taskId?: number
    editable?: boolean
    /** 折叠阈值：标签数超过该值即折叠（D2，默认 3） */
    foldThreshold?: number
  }>(),
  { foldThreshold: 3 }
)
const emit = defineEmits<{ (e: 'updated'): void }>()

const popVisible = ref(false)
const selectedIds = ref<number[]>([])
const submitting = ref(false)
/** 是否已展开全部标签（D3：折叠态 ↔ 展开态双向切换） */
const expanded = ref(false)

const canAdd = computed(() => !!props.allTags && props.allTags.length > 0)
const currentIds = computed(() => (props.tags ?? []).map((t) => t.id))
const candidateTags = computed(() =>
  (props.allTags ?? []).filter((t) => !currentIds.value.includes(t.id))
)

/** 标签数是否超出阈值（D2） */
const overflow = computed(() => (props.tags?.length ?? 0) > props.foldThreshold)
/** 剩余隐藏数量（D3：折叠态展示剩余数量） */
const hiddenCount = computed(() =>
  Math.max(0, (props.tags?.length ?? 0) - props.foldThreshold)
)
/** 实际渲染的标签：未展开且溢出时仅展示前 N 个（D2/D3） */
const visibleTags = computed(() => {
  const list = props.tags ?? []
  return !expanded.value && overflow.value ? list.slice(0, props.foldThreshold) : list
})

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

.fold-toggle {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 6px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-muted, #9aa7b5);
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}

.fold-toggle:hover {
  color: var(--color-primary, #1a73e8);
  background: var(--color-primary-light, #eef4ff);
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
