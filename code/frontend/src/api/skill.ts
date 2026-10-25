import http from './request'
import type { PageData, SkillOut } from '@/types'

/** skill 市场公开列表（所有登录用户可见） */
export function listMarket(
  page = 1,
  page_size = 20,
  keyword?: string,
  sort: 'heat' | 'latest' = 'heat',
) {
  return http<PageData<SkillOut>>({
    url: '/b08/skills/market',
    method: 'GET',
    params: { page, page_size, keyword, sort },
  })
}

/** 我的 skill（含私有，作者本人 + L0 可见） */
export function mySkills(page = 1, page_size = 20) {
  return http<PageData<SkillOut>>({
    url: '/b08/skills/me',
    method: 'GET',
    params: { page, page_size },
  })
}

/** 上传 skill（multipart：file + 元数据） */
export function uploadSkill(
  file: File,
  meta: { name: string; intro?: string; is_public: number },
) {
  const form = new FormData()
  form.append('file', file)
  form.append('name', meta.name)
  if (meta.intro) form.append('intro', meta.intro)
  form.append('is_public', String(meta.is_public))
  return http<SkillOut>({
    url: '/b08/skills',
    method: 'POST',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 上架 / 下架（作者本人 + L0） */
export function setSkillStatus(skill_code: string, status: string) {
  return http<SkillOut>({
    url: `/b08/skills/${skill_code}/status`,
    method: 'PATCH',
    data: { status },
  })
}

/** 删除 skill（作者本人 + L0） */
export function deleteSkill(skill_code: string) {
  return http<null>({
    url: `/b08/skills/${skill_code}`,
    method: 'DELETE',
  })
}
