import { defineStore } from 'pinia'
import { ref } from 'vue'
import { feishuApi } from '@/api/feishu'
import type { FeishuConfig, Contact } from '@/types'

export const useFeishuStore = defineStore('feishu', () => {
  const config = ref<FeishuConfig | null>(null)
  const contacts = ref<Contact[]>([])
  const loading = ref(false)

  const fetchConfig = async () => {
    loading.value = true
    try {
      const res = await feishuApi.getConfig()
      config.value = res.data
      contacts.value = res.data.contacts
    } finally {
      loading.value = false
    }
  }

  const updateGroupChatId = async (groupChatId: string) => {
    loading.value = true
    try {
      const res = await feishuApi.updateGroupChatId(groupChatId)
      config.value = res.data
    } finally {
      loading.value = false
    }
  }

  const fetchContacts = async () => {
    loading.value = true
    try {
      const res = await feishuApi.getContacts()
      contacts.value = res.data
    } finally {
      loading.value = false
    }
  }

  const createContact = async (data: any) => {
    loading.value = true
    try {
      await feishuApi.createContact(data)
      await fetchContacts()
    } finally {
      loading.value = false
    }
  }

  const updateContact = async (id: string, data: any) => {
    loading.value = true
    try {
      await feishuApi.updateContact(id, data)
      await fetchContacts()
    } finally {
      loading.value = false
    }
  }

  const deleteContact = async (id: string) => {
    loading.value = true
    try {
      await feishuApi.deleteContact(id)
      await fetchContacts()
    } finally {
      loading.value = false
    }
  }

  return {
    config,
    contacts,
    loading,
    fetchConfig,
    updateGroupChatId,
    fetchContacts,
    createContact,
    updateContact,
    deleteContact
  }
})
