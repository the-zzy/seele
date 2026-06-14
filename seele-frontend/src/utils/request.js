import axios from 'axios'
import { getToken, removeToken, requireAuth } from '@/utils/auth'
import { clearStaleState, forceReload, getClientVersion } from '@/utils/version'

export const baseURL = process.env.VUE_APP_BASE_API || '/api'

const request = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['X-Client-Version'] = getClientVersion()
    return config
  },
  error => Promise.reject(error)
)

// 业务约定：所有响应统一为 { code, message, data }
// 拦截器在 code 为 200 时直接返回 data，否则拒绝
request.interceptors.response.use(
  response => {
    const res = response.data
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 200) {
        return res.data
      }
      const error = new Error(res.message || `请求失败 (code: ${res.code})`)
      error.code = res.code
      error.payload = res
      return Promise.reject(error)
    }
    return res
  },
  error => {
    if (error.response?.status === 401) {
      removeToken()
      requireAuth()
    }
    if (error.response?.status === 409) {
      const detail = error.response.data?.detail
      if (detail?.code === 'VERSION_MISMATCH') {
        clearStaleState()
        forceReload()
        return new Promise(() => {})
      }
    }
    console.error('请求错误:', error.message)
    return Promise.reject(error)
  }
)

export default request
