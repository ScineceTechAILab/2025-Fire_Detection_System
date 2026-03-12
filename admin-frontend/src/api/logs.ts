import request from '@/utils/request'
import type { LogFileInfo, LogQueryResponse } from '@/types'

export const logsApi = {
  query: (params: {
    start?: string
    end?: string
    levels?: string[]
    keyword?: string
    offset?: number
    limit?: number
    order?: 'asc' | 'desc'
  }) => {
    return request.get<LogQueryResponse>('/api/v1/logs', { params })
  },

  listFiles: (days?: number) => {
    return request.get<LogFileInfo[]>('/api/v1/logs/files', { params: { days: days ?? 7 } })
  }
}

