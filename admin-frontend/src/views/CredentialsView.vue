<template>
  <div class="fd-page">
    <PageHeader title="凭证配置" description="集中管理飞书与短信服务密钥，修改后即时生效。">
      <template #actions>
        <ActionBar>
          <el-button type="primary" :loading="loading" @click="loadCredentials">刷新</el-button>
        </ActionBar>
      </template>
    </PageHeader>

    <DataCard title="服务商设置">
      <el-form label-width="140px" class="provider-form">
        <el-form-item label="短信服务商">
          <el-select v-model="selectedSmsProvider" @change="handleSmsProviderChange" style="width: 220px">
            <el-option label="阿里云" value="aliyun" />
          </el-select>
        </el-form-item>
      </el-form>
    </DataCard>

    <DataCard>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="飞书配置" name="feishu">
          <el-form :model="feishuForm" label-width="160px" class="credentials-form">
            <el-form-item label="应用 ID (App ID)">
              <el-input v-model="feishuForm.app_id" placeholder="请输入飞书 App ID" />
            </el-form-item>
            <el-form-item label="应用密钥 (App Secret)">
              <el-input v-model="feishuForm.app_secret" type="password" show-password placeholder="请输入飞书 App Secret" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveFeishu">保存飞书配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="阿里云配置" name="aliyun">
          <el-form :model="aliyunForm" label-width="160px" class="credentials-form">
            <el-form-item label="AccessKey ID">
              <el-input v-model="aliyunForm.access_key_id" placeholder="请输入 AccessKey ID" />
            </el-form-item>
            <el-form-item label="AccessKey Secret">
              <el-input v-model="aliyunForm.access_key_secret" type="password" show-password placeholder="请输入 AccessKey Secret" />
            </el-form-item>
            <el-form-item label="短信签名">
              <el-input v-model="aliyunForm.sms_sign_name" placeholder="请输入短信签名" />
            </el-form-item>
            <el-form-item label="短信模板码">
              <el-input v-model="aliyunForm.sms_template_code" placeholder="请输入短信模板码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveAliyun">保存阿里云配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </DataCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCredentials, updateAliyunCredentials, updateFeishuCredentials, updateSmsProvider } from '@/api/credentials'
import type { AliyunCredentials, FeishuCredentials } from '@/api/credentials'
import ActionBar from '@/components/layout/ActionBar.vue'
import DataCard from '@/components/layout/DataCard.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const activeTab = ref('feishu')
const loading = ref(false)
const saving = ref(false)
const selectedSmsProvider = ref('aliyun')

const feishuForm = reactive<FeishuCredentials>({
  app_id: '',
  app_secret: ''
})

const aliyunForm = reactive<AliyunCredentials>({
  access_key_id: '',
  access_key_secret: '',
  sms_sign_name: '',
  sms_template_code: ''
})

const loadCredentials = async () => {
  loading.value = true
  try {
    const res = await getCredentials()
    const data = res.data
    selectedSmsProvider.value = data.sms_provider || 'aliyun'
    feishuForm.app_id = data.feishu?.app_id || ''
    feishuForm.app_secret = data.feishu?.app_secret || ''
    aliyunForm.access_key_id = data.aliyun?.access_key_id || ''
    aliyunForm.access_key_secret = data.aliyun?.access_key_secret || ''
    aliyunForm.sms_sign_name = data.aliyun?.sms_sign_name || ''
    aliyunForm.sms_template_code = data.aliyun?.sms_template_code || ''
  } catch {
    ElMessage.error('加载凭证配置失败')
  } finally {
    loading.value = false
  }
}

const handleSmsProviderChange = async (provider: string) => {
  try {
    await updateSmsProvider(provider)
    ElMessage.success('短信服务商切换成功')
  } catch {
    ElMessage.error('短信服务商切换失败')
    selectedSmsProvider.value = 'aliyun'
  }
}

const saveFeishu = async () => {
  saving.value = true
  try {
    await updateFeishuCredentials(feishuForm)
    ElMessage.success('飞书配置保存成功')
  } catch {
    ElMessage.error('飞书配置保存失败')
  } finally {
    saving.value = false
  }
}

const saveAliyun = async () => {
  saving.value = true
  try {
    await updateAliyunCredentials(aliyunForm)
    ElMessage.success('阿里云配置保存成功')
  } catch {
    ElMessage.error('阿里云配置保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadCredentials)
</script>

<style scoped>
.provider-form,
.credentials-form {
  max-width: 760px;
}
</style>
