import axios, { type AxiosRequestConfig, type AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

/** 业务错误码（与后端 app/core/exceptions.py 对齐） */
export const CODE_UNAUTHORIZED = 40100
export const CODE_CAPTCHA = 40001

/** 带业务错误码的错误对象，便于页面按码分支处理 */
export class BizError extends Error {
  code: number
  constructor(message: string, code: number) {
    super(message)
    this.code = code
    this.name = 'BizError'
  }
}

// 统一请求封装：baseURL 指向后端 /api/v1，响应拦截器处理统一结构
// { code, message, data }（code!==0 自动 ElMessage.error 并 reject），并剥离 data 返回。
// config.silent=true 时仅 reject、不弹错误提示（用于非关键的增强数据，如血缘节点校验□）。
const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截器：附加登录态 Bearer Token（直接从 localStorage 读取，避免与 store 循环依赖）
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem('migops_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

instance.interceptors.response.use(
  (resp) => {
    const body = resp.data
    const silent = !!(resp.config as { silent?: boolean })?.silent
    if (body && typeof body.code === 'number' && body.code !== 0) {
      // 登录态失效：清理本地状态并跳转登录页
      if (body.code === CODE_UNAUTHORIZED) {
        const store = useUserStore()
        store.logout()
        const redirect = encodeURIComponent(
          window.location.pathname + window.location.search
        )
        if (!window.location.pathname.startsWith('/login')) {
          window.location.assign(`/login?redirect=${redirect}`)
        }
      }
      // 非关键取数（silent）失败时不弹错误提示，避免干扰主流程
      if (!silent) ElMessage.error(body.message || '请求失败')
      return Promise.reject(new BizError(body.message || '业务错误', body.code))
    }
    // 成功：剥离统一结构，直接返回 data 字段
    return body.data
  },
  (error: AxiosError) => {
    // 网络层 401（如直接命中间件）同样按登录失效处理
    if (error.response?.status === 401) {
      const store = useUserStore()
      store.logout()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign(`/login?redirect=${encodeURIComponent(window.location.pathname)}`)
      }
    }
    const data = error.response?.data as { message?: string } | undefined
    const msg = data?.message || error.message || '网络错误'
    if (!(error.config as { silent?: boolean })?.silent) ElMessage.error(msg)
    return Promise.reject(error)
  },
)

/**
 * 类型安全的请求封装：泛型 T 即后端 data 字段的类型。
 * 调用方拿到的就是业务数据，无需再处理 AxiosResponse。
 */
function http<T = unknown>(config: AxiosRequestConfig & { silent?: boolean }): Promise<T> {
  return instance.request<T>(config) as unknown as Promise<T>
}

export default http
