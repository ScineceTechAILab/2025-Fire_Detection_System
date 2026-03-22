<template>
  <div class="fd-page">
    <PageHeader title="飞书管理" description="维护群聊配置与通知联系人，支持快速获取机器人所在群聊 ID。">
      <template #actions>
        <ActionBar>
          <el-button plain @click="openChatsDialog">
            <el-icon><Search /></el-icon>
            获取群聊 ID
          </el-button>
          <el-button type="primary" @click="handleReload">
            <el-icon><Refresh /></el-icon>
            热加载配置
          </el-button>
        </ActionBar>
      </template>
    </PageHeader>

    <DataCard title="群聊配置">
      <el-form :model="configForm" label-width="120px" class="group-form">
        <el-form-item label="群聊 ID">
          <el-input v-model="configForm.group_chat_id" placeholder="请输入飞书群聊 ID" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="updateLoading" @click="handleUpdateGroupChat">保存</el-button>
        </el-form-item>
      </el-form>
    </DataCard>

    <DataCard title="飞书联系人">
      <ContactList
        :contacts="feishuStore.contacts"
        :loading="feishuStore.loading"
        :on-add="feishuStore.createContact"
        :on-edit="feishuStore.updateContact"
        :on-delete="feishuStore.deleteContact"
        :on-refresh="feishuStore.fetchContacts"
      />
    </DataCard>

    <el-dialog v-model="chatsDialogVisible" title="机器人所在群聊" width="860px">
      <div class="chats-toolbar">
        <el-input v-model="chatKeyword" placeholder="搜索群名称或群聊 ID" clearable @input="debounceFilter" />
        <el-button plain :loading="chatsLoading" @click="loadChats">刷新</el-button>
      </div>
      <el-table v-loading="chatsLoading" :data="filteredChats" stripe>
        <el-table-column prop="name" label="群名称" min-width="260" />
        <el-table-column prop="chat_id" label="群聊 ID" min-width="350" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="useChatId(row.chat_id)">填入</el-button>
            <el-button size="small" type="primary" plain @click="copyChatId(row.chat_id)">复制</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="chatsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useFeishuStore } from '@/stores/feishu'
import { feishuApi } from '@/api/feishu'
import ContactList from '@/components/ContactList.vue'
import type { FeishuChatItem } from '@/types'
import ActionBar from '@/components/layout/ActionBar.vue'
import DataCard from '@/components/layout/DataCard.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const feishuStore = useFeishuStore()
const configForm = ref({ group_chat_id: '' })
const updateLoading = ref(false)
const chatsDialogVisible = ref(false)
const chatsLoading = ref(false)
const chats = ref<FeishuChatItem[]>([])
const chatKeyword = ref('')
const debouncedKeyword = ref('')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await feishuStore.fetchConfig()
  if (feishuStore.config) {
    configForm.value.group_chat_id = feishuStore.config.group_chat_id
  }
})

const handleUpdateGroupChat = async () => {
  updateLoading.value = true
  try {
    await feishuStore.updateGroupChatId(configForm.value.group_chat_id)
    ElMessage.success('群聊 ID 更新成功')
  } finally {
    updateLoading.value = false
  }
}

const handleReload = async () => {
  try {
    await feishuApi.reloadConfig()
    await feishuStore.fetchConfig()
    ElMessage.success('配置热加载成功')
  } catch {
    ElMessage.error('配置热加载失败')
  }
}

const loadChats = async () => {
  chatsLoading.value = true
  try {
    const res = await feishuApi.listBotChats(50, 10)
    chats.value = res.data
  } finally {
    chatsLoading.value = false
  }
}

const openChatsDialog = async () => {
  chatsDialogVisible.value = true
  if (chats.value.length === 0) {
    await loadChats()
  }
}

const debounceFilter = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedKeyword.value = chatKeyword.value.trim().toLowerCase()
  }, 200)
}

const filteredChats = computed(() => {
  const keyword = debouncedKeyword.value
  if (!keyword) return chats.value
  return chats.value.filter((item) => item.name.toLowerCase().includes(keyword) || item.chat_id.toLowerCase().includes(keyword))
})

const useChatId = (chatId: string) => {
  configForm.value.group_chat_id = chatId
  ElMessage.success('已填入群聊 ID')
}

const copyChatId = async (chatId: string) => {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(chatId)
      ElMessage.success('已复制群聊 ID')
      return
    }
  } catch {
    // noop
  }
  const input = document.createElement('input')
  input.value = chatId
  document.body.appendChild(input)
  input.select()
  document.execCommand('copy')
  document.body.removeChild(input)
  ElMessage.success('已复制群聊 ID')
}
</script>

<style scoped>
.group-form {
  max-width: 720px;
}

.chats-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
</style>
