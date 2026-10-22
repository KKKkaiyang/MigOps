<template>
  <!-- 项目资料索引（b02）：按分类分组展示，markdown 查看/下载受密码保护 -->
  <div class="material-page">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <span class="page-title">项目资料索引</span>
          <div class="head-actions">
            <el-button @click="categoryVisible = true">管理分类</el-button>
            <el-button type="primary" @click="openCreate">+ 新增资料索引</el-button>
          </div>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索资料名称..."
          clearable
          style="width: 240px"
          @keyup.enter="load"
          @clear="load"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <span class="scope-tip">按分类分组展示，置顶资料排在分组前列；带锁图标表示需密码查看</span>
      </div>

      <div v-loading="loading">
        <template v-for="group in grouped" :key="group.key">
          <h4 class="group-title">
            {{ group.name }}
            <span class="group-count">{{ group.items.length }}</span>
          </h4>
          <el-table :data="group.items" border size="small" class="group-table">
            <el-table-column prop="name" label="资料名称" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">
                <el-icon v-if="row.has_password" class="lock-icon"><Lock /></el-icon>
                <span>{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <MaterialTypeTag :type="row.type" />
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="170">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="维护人" width="90">
              <template #default="{ row }">{{ row.updated_by || row.created_by || '—' }}</template>
            </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <template v-if="row.type === 'markdown'">
                <el-button link type="primary" @click="openView(row as MaterialOut)">查看</el-button>
                <el-button link type="primary" @click="downloadMaterial(row as MaterialOut)">下载</el-button>
              </template>
              <el-button v-else link type="primary" @click="openTarget(row as MaterialOut)">打开</el-button>
              <el-button link type="primary" @click="openEdit(row as MaterialOut)">编辑</el-button>
              <el-button link type="danger" @click="remove(row as MaterialOut)">删除</el-button>
            </template>
          </el-table-column>
          </el-table>
        </template>

        <el-empty v-if="!loading && grouped.length === 0" description="暂无资料索引，点击右上角「新增资料索引」创建" />
      </div>
    </el-card>

    <!-- 新增 / 编辑 -->
    <MaterialFormDialog v-model="formVisible" :material="current" @success="load" />

    <!-- markdown 查看（渲染预览 + 下载） -->
    <MaterialViewDialog v-model="viewVisible" :material="viewing" />

    <!-- 查看密码验证 -->
    <MaterialPasswordDialog
      v-model="passwordVisible"
      :material="passwordTarget"
      @verified="onPasswordVerified"
    />

    <!-- 分类管理 -->
    <CategoryManageDialog v-model="categoryVisible" @changed="load" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import MaterialTypeTag from '@/components/common/MaterialTypeTag.vue'
import MaterialFormDialog from './components/MaterialFormDialog.vue'
import MaterialViewDialog from './components/MaterialViewDialog.vue'
import MaterialPasswordDialog from './components/MaterialPasswordDialog.vue'
import CategoryManageDialog from './components/CategoryManageDialog.vue'
import {
  deleteMaterial,
  getMaterial,
  listCategories,
  listMaterials,
} from '@/api/material'
import { downloadFile } from '@/utils/download'
import { formatTime } from '@/utils/format'
import { getViewToken, setViewToken } from '@/utils/view-token'
import type { MaterialCategoryOut, MaterialOut } from '@/types'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const loading = ref(true)
const keyword = ref('')
const categories = ref<MaterialCategoryOut[]>([])
const materials = ref<MaterialOut[]>([])

const formVisible = ref(false)
const current = ref<MaterialOut | null>(null)
const viewVisible = ref(false)
const viewing = ref<MaterialOut | null>(null)
const passwordVisible = ref(false)
const passwordTarget = ref<MaterialOut | null>(null)
const categoryVisible = ref(false)

/** 按分类分组：预置/自定义分类 + 未分类 */
const grouped = computed(() => {
  const groups: { key: string; name: string; items: MaterialOut[] }[] = []
  for (const c of categories.value) {
    const items = materials.value.filter((m) => m.category_id === c.id)
    if (items.length) groups.push({ key: `c${c.id}`, name: c.name, items })
  }
  const uncategorized = materials.value.filter((m) => !m.category_id)
  if (uncategorized.length) {
    groups.push({ key: 'uncategorized', name: '未分类', items: uncategorized })
  }
  return groups
})

async function load() {
  loading.value = true
  try {
    const [cats, page] = await Promise.all([
      listCategories(spaceId.value),
      listMaterials(spaceId.value, 1, 100, keyword.value || undefined),
    ])
    categories.value = cats
    materials.value = page.list
  } finally {
    loading.value = false
  }
}

function openCreate() {
  current.value = null
  formVisible.value = true
}

function openEdit(row: MaterialOut) {
  current.value = row
  formVisible.value = true
}

/** 打开外部链接 / 平台台账入口 */
function openTarget(row: MaterialOut) {
  if (row.type === 'external_link') {
    if (row.url) window.open(row.url, '_blank')
    else ElMessage.warning('该资料未维护链接地址')
    return
  }
  if (row.type === 'platform_ledger') {
    const target = row.target_module === 'b03' ? 'space-data-migrations' : 'space-tasks'
    // 平台台账入口：跳转空间视图内对应模块（确认决策 D14）
    window.open(
      `${window.location.origin}/space/${spaceId.value}/${target === 'space-data-migrations' ? 'data-migrations' : 'tasks'}`,
      '_blank'
    )
  }
}

/** markdown 查看：有密码且无令牌时先弹验证 */
async function openView(row: MaterialOut) {
  if (row.has_password && !getViewToken(row.id)) {
    passwordTarget.value = row
    passwordVisible.value = true
    return
  }
  const detail = await getMaterial(spaceId.value, row.id, getViewToken(row.id))
  viewing.value = detail
  viewVisible.value = true
}

async function onPasswordVerified(token: string) {
  const row = passwordTarget.value
  if (!row) return
  setViewToken(row.id, token)
  passwordVisible.value = false
  const detail = await getMaterial(spaceId.value, row.id, token)
  viewing.value = detail
  viewVisible.value = true
}

/** markdown 下载：同样受密码保护（确认决策 D4） */
async function downloadMaterial(row: MaterialOut) {
  if (row.has_password && !getViewToken(row.id)) {
    passwordTarget.value = row
    passwordVisible.value = true
    return
  }
  await downloadFile(
    `/b02/materials/${row.id}/download`,
    { space_id: spaceId.value, view_token: getViewToken(row.id) },
    `${row.name}.md`
  )
}

async function remove(row: MaterialOut) {
  await ElMessageBox.confirm(`确认删除资料「${row.name}」？`, '删除确认', { type: 'warning' })
  await deleteMaterial(spaceId.value, row.id)
  ElMessage.success('删除成功')
  await load()
}

onMounted(load)
</script>

<style scoped>
.material-page {
  display: flex;
  flex-direction: column;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.head-actions {
  display: flex;
  gap: 8px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.scope-tip {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-muted);
}

.group-title {
  color: var(--color-primary);
  font-size: 13px;
  margin: 4px 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.group-count {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 400;
}

.group-table {
  margin-bottom: 16px;
}

.lock-icon {
  color: var(--color-warning-deep, #b06a00);
  margin-right: 4px;
  vertical-align: -2px;
}
</style>
