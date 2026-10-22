/** markdown 资料查看令牌的会话内存存储（确认决策 D16）。

仅存内存：刷新页面即失效，需重新验证密码；不落 localStorage。
 */
const tokens = new Map<number, string>()

export function getViewToken(materialId: number): string | undefined {
  return tokens.get(materialId)
}

export function setViewToken(materialId: number, token: string): void {
  tokens.set(materialId, token)
}

export function clearViewToken(materialId: number): void {
  tokens.delete(materialId)
}
