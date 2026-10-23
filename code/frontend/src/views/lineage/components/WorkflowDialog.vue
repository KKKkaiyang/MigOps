<template>
  <el-dialog
    v-model="visible"
    :title="mode === 'rebuild' ? '重建工作流血缘' : '新增工作流血缘'"
    width="560px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <el-form label-width="92px">
      <el-form-item label="模式">
        <el-radio-group v-model="mode">
          <el-radio value="add">新增（追加）</el-radio>
          <el-radio value="rebuild">重建（覆盖）</el-radio>
        </el-radio-group>
        <div class="hint">重建将逻辑删除该工作流旧血缘后重新入库。</div>
      </el-form-item>
      <el-form-item label="工作流名称" required>
        <el-input v-model="workflow" placeholder="如 hr_dw_etl" />
      </el-form-item>
      <el-form-item label="任务名">
        <el-input v-model="task" placeholder="可选" />
      </el-form-item>
      <el-form-item label="任务类型">
        <el-input v-model="taskType" placeholder="可选，如 SQL / PySpark" list="wf-task-type" />
        <datalist id="wf-task-type">
          <option v-for="t in optionTasks.task_types" :key="t" :value="t" />
        </datalist>
      </el-form-item>
      <el-form-item label="项目">
        <el-input v-model="project" list="wf-project" />
        <datalist id="wf-project">
          <option v-for="p in optionTasks.projects" :key="p" :value="p" />
        </datalist>
      </el-form-item>
      <el-form-item label="脚本名称">
        <el-input v-model="scriptName" list="wf-script" />
        <datalist id="wf-script">
          <option v-for="s in optionTasks.scripts" :key="s" :value="s" />
        </datalist>
      </el-form-item>
      <el-form-item label="默认库名">
        <el-input v-model="defaultDb" placeholder="为无库名的正式表自动补前缀，如 hr_prd" />
      </el-form-item>
      <el-form-item label="脚本">
        <el-input
          v-model="code"
          type="textarea"
          :rows="6"
          placeholder="粘贴 SQL 或 PySpark 脚本；或下方上传文件"
        />
        <div class="upload-row">
          <input type="file" accept=".sql,.py,.txt" @change="onFile" />
          <el-button size="small" :loading="parsing" @click="preview">解析预览</el-button>
        </div>
      </el-form-item>
      <el-form-item v-if="previewEdges" label="解析预览">
        <div class="preview">
          <div v-if="!previewEdges.length" class="muted">未解析到血缘边，请检查脚本。</div>
          <div v-for="(e, i) in previewEdges.slice(0, 50)" :key="i" class="preview-row">
            <span class="mono">{{ e.source }}</span>
            <span class="arrow">→</span>
            <span class="mono">{{ e.target }}</span>
            <span class="muted">{{ e.sourceType }}/{{ e.targetType }}</span>
          </div>
          <div v-if="previewEdges.length > 50" class="muted">… 共 {{ previewEdges.length }} 条</div>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!workflow || !code" @click="submit">
        入库
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorkflowOptions, importLineage, parseLineage } from '@/api/lineage'
import type { LineageParsedEdge, LineageWorkflowOptions } from '@/types'

const props = defineProps<{
  modelValue: boolean
  spaceId: number
  mode: 'add' | 'rebuild'
  defaultWorkflow?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const mode = ref<'add' | 'rebuild'>(props.mode)
const workflow = ref('')
const task = ref('')
const taskType = ref('')
const project = ref('')
const scriptName = ref('')
const defaultDb = ref('')
const code = ref('')
const parsing = ref(false)
const submitting = ref(false)
const previewEdges = ref<LineageParsedEdge[] | null>(null)
const optionTasks = ref<LineageWorkflowOptions>({ workflow: '', tasks: [], scripts: [], task_types: [], projects: [] })

watch(
  () => props.mode,
  (m) => {
    mode.value = m
  }
)

function onOpen() {
  if (props.defaultWorkflow) workflow.value = props.defaultWorkflow
  loadOptions()
}

async function loadOptions() {
  if (mode.value !== 'rebuild' || !workflow.value) return
  try {
    optionTasks.value = await getWorkflowOptions(props.spaceId, workflow.value)
    if (!taskType.value && optionTasks.value.task_types[0]) taskType.value = optionTasks.value.task_types[0]
    if (!project.value && optionTasks.value.projects[0]) project.value = optionTasks.value.projects[0]
    if (!scriptName.value && optionTasks.value.scripts[0]) scriptName.value = optionTasks.value.scripts[0]
  } catch {
    /* 无历史选项则忽略 */
  }
}

function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    code.value = String(reader.result || '')
  }
  reader.readAsText(file)
}

async function preview() {
  if (!code.value.trim()) {
    ElMessage.warning('请先粘贴或上传脚本')
    return
  }
  parsing.value = true
  try {
    previewEdges.value = await parseLineage(props.spaceId, { code: code.value })
  } finally {
    parsing.value = false
  }
}

async function submit() {
  if (!workflow.value || !code.value.trim()) {
    ElMessage.warning('工作流名称与脚本均不能为空')
    return
  }
  submitting.value = true
  try {
    const res = await importLineage(props.spaceId, {
      workflow: workflow.value,
      task: task.value || undefined,
      task_type: taskType.value || undefined,
      project: project.value || undefined,
      script_name: scriptName.value || undefined,
      mode: mode.value,
      default_db: defaultDb.value || undefined,
      code: code.value,
    })
    ElMessage.success(
      `已${mode.value === 'rebuild' ? '重建' : '新增'}工作流「${workflow.value}」，写入 ${res.inserted} 条血缘边`
    )
    visible.value = false
    emit('success')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.hint {
  font-size: 11px;
  color: var(--color-text-muted, #8a96a3);
  margin-top: 4px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.preview {
  max-height: 200px;
  overflow: auto;
  background: #f3f6fb;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
}
.preview-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.arrow {
  color: #1a73e8;
}
.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  word-break: break-all;
}
.muted {
  color: var(--color-text-muted, #9aa7b5);
}
</style>
