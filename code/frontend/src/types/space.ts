// 项目空间（b01）类型定义，与后端 Pydantic Schema 对齐

/** 项目空间状态机：初始化 → 交付中 → 已验收 */
export type SpaceStatus = '初始化' | '交付中' | '已验收'

/** 项目空间实体（b01_space） */
export interface SpaceOut {
  id: number
  space_code: string
  space_name: string
  customer_name?: string
  source_platform?: string
  target_platform?: string
  owner?: string
  status: SpaceStatus | string
  /** 整体进展（0-100，手工维护） */
  overall_progress: number
  remark?: string
  db_name?: string
  start_date?: string
  end_date?: string
  /** 后端计算：当前登录用户在该空间内的角色（L0 恒为 L0） */
  my_role?: 'L0' | 'L1' | 'L2' | null
  /** 后端聚合：空间成员数 */
  member_count: number
  created_at?: string
  updated_at?: string
}

/** 空间成员 */
export interface SpaceMemberOut {
  user_id: number
  username: string
  name: string
  org_type?: string
  role_level: 'L1' | 'L2'
  role_name: string
}

/** 空间真实统计（空间概览页，后端 GET /b01/spaces/{id}/stats 聚合） */
export interface SpaceStatsOut {
  b02_material_count: number
  b02_category_count: number
  b03_scenario_count: number
  b03_table_total: number
  b03_metadata_stats: Record<string, number>
  b03_full_sync_stats: Record<string, number>
  b03_incr_sync_stats: Record<string, number>
  b03_record_count: number
  b04_scenario_count: number
  b04_task_total: number
  b04_migration_stats: Record<string, number>
  b04_note_count: number
  b04_view_count: number
  b04_fixed_view_count: number
  b06_tag_count: number
  b06_manage_tag_count: number
  b06_tech_tag_count: number
  b07_edge_count: number
  b07_workflow_count: number
}

/** 统一分页结构（所有列表接口共用） */
export interface PageData<T> {
  list: T[]
  total: number
  page: number
  page_size: number
}
