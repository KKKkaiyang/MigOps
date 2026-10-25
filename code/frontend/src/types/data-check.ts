// 数据校验管理（b05）类型定义，与后端 Pydantic Schema 对齐

/** 校验结果码值 */
export type CheckResult = '通过' | '不通过'

/** 任务数据校验结果码值（含无校验结果） */
export type TaskCheckResult = CheckResult | '无校验结果'

/** 导入模板类型 */
export const CHECK_TEMPLATES = ['default', 'tencent'] as const
export type CheckTemplate = (typeof CHECK_TEMPLATES)[number]

/** 导入模板中文名 */
export const CHECK_TEMPLATE_LABELS: Record<CheckTemplate, string> = {
  default: '默认模板',
  tencent: '腾讯数据校验工具模板',
}

/** 导入模板列说明 */
export const CHECK_TEMPLATE_HEADERS: Record<CheckTemplate, string[]> = {
  default: ['库名', '表名', '源端数据量', '目标端数据量', '结果(通过/不通过)'],
  tencent: ['srcDatabase', 'srcTable', 'srcResult', 'dstResult', 'checkResult(true/false)'],
}

/** 最新校验结果筛选项（含无校验结果） */
export const CHECK_RESULT_FILTER_OPTIONS: (CheckResult | '无校验结果')[] = [
  '通过',
  '不通过',
  '无校验结果',
]

/** 近 7 天中的一天（无数据 result 为 null） */
export interface CheckResultDay {
  data_date: string
  result?: CheckResult | null
  src_volume?: number | null
  dst_volume?: number | null
}

/** 数据校验列表行：库表清单 + 最新校验结果 + 近 7 天序列 */
export interface CheckOverviewOut {
  item_id: number
  scenario_id: number
  db_name: string
  table_name: string
  target_db_name?: string | null
  target_table_name?: string | null
  table_type?: string | null
  latest_result?: CheckResult | null
  latest_date?: string | null
  latest_src_volume?: number | null
  latest_dst_volume?: number | null
  /** 近 7 天校验序列（按日期降序：索引 0 = 昨天 T-1，索引 6 = T-7；不含今天，长度 7） */
  recent_days: CheckResultDay[]
}

/** 校验结果导入结果 */
export interface CheckImportResult {
  inserted: number
  updated: number
  skipped: number
  errors: { row: number; message: string }[]
  /** 本次导入刷新任务数据校验结果的任务数（实际发生变更） */
  refreshed_tasks: number
  /** 本次导入中不在当前迁移场景库表清单内的库表条数（正常入库，仅提示） */
  not_in_list: number
}

/** 单表单日校验结果（供血缘节点□渲染，D4） */
export interface CheckResultByTable {
  data_date: string
  result?: CheckResult | null
  src_volume?: number | null
  dst_volume?: number | null
}

/** 按表批量校验结果（key 为 db.table） */
export interface CheckResultsByTables {
  tables: Record<string, CheckResultByTable[]>
}
