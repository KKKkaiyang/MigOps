// 空间级迁移模板 composable：拉取模板并派生出列表列、扩展字段取值等（需求 D4/D5）。
import { computed, ref } from 'vue'
import { getTemplate } from '@/api/task-migration'
import type {
  MigrationTemplateField,
  MigrationTemplateOut,
  StatusDimensionKey,
  TaskOut,
} from '@/types'

const STATUS_KEYS: StatusDimensionKey[] = [
  'active_status',
  'migration_status',
  'dualrun_status',
  'check_status',
  'acceptance_status',
]

/** 扩展字段在模板中的顺序位置（按 order 升序）→ 物理列名 f_{idx+1} */
export function useTemplate(spaceId: number) {
  const template = ref<MigrationTemplateOut | null>(null)
  const loading = ref(false)

  async function load(force = false) {
    if (template.value && !force) return
    loading.value = true
    try {
      template.value = await getTemplate(spaceId)
    } finally {
      loading.value = false
    }
  }

  /** 按 order 升序排好的扩展字段（用于位置 → f_n 映射） */
  const orderedExtFields = computed<MigrationTemplateField[]>(() => {
    const fields = template.value?.config_json.fields ?? []
    return fields
      .filter((f) => f.field_source === 'extension')
      .sort((a, b) => a.order - b.order)
  })

  /** 某扩展字段对应的物理列名 f_n */
  function extColumnForField(field: MigrationTemplateField): string {
    const idx = orderedExtFields.value.indexOf(field)
    return `f_${idx + 1}`
  }

  /** 列表展示字段（display_in_list 且非任务名称；任务名称由首列固定渲染） */
  const listFields = computed<MigrationTemplateField[]>(() => {
    const fields = template.value?.config_json.fields ?? []
    return fields
      .filter((f) => f.display_in_list && f.field_key !== 'task_name')
      .sort((a, b) => a.order - b.order)
  })

  /** 单元格取值：基础字段取 row[field_key]；扩展字段取 row.ext[f_n] */
  function cellValue(row: TaskOut, field: MigrationTemplateField): string {
    if (field.field_source === 'extension') {
      const col = extColumnForField(field)
      return (row.ext && row.ext[col]) || ''
    }
    const v = (row as unknown as Record<string, unknown>)[field.field_key]
    return v == null ? '' : String(v)
  }

  function isStatusField(field: MigrationTemplateField): boolean {
    return STATUS_KEYS.includes(field.field_key as StatusDimensionKey)
  }

  return {
    template,
    loading,
    load,
    orderedExtFields,
    listFields,
    cellValue,
    isStatusField,
    extColumnForField,
  }
}
