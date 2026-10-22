import http from './request'
import type {
  PageData,
  RoleItem,
  UserCreatePayload,
  UserOut,
  UserRoleOut,
  UserUpdatePayload,
} from '@/types'

/** 用户列表（仅系统管理员） */
export function listUsers(page = 1, page_size = 20, keyword?: string) {
  return http<PageData<UserOut>>({
    url: '/common/users',
    method: 'GET',
    params: { page, page_size, keyword },
  })
}

/** 创建用户；后端返回一次性明文密码（系统生成时） */
export function createUser(payload: UserCreatePayload) {
  return http<{ user: UserOut; password: string }>({
    url: '/common/users',
    method: 'POST',
    data: payload,
  })
}

/** 更新用户资料 */
export function updateUser(id: number, payload: UserUpdatePayload) {
  return http<UserOut>({
    url: `/common/users/${id}`,
    method: 'PUT',
    data: payload,
  })
}

/** 停用用户（注销语义，可恢复） */
export function disableUser(id: number) {
  return http<UserOut>({
    url: `/common/users/${id}/disable`,
    method: 'POST',
  })
}

/** 启用用户 */
export function enableUser(id: number) {
  return http<UserOut>({
    url: `/common/users/${id}/enable`,
    method: 'POST',
  })
}

/** 重置密码：生成临时密码，用户首次登录强制修改 */
export function resetUserPassword(id: number) {
  return http<{ temp_password: string }>({
    url: `/common/users/${id}/reset-password`,
    method: 'POST',
  })
}

/** 查询用户角色绑定 */
export function getUserRoles(id: number) {
  return http<UserRoleOut[]>({
    url: `/common/users/${id}/roles`,
    method: 'GET',
  })
}

/** 设置用户角色（全量覆盖）：L0 全局；L1/L2 绑定具体空间 */
export function setUserRoles(id: number, roles: RoleItem[]) {
  return http<UserRoleOut[]>({
    url: `/common/users/${id}/roles`,
    method: 'PUT',
    data: { roles },
  })
}
