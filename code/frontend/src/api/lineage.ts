// 血缘管理（b07）接口封装
import http from './request'
import type {
  LineageByTaskOut,
  LineageImportPayload,
  LineageOut,
  LineageParsedEdge,
  LineageWorkflowOptions,
  LineageWorkflowOut,
} from '@/types'

/** 血缘边列表（含筛选） */
export function listLineages(
  spaceId: number,
  filters: { workflow?: string; keyword?: string; table_type?: string } = {}
) {
  const params: Record<string, unknown> = { space_id: spaceId }
  if (filters.workflow) params.workflow = filters.workflow
  if (filters.keyword) params.keyword = filters.keyword
  if (filters.table_type) params.table_type = filters.table_type
  return http<LineageOut[]>({
    url: '/b07/lineages',
    method: 'GET',
    params,
  })
}

/** 解析脚本为血缘边预览（不落库） */
export function parseLineage(spaceId: number, payload: { code?: string; lang?: string }) {
  return http<LineageParsedEdge[]>({
    url: '/b07/lineages/parse',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 按工作流入库（add=新增; rebuild=重建覆盖） */
export function importLineage(spaceId: number, payload: LineageImportPayload) {
  return http<{ mode: string; workflow: string; inserted: number; parsed: number; dropped: number }>({
    url: '/b07/lineages/import',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 工作流聚合列表 */
export function listWorkflows(spaceId: number) {
  return http<LineageWorkflowOut[]>({
    url: '/b07/lineages/workflows',
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 某工作流可选项（重建预填） */
export function getWorkflowOptions(spaceId: number, workflow: string) {
  return http<LineageWorkflowOptions>({
    url: `/b07/lineages/workflows/${encodeURIComponent(workflow)}/options`,
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 按（数仓项目空间 + 任务名称）聚合输入/输出表清单（去重，跨工作流合并），用于任务详情关联血缘展示（D5/D6） */
export function getLineageByTask(spaceId: number, dwProjectSpace: string, taskName: string) {
  return http<LineageByTaskOut>({
    url: '/b07/lineages/by-task',
    method: 'GET',
    params: { space_id: spaceId, dw_project_space: dwProjectSpace, task_name: taskName },
  })
}

/** 逻辑删除单条血缘边 */
export function deleteLineage(spaceId: number, id: number) {
  return http<null>({
    url: `/b07/lineages/${id}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 批量逻辑删除某工作流的全部血缘边 */
export function deleteWorkflow(spaceId: number, workflow: string) {
  return http<{ workflow: string; deleted: number }>({
    url: `/b07/lineages/workflows/${encodeURIComponent(workflow)}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}
