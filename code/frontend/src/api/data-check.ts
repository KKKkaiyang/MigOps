// 数据校验管理（b05）接口封装
import http from './request'
import { downloadFile } from '@/utils/download'
import type { CheckImportResult, CheckOverviewOut, CheckResultsByTables, CheckTemplate, PageData } from '@/types'

/** 数据校验列表（数据迁移清单全部库表 + 最新/近7天校验结果） */
export function listChecks(
  spaceId: number,
  page = 1,
  page_size = 20,
  filters: { keyword?: string; result?: string; scenario_id?: number } = {}
) {
  return http<PageData<CheckOverviewOut>>({
    url: '/b05/checks',
    method: 'GET',
    params: { space_id: spaceId, page, page_size, ...filters },
  })
}

/** 导入数据校验结果（xls/csv/xlsx），按所选数据日期批量落库并刷新任务校验结果 */
export function importCheckResults(
  spaceId: number,
  file: File,
  dataDate: string,
  template: CheckTemplate,
  scenarioId?: number
) {
  const form = new FormData()
  form.append('file', file)
  return http<CheckImportResult>({
    url: '/b05/checks/import',
    method: 'POST',
    params: {
      space_id: spaceId,
      data_date: dataDate,
      template,
      ...(scenarioId ? { scenario_id: scenarioId } : {}),
    },
    data: form,
    // 大批量导入（上限 5 万行）需要更长超时，避免默认 15s 被打断
    timeout: 300000,
  })
}

/** 下载校验结果导入模板 */
export function downloadCheckTemplate(spaceId: number, template: CheckTemplate) {
  return downloadFile(
    '/b05/checks/import-template',
    { space_id: spaceId, template },
    '数据校验结果导入模板.xlsx'
  )
}

/** 全空间重跑任务级数据校验结果刷新（B05-04：刷新任务状态按钮） */
export function refreshChecks(spaceId: number) {
  return http<{ refreshed_tasks: number }>({
    url: '/b05/checks/refresh',
    method: 'POST',
    params: { space_id: spaceId },
  })
}

/** 按表批量取最近 N 天校验结果（供血缘节点校验□渲染，D4）。
 *  tables 省略时后端返回本空间全部表的最近 N 天结果（避免整图超长 URL 被拒）。
 *  silent：校验□为血缘展示的增强数据，拉取失败不应阻断血缘弹层，故静默处理。 */
export function getCheckResultsByTables(spaceId: number, tables?: string, days = 7) {
  const params: Record<string, unknown> = { space_id: spaceId, days }
  if (tables) params.tables = tables
  return http<CheckResultsByTables>({
    url: '/b05/checks/by-tables',
    method: 'GET',
    params,
    silent: true,
  })
}
