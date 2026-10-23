<template>
  <!-- 空间级标签管理面板（b06 标签管理模块）：行内新增 / 编辑 / 删除 -->
  <div class="tag-manage">
    <el-table
      :data="tableData"
      border
      size="small"
      class="tag-table"
      v-loading="loading"
      :span-method="spanMethod"
    >
      <el-table-column label="标签" min-width="170">
        <template #default="{ row }">
          <template v-if="isEditingRow(row)">
            <div class="edit-row">
              <el-input
                v-model="draft.tag_name"
                placeholder="标签名称"
                maxlength="64"
                size="small"
                style="width: 120px"
              />
              <el-color-picker v-model="draft.color" />
            </div>
          </template>
          <el-button
            v-else-if="row.__newButton"
            class="add-row-btn"
            @click="startNew"
          >
            ＋ 新增标签
          </el-button>
          <span v-else class="pill" :style="pillStyle(row.color)">{{ row.tag_name }}</span>
        </template>
      </el-table-column>

      <el-table-column label="描述" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">
          <el-input
            v-if="isEditingRow(row)"
            v-model="draft.tag_description"
            placeholder="描述（选填）"
            maxlength="512"
            size="small"
            style="width: 100%"
          />
          <span v-else class="muted-inline">{{ row.tag_description || '—' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="分类" width="110" align="center">
        <template #default="{ row }">
          <el-select
            v-if="isEditingRow(row)"
            v-model="draft.tag_category"
            size="small"
            style="width: 100%"
          >
            <el-option v-for="c in TAG_CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
          <span v-else class="cat-pill">{{ row.tag_category || '技术标签' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="130" align="center">
        <template #default="{ row }">
          <template v-if="isEditingRow(row)">
            <el-button link type="primary" :loading="submitting" @click="save">保存</el-button>
            <el-button link @click="cancel">取消</el-button>
          </template>
          <template v-else-if="!row.__newButton">
            <el-button link type="primary" @click="startEdit(row as TagOut)">编辑</el-button>
            <el-button link type="danger" @click="remove(row as TagOut)">删除</el-button>
          </template>
        </template>
      </el-table-column>

      <template #empty><span class="muted">暂无标签，请点击下方「＋ 新增标签」创建</span></template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTag, deleteTag, listTags, updateTag } from '@/api/tag'
import { useTagStore } from '@/store/tags'
import { TAG_CATEGORIES } from '@/types'
import type { TagOut } from '@/types'

const tagStore = useTagStore()

const props = defineProps<{ spaceId: number }>()
const emit = defineEmits<{ (e: 'updated'): void }>()

const COLS = 4
const tags = ref<TagOut[]>([])
const loading = ref(false)
const submitting = ref(false)
const editingId = ref<number | 'new' | null>(null)
const draft = reactive({
  tag_name: '',
  tag_description: '',
  tag_category: '技术标签',
  color: '#1a73e8',
})

const tableData = computed<any[]>(() => {
  const base = tags.value
  if (editingId.value === 'new') return [...base, { __new: true }]
  return [...base, { __newButton: true }]
})

function isEditingRow(row: Record<string, unknown>): boolean {
  if (editingId.value === 'new') return !!row.__new
  return editingId.value !== null && row.id === editingId.value
}

function spanMethod({ row, columnIndex }: { row: Record<string, unknown>; columnIndex: number }) {
  if (row.__newButton) {
    if (columnIndex === 0) return { rowspan: 1, colspan: COLS }
    return { rowspan: 0, colspan: 0 }
  }
  return { rowspan: 1, colspan: 1 }
}

function pillStyle(color: string): Record<string, string> {
  const c = color || '#1a73e8'
  return { color: c, borderColor: c, backgroundColor: `${c}22` }
}

function resetDraft() {
  draft.tag_name = ''
  draft.tag_description = ''
  draft.tag_category = '技术标签'
  draft.color = '#1a73e8'
}

async function load() {
  loading.value = true
  try {
    tags.value = await listTags(props.spaceId)
  } finally {
    loading.value = false
  }
}

function startNew() {
  editingId.value = 'new'
  resetDraft()
}

function startEdit(row: TagOut) {
  editingId.value = row.id
  draft.tag_name = row.tag_name
  draft.tag_description = row.tag_description || ''
  draft.tag_category = row.tag_category || '技术标签'
  draft.color = row.color
}

function cancel() {
  editingId.value = null
  resetDraft()
}

async function save() {
  if (!draft.tag_name) {
    ElMessage.warning('请填写标签名称')
    return
  }
  submitting.value = true
  try {
    const payload = {
      tag_name: draft.tag_name,
      tag_description: draft.tag_description || undefined,
      tag_category: draft.tag_category,
      color: draft.color,
    }
    if (editingId.value === 'new') {
      await createTag(props.spaceId, payload)
      ElMessage.success('标签已创建')
    } else if (typeof editingId.value === 'number') {
      await updateTag(props.spaceId, editingId.value, payload)
      ElMessage.success('标签已更新')
    }
    editingId.value = null
    resetDraft()
    await load()
    await tagStore.refresh(props.spaceId)
    emit('updated')
  } finally {
    submitting.value = false
  }
}

async function remove(row: TagOut) {
  await ElMessageBox.confirm(
    `删除标签「${row.tag_name}」将解除其下 ${row.task_count ?? 0} 个任务的关联（不删除任务），确认删除？`,
    '删除标签',
    { type: 'warning' }
  )
  await deleteTag(props.spaceId, row.id)
  ElMessage.success('标签已删除')
  await load()
  await tagStore.refresh(props.spaceId)
  emit('updated')
}

onMounted(load)
</script>

<style scoped>
.tag-table {
  margin-top: 4px;
}

.edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pill {
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

.cat-pill {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface, #f3f6fb);
  color: var(--color-text-regular);
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}

.muted-inline {
  color: var(--color-text-muted);
  font-size: 12px;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

/* 末行居中虚线「新增标签」按钮 */
.add-row-btn {
  width: 100%;
  border: 1px dashed var(--color-border-strong, #c7d2e0);
  border-radius: 8px;
  background: transparent;
  color: var(--color-primary, #1a73e8);
  font-size: 13px;
  padding: 6px 0;
  transition: all 0.15s;
}

.add-row-btn:hover {
  border-color: var(--color-primary, #1a73e8);
  background: var(--color-primary-light, #eef4ff);
}
</style>
