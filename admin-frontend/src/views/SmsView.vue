<template>
  <div class="fd-page">
    <PageHeader title="短信管理" description="维护短信通知联系人列表，支持新增、编辑、删除与即时刷新。">
      <template #actions>
        <ActionBar>
          <el-button type="primary" @click="handleReload">
            <el-icon><Refresh /></el-icon>
            热加载配置
          </el-button>
        </ActionBar>
      </template>
    </PageHeader>

    <DataCard title="短信联系人">
      <ContactList
        :contacts="smsStore.contacts"
        :loading="smsStore.loading"
        :on-add="smsStore.createContact"
        :on-edit="smsStore.updateContact"
        :on-delete="smsStore.deleteContact"
        :on-refresh="smsStore.fetchContacts"
      />
    </DataCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useSmsStore } from '@/stores/sms'
import { smsApi } from '@/api/sms'
import ContactList from '@/components/ContactList.vue'
import ActionBar from '@/components/layout/ActionBar.vue'
import DataCard from '@/components/layout/DataCard.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const smsStore = useSmsStore()

onMounted(async () => {
  await smsStore.fetchConfig()
})

const handleReload = async () => {
  try {
    await smsApi.reloadConfig()
    await smsStore.fetchConfig()
    ElMessage.success('配置热加载成功')
  } catch {
    ElMessage.error('配置热加载失败')
  }
}
</script>
