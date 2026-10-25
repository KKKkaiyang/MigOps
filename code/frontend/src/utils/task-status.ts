// 任务迁移 5 维独立状态 的展示配置（替代旧状态机），与后端常量对齐（需求 D1~D7）
// 颜色编码沿用 CODEBUDDY.md §6.4.2 语义配色：通过=绿、不通过/报错=红、微小差距/待关注=黄、未开始/未调度=灰

export type StatusDimensionKey =
  | 'active_status'
  | 'migration_status'
  | 'dualrun_status'
  | 'check_status'
  | 'acceptance_status'

export interface StatusDimension {
  key: StatusDimensionKey
  label: string
  options: string[]
}

/** 5 个独立状态维度（顺序即展示顺序） */
export const STATUS_DIMENSIONS: StatusDimension[] = [
  { key: 'active_status', label: '任务活跃状态', options: ['草稿', '正常调度', '下线', '冻结'] },
  { key: 'migration_status', label: '迁移状态', options: ['未开始', '迁移中', '已完成'] },
  {
    key: 'dualrun_status',
    label: '双跑调度状态',
    options: ['未调度', '调度中', '空跑调度', '提交报错'],
  },
  { key: 'check_status', label: '数据校验状态', options: ['校验通过', '校验不通过', '微小差距'] },
  { key: 'acceptance_status', label: '客户验收状态', options: ['通过', '不通过'] },
]

export const STATUS_DIMENSION_MAP: Record<string, StatusDimension> = Object.fromEntries(
  STATUS_DIMENSIONS.map((d) => [d.key, d])
)

/** 基础表业务字段的中文名（用于模板配置、详情、列标题回退） */
export const BASE_FIELD_LABELS: Record<string, string> = {
  project_name: '项目名称',
  task_name: '任务名称',
  workflow_name: '工作流名称',
  env: '归属环境',
  business: '归属业务',
  task_type: '任务类型',
  migration_owner: '迁移负责人',
  active_status: '任务活跃状态',
  migration_status: '迁移状态',
  dualrun_status: '双跑调度状态',
  check_status: '数据校验状态',
  acceptance_status: '客户验收状态',
  remark: '备注信息',
  task_uri: '任务URI',
  check_result: '数据校验结果',
}

/** 9 个锁定必填字段（模板不可取消；数据校验结果由校验结果导入按血缘输出表刷新） */
export const REQUIRED_BASE_FIELDS: string[] = [
  'project_name',
  'task_name',
  'migration_owner',
  'active_status',
  'migration_status',
  'dualrun_status',
  'check_status',
  'acceptance_status',
  'check_result',
]

/** 数据校验结果码值（b05 校验结果导入刷新到任务） */
export const CHECK_RESULT_OPTIONS = ['通过', '不通过', '无校验结果'] as const
export type CheckResultValue = (typeof CHECK_RESULT_OPTIONS)[number]

/** 状态取值 → Element Plus Tag 类型（颜色） */
export function statusTagType(value?: string | null): 'success' | 'warning' | 'danger' | 'info' {
  if (!value) return 'info'
  if (value === '校验通过' || value === '通过' || value === '已完成' || value === '正常调度')
    return 'success'
  if (
    value === '校验不通过' ||
    value === '不通过' ||
    value === '提交报错' ||
    value === '下线' ||
    value === '冻结'
  )
    return 'danger'
  if (value === '微小差距' || value === '空跑调度' || value === '迁移中' || value === '调度中')
    return 'warning'
  return 'info'
}

/** 状态取值 → 展示颜色（用于自定义点/文字色，与 §6.4.2 一致） */
export function statusColor(value?: string | null): string {
  switch (statusTagType(value)) {
    case 'success':
      return '#27ae60'
    case 'danger':
      return '#e74c3c'
    case 'warning':
      return '#f1c40f'
    default:
      return '#bdc3c7'
  }
}
