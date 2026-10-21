import request from './request'

export interface SpaceOut {
  id: number
  space_code: string
  space_name: string
  customer_name?: string
  source_platform?: string
  target_platform?: string
  owner?: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface PageData<T> {
  list: T[]
  total: number
  page: number
  page_size: number
}

export function listSpaces(page = 1, page_size = 20, keyword?: string) {
  return request.get<PageData<SpaceOut>>('/b01/spaces', {
    params: { page, page_size, keyword },
  })
}

export function createSpace(payload: Partial<SpaceOut>) {
  return request.post<SpaceOut>('/b01/spaces', payload)
}
