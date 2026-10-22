// 数据迁移管理（b03）类型定义，与后端 Pydantic Schema 对齐

/** 表类型 */
export type TableType = '内部表' | '外部表' | '视图' | '分区表'

/** 元数据/全量迁移状态 */
export type MigrationLineStatus = '未迁移' | '迁移中' | '已完成' | '异常'

/** 增量迁移状态 */
export type IncrSyncStatus = '未开始' | '进行中' | '已停止' | '异常'

/** 迁移过程类型 */
export type MigrationType = '全量历史迁移' | '增量迁移'

/** 迁移记录状态 */
export type RecordStatus = '成功' | '失败' | '部分成功'

/** 数据迁移场景 */
export interface DataMigrationScenarioOut {
  id: number
  name: string
  remark?: string | null
  table_count: number
  created_by?: string | null
  created_at?: string
}

/** 库表清单 */
export interface TableItemOut {
  id: number
  scenario_id: number
  db_name: string
  table_name: string
  target_db_name?: string | null
  target_table_name?: string | null
  table_type?: TableType | string | null
  data_volume?: number | null
  partition_count?: number | null
  metadata_status: MigrationLineStatus | string
  full_sync_status: MigrationLineStatus | string
  full_sync_cutoff_date?: string | null
  incr_sync_status: IncrSyncStatus | string
  incr_sync_latest_at?: string | null
  remark?: string | null
  /** 后端聚合：迁移记录数 */
  record_count: number
  updated_by?: string | null
  updated_at?: string | null
}

/** 迁移过程记录 */
export interface MigrationRecordOut {
  id: number
  table_item_id: number
  migration_type: MigrationType | string
  started_at?: string | null
  finished_at?: string | null
  data_volume?: number | null
  method?: string | null
  data_cutoff_date?: string | null
  status: RecordStatus | string
  remark?: string | null
  created_by?: string | null
  created_at?: string
}

/** 导入结果（含行级错误） */
export interface ImportResult {
  inserted: number
  updated: number
  skipped: number
  errors: { row: number; message: string }[]
}

/** 表类型筛选项 */
export const TABLE_TYPE_OPTIONS: TableType[] = ['内部表', '外部表', '视图', '分区表']

/** 元数据/全量状态筛选项 */
export const MIGRATION_LINE_STATUS_OPTIONS: MigrationLineStatus[] = [
  '未迁移',
  '迁移中',
  '已完成',
  '异常',
]

/** 增量状态筛选项 */
export const INCR_SYNC_STATUS_OPTIONS: IncrSyncStatus[] = [
  '未开始',
  '进行中',
  '已停止',
  '异常',
]

/** 迁移类型选项（记录表单） */
export const MIGRATION_TYPE_OPTIONS: MigrationType[] = ['全量历史迁移', '增量迁移']

/** 记录状态选项（记录表单） */
export const RECORD_STATUS_OPTIONS: RecordStatus[] = ['成功', '失败', '部分成功']
