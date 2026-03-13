<template>
  <div class="credentials-container">
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>凭证配置管理</span>
          <el-button type="primary" @click="loadCredentials" :loading="loading">
            刷新
          </el-button>
        </div>
      </template>

      <el-form label-width="140px" style="margin-bottom: 20px;">
        <el-form-item label="短信服务商">
          <el-select v-model="selectedSmsProvider" @change="handleSmsProviderChange" style="width: 200px;">
            <el-option label="阿里云" value="aliyun" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="飞书配置" name="feishu">
          <el-form :model="feishuForm" label-width="140px">
            <el-form-item label="应用 ID (App ID)">
              <el-input v-model="feishuForm.app_id" placeholder="请输入飞书应用 ID" />
            </el-form-item>
            <el-form-item label="应用密钥 (App Secret)">
              <el-input v-model="feishuForm.app_secret" type="password" show-password placeholder="请输入飞书应用密钥" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveFeishu" :loading="saving">保存飞书配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="阿里云配置" name="aliyun">
          <el-form :model="aliyunForm" label-width="140px">
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
              <el-button type="primary" @click="saveAliyun" :loading="saving">保存阿里云配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCredentials, updateFeishuCredentials, updateAliyunCredentials, updateSmsProvider } from '@/api/credentials'
import type { FeishuCredentials, AliyunCredentials } from '@/api/credentials'

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

async function loadCredentials() {
  loading.value = true
  try {
    const res = await getCredentials()
    if (res.data) {
      selectedSmsProvider.value = res.data.sms_provider || 'aliyun'
      if (res.data.feishu) {
        feishuForm.app_id = res.data.feishu.app_id || ''
        feishuForm.app_secret = res.data.feishu.app_secret || ''
      }
      if (res.data.aliyun) {
        aliyunForm.access_key_id = res.data.aliyun.access_key_id || ''
        aliyunForm.access_key_secret = res.data.aliyun.access_key_secret || ''
        aliyunForm.sms_sign_name = res.data.aliyun.sms_sign_name || ''
        aliyunForm.sms_template_code = res.data.aliyun.sms_template_code || ''
      }
    }
  } catch (error) {
    ElMessage.error('加载凭证配置失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleSmsProviderChange(provider: string) {
  try {
    await updateSmsProvider(provider)
    ElMessage.success('短信服务商切换成功')
  } catch (error) {
    ElMessage.error('切换失败')
    console.error(error)
    selectedSmsProvider.value = 'aliyun'
  }
}

async function saveFeishu() {
  saving.value = true
  try {
    await updateFeishuCredentials(feishuForm)
    ElMessage.success('飞书配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

async function saveAliyun() {
  saving.value = true
  try {
    await updateAliyunCredentials(aliyunForm)
    ElMessage.success('阿里云配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadCredentials()
})
</script>

<style scoped>
.credentials-container {
  padding: 20px;
}

.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
