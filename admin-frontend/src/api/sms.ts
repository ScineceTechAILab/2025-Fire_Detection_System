import request from '@/utils/request'
import type { SmsConfig, Contact, ContactCreate, ContactUpdate } from '@/types'

export const smsApi = {
  getConfig: () => {
    return request.get<SmsConfig>('/api/v1/sms')
  },

  getContacts: () => {
    return request.get<Contact[]>('/api/v1/sms/contacts')
  },

  getContact: (id: string) => {
    return request.get<Contact>(`/api/v1/sms/contacts/${id}`)
  },

  createContact: (data: ContactCreate) => {
    return request.post<Contact>('/api/v1/sms/contacts', data)
  },

  updateContact: (id: string, data: ContactUpdate) => {
    return request.put<Contact>(`/api/v1/sms/contacts/${id}`, data)
  },

  deleteContact: (id: string) => {
    return request.delete<null>(`/api/v1/sms/contacts/${id}`)
  },

  reloadConfig: () => {
    return request.post<null>('/api/v1/system/reload')
  }
}
