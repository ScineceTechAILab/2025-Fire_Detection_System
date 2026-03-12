import request from '@/utils/request'
import type {
  SystemParam,
  ParamCategory,
  SystemConfigUpdate,
  SystemConfigResponse,
  ParamVersion,
  ParamAuditLog
} from '@/types'

export const getSystemParams = (category?: ParamCategory) => {
  return request.get<SystemConfigResponse>('/api/v1/system/params', {
    params: category ? { category } : {}
  })
}

export const getSystemParam = (key: string) => {
  return request.get<SystemParam>(`/api/v1/system/params/${key}`)
}

export const updateSystemParams = (data: SystemConfigUpdate) => {
  return request.put<SystemParam[]>('/api/v1/system/params', data)
}

export const getParamVersions = (key: string, limit?: number) => {
  return request.get<ParamVersion[]>(`/api/v1/system/params/${key}/versions`, {
    params: limit ? { limit } : {}
  })
}

export const rollbackParam = (key: string, versionId: string, operator?: string) => {
  return request.post<SystemParam>(
    `/api/v1/system/params/${key}/rollback/${versionId}`,
    null,
    { params: operator ? { operator } : {} }
  )
}

export const getAuditLogs = (limit?: number) => {
  return request.get<ParamAuditLog[]>('/api/v1/system/audit-logs', {
    params: limit ? { limit } : {}
  })
}

export const exportConfig = () => {
  return request.get<Record<string, any>>('/api/v1/system/export')
}

export const importConfig = (file: File, operator?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/v1/system/import', formData, {
    params: operator ? { operator } : {},
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const reloadConfig = () => {
  return request.post('/api/v1/system/reload')
}

export const getRestartRequiredParams = () => {
  return request.get<string[]>('/api/v1/system/restart-required')
}
