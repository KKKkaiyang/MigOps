// 标签管理（b06）接口封装
import http from './request'
import type { TagOut } from '@/types'

/** 标签列表（空间级） */
export function listTags(spaceId: number) {
  return http<TagOut[]>({
    url: '/b06/tags',
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 新建标签 */
export function createTag(
  spaceId: number,
  payload: {
    tag_name: string
    tag_description?: string
    tag_category?: string
    color?: string
  }
) {
  return http<TagOut>({
    url: '/b06/tags',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新标签 */
export function updateTag(
  spaceId: number,
  tagId: number,
  payload: {
    tag_name?: string
    tag_description?: string
    tag_category?: string
    color?: string
  }
) {
  return http<null>({
    url: `/b06/tags/${tagId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除标签（级联解除任务关联） */
export function deleteTag(spaceId: number, tagId: number) {
  return http<null>({
    url: `/b06/tags/${tagId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}
