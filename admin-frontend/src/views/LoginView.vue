<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">STALAB 管理后台登录</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0">
        <el-form-item prop="user">
          <el-input v-model="form.user" placeholder="用户名" @keyup.enter="handleSubmit">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" @keyup.enter="handleSubmit">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="remember">记住用户名</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="submit-btn" :loading="loading" @click="handleSubmit">登录</el-button>
        </el-form-item>
      </el-form>
      <div v-if="errorMsg" class="tips">{{ errorMsg }}</div>
    </el-card>
  </div>
  <div class="login-bg"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '@/utils/request'
import type { LoginResponse } from '@/types'

interface FormData {
  user: string
  password: string
}

const router = useRouter()
const route = useRoute()
const formRef = ref()
const loading = ref(false)
const errorMsg = ref('')
const remember = ref(true)
const form = ref<FormData>({ user: '', password: '' })

const rules = {
  user: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

onMounted(() => {
  const saved = localStorage.getItem('remember_user')
  if (saved) form.value.user = saved
})

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
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
      errorMsg.value = e?.response?.data?.detail || e.message || '登录失败'
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 20px;
}
.login-card {
  width: 360px;
  padding: 10px 20px 20px 20px;
}
.title {
  text-align: center;
  margin: 10px 0 20px;
}
.submit-btn {
  width: 100%;
}
.tips {
  color: #f56c6c;
  text-align: center;
}
.login-bg {
  position: fixed;
  inset: 0;
  background: radial-gradient(1200px 600px at 10% 10%, #eef2ff, #f8fafc 60%);
  z-index: -1;
}
</style>

