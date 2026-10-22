<template>
  <!-- 迁移过程记录抽屉：某库表的迁移历史 + 手工补录（需求 §5.2.5） -->
  <el-drawer
    v-model="visible"
    :title="item ? `迁移过程记录 — ${item.db_name}.${item.table_name}` : '迁移过程记录'"
    size="640px"
  >
    <div v-loading="loading" class="record-drawer">
      <el-table :data="list" border size="small" :show-overflow-tooltip="true">
        <el-table-column label="迁移类型" width="110">
          <template #default="{ row }">{{ row.migration_type }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="150">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="150">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="数据量" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.data_volume) }}</template>
        </el-table-column>
        <el-table-column label="方式" width="90">
          <template #default="{ row }">{{ row.method || '—' }}</template>
        </el-table-column>
        <el-table-column label="数据截止" width="110">
          <template #default="{ row }">{{ formatDate(row.data_cutoff_date) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <MigrationStatusTag v-if="row.status === '成功'" status="已完成" />
            <span v-else-if="row.status === '失败'" class="record-fail">失败</span>
            <span v-else class="record-partial">部分成功</span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="80">
          <template #default="{ row }">{{ row.created_by || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="remove(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无迁移记录" />

      <!-- 手工补录 -->
      <div class="add-form">
        <div class="add-title">补录迁移记录</div>
        <el-form :model="form" size="small" label-width="84px">
          <el-form-item label="迁移类型">
            <el-select v-model="form.migration_type" style="width: 100%">
              <el-option v-for="t in MIGRATION_TYPE_OPTIONS" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="form.started_at"
                type="datetime"
                placeholder="选择时间"
                value-format="YYYY-MM-DDTHH:mm:ss"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="form.finished_at"
                type="datetime"
                placeholder="选择时间"
                value-format="YYYY-MM-DDTHH:mm:ss"
                style="width: 100%"
              />
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="数据量">
              <el-input-number v-model="form.data_volume" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="迁移方式">
              <el-input v-model="form.method" placeholder="DistCp / DataX..." maxlength="64" />
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="数据截止">
              <el-date-picker
                v-model="form.data_cutoff_date"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option v-for="t in RECORD_STATUS_OPTIONS" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="1024" />
          </el-form-item>
          <div class="form-actions">
            <el-button size="small" type="primary" :loading="submitting" @click="add">添加记录</el-button>
          </div>
        </el-form>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MigrationStatusTag from '@/components/common/MigrationStatusTag.vue'
import { createRecord, deleteRecord, listRecords } from '@/api/data-migration'
import { formatDate, formatNumber, formatTime } from '@/utils/format'
import { MIGRATION_TYPE_OPTIONS, RECORD_STATUS_OPTIONS } from '@/types'
import type { MigrationRecordOut, TableItemOut } from '@/types'

const props = defineProps<{ modelValue: boolean; item?: TableItemOut | null }>()
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
const list = ref<MigrationRecordOut[]>([])
const submitting = ref(false)

const form = reactive({
  migration_type: '全量历史迁移',
  started_at: '',
  finished_at: '',
  data_volume: undefined as number | undefined,
  method: '',
  data_cutoff_date: '',
  status: '成功',
  remark: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (open && props.item) load()
  }
)

async function load() {
  if (!props.item) return
  loading.value = true
  try {
    const data = await listRecords(spaceId.value, props.item.id, 1, 50)
    list.value = data.list
  } finally {
    loading.value = false
  }
}

async function add() {
  if (!props.item) return
  submitting.value = true
  try {
    await createRecord(spaceId.value, props.item.id, {
      migration_type: form.migration_type,
      started_at: form.started_at || undefined,
      finished_at: form.finished_at || undefined,
      data_volume: form.data_volume,
      method: form.method || undefined,
      data_cutoff_date: form.data_cutoff_date || undefined,
      status: form.status,
      remark: form.remark || undefined,
    })
    ElMessage.success('记录已添加')
    await load()
    emit('changed')
  } finally {
    submitting.value = false
  }
}

async function remove(id: number) {
  await ElMessageBox.confirm('确认删除该迁移记录？', '删除确认', { type: 'warning' })
  await deleteRecord(spaceId.value, id)
  ElMessage.success('删除成功')
  await load()
  emit('changed')
}
</script>

<style scoped>
.record-drawer {
  padding: 0 16px 16px;
}

.record-fail {
  color: #c62828;
  font-size: 12px;
  font-weight: 600;
}

.record-partial {
  color: #b06a00;
  font-size: 12px;
  font-weight: 600;
}

.add-form {
  margin-top: 20px;
  padding: 14px 16px;
  background: var(--color-page-bg, #eef2f7);
  border-radius: 8px;
}

.add-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
