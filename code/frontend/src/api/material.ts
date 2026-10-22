// 项目资料索引（b02）接口封装
import http from './request'
import type {
  MaterialCategoryOut,
  MaterialOut,
  PageData,
  VerifyPasswordResult,
} from '@/types'

/** 资料列表（分页；不返回 content） */
export function listMaterials(
  spaceId: number,
  page = 1,
  page_size = 50,
  keyword?: string,
  type?: string,
  categoryId?: number
) {
  return http<PageData<MaterialOut>>({
    url: '/b02/materials',
    method: 'GET',
    params: { space_id: spaceId, page, page_size, keyword, type, category_id: categoryId },
  })
}

/** 资料详情（markdown 有密码时需 viewToken，否则后端 40300） */
export function getMaterial(spaceId: number, materialId: number, viewToken?: string) {
  return http<MaterialOut>({
    url: `/b02/materials/${materialId}`,
    method: 'GET',
    params: { space_id: spaceId },
    headers: viewToken ? { 'X-View-Token': viewToken } : {},
  })
}

/** 新建资料 */
export function createMaterial(
  spaceId: number,
  payload: {
    name: string
    type: string
    category_id?: number | null
    url?: string
    target_module?: string
    content?: string
    description?: string
    sort_no?: number
    view_password?: string
  }
) {
  return http<MaterialOut>({
    url: '/b02/materials',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新资料（view_password: 不传=不改；空串=清除；非空=设置） */
export function updateMaterial(
  spaceId: number,
  materialId: number,
  payload: {
    name?: string
    type?: string
    category_id?: number | null
    url?: string
    target_module?: string
    content?: string
    description?: string
    sort_no?: number
    view_password?: string
  }
) {
  return http<MaterialOut>({
    url: `/b02/materials/${materialId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除资料 */
export function deleteMaterial(spaceId: number, materialId: number) {
  return http<null>({
    url: `/b02/materials/${materialId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}

/** 验证查看密码，成功返回 view_token */
export function verifyMaterialPassword(
  spaceId: number,
  materialId: number,
  password: string
) {
  return http<VerifyPasswordResult>({
    url: `/b02/materials/${materialId}/verify-password`,
    method: 'POST',
    params: { space_id: spaceId },
    data: { password },
  })
}

/** 分类列表（含资料数） */
export function listCategories(spaceId: number) {
  return http<MaterialCategoryOut[]>({
    url: '/b02/categories',
    method: 'GET',
    params: { space_id: spaceId },
  })
}

/** 新建分类 */
export function createCategory(spaceId: number, payload: { name: string; sort_no?: number }) {
  return http<MaterialCategoryOut>({
    url: '/b02/categories',
    method: 'POST',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 更新分类 */
export function updateCategory(
  spaceId: number,
  categoryId: number,
  payload: { name?: string; sort_no?: number }
) {
  return http<MaterialCategoryOut>({
    url: `/b02/categories/${categoryId}`,
    method: 'PUT',
    params: { space_id: spaceId },
    data: payload,
  })
}

/** 删除分类（预置分类不可删；其下资料置为未分类） */
export function deleteCategory(spaceId: number, categoryId: number) {
  return http<null>({
    url: `/b02/categories/${categoryId}`,
    method: 'DELETE',
    params: { space_id: spaceId },
  })
}
