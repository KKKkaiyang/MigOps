// 任务迁移管理（b04）类型定义，与后端 Pydantic Schema 对齐

/** 任务迁移状态（BRD 4.2 状态机） */
export type TaskMigrationStatus =
  | '未开始'
  | '改造完成'
  | '调度成功'
  | '数据校验通过'
  | '数据校验不通过'
  | '客户验收通过'
  | '客户验收不通过'
  | '挂起'
  | '废弃'

/** 调度状态 */
export type ScheduleStatus = '未提交' | '已提交' | '调度中' | '调度成功' | '调度失败'

/** 数据校验状态 */
export type CheckStatus = '未校验' | '校验中' | '校验通过' | '校验不通过'

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

/** 任务台账 */
export interface TaskOut {
  id: number
  scenario_id: number
  workflow_name: string
  task_name: string
  script_name?: string | null
  owner?: string | null
  task_uri: string
  migration_status: TaskMigrationStatus | string
  schedule_status: ScheduleStatus | string
  check_status: CheckStatus | string
  input_tables?: string | null
  output_tables?: string | null
  latest_note?: string | null
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

/** 自定义台账（保存的筛选视图） */
export interface SavedViewOut {
  id: number
  scenario_id: number
  name: string
  description?: string | null
  filter_config: Record<string, string>
  /** 后端聚合：命中任务数 */
  task_count: number
  created_by?: string | null
  created_at?: string
}

/** 状态机：当前状态 → 可流转目标（与后端 TASK_STATUS_TRANSITIONS 对齐） */
export const TASK_STATUS_TRANSITIONS: Record<string, TaskMigrationStatus[]> = {
  未开始: ['改造完成', '挂起', '废弃'],
  改造完成: ['调度成功', '挂起', '废弃'],
  调度成功: ['数据校验通过', '数据校验不通过', '挂起', '废弃'],
  数据校验通过: ['客户验收通过', '客户验收不通过', '挂起', '废弃'],
  数据校验不通过: ['数据校验通过', '调度成功', '挂起', '废弃'],
  客户验收通过: ['挂起', '废弃'],
  客户验收不通过: ['数据校验通过', '数据校验不通过', '调度成功', '挂起', '废弃'],
  挂起: [
    '未开始',
    '改造完成',
    '调度成功',
    '数据校验通过',
    '数据校验不通过',
    '客户验收不通过',
    '废弃',
  ],
  废弃: [],
}

/** 迁移状态筛选项 */
export const TASK_MIGRATION_STATUS_OPTIONS: TaskMigrationStatus[] = [
  '未开始',
  '改造完成',
  '调度成功',
  '数据校验通过',
  '数据校验不通过',
  '客户验收通过',
  '客户验收不通过',
  '挂起',
  '废弃',
]

/** 调度状态筛选项 */
export const SCHEDULE_STATUS_OPTIONS: ScheduleStatus[] = [
  '未提交',
  '已提交',
  '调度中',
  '调度成功',
  '调度失败',
]

/** 校验状态筛选项 */
export const CHECK_STATUS_OPTIONS: CheckStatus[] = ['未校验', '校验中', '校验通过', '校验不通过']

/** 导入模式 */
export type TaskImportMode = 'overwrite' | 'incremental'
