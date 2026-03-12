import axios, { type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { Response } from '@/types'

const instance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
  timeout: 10000,
  withCredentials: true
})

instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('auth_token')
  const csrf = localStorage.getItem('csrf_token')
  
  config.headers = config.headers || {}
  
  if (token) {
    ;(config.headers as any)['Authorization'] = `Bearer ${token}`
  }
  
  if (['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
    ;(config.headers as any)['X-CSRF-Token'] = csrf || ''
  }
  
  return config
}, (error) => Promise.reject(error))

instance.interceptors.response.use(
  (response: AxiosResponse<Response<any>>) => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    return res as any
  },
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('csrf_token')
      if (location.pathname !== '/login') {
        const redirect = encodeURIComponent(location.pathname + location.search)
        location.href = `/login?redirect=${redirect}`
      }
    } else {
      ElMessage.error(error.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

type TypedRequest = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<Response<T>>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<Response<T>>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<Response<T>>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<Response<T>>
}

const request = instance as unknown as TypedRequest

export default request
