import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一请求封装：baseURL 指向后端 /api/v1，开发环境由 vite 代理转发
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

request.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(body)
    }
    return body?.data ?? body
  },
  (error) => {
    ElMessage.error(error?.message || '网络错误')
    return Promise.reject(error)
  },
)

export default request
