<template>
  <!-- 分类管理：预置三类 + 自定义分类增改；删除分类不删资料（需求 §4.3） -->
  <el-dialog v-model="visible" title="管理分类" width="520px" :close-on-click-modal="false">
    <div class="cat-toolbar">
      <el-input
        v-model="newName"
        placeholder="新分类名称"
        maxlength="64"
        style="width: 220px"
        @keyup.enter="add"
      />
      <el-button type="primary" :disabled="!newName" @click="add">添加分类</el-button>
    </div>
    <el-table :data="categories" border size="small" v-loading="loading" max-height="360">
      <el-table-column prop="name" label="分类名称" min-width="160">
        <template #default="{ row }">
              <el-input
                v-if="row.editing"
                v-model="row.editName"
                size="small"
                maxlength="64"
                @keyup.enter="save(row as CategoryRow)"
              />
          <span v-else>
            {{ row.name }}
            <el-tag v-if="row.is_preset" size="small" type="info">预置</el-tag>
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="material_count" label="资料数" width="80" align="center" />
      <el-table-column label="操作" width="140" align="center">
        <template #default="{ row }">
          <template v-if="row.editing">
            <el-button link type="primary" size="small" @click="save(row as CategoryRow)">保存</el-button>
            <el-button link size="small" @click="row.editing = false">取消</el-button>
          </template>
          <template v-else>
            <el-button link type="primary" size="small" @click="startEdit(row as CategoryRow)">重命名</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.is_preset === 1"
              @click="remove(row as MaterialCategoryOut)"
            >
              删除
            </el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <div class="dialog-note">预置分类不可删除；删除自定义分类后，其下资料将变为「未分类」。</div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
} from '@/api/material'
import type { MaterialCategoryOut } from '@/types'

type CategoryRow = MaterialCategoryOut & { editing?: boolean; editName?: string }

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'changed'): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const categories = ref<(MaterialCategoryOut & { editing?: boolean; editName?: string })[]>([])
const newName = ref('')

async function load() {
  loading.value = true
  try {
    categories.value = await listCategories(spaceId.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function add() {
  if (!newName.value.trim()) return
  await createCategory(spaceId.value, { name: newName.value.trim() })
  ElMessage.success('分类已创建')
  newName.value = ''
  await load()
  emit('changed')
}

function startEdit(row: (typeof categories.value)[number]) {
  row.editing = true
  row.editName = row.name
}

async function save(row: (typeof categories.value)[number]) {
  const name = (row.editName ?? '').trim()
  if (!name) {
    ElMessage.warning('分类名称不能为空')
    return
  }
  await updateCategory(spaceId.value, row.id, { name })
  row.editing = false
  ElMessage.success('已重命名')
  await load()
  emit('changed')
}

async function remove(row: MaterialCategoryOut) {
  await ElMessageBox.confirm(
    `确认删除分类「${row.name}」？其下资料将变为未分类。`,
    '删除确认',
    { type: 'warning' }
  )
  await deleteCategory(spaceId.value, row.id)
  ElMessage.success('删除成功')
  await load()
  emit('changed')
}
</script>

<style scoped>
.cat-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.dialog-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}
</style>
