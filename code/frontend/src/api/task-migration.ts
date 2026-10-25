// 任务迁移管理（b04）接口封装
import http from './request'
import { downloadFile } from '@/utils/download'
import type {
  ImportResult,
  MigrationTemplateOut,
  MigrationTemplateUpsert,
  PageData,
  SavedViewOut,
  TaskListFilters,
  TaskNoteOut,
  TaskOut,
  TaskScenarioOut,
  TaskStatusIn,
  TaskTagBrief,
} from '@/types'

/** 任务迁移场景列表（含 task_count） */
export function listScenarios(spaceId: number) {
  return http<TaskScenarioOut[]>({
    url: '/b04/scenarios',
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 新建任务迁移场景 */
export function createScenario(spaceId: number, payload: { name: string; remark?: string }) {
  return http<{ id: number; name: string }>({
    url: '/b04/scenarios',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新任务迁移场景 */
export function updateScenario(
  spaceId: number,
  scenarioId: number,
  payload: { name?: string; remark?: string }
) {
  return http<null>({
    url: `/b04/scenarios/${scenarioId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除任务迁移场景（级联删除任务、备注与自定义视图） */
export function deleteScenario(spaceId: number, scenarioId: number) {
  return http<null>({
    url: `/b04/scenarios/${scenarioId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 任务标签读写（标签主表与 CRUD 见 @/api/tag，b06 标签管理模块） */
export function getTaskTags(spaceId: number, taskId: number) {
  return http<TaskTagBrief[]>({
    url: `/b04/tasks/${taskId}/tags`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

export function setTaskTags(spaceId: number, taskId: number, tagIds: number[]) {
  return http<TaskTagBrief[]>({
    url: `/b04/tasks/${taskId}/tags`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: { tag_ids: tagIds },
  })
}

export function batchTaskTags(
  spaceId: number,
  scenarioId: number,
  payload: { ids: number[]; tag_ids: number[]; action: 'add' | 'remove' }
) {
  return http<{ affected: number }>({
    url: `/b04/scenarios/${scenarioId}/tasks/batch-tags`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 筛选条件序列化：剔除空值，tag_ids 合并为逗号串，ext 转为 JSON 串 */
function serializeFilters(filters: TaskListFilters): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === '' || (Array.isArray(v) && v.length === 0)) continue
    if (k === 'tag_ids') params[k] = (v as number[]).join(',')
    else if (k === 'ext') params[k] = JSON.stringify(v)
    else params[k] = v
  }
  return params
}

/** 任务视图分页 */
export function listTasks(
  spaceId: number,
  scenarioId: number,
  page = 1,
  page_size = 20,
  filters: TaskListFilters = {}
) {
  const params: Record<string, unknown> = {
    space_id: spaceId,
    page,
    page_size,
    ...serializeFilters(filters),
  }
  return http<PageData<TaskOut>>({
    url: `/b04/scenarios/${scenarioId}/tasks`,
    method: 'GET',
    params,
  })
}

/** 空间级迁移模板：获取当前空间模板 */
export function getTemplate(spaceId: number) {
  return http<MigrationTemplateOut | null>({
    url: `/b04/spaces/${spaceId}/template`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 空间级迁移模板：保存（新建或覆盖同名） */
export function upsertTemplate(spaceId: number, payload: MigrationTemplateUpsert) {
  return http<MigrationTemplateOut>({
    url: `/b04/spaces/${spaceId}/template`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 空间级迁移模板：下载导入 Excel 模板（按当前模板字段生成） */
export function downloadTemplate(spaceId: number) {
  return downloadFile(`/b04/spaces/${spaceId}/template/import-excel`, undefined, '任务导入模板.xlsx')
}

/** 更新任务基础信息（含扩展字段 ext: f_n→值） */
export function updateTask(
  spaceId: number,
  taskId: number,
  payload: {
    project_name?: string
    workflow_name?: string
    task_name?: string
    env?: string
    business?: string
    task_type?: string
    migration_owner?: string
    active_status?: string
    migration_status?: string
    dualrun_status?: string
    check_status?: string
    acceptance_status?: string
    remark?: string
    ext?: Record<string, string>
  }
) {
  return http<null>({
    url: `/b04/tasks/${taskId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 单个任务 5 维状态独立更新（仅传需更新维度） */
export function updateTaskStatus(spaceId: number, taskId: number, payload: TaskStatusIn) {
  return http<null>({
    url: `/b04/tasks/${taskId}/status`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 批量任务状态流转（按维度整体更新，任一非法整体拒绝） */
export function batchUpdateTaskStatus(
  spaceId: number,
  scenarioId: number,
  payload: { ids: number[]; dimension: string; value: string }
) {
  return http<{ affected: number }>({
    url: `/b04/scenarios/${scenarioId}/tasks/batch-status`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 导入任务视图（mode: overwrite=覆盖; incremental=增量；须先配模板） */
export function importTasks(
  spaceId: number,
  scenarioId: number,
  file: File,
  mode: 'overwrite' | 'incremental' = 'overwrite'
) {
  const form = new FormData()
  form.append('file', file)
  return http<ImportResult>({
    url: `/b04/scenarios/${scenarioId}/tasks/import`,
    method: 'POST',
    params: { space_id: spaceId, mode },
    data: form,
    // 大批量导入（上限 5 万行）需要更长超时，避免默认 15s 被打断
    timeout: 300000,
  })
}

/** 排查备注时间线 */
export function listNotes(spaceId: number, taskId: number) {
  return http<TaskNoteOut[]>({
    url: `/b04/tasks/${taskId}/notes`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 按（项目名称 + 任务名称）查任务详情（D5：血缘任务名直达详情） */
export function getTaskByKey(spaceId: number, projectName: string, taskName: string) {
  return http<TaskOut>({
    url: '/b04/tasks/by-key',
    method: 'GET',
    params: { space_id: spaceId, project_name: projectName, task_name: taskName },
  })
}

/** 添加排查备注 */
export function createNote(
  spaceId: number,
  taskId: number,
  payload: {
    note_kind: string
    problem_desc?: string
    cause_analysis?: string
    fix_plan?: string
  }
) {
  return http<TaskNoteOut>({
    url: `/b04/tasks/${taskId}/notes`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 自定义视图列表（含 task_count） */
export function listSavedViews(spaceId: number, scenarioId: number) {
  return http<SavedViewOut[]>({
    url: `/b04/scenarios/${scenarioId}/saved-views`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 自定义视图详情 */
export function getSavedView(spaceId: number, viewId: number) {
  return http<SavedViewOut>({
    url: `/b04/saved-views/${viewId}`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 保存筛选条件为自定义视图（含视图模式）或勾选任务创建固化视图 */
export function createSavedView(
  spaceId: number,
  scenarioId: number,
  payload: {
    name: string
    description?: string
    filter_config?: Record<string, unknown>
    view_mode?: 'dynamic' | 'fixed'
    /** R3：勾选任务创建视图，直接固化为成员（与 filter_config 互斥） */
    member_ids?: number[]
  }
) {
  return http<{ id: number; name: string }>({
    url: `/b04/scenarios/${scenarioId}/saved-views`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新自定义视图 */
export function updateSavedView(
  spaceId: number,
  viewId: number,
  payload: {
    name?: string
    description?: string
    filter_config?: Record<string, unknown>
    view_mode?: 'dynamic' | 'fixed'
  }
) {
  return http<null>({
    url: `/b04/saved-views/${viewId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除自定义视图（仅删视图） */
export function deleteSavedView(spaceId: number, viewId: number) {
  return http<null>({
    url: `/b04/saved-views/${viewId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 自定义视图数据（引用原任务），支持视图内再筛选（R2/D4） */
export function listSavedViewTasks(
  spaceId: number,
  viewId: number,
  page = 1,
  page_size = 20,
  filters: TaskListFilters = {}
) {
  const params: Record<string, unknown> = {
    space_id: spaceId,
    page,
    page_size,
    ...serializeFilters(filters),
  }
  return http<PageData<TaskOut>>({
    url: `/b04/saved-views/${viewId}/tasks`,
    method: 'GET',
    params,
  })
}

/** R4：从视图移除任务（批量）→ 视图强制转固化并锁定剩余成员 */
export function removeSavedViewMembers(spaceId: number, viewId: number, taskIds: number[]) {
  return http<null>({
    url: `/b04/saved-views/${viewId}/remove-members`,
    method: 'POST',
    params: { space_id: spaceId },
    data: { task_ids: taskIds },
  })
}

/** 补充需求：向视图补充新增任务（批量）→ 动态引用视图自动固化为成员集合 */
export function addSavedViewMembers(spaceId: number, viewId: number, taskIds: number[]) {
  return http<null>({
    url: `/b04/saved-views/${viewId}/add-members`,
    method: 'POST',
    params: { space_id: spaceId },
    data: { task_ids: taskIds },
  })
}
