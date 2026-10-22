/** 通用格式化工具（消除各页面重复实现） */

/** 日期时间格式化：ISO → 'YYYY-MM-DD HH:mm:ss'；仅日期时截断 */
export function formatTime(t?: string | null): string {
  if (!t) return '—'
  return t.replace('T', ' ').slice(0, 19)
}

/** 仅日期：ISO → 'YYYY-MM-DD' */
export function formatDate(t?: string | null): string {
  if (!t) return '—'
  return t.slice(0, 10)
}

/** 数字千分位 */
export function formatNumber(n?: number | null): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('zh-CN')
}
