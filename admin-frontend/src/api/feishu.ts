import request from '@/utils/request'
import type { FeishuChatItem, FeishuConfig, Contact, ContactCreate, ContactUpdate } from '@/types'

export const feishuApi = {
  getConfig: () => {
    return request.get<FeishuConfig>('/api/v1/feishu')
  },

  updateGroupChatId: (groupChatId: string) => {
    return request.put<FeishuConfig>('/api/v1/feishu/group-chat', { group_chat_id: groupChatId })
  },

  getContacts: () => {
    return request.get<Contact[]>('/api/v1/feishu/contacts')
  },

  getContact: (id: string) => {
    return request.get<Contact>(`/api/v1/feishu/contacts/${id}`)
  },

  createContact: (data: ContactCreate) => {
    return request.post<Contact>('/api/v1/feishu/contacts', data)
  },

  updateContact: (id: string, data: ContactUpdate) => {
    return request.put<Contact>(`/api/v1/feishu/contacts/${id}`, data)
  },

  deleteContact: (id: string) => {
    return request.delete<null>(`/api/v1/feishu/contacts/${id}`)
  },

  reloadConfig: () => {
    return request.post<null>('/api/v1/system/reload')
  },

  listBotChats: (pageSize?: number, maxPages?: number) => {
    return request.get<FeishuChatItem[]>('/api/v1/feishu/chats', {
      params: {
        page_size: pageSize ?? 50,
        max_pages: maxPages ?? 10
      }
    })
  }
}
