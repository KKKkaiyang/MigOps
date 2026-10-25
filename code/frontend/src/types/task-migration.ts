// 任务迁移管理（b04）类型定义，与后端 Pydantic Schema 对齐（需求 D1~D7 重塑）

import type { TaskCheckResult } from './data-check'

/** 排查备注类型 */
export type NoteKind = 'troubleshoot' | 'check_result'

/** 任务迁移场景 */
export interface TaskScenarioOut {
  id: number
  name: string
  remark?: string | null
  task_count: number
  created_by?: string | null
  created_at?: string
}

/** 标签（空间级） */
export interface TagOut {
  id: number
  tag_name: string
  tag_description?: string | null
  /** 标签分类：管理标签 / 技术标签 */
  tag_category: string
  color: string
  /** 后端聚合：已关联任务数 */
  task_count: number
  created_by?: string | null
  created_at?: string
}

/** 标签分类枚举 */
export const TAG_CATEGORIES = ['技术标签', '管理标签'] as const
export type TagCategory = (typeof TAG_CATEGORIES)[number]

/** 任务上的精简标签（用于列表/详情展示） */
export interface TaskTagBrief {
  id: number
  name: string
  color: string
}

/** 任务视图（基础表 + 扩展字段 ext: f_n → 值） */
export interface TaskOut {
  id: number
  scenario_id: number
  project_name: string
  workflow_name?: string | null
  task_name: string
  env: string
  business?: string | null
  task_type?: string | null
  migration_owner: string
  active_status: string
  migration_status: string
  dualrun_status: string
  check_status?: string | null
  acceptance_status?: string | null
  /** 数据校验结果：通过/不通过/无校验结果（b05 校验结果导入后按血缘输出表刷新） */
  check_result?: TaskCheckResult | string | null
  remark?: string | null
  task_uri: string
  /** 扩展字段：系统列名 f_1..f_n → 值 */
  ext: Record<string, string>
  tags?: TaskTagBrief[]
  updated_by?: string | null
  updated_at?: string | null
}

/** 排查备注 */
export interface TaskNoteOut {
  id: number
  task_id: number
  note_kind: NoteKind | string
  problem_desc?: string | null
  cause_analysis?: string | null
  fix_plan?: string | null
  created_by?: string | null
  created_at?: string
}

/** 自定义视图（保存的筛选视图） */
export interface SavedViewOut {
  id: number
  scenario_id: number
  name: string
  description?: string | null
  filter_config: Record<string, unknown>
  /** 视图模式：dynamic=动态引用; fixed=固化台账(锁定成员) */
  view_mode: 'dynamic' | 'fixed' | string
  /** 后端聚合：命中任务数 */
  task_count: number
  created_by?: string | null
  created_at?: string
}

/** 台账模式通俗化标签 */
export const VIEW_MODE_LABEL: Record<string, string> = {
  dynamic: '自动更新',
  fixed: '固定名单',
}

/** 台账模式通俗化说明 */
export const VIEW_MODE_NOTE: Record<string, string> = {
  dynamic: '名单随筛选条件实时变化：任务改标签/状态后自动移出或加入',
  fixed: '保存时锁定当前任务名单，之后任务变化不影响成员；状态变更仍回写原任务',
}

/** 空间级迁移模板：字段定义 */
export interface MigrationTemplateField {
  field_key: string // 基础表字段名 或 扩展字段序号 ext_1
  field_label: string // 中文显示名（扩展字段中文名在此定义）
  field_source: 'base' | 'extension'
  is_required: boolean
  display_in_list: boolean
  order: number
  ext_type?: 'enum' | 'string' | null
  enum_options?: { code: string; label: string }[] | null
}

/** 空间级迁移模板 config_json */
export interface MigrationTemplateConfig {
  fields: MigrationTemplateField[]
}

/** 空间级迁移模板 */
export interface MigrationTemplateOut {
  id: number
  space_id: number
  name: string
  config_json: MigrationTemplateConfig
  created_by?: string | null
  created_at?: string
  updated_by?: string | null
  updated_at?: string
}

/** 5 维状态维度键 */
export type StatusDimensionKey =
  | 'active_status'
  | 'migration_status'
  | 'dualrun_status'
  | 'check_status'
  | 'acceptance_status'

/** 5 维状态独立更新入参（仅传需更新维度，互不约束） */
export interface TaskStatusIn {
  active_status?: string | null
  migration_status?: string | null
  dualrun_status?: string | null
  check_status?: string | null
  acceptance_status?: string | null
}

/** 批量更新某一维度状态 */
export interface TaskBatchStatusPayload {
  ids: number[]
  dimension: StatusDimensionKey
  value: string
}

/** 空间级迁移模板保存入参 */
export interface MigrationTemplateUpsert {
  name: string
  config_json: MigrationTemplateConfig
}

/** 导入模式 */
export type TaskImportMode = 'overwrite' | 'incremental'

/** 任务视图筛选条件（5 维状态 + 项目/负责人 + 扩展字段） */
export interface TaskListFilters {
  keyword?: string
  workflow_name?: string
  project_name?: string
  migration_owner?: string
  active_status?: string
  migration_status?: string
  dualrun_status?: string
  check_status?: string
  acceptance_status?: string
  tag_ids?: number[]
  tag_match?: 'all' | 'any'
  /** 扩展字段筛选：{f_1: value} */
  ext?: Record<string, string>
}
