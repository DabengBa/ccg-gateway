import axios from 'axios'
import { ElMessage } from 'element-plus'

const instance = axios.create({
  baseURL: '/admin/v1',
  timeout: 30000
})

instance.interceptors.request.use(config => {
  const token = localStorage.getItem('ccg_gateway_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['X-CCG-Token'] = token
  }
  return config
})

instance.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default instance
