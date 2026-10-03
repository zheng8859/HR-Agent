import axios from 'axios'
import { tokenStorage, buildAuthHeader } from '@/utils/token'

const http = axios.create({ baseURL: '/api/v1' })

// 请求拦截：注入 Bearer token
http.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) config.headers = { ...config.headers, ...buildAuthHeader(token) }
  return config
})

// 响应拦截：401 清理 token 并跳登录（登录接口自身 401 除外，避免死循环）
http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    if (status === 401 && !url.includes('/auth/login')) {
      tokenStorage.clear()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default http
