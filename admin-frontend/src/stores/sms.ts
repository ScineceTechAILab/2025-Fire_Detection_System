import { defineStore } from 'pinia'
import { ref } from 'vue'
import { smsApi } from '@/api/sms'
import type { SmsConfig, Contact } from '@/types'

export const useSmsStore = defineStore('sms', () => {
  const config = ref<SmsConfig | null>(null)
  const contacts = ref<Contact[]>([])
  const loading = ref(false)

  const fetchConfig = async () => {
    loading.value = true
    try {
      const res = await smsApi.getConfig()
      config.value = res.data
      contacts.value = res.data.contacts
    } finally {
      loading.value = false
    }
  }

  const fetchContacts = async () => {
    loading.value = true
    try {
      const res = await smsApi.getContacts()
      contacts.value = res.data
    } finally {
      loading.value = false
    }
  }

  const createContact = async (data: any) => {
    loading.value = true
    try {
      await smsApi.createContact(data)
      await fetchContacts()
    } finally {
      loading.value = false
    }
  }

  const updateContact = async (id: string, data: any) => {
    loading.value = true
    try {
      await smsApi.updateContact(id, data)
      await fetchContacts()
    } finally {
      loading.value = false
    }
  }

  const deleteContact = async (id: string) => {
    loading.value = true
    try {
      await smsApi.deleteContact(id)
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
    fetchContacts,
    createContact,
    updateContact,
    deleteContact
  }
})
