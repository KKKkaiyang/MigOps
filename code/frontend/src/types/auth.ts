// 公共业务（用户/角色/认证）类型定义，与后端 Pydantic Schema 对齐

/** 用户归属（仅标签区分，无功能权限差异） */
export type OrgType = '内部' | '腾讯' | '其他厂商' | '客户'

/** 角色等级：L0 系统管理员(全局) / L1 项目管理员(按空间) / L2 项目成员(按空间) */
export type RoleLevel = 'L0' | 'L1' | 'L2'

export const ORG_TYPE_OPTIONS: OrgType[] = ['内部', '腾讯', '其他厂商', '客户']

export const ROLE_LEVEL_MAP: Record<RoleLevel, string> = {
  L0: '系统管理员',
  L1: '项目管理员',
  L2: '项目成员',
}

/** 用户实体（common_user） */
export interface UserOut {
  id: number
  username: string
  name: string
  email?: string
  phone?: string
  org_type?: OrgType
  /** 账号状态：enabled 启用 / disabled 停用 */
  status: 'enabled' | 'disabled'
  last_login_at?: string
  created_at?: string
}

/** 用户角色绑定（common_user_role） */
export interface UserRoleOut {
  id: number
  role_level: RoleLevel
  role_name: string
  space_id?: number | null
  space_name?: string | null
}

/** 角色设置项 */
export interface RoleItem {
  role_level: RoleLevel
  space_id?: number | null
}

/** 登录结果 */
export interface LoginResult {
  token: string
  token_type: string
  expires_in: number
  user: {
    id: number
    username: string
    name: string
    org_type?: OrgType
  }
  /** 临时密码登录后需强制修改密码 */
  must_change_password: boolean
}

/** 当前登录用户（含角色） */
export interface CurrentUser {
  id: number
  username: string
  name: string
  email?: string
  phone?: string
  org_type?: OrgType
  status: string
  /** 是否为系统管理员（全局 L0） */
  is_l0: boolean
  roles: UserRoleOut[]
  last_login_at?: string
}

/** 创建用户参数 */
export interface UserCreatePayload {
  username: string
  name: string
  org_type?: OrgType
  email?: string
  phone?: string
  /** 留空则由系统生成临时密码 */
  password?: string
}

/** 更新用户参数 */
export interface UserUpdatePayload {
  name?: string
  org_type?: OrgType
  email?: string
  phone?: string
}

/** 验证码 */
export interface CaptchaOut {
  captcha_id: string
  svg: string
}
