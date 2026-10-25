<template>
  <div class="api-keys">
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span class="title">API 密钥（ak/sk）</span>
          <el-button type="primary" :icon="Key" @click="onCreate">生成密钥</el-button>
        </div>
      </template>

      <el-alert type="warning" :closable="false" show-icon class="tip">
        <template #title>
          API 密钥（ak/sk）用于以签名方式调用平台 REST API，完成台账刷新、数据校验结果回写、skill 上传等自动化操作。
        </template>
        密钥 secret_key 仅在生成时展示一次，请立即复制并妥善保存；遗失后须吊销旧密钥并重新生成，无法再次查看。
      </el-alert>

      <el-table :data="list" border stripe v-loading="loading" class="tbl">
        <el-table-column prop="access_key" label="AccessKey" min-width="200">
          <template #default="{ row }">
            <span class="mono">{{ row.access_key }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '启用' ? 'success' : 'info'" size="small" effect="light">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_used_at" label="最近使用" width="170" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <el-button
              link
              :type="row.status === '启用' ? 'warning' : 'success'"
              @click="onToggle(row as ApiKeyOut)"
            >
              {{ row.status === '启用' ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click="onRevoke(row as ApiKeyOut)">吊销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !list.length" description="尚未生成 API 密钥" />
    </el-card>

    <!-- 生成成功：一次性展示 secret_key -->
    <el-dialog v-model="secretVisible" title="密钥已生成" width="520px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" show-icon>
        <template #title>secret_key 仅展示一次，请立即复制保存，关闭后无法再次查看。</template>
      </el-alert>
      <div class="secret-block">
        <div class="secret-row">
          <span class="label">access_key</span>
          <code class="mono">{{ created?.access_key }}</code>
          <el-button link type="primary" @click="copy(created?.access_key)">复制</el-button>
        </div>
        <div class="secret-row">
          <span class="label">secret_key</span>
          <code class="mono break">{{ created?.secret_key }}</code>
          <el-button link type="primary" @click="copy(created?.secret_key)">复制</el-button>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="secretVisible = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Key } from '@element-plus/icons-vue'
import { createApiKey, listApiKeys, revokeApiKey, toggleApiKey } from '@/api/apikey'
import type { ApiKeyCreated, ApiKeyOut } from '@/types'

const list = ref<ApiKeyOut[]>([])
const loading = ref(false)
const secretVisible = ref(false)
const created = ref<ApiKeyCreated | null>(null)

onMounted(load)

async function load() {
  loading.value = true
  try {
    list.value = await listApiKeys()
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  const data = await createApiKey()
  created.value = data
  secretVisible.value = true
  load()
}

async function onToggle(row: ApiKeyOut) {
  await toggleApiKey(row.id)
  ElMessage.success('状态已更新')
  load()
}

async function onRevoke(row: ApiKeyOut) {
  await ElMessageBox.confirm('吊销后该密钥立即失效，且不可恢复。', '确认吊销', {
    type: 'warning',
  })
  await revokeApiKey(row.id)
  ElMessage.success('已吊销')
  load()
}

async function copy(text?: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择')
  }
}
</script>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.tip {
  margin-bottom: 14px;
}

.tbl {
  margin-top: 4px;
}

.mono {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 12px;
}

.secret-block {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.secret-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.secret-row .label {
  width: 92px;
  color: var(--color-text-regular);
  font-size: 13px;
}

.secret-row code {
  flex: 1;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 4px 8px;
}

.secret-row code.break {
  word-break: break-all;
}
</style>
