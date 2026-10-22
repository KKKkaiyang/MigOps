<template>
  <!-- 库表新增 / 编辑 -->
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑库表' : '新增库表'"
    width="520px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="源库名" prop="db_name">
        <el-input v-model="form.db_name" :disabled="isEdit" placeholder="如：ods" maxlength="128" />
      </el-form-item>
      <el-form-item label="源表名" prop="table_name">
        <el-input v-model="form.table_name" :disabled="isEdit" placeholder="如：ods_order_di" maxlength="128" />
      </el-form-item>
      <el-form-item label="目标库名">
        <el-input v-model="form.target_db_name" placeholder="如：ods" maxlength="128" />
      </el-form-item>
      <el-form-item label="目标表名">
        <el-input v-model="form.target_table_name" placeholder="如：ods_order_di" maxlength="128" />
      </el-form-item>
      <el-form-item label="表类型">
        <el-select v-model="form.table_type" placeholder="请选择" clearable style="width: 100%">
          <el-option v-for="t in TABLE_TYPE_OPTIONS" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="预估数据量">
        <el-input-number v-model="form.data_volume" :min="0" :step="10000" controls-position="right" style="width: 100%" />
      </el-form-item>
      <el-form-item label="分区数">
        <el-input-number v-model="form.partition_count" :min="0" :step="1" controls-position="right" style="width: 100%" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="1024" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createTableItem, updateTableItem } from '@/api/data-migration'
import { TABLE_TYPE_OPTIONS } from '@/types'
import type { TableItemOut } from '@/types'

const props = defineProps<{ modelValue: boolean; item?: TableItemOut | null; scenarioId: number }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.item)

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  db_name: '',
  table_name: '',
  target_db_name: '',
  target_table_name: '',
  table_type: '',
  data_volume: undefined as number | undefined,
  partition_count: undefined as number | undefined,
  remark: '',
})

const rules: FormRules = {
  db_name: [{ required: true, message: '请输入源库名', trigger: 'blur' }],
  table_name: [{ required: true, message: '请输入源表名', trigger: 'blur' }],
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  }
)

function reset() {
  const it = props.item
  form.db_name = it?.db_name ?? ''
  form.table_name = it?.table_name ?? ''
  form.target_db_name = it?.target_db_name ?? ''
  form.target_table_name = it?.target_table_name ?? ''
  form.table_type = it?.table_type ?? ''
  form.data_volume = it?.data_volume ?? undefined
  form.partition_count = it?.partition_count ?? undefined
  form.remark = it?.remark ?? ''
  formRef.value?.clearValidate()
}

async function submit() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const payload = {
        target_db_name: form.target_db_name || undefined,
        target_table_name: form.target_table_name || undefined,
        table_type: form.table_type || undefined,
        data_volume: form.data_volume,
        partition_count: form.partition_count,
        remark: form.remark || undefined,
      }
      if (isEdit.value && props.item) {
        await updateTableItem(spaceId.value, props.item.id, payload)
        ElMessage.success('更新成功')
      } else {
        await createTableItem(spaceId.value, props.scenarioId, {
          db_name: form.db_name,
          table_name: form.table_name,
          ...payload,
        })
        ElMessage.success('创建成功')
      }
      visible.value = false
      emit('success')
    } finally {
      submitting.value = false
    }
  })
}
</script>
