import http from './request'
import type { ApiKeyCreated, ApiKeyOut } from '@/types'

/** 个人中心：我的 API 密钥列表（secret 掩码） */
export function listApiKeys() {
  return http<ApiKeyOut[]>({
    url: '/common/users/me/api-keys',
    method: 'GET',
  })
}

/** 生成 API 密钥（secret_key 仅返回一次明文） */
export function createApiKey() {
  return http<ApiKeyCreated>({
    url: '/common/users/me/api-keys',
    method: 'POST',
  })
}

/** 吊销 API 密钥 */
export function revokeApiKey(id: number) {
  return http<null>({
    url: `/common/users/me/api-keys/${id}`,
    method: 'DELETE',
  })
}

/** 启用 / 停用 API 密钥 */
export function toggleApiKey(id: number) {
  return http<ApiKeyOut>({
    url: `/common/users/me/api-keys/${id}`,
    method: 'PATCH',
  })
}
