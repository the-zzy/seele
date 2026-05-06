import axios from 'axios'

const request = axios.create({
  baseURL: process.env.VUE_APP_BASE_API || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.request.use(
  config => config,
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
    console.error('请求错误:', error.message)
    return Promise.reject(error)
  }
)

export default request
