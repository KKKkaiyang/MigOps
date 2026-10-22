import http from './request'
import type { PageData, SpaceMemberOut, SpaceOut, SpaceStatus } from '@/types'

/** 项目空间列表（L0 看全部；其他人仅看已绑定的空间） */
export function listSpaces(page = 1, page_size = 20, keyword?: string, status?: string) {
  return http<PageData<SpaceOut>>({
    url: '/b01/spaces',
    method: 'GET',
    params: { page, page_size, keyword, status },
  })
}

/** 新建项目空间（space_code 由用户填写：小写字母开头，可含数字/下划线） */
export function createSpace(payload: {
  space_code: string
  space_name: string
  customer_name?: string
  source_platform?: string
  target_platform?: string
  owner?: string
  remark?: string
  overall_progress?: number
  start_date?: string
  end_date?: string
}) {
  return http<SpaceOut>({
    url: '/b01/spaces',
    method: 'POST',
    data: payload,
  })
}

/** 更新项目空间信息 */
export function updateSpace(
  id: number,
  payload: {
    space_name?: string
    customer_name?: string
    source_platform?: string
    target_platform?: string
    owner?: string
    remark?: string
    overall_progress?: number
    start_date?: string
    end_date?: string
  }
) {
  return http<SpaceOut>({
    url: `/b01/spaces/${id}`,
    method: 'PUT',
    data: payload,
  })
}

/** 修改空间状态（仅系统管理员 / 项目管理员），须按状态机方向流转 */
export function changeSpaceStatus(id: number, status: SpaceStatus) {
  return http<SpaceOut>({
    url: `/b01/spaces/${id}/status`,
    method: 'POST',
    data: { status },
  })
}

/** 空间成员列表 */
export function listMembers(id: number) {
  return http<SpaceMemberOut[]>({
    url: `/b01/spaces/${id}/members`,
    method: 'GET',
  })
}

/** 项目空间详情 */
export function getSpace(id: number) {
  return http<SpaceOut>({
    url: `/b01/spaces/${id}`,
    method: 'GET',
  })
}

/** 添加空间成员 */
export function addMember(id: number, payload: { user_id: number; role_level: 'L1' | 'L2' }) {
  return http<SpaceMemberOut>({
    url: `/b01/spaces/${id}/members`,
    method: 'POST',
    data: payload,
  })
}

/** 修改空间成员角色 */
export function updateMemberRole(id: number, userId: number, role_level: 'L1' | 'L2') {
  return http<SpaceMemberOut>({
    url: `/b01/spaces/${id}/members/${userId}`,
    method: 'PUT',
    data: { role_level },
  })
}

/** 移除空间成员 */
export function removeMember(id: number, userId: number) {
  return http<null>({
    url: `/b01/spaces/${id}/members/${userId}`,
    method: 'DELETE',
  })
}
