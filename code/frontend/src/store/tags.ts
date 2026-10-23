import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listTags } from '@/api/tag'
import type { TagOut } from '@/types'

/**
 * 空间级标签库共享 store：标签增删改后全局实时同步（需求 A12 / F2）。
 * 供任务清单筛选下拉、行内 + 号打标、任务详情抽屉、批量打标等场景共用，
 * 避免出现「新增标签后需刷新页面才能看到」的缓存陈旧问题。
 */
export const useTagStore = defineStore('tags', () => {
  const spaceId = ref<number | null>(null)
  const tags = ref<TagOut[]>([])
  const loading = ref(false)

  /** 强制刷新当前空间的标签库 */
  async function refresh(sid: number) {
    spaceId.value = sid
    loading.value = true
    try {
      tags.value = await listTags(sid)
    } finally {
      loading.value = false
    }
  }

  /** 按需加载：空间切换或尚未加载时才拉取，避免重复请求 */
  async function ensure(sid: number) {
    if (sid === spaceId.value && tags.value.length > 0) return
    await refresh(sid)
  }

  return { spaceId, tags, loading, ensure, refresh }
})
