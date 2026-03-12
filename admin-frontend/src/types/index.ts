export interface Response<T = any> {
  code: number
  msg: string
  data: T
}

export interface Contact {
  id: string
  name: string
  identity: string
  phone: string
  created_at: string
  updated_at: string
}

export interface ContactCreate {
  name: string
  identity: string
  phone: string
}

export interface ContactUpdate {
  name?: string
  identity?: string
  phone?: string
}

export interface FeishuConfig {
  group_chat_id: string
  contacts: Contact[]
}

export interface FeishuChatItem {
  chat_id: string
  name: string
}

export interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
}

export interface LogQueryResponse {
  items: LogEntry[]
  total: number
}

export interface LogFileInfo {
  file_name: string
  date: string
  size: number
  mtime: string
}

export interface LoginResponse {
  token: string
  csrf_token: string
  token_type: string
  expires_in: number
  user: string
}

export interface SmsConfig {
  contacts: Contact[]
}

export type ParamType = 'string' | 'integer' | 'float' | 'boolean' | 'list' | 'dict'
export type ParamCategory = 'yolo_detection' | 'alarm_logic' | 'hardware' | 'general'
export type ParamPermission = 'read_only' | 'editable' | 'restricted'

export interface SystemParam {
  key: string
  value: any
  type: ParamType
  category: ParamCategory
  description: string
  default_value?: any
  min_value?: number
  max_value?: number
  options?: any[]
  permission: ParamPermission
  requires_restart: boolean
  created_at: string
  updated_at: string
  updated_by?: string
}

export interface ParamVersion {
  version_id: string
  param_key: string
  old_value?: any
  new_value: any
  changed_at: string
  changed_by?: string
  change_reason?: string
}

export interface ParamAuditLog {
  log_id: string
  action: string
  param_key?: string
  old_value?: any
  new_value?: any
  operator?: string
  timestamp: string
  ip_address?: string
}

export interface SystemConfigUpdate {
  updates: Record<string, any>
  change_reason?: string
  operator?: string
}

export interface SystemConfigResponse {
  params: SystemParam[]
  total_count: number
  last_updated?: string
}
