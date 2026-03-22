<template>
  <router-view v-if="isLoginPage" />

  <el-container v-else class="app-shell">
    <el-header class="app-shell__header">
      <div class="header-left">
        <el-button class="menu-toggle" text @click="drawerVisible = true">
          <el-icon><Operation /></el-icon>
        </el-button>
        <div class="brand">
          <div class="brand__logo">FD</div>
          <div>
            <div class="brand__title">STALAB 火灾检测系统</div>
            <div class="brand__subtitle">管理后台</div>
          </div>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="info" effect="plain">实时配置</el-tag>
      </div>
    </el-header>

    <el-container class="app-shell__body">
      <el-aside class="app-shell__aside" width="240px">
        <div class="menu-wrapper">
          <el-menu
            :default-active="activeMenu"
            router
            class="app-menu"
            @select="drawerVisible = false"
          >
            <el-menu-item index="/feishu">
              <el-icon><ChatDotRound /></el-icon>
              <span>飞书管理</span>
            </el-menu-item>
            <el-menu-item index="/sms">
              <el-icon><Message /></el-icon>
              <span>短信管理</span>
            </el-menu-item>
            <el-menu-item index="/system">
              <el-icon><Setting /></el-icon>
              <span>系统参数</span>
            </el-menu-item>
            <el-menu-item index="/credentials">
              <el-icon><Key /></el-icon>
              <span>凭证配置</span>
            </el-menu-item>
            <el-menu-item index="/logs">
              <el-icon><Document /></el-icon>
              <span>日志查询</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-aside>

      <el-main class="app-shell__main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-drawer v-model="drawerVisible" direction="ltr" size="240px" :with-header="false">
    <el-menu :default-active="activeMenu" router class="app-menu mobile" @select="drawerVisible = false">
      <el-menu-item index="/feishu">
        <el-icon><ChatDotRound /></el-icon>
        <span>飞书管理</span>
      </el-menu-item>
      <el-menu-item index="/sms">
        <el-icon><Message /></el-icon>
        <span>短信管理</span>
      </el-menu-item>
      <el-menu-item index="/system">
        <el-icon><Setting /></el-icon>
        <span>系统参数</span>
      </el-menu-item>
      <el-menu-item index="/credentials">
        <el-icon><Key /></el-icon>
        <span>凭证配置</span>
      </el-menu-item>
      <el-menu-item index="/logs">
        <el-icon><Document /></el-icon>
        <span>日志查询</span>
      </el-menu-item>
    </el-menu>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ChatDotRound, Document, Key, Message, Operation, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const drawerVisible = ref(false)

const isLoginPage = computed(() => route.path === '/login')
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-shell__header {
  height: 64px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid var(--fd-border);
  backdrop-filter: blur(10px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 18px;
  position: sticky;
  top: 0;
  z-index: 30;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.menu-toggle {
  display: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand__logo {
  width: 34px;
  height: 34px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #1f6feb, #1d4ed8);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.8px;
}

.brand__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--fd-text);
  line-height: 1.1;
}

.brand__subtitle {
  font-size: 12px;
  color: var(--fd-text-secondary);
}

.app-shell__body {
  min-height: calc(100vh - 64px);
}

.app-shell__aside {
  border-right: 1px solid var(--fd-border);
  background: #f6f9ff;
}

.menu-wrapper {
  padding: 14px 10px;
}

.app-menu {
  border-right: none;
  background: transparent;
}

.app-shell__main {
  padding: 0;
  overflow-x: hidden;
}

:deep(.app-menu .el-menu-item) {
  height: 44px;
  margin: 4px 0;
  border-radius: 10px;
}

:deep(.app-menu .el-menu-item.is-active) {
  background: #eaf2ff;
  color: #1d4ed8;
  font-weight: 600;
}

@media (max-width: 992px) {
  .menu-toggle {
    display: inline-flex;
  }

  .app-shell__aside {
    display: none;
  }

  .brand__subtitle {
    display: none;
  }
}
</style>
