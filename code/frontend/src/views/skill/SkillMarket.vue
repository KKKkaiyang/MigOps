<template>
  <div class="skill-market">
    <el-card shadow="never" class="market-card">
      <template #header>
        <div class="market-header">
          <div class="title-row">
            <el-tabs v-model="activeTab" class="market-tabs" @tab-change="onTabChange">
              <el-tab-pane label="skill 市场" name="market" />
              <el-tab-pane label="我的 skill" name="mine" />
            </el-tabs>
            <el-button type="primary" :icon="UploadFilled" @click="uploadVisible = true">
              上传 skill
            </el-button>
          </div>
          <div v-if="activeTab === 'market'" class="toolbar">
            <el-input
              v-model="keyword"
              placeholder="搜索名称 / 简介"
              clearable
              class="kw"
              @keyup.enter="load"
              @clear="load"
            />
            <el-select v-model="sort" class="sort" @change="load">
              <el-option label="热度优先" value="heat" />
              <el-option label="最新上传" value="latest" />
            </el-select>
            <el-button type="primary" @click="load">查询</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loading">
        <div v-if="list.length" class="grid">
          <el-card
            v-for="s in list"
            :key="s.skill_code"
            shadow="hover"
            class="skill-item"
          >
            <div class="skill-top">
              <span class="skill-name" :title="s.name">{{ s.name }}</span>
              <el-tag
                size="small"
                :class="s.is_public === 1 ? 'tag-public' : 'tag-private'"
                effect="light"
              >
                {{ s.is_public === 1 ? '公开' : '私有' }}
              </el-tag>
            </div>
            <div class="skill-intro">{{ s.intro || '暂无简介' }}</div>
            <div class="skill-meta">
              <span class="heat">
                <el-icon><Download /></el-icon>
                {{ s.download_count }}
              </span>
              <span class="author">{{ s.author_name || '未知作者' }}</span>
              <el-tag v-if="activeTab === 'mine' && s.status === '下架'" size="small" type="info" effect="plain">
                已下架
              </el-tag>
            </div>
            <div class="skill-actions">
              <el-button
                v-if="activeTab === 'market' || s.is_public === 1 || isL0OrOwner(s)"
                type="primary"
                link
                :icon="Download"
                @click="onDownload(s)"
              >
                下载
              </el-button>
              <template v-if="activeTab === 'mine'">
                <el-button
                  link
                  :type="s.status === '上架' ? 'warning' : 'success'"
                  @click="onToggleStatus(s)"
                >
                  {{ s.status === '上架' ? '下架' : '上架' }}
                </el-button>
                <el-button link type="danger" @click="onDelete(s)">删除</el-button>
              </template>
            </div>
          </el-card>
        </div>
        <el-empty v-else description="暂无 skill" />

        <el-pagination
          v-if="total > pageSize"
          class="pager"
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="onPage"
        />
      </div>
    </el-card>

    <UploadSkillDialog v-model="uploadVisible" @success="load" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { deleteSkill, listMarket, mySkills, setSkillStatus } from '@/api/skill'
import { downloadFile } from '@/utils/download'
import type { SkillOut } from '@/types'
import UploadSkillDialog from './components/UploadSkillDialog.vue'

const userStore = useUserStore()
const isL0 = computed(() => userStore.isL0)

const activeTab = ref<'market' | 'mine'>('market')
const keyword = ref('')
const sort = ref<'heat' | 'latest'>('heat')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const list = ref<SkillOut[]>([])
const loading = ref(false)
const uploadVisible = ref(false)

onMounted(load)

function isL0OrOwner(s: SkillOut): boolean {
  return isL0.value || s.author_user_id === userStore.user?.id
}

async function load() {
  loading.value = true
  try {
    const resp =
      activeTab.value === 'market'
        ? await listMarket(page.value, pageSize.value, keyword.value || undefined, sort.value)
        : await mySkills(page.value, pageSize.value)
    list.value = resp.list
    total.value = resp.total
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  page.value = 1
  load()
}

function onPage(p: number) {
  page.value = p
  load()
}

function onDownload(s: SkillOut) {
  downloadFile(
    `/b08/skills/${s.skill_code}/download`,
    undefined,
    `${s.name}.zip`,
  ).catch(() => {
    ElMessage.error('下载失败')
  })
}

async function onToggleStatus(s: SkillOut) {
  const next = s.status === '上架' ? '下架' : '上架'
  await setSkillStatus(s.skill_code, next)
  ElMessage.success(next === '上架' ? '已上架' : '已下架')
  load()
}

async function onDelete(s: SkillOut) {
  await ElMessageBox.confirm(`确认删除 skill「${s.name}」？删除后不可恢复。`, '提示', {
    type: 'warning',
  })
  await deleteSkill(s.skill_code)
  ElMessage.success('已删除')
  load()
}
</script>

<style scoped>
.market-card {
  border-radius: var(--el-border-radius-base);
}

.market-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.market-tabs {
  flex: 1;
}

.market-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kw {
  width: 260px;
}

.sort {
  width: 130px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 4px;
}

.skill-item {
  border-radius: var(--el-border-radius-base);
  border-color: var(--color-border);
  display: flex;
  flex-direction: column;
}

.skill-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.skill-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-intro {
  margin-top: 8px;
  min-height: 38px;
  font-size: 12px;
  color: var(--color-text-regular);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-meta {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.heat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.skill-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  border-top: 1px solid var(--color-border-strong);
  padding-top: 10px;
}

.tag-public {
  --el-tag-bg-color: #f0e8ff;
  --el-tag-border-color: #d9c7f5;
  --el-tag-text-color: #6a3fb5;
  border-radius: 10px;
}

.tag-private {
  --el-tag-bg-color: #eef1f5;
  --el-tag-border-color: #d7dee7;
  --el-tag-text-color: #8a96a3;
  border-radius: 10px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
