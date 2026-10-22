// 任务迁移管理（b04）接口封装
import http from './request'
import type {
  ImportResult,
  PageData,
  SavedViewOut,
  TaskNoteOut,
  TaskOut,
  TaskScenarioOut,
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

/** 删除任务迁移场景（级联删除任务、备注与自定义台账） */
export function deleteScenario(spaceId: number, scenarioId: number) {
  return http<null>({
    url: `/b04/scenarios/${scenarioId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 任务台账分页 */
export function listTasks(
  spaceId: number,
  scenarioId: number,
  page = 1,
  page_size = 20,
  filters: {
    keyword?: string
    workflow_name?: string
    migration_status?: string
    schedule_status?: string
    check_status?: string
    owner?: string
  } = {}
) {
  return http<PageData<TaskOut>>({
    url: `/b04/scenarios/${scenarioId}/tasks`,
    method: 'GET',
    params: { space_id: spaceId, page, page_size, ...filters },
  })
}

/** 更新任务基础信息 */
export function updateTask(
  spaceId: number,
  taskId: number,
  payload: {
    script_name?: string
    owner?: string
    schedule_status?: string
    check_status?: string
    input_tables?: string
    output_tables?: string
  }
) {
  return http<null>({
    url: `/b04/tasks/${taskId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 单个任务状态流转（须符合状态机） */
export function updateTaskStatus(spaceId: number, taskId: number, status: string) {
  return http<null>({
    url: `/b04/tasks/${taskId}/status`,
    method: 'POST',
    params: { space_id: spaceId },
    data: { status },
  })
}

/** 批量任务状态流转（任一非法整体拒绝） */
export function batchUpdateTaskStatus(
  spaceId: number,
  scenarioId: number,
  payload: { ids: number[]; status: string }
) {
  return http<{ affected: number }>({
    url: `/b04/scenarios/${scenarioId}/tasks/batch-status`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 导入任务台账（mode: overwrite=覆盖; incremental=增量） */
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

/** 自定义台账列表（含 task_count） */
export function listSavedViews(spaceId: number, scenarioId: number) {
  return http<SavedViewOut[]>({
    url: `/b04/scenarios/${scenarioId}/saved-views`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 自定义台账详情 */
export function getSavedView(spaceId: number, viewId: number) {
  return http<SavedViewOut>({
    url: `/b04/saved-views/${viewId}`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 保存筛选条件为自定义台账 */
export function createSavedView(
  spaceId: number,
  scenarioId: number,
  payload: { name: string; description?: string; filter_config: Record<string, string> }
) {
  return http<{ id: number; name: string }>({
    url: `/b04/scenarios/${scenarioId}/saved-views`,
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新自定义台账 */
export function updateSavedView(
  spaceId: number,
  viewId: number,
  payload: { name?: string; description?: string; filter_config?: Record<string, string> }
) {
  return http<null>({
    url: `/b04/saved-views/${viewId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除自定义台账（仅删视图） */
export function deleteSavedView(spaceId: number, viewId: number) {
  return http<null>({
    url: `/b04/saved-views/${viewId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 自定义台账数据（引用原任务） */
export function listSavedViewTasks(
  spaceId: number,
  viewId: number,
  page = 1,
  page_size = 20
) {
  return http<PageData<TaskOut>>({
    url: `/b04/saved-views/${viewId}/tasks`,
    method: 'GET',
    params: { space_id: spaceId, page, page_size },
  })
}
