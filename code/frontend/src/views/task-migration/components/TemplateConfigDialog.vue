<template>
  <!-- 空间级迁移模板配置（D4/D5/D6 + B04-07 拖动排序）：
       基础+扩展字段统一列表，拖动 ⠿ 手柄整行上下移动，顺序决定查询列表列与导入模板列顺序 -->
  <el-dialog
    v-model="visible"
    title="配置字段模板"
    width="720px"
    top="5vh"
    :close-on-click-modal="false"
  >
    <div v-loading="loading" class="tpl-config">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="tip"
        title="模板决定导入列、列表展示列与必填约束；9 个基础字段为锁定必填，不可取消（数据校验结果由校验结果导入自动刷新，列表展示默认关闭）。拖动行首 ⠿ 手柄可调整字段顺序，查询列表与导入模板的列顺序随模板顺序变化。"
      />

      <el-form :model="form" label-width="84px" class="name-form">
        <el-form-item label="模板名称">
          <el-input v-model="form.name" placeholder="如：默认迁移模板" maxlength="128" />
        </el-form-item>
      </el-form>

      <!-- 统一字段列表（基础 + 扩展，可拖动排序） -->
      <div class="section-title ext-head">
        <span>字段顺序（共 {{ rows.length }} 项）</span>
        <el-button size="small" type="primary" plain @click="addExt">+ 添加扩展字段</el-button>
      </div>
      <div class="field-list">
        <div
          v-for="(row, i) in rows"
          :key="row.field_key"
          class="field-row"
          :class="{ dragging: dragIndex === i, over: overIndex === i && dragIndex !== i }"
          draggable="true"
          @dragstart="onDragStart(i, $event)"
          @dragover.stop="onDragOver(i, $event)"
          @drop.stop="onDrop(i, $event)"
          @dragend="onDragEnd"
        >
          <span class="drag-handle" title="拖动排序">⠿</span>
          <span class="field-name" :title="row.field_label">{{ row.field_label }}</span>
          <el-tag size="small" :type="row.field_source === 'base' ? 'primary' : 'warning'" effect="light">
            {{ row.field_source === 'base' ? '基础' : '扩展' }}
          </el-tag>
          <span class="row-actions">
            <el-checkbox v-model="row.is_required" :disabled="row.locked">必选</el-checkbox>
            <el-checkbox v-model="row.display_in_list">列表展示</el-checkbox>
            <el-button v-if="row.field_source === 'extension'" size="small" type="danger" text @click="removeRow(i)">
              删除
            </el-button>
          </span>
        </div>
      </div>

      <!-- 扩展字段明细（枚举候选项） -->
      <div v-for="(ext, i) in extRows" :key="ext.field_key" class="ext-card">
        <div class="ext-row">
          <span class="ext-title">{{ ext.field_label }}</span>
          <el-select v-model="ext.ext_type" placeholder="类型" style="width: 120px" @change="onExtTypeChange(ext)">
            <el-option label="文本" value="string" />
            <el-option label="枚举" value="enum" />
          </el-select>
          <el-checkbox v-model="ext.is_required">必选</el-checkbox>
          <el-checkbox v-model="ext.display_in_list">列表展示</el-checkbox>
        </div>
        <div v-if="ext.ext_type === 'enum'" class="enum-editor">
          <div class="enum-title">枚举候选项</div>
          <div v-for="(opt, oi) in ext.enum_options" :key="oi" class="enum-row">
            <el-input v-model="opt.code" placeholder="取值编码" style="width: 160px" />
            <el-input v-model="opt.label" placeholder="展示名" style="width: 160px" />
            <el-button size="small" text type="danger" @click="ext.enum_options.splice(oi, 1)">删除</el-button>
          </div>
          <el-button size="small" link type="primary" @click="ext.enum_options.push({ code: '', label: '' })">
            + 添加候选项
          </el-button>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存模板</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTemplate, upsertTemplate } from '@/api/task-migration'
import { BASE_FIELD_LABELS, REQUIRED_BASE_FIELDS } from '@/utils/task-status'
import type { MigrationTemplateField } from '@/types'

const props = defineProps<{ modelValue: boolean; spaceId: number }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const saving = ref(false)
const form = reactive<{ name: string }>({ name: '默认迁移模板' })

/** 统一字段行（基础 + 扩展混排，B04-07） */
interface FieldRow {
  field_key: string
  field_label: string
  field_source: 'base' | 'extension'
  is_required: boolean
  /** 锁定必选：不可取消（9 项基础字段） */
  locked: boolean
  display_in_list: boolean
  ext_type: 'enum' | 'string'
  enum_options: { code: string; label: string }[]
}
const rows = ref<FieldRow[]>([])

/** 加载时的扩展字段 key 序列（用于检测相对顺序变化 → f_n 重映射提示） */
const extKeysBefore = ref<string[]>([])

const extRows = computed(() => rows.value.filter((r) => r.field_source === 'extension'))

// ── 拖动排序（原生 HTML5 drag，不引入额外依赖） ──
const dragIndex = ref<number | null>(null)
const overIndex = ref<number | null>(null)

function onDragStart(index: number, e: DragEvent) {
  dragIndex.value = index
  overIndex.value = null
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(index: number, e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  overIndex.value = index
}

function onDrop(toIndex: number, e: DragEvent) {
  e.preventDefault()
  const from = dragIndex.value
  if (from === null || from === toIndex) {
    clearDrag()
    return
  }
  const [item] = rows.value.splice(from, 1)
  rows.value.splice(toIndex, 0, item)
  clearDrag()
}

function onDragEnd() {
  clearDrag()
}

function clearDrag() {
  dragIndex.value = null
  overIndex.value = null
}

// ── 加载 / 保存 ──
function toRow(f: MigrationTemplateField): FieldRow {
  const base = f.field_source === 'base'
  return {
    field_key: f.field_key,
    field_label: f.field_label,
    field_source: base ? 'base' : 'extension',
    is_required: !!f.is_required,
    locked: base && REQUIRED_BASE_FIELDS.includes(f.field_key),
    display_in_list: !!f.display_in_list,
    ext_type: (f.ext_type as 'enum' | 'string') || 'string',
    enum_options: (f.enum_options ?? []).map((o) => ({ code: o.code, label: o.label })),
  }
}

async function load() {
  loading.value = true
  try {
    const tpl = await getTemplate(props.spaceId)
    const loaded: FieldRow[] = []
    if (tpl) {
      form.name = tpl.name
      // 按模板已保存的顺序构建统一列表
      for (const f of tpl.config_json.fields ?? []) loaded.push(toRow(f))
      // 补齐缺失的基础字段（存量模板兼容，如缺 check_result）
      const have = new Set(loaded.map((r) => r.field_key))
      for (const [key, label] of Object.entries(BASE_FIELD_LABELS)) {
        if (key === 'task_uri' || have.has(key)) continue
        loaded.push({
          field_key: key,
          field_label: label,
          field_source: 'base',
          is_required: REQUIRED_BASE_FIELDS.includes(key),
          locked: REQUIRED_BASE_FIELDS.includes(key),
          // 数据校验结果默认不展示（需求：列表显示默认：否）
          display_in_list: key !== 'check_result',
          ext_type: 'string',
          enum_options: [],
        })
      }
    } else {
      // 无模板：按默认顺序初始化
      for (const [key, label] of Object.entries(BASE_FIELD_LABELS)) {
        if (key === 'task_uri') continue
        loaded.push({
          field_key: key,
          field_label: label,
          field_source: 'base',
          is_required: REQUIRED_BASE_FIELDS.includes(key),
          locked: REQUIRED_BASE_FIELDS.includes(key),
          display_in_list: key !== 'check_result',
          ext_type: 'string',
          enum_options: [],
        })
      }
    }
    rows.value = loaded
    extKeysBefore.value = loaded.filter((r) => r.field_source === 'extension').map((r) => r.field_key)
  } finally {
    loading.value = false
  }
}

function addExt() {
  const used = rows.value
    .filter((r) => r.field_source === 'extension')
    .map((r) => Number(r.field_key.replace(/^\D+/, '')) || 0)
  const next = (used.length ? Math.max(...used) : 0) + 1
  rows.value.push({
    field_key: `ext_${next}`,
    field_label: `扩展字段${next}`,
    field_source: 'extension',
    is_required: false,
    locked: false,
    display_in_list: true,
    ext_type: 'string',
    enum_options: [],
  })
}

function removeRow(i: number) {
  rows.value.splice(i, 1)
}

function onExtTypeChange(ext: FieldRow) {
  if (ext.ext_type === 'enum' && !ext.enum_options.length) {
    ext.enum_options = [{ code: '', label: '' }]
  }
}

function buildConfig(): { fields: MigrationTemplateField[] } {
  return {
    fields: rows.value.map((r, i) => ({
      field_key: r.field_key,
      field_label: r.field_label,
      field_source: r.field_source,
      is_required: r.is_required,
      display_in_list: r.display_in_list,
      order: i + 1,
      ext_type: r.field_source === 'extension' ? r.ext_type : null,
      enum_options:
        r.field_source === 'extension' && r.ext_type === 'enum'
          ? r.enum_options.map((o) => ({ code: o.code, label: o.label }))
          : null,
    })),
  }
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }
  // 校验：9 个锁定必填不可取消
  const missing = rows.value.filter((r) => r.locked && !r.is_required)
  if (missing.length) {
    ElMessage.warning(`以下必填字段不可取消：${missing.map((m) => m.field_label).join('、')}`)
    return
  }
  // B04-07：已有扩展字段相对顺序变化 → f_n 物理列重映射，需提示确认
  const afterSeq = rows.value.filter((r) => r.field_source === 'extension').map((r) => r.field_key)
  const beforeInAfter = afterSeq.filter((k) => extKeysBefore.value.includes(k))
  if (beforeInAfter.join(',') !== extKeysBefore.value.join(',')) {
    try {
      await ElMessageBox.confirm(
        '扩展字段顺序变化将改变扩展列（f_n）映射，已有扩展数据将按新顺序展示，确定保存？',
        '扩展字段顺序变化',
        { type: 'warning' }
      )
    } catch {
      return
    }
  }
  saving.value = true
  try {
    await upsertTemplate(props.spaceId, { name: form.name.trim(), config_json: buildConfig() })
    ElMessage.success('模板已保存')
    visible.value = false
    emit('saved')
  } finally {
    saving.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) load()
  }
)
</script>

<style scoped>
.tpl-config {
  padding: 0 4px;
}

.tip {
  margin-bottom: 12px;
}

.name-form {
  margin-bottom: 4px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 14px 0 8px;
}

.ext-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-list {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  font-size: 13px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
  cursor: grab;
}

.field-row:last-child {
  border-bottom: none;
}

.field-row:hover {
  background: var(--el-color-primary-light-9);
}

.field-row.dragging {
  opacity: 0.5;
}

.field-row.over {
  box-shadow: inset 0 2px 0 var(--color-primary);
}

.drag-handle {
  color: var(--color-text-muted);
  cursor: grab;
  flex-shrink: 0;
  user-select: none;
}

.field-name {
  min-width: 90px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary);
}

.row-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.ext-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 10px;
}

.ext-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ext-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  min-width: 90px;
}

.enum-editor {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--color-page-bg, #eef2f7);
  border-radius: 6px;
}

.enum-title {
  font-size: 12px;
  color: var(--color-text-regular);
  margin-bottom: 6px;
}

.enum-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
</style>
