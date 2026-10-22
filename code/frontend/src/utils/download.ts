/** 文件下载工具：走后端生成的二进制流（xlsx / .md）。

与 `api/request.ts` 的区别：响应为 blob，不能走统一响应拦截器，
故使用独立 axios 实例；错误响应（HTTP 200 + JSON body）在此解析并提示。
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const instance = axios.create({ baseURL: '/api/v1', timeout: 60000 })

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem('migops_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

instance.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('migops_token')
      localStorage.removeItem('migops_user')
      window.location.assign('/login')
    }
    return Promise.reject(error)
  }
)

function parseFilename(disposition?: string): string {
  if (!disposition) return ''
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (star) return decodeURIComponent(star[1])
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  return plain ? plain[1] : ''
}

/** 下载文件并触发浏览器保存；失败时自动提示后端 message */
export async function downloadFile(
  url: string,
  params?: Record<string, unknown>,
  fallbackName = 'download'
): Promise<void> {
  const res = await instance.get(url, { params, responseType: 'blob' })
  const contentType = (res.headers['content-disposition'] && res.headers['content-type']) as
    | string
    | undefined
  if (contentType && contentType.includes('application/json')) {
    const text = await (res.data as Blob).text()
    try {
      const body = JSON.parse(text)
      ElMessage.error(body.message || '下载失败')
    } catch {
      ElMessage.error('下载失败')
    }
    return
  }
  const filename =
    parseFilename(res.headers['content-disposition'] as string | undefined) || fallbackName
  const blobUrl = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(blobUrl)
}
