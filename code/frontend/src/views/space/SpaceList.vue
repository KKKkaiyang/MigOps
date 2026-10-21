<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>项目空间管理</span>
        <el-button type="primary" @click="openCreate">新建空间</el-button>
      </div>
    </template>

    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="按项目名称搜索"
        style="width: 240px"
        @keyup.enter="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border style="margin-top: 12px">
      <el-table-column prop="space_code" label="空间编码" width="140" />
      <el-table-column prop="space_name" label="项目名称" />
      <el-table-column prop="customer_name" label="客户" />
      <el-table-column prop="source_platform" label="源端" width="110" />
      <el-table-column prop="target_platform" label="目标端" width="110" />
      <el-table-column prop="owner" label="负责人" width="110" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>

    <el-pagination
      class="pager"
      layout="total, prev, pager, next"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @current-change="onPage"
    />

    <el-dialog v-model="dialogVisible" title="新建空间" width="480px">
      <el-form :model="form" label-width="88px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.space_name" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="form.customer_name" />
        </el-form-item>
        <el-form-item label="源端平台">
          <el-input v-model="form.source_platform" placeholder="华为云/阿里云/私有云/火山云" />
        </el-form-item>
        <el-form-item label="目标平台">
          <el-input v-model="form.target_platform" placeholder="腾讯云/AWS/Azure" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.owner" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listSpaces,
  createSpace,
  type SpaceOut,
  type PageData,
} from '@/api/space'

const list = ref<SpaceOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = ref({
  space_name: '',
  customer_name: '',
  source_platform: '',
  target_platform: '',
  owner: '',
})

async function load() {
  loading.value = true
  try {
    const data = await listSpaces(page.value, pageSize.value, keyword.value || undefined)
    list.value = (data as unknown as PageData<SpaceOut>).list
    total.value = (data as unknown as PageData<SpaceOut>).total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  load()
}

function openCreate() {
  form.value = {
    space_name: '',
    customer_name: '',
    source_platform: '',
    target_platform: '',
    owner: '',
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.space_name) {
    ElMessage.warning('请填写项目名称')
    return
  }
  submitting.value = true
  try {
    await createSpace(form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
.toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
.pager { margin-top: 12px; justify-content: flex-end; }
</style>
