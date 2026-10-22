import http from './request'
import type { CaptchaOut, CurrentUser, LoginResult } from '@/types'

/** 获取图形验证码（4 位字符，排除易混字符 1/I/0/O） */
export function getCaptcha() {
  return http<CaptchaOut>({
    url: '/common/auth/captcha',
    method: 'GET',
  })
}

/** 登录：连续失败达阈值后需传 captcha_id / captcha_code */
export function login(payload: {
  username: string
  password: string
  captcha_id?: string
  captcha_code?: string
}) {
  return http<LoginResult>({
    url: '/common/auth/login',
    method: 'POST',
    data: payload,
  })
}

/** 当前登录用户信息与角色 */
export function getMe() {
  return http<CurrentUser>({
    url: '/common/auth/me',
    method: 'GET',
  })
}

/** 修改密码（临时密码登录后强制走此流程） */
export function changePassword(payload: { old_password: string; new_password: string }) {
  return http<null>({
    url: '/common/auth/change-password',
    method: 'POST',
    data: payload,
  })
}

/** 登出（JWT 无状态，客户端丢弃令牌） */
export function logout() {
  return http<null>({
    url: '/common/auth/logout',
    method: 'POST',
  })
}
