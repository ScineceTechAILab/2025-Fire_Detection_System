<template>
  <div class="sms-view">
    <el-card class="contacts-card">
      <template #header>
        <div class="card-header">
          <span>云短信 - 紧急联系人列表</span>
          <el-button type="primary" size="small" @click="handleReload">
            <el-icon><Refresh /></el-icon>
            热加载配置
          </el-button>
        </div>
      </template>
      
      <ContactList
        :contacts="smsStore.contacts"
        :loading="smsStore.loading"
        :on-add="smsStore.createContact"
        :on-edit="smsStore.updateContact"
        :on-delete="smsStore.deleteContact"
        :on-refresh="smsStore.fetchContacts"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useSmsStore } from '@/stores/sms'
import { smsApi } from '@/api/sms'
import ContactList from '@/components/ContactList.vue'

const smsStore = useSmsStore()

onMounted(async () => {
  await smsStore.fetchConfig()
})

const handleReload = async () => {
  try {
    await smsApi.reloadConfig()
    await smsStore.fetchConfig()
    ElMessage.success('配置热加载成功')
  } catch (error) {
    console.error(error)
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

<style scoped>
.sms-view {
  padding: 20px;
}
</style>
