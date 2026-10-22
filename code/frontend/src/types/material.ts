// 项目资料索引（b02）类型定义，与后端 Pydantic Schema 对齐

/** 资料类型（确认决策 D1：三种） */
export type MaterialType = 'external_link' | 'markdown' | 'platform_ledger'

/** 平台台账预置跳转目标（确认决策 D14：一期仅 b03/b04） */
export const PLATFORM_LEDGER_TARGET_OPTIONS: { value: string; label: string }[] = [
  { value: 'b03', label: '数据迁移管理' },
  { value: 'b04', label: '任务迁移管理' },
]

/** 资料分类 */
export interface MaterialCategoryOut {
  id: number
  name: string
  sort_no: number
  is_preset: number
  material_count: number
}

/** 资料索引实体（列表不返回 content） */
export interface MaterialOut {
  id: number
  space_id: number
  category_id?: number | null
  name: string
  type: MaterialType
  url?: string | null
  target_module?: string | null
  /** 仅详情端点在密码校验通过后返回；列表恒为 null */
  content?: string | null
  description?: string | null
  sort_no: number
  /** 是否设置了查看密码 */
  has_password: boolean
  created_by?: string | null
  created_at?: string
  updated_by?: string | null
  updated_at?: string
}

/** 查看密码验证结果 */
export interface VerifyPasswordResult {
  view_token: string
  expires_in: number
}
