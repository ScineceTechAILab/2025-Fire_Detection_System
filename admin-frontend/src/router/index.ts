import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/feishu'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/feishu',
    name: 'Feishu',
    component: () => import('@/views/FeishuView.vue')
  },
  {
    path: '/sms',
    name: 'Sms',
    component: () => import('@/views/SmsView.vue')
  },
  {
    path: '/system',
    name: 'System',
    component: () => import('@/views/SystemView.vue')
  },
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('@/views/LogsView.vue')
  },
  {
    path: '/credentials',
    name: 'Credentials',
    component: () => import('@/views/CredentialsView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.path === '/login') {
    return next()
  }
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  next()
})

export default router
