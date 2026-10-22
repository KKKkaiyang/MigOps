import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { CurrentUser, LoginResult, RoleLevel, UserRoleOut } from '@/types'
import { getMe, login as loginApi } from '@/api/auth'

const TOKEN_KEY = 'migops_token'
const USER_KEY = 'migops_user'

function readStorage(): { token: string; user: CurrentUser | null } {
  try {
    return {
      token: localStorage.getItem(TOKEN_KEY) || '',
      user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
    }
  } catch {
    return { token: '', user: null }
  }
}

function writeStorage(token: string, user: CurrentUser | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export const useUserStore = defineStore('user', () => {
  const stored = readStorage()
  const token = ref<string>(stored.token)
  const user = ref<CurrentUser | null>(stored.user)

  /** 是否系统管理员（全局 L0） */
  const isL0 = computed(() => user.value?.is_l0 === true)

  /** 用户在指定空间内的角色；L0 恒为 L0 */
  function roleIn(spaceId: number): RoleLevel | null {
    if (user.value?.is_l0) return 'L0'
    const found = user.value?.roles.find((r: UserRoleOut) => r.space_id === spaceId)
    return found ? found.role_level : null
  }

  async function login(payload: {
    username: string
    password: string
    captcha_id?: string
    captcha_code?: string
  }): Promise<LoginResult> {
    const result = await loginApi(payload)
    token.value = result.token
    writeStorage(result.token, user.value)
    // 拉取完整用户信息（含角色），供权限判断使用
    await fetchMe()
    return result
  }

  async function fetchMe(): Promise<CurrentUser> {
    const me = await getMe()
    user.value = me
    writeStorage(token.value, me)
    return me
  }

  function logout() {
    token.value = ''
    user.value = null
    writeStorage('', null)
  }

  return { token, user, isL0, roleIn, login, fetchMe, logout }
})
