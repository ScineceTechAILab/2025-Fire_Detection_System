import request from '@/utils/request'

export interface FeishuCredentials {
  app_id: string
  app_secret: string
}

export interface AliyunCredentials {
  access_key_id: string
  access_key_secret: string
  sms_sign_name: string
  sms_template_code: string
}

export interface Credentials {
  sms_provider: string
  feishu: FeishuCredentials
  aliyun: AliyunCredentials
  version?: number
  updated_at?: string
}

export const getCredentials = () => {
  return request.get<Credentials>('/api/v1/credentials')
}

export const getFeishuCredentials = () => {
  return request.get<FeishuCredentials>('/api/v1/credentials/feishu')
}

export const updateFeishuCredentials = (data: FeishuCredentials) => {
  return request.put<Credentials>('/api/v1/credentials/feishu', data)
}

export const getAliyunCredentials = () => {
  return request.get<AliyunCredentials>('/api/v1/credentials/aliyun')
}

export const updateAliyunCredentials = (data: AliyunCredentials) => {
  return request.put<Credentials>('/api/v1/credentials/aliyun', data)
}

export const getSmsProvider = () => {
  return request.get<string>('/api/v1/credentials/sms-provider')
}

export const updateSmsProvider = (provider: string) => {
  return request.put<Credentials>('/api/v1/credentials/sms-provider', { provider })
}
