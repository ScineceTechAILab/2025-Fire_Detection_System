<template>
  <div class="login-page">
    <div class="login-page__bg"></div>
    <el-card class="login-card fd-card" shadow="never">
      <div class="login-card__header">
        <div class="login-card__badge">FD</div>
        <h1>管理后台登录</h1>
        <p>火灾检测系统管理与配置入口</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item prop="user" label="用户名">
          <el-input v-model="form.user" placeholder="请输入用户名" @keyup.enter="handleSubmit">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password" label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            @keyup.enter="handleSubmit"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>

        <div class="login-card__extra">
          <el-checkbox v-model="remember">记住用户名</el-checkbox>
        </div>

        <el-button type="primary" class="submit-btn" :loading="loading" @click="handleSubmit">登录</el-button>
      </el-form>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
        class="login-card__error"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import request from '@/utils/request'
import type { FormInstance, FormRules } from 'element-plus'
import type { LoginResponse } from '@/types'

interface FormData {
  user: string
  password: string
}

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')
const remember = ref(true)
const form = ref<FormData>({ user: '', password: '' })

const rules: FormRules = {
  user: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

onMounted(() => {
  const saved = localStorage.getItem('remember_user')
  if (saved) {
    form.value.user = saved
  }
})

const handleSubmit = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''
  try {
    const resp = await request.post<LoginResponse>('/api/v1/auth/login', { ...form.value })
    const data = resp.data
    localStorage.setItem('auth_token', data.token)
    localStorage.setItem('csrf_token', data.csrf_token)

    if (remember.value) {
      localStorage.setItem('remember_user', form.value.user)
    } else {
      localStorage.removeItem('remember_user')
    }

    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/feishu'
    router.replace(redirect)
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.login-page__bg {
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(460px 260px at 15% 20%, rgba(31, 111, 235, 0.2), transparent),
    radial-gradient(380px 240px at 85% 75%, rgba(245, 158, 11, 0.16), transparent),
    linear-gradient(160deg, #f8fbff 0%, #edf4ff 62%, #f8fbff 100%);
}

.login-card {
  width: min(420px, 100%);
  padding: 12px 14px 18px;
  border-radius: var(--fd-radius-md);
  box-shadow: var(--fd-shadow-lg);
}

.login-card__header {
  text-align: center;
  margin-bottom: 18px;
}

.login-card__badge {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  margin: 0 auto 12px;
  color: white;
  background: linear-gradient(140deg, #1f6feb, #1d4ed8);
  font-weight: 700;
  letter-spacing: 1px;
}

.login-card__header h1 {
  margin: 0;
  font-size: 24px;
}

.login-card__header p {
  margin: 8px 0 0;
  color: var(--fd-text-secondary);
  font-size: 13px;
}

.login-card__extra {
  margin: 2px 0 14px;
  display: flex;
  justify-content: flex-start;
}

.submit-btn {
  width: 100%;
  height: 40px;
  font-weight: 600;
}

.login-card__error {
  margin-top: 14px;
}
</style>
