<template>
  <div class="feishu-view">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>飞书群聊配置</span>
          <div class="header-actions">
            <el-button size="small" plain @click="openChatsDialog">
              <el-icon><Search /></el-icon>
              获取群聊ID
            </el-button>
            <el-button type="primary" size="small" @click="handleReload">
              <el-icon><Refresh /></el-icon>
              热加载配置
            </el-button>
          </div>
        </div>
      </template>
      
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="群聊ID">
          <el-input v-model="configForm.group_chat_id" placeholder="请输入飞书群聊ID" style="width: 400px;" />
          <el-button type="primary" :loading="updateLoading" @click="handleUpdateGroupChat">
            保存
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-dialog v-model="chatsDialogVisible" title="机器人所在群聊" width="820px">
      <div class="chats-toolbar">
        <el-input
          v-model="chatKeyword"
          placeholder="搜索群名称或群聊ID"
          clearable
          @input="debounceFilter"
        />
        <el-button size="small" plain :loading="chatsLoading" @click="loadChats">刷新</el-button>
      </div>
      <el-table v-loading="chatsLoading" :data="filteredChats" stripe style="width: 100%">
        <el-table-column prop="name" label="群名称" min-width="260" />
        <el-table-column prop="chat_id" label="群聊ID" min-width="320" />
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

    <el-card class="contacts-card" style="margin-top: 20px;">
      <template #header>
        <span>紧急联系人列表</span>
      </template>
      
      <ContactList
        :contacts="feishuStore.contacts"
        :loading="feishuStore.loading"
        :on-add="feishuStore.createContact"
        :on-edit="feishuStore.updateContact"
        :on-delete="feishuStore.deleteContact"
        :on-refresh="feishuStore.fetchContacts"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useFeishuStore } from '@/stores/feishu'
import { feishuApi } from '@/api/feishu'
import ContactList from '@/components/ContactList.vue'
import type { FeishuChatItem } from '@/types'

const feishuStore = useFeishuStore()

const configForm = ref({
  group_chat_id: ''
})
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
    ElMessage.success('群聊ID更新成功')
  } finally {
    updateLoading.value = false
  }
}

const handleReload = async () => {
  try {
    await feishuApi.reloadConfig()
    await feishuStore.fetchConfig()
    ElMessage.success('配置热加载成功')
  } catch (error) {
    console.error(error)
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
  return chats.value.filter((c) => c.name.toLowerCase().includes(keyword) || c.chat_id.toLowerCase().includes(keyword))
})

const useChatId = (chatId: string) => {
  configForm.value.group_chat_id = chatId
  ElMessage.success('已填入群聊ID')
}

const copyChatId = async (chatId: string) => {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(chatId)
      ElMessage.success('已复制群聊ID')
      return
    }
  } catch (e) {
    console.error(e)
  }
  const input = document.createElement('input')
  input.value = chatId
  document.body.appendChild(input)
  input.select()
  document.execCommand('copy')
  document.body.removeChild(input)
  ElMessage.success('已复制群聊ID')
}
</script>

<style scoped>
.feishu-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chats-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
