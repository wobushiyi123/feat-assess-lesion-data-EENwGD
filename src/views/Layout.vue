<template>
  <div class="app-container">
    <header class="app-header" :class="{ scrolled: isScrolled }">
      <div class="header-content">
        <router-link to="/" class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="10" width="10" height="24" rx="2" fill="currentColor"/>
              <rect x="15" y="6" width="10" height="28" rx="2" fill="currentColor"/>
              <rect x="26" y="14" width="10" height="20" rx="2" fill="currentColor"/>
            </svg>
          </div>
          <div class="logo-text">
            <h1 class="logo-title">RECIST病灶评估系统</h1>
            <p class="logo-subtitle">智能肿瘤疗效评估平台</p>
          </div>
        </router-link>
        <nav class="nav-menu">
          <router-link 
            v-for="item in navItems" 
            :key="item.path"
            :to="item.path" 
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            {{ item.label }}
          </router-link>
        </nav>
        <div class="header-right">
          <div class="user-info" @click="handleLogout">
            <el-avatar :size="32" :style="{ backgroundColor: 'var(--primary-color)', fontSize: '14px' }">
              {{ userInitial }}
            </el-avatar>
            <div class="user-details">
              <span class="username">{{ username }}</span>
              <span class="logout-text">退出登录</span>
            </div>
            <el-icon class="logout-icon"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="slide" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
    <footer class="app-footer">
      <div class="footer-content">
        <p>RECIST病灶评估系统 © 2026</p>
        <p class="footer-version">Version 1.0.0</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const isScrolled = ref(false)

const navItems = [
    { path: '/', label: '首页' },
    { path: '/upload', label: '数据导入' },
    { path: '/subjects', label: '受试者' },
    { path: '/analysis', label: '智能分析' },
    { path: '/standard', label: '评估标准' }
  ]

const user = JSON.parse(localStorage.getItem('user') || '{}')
const username = computed(() => user.full_name || user.username || '用户')
const userInitial = computed(() => (user.username || 'U').charAt(0).toUpperCase())

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  if (path === '/subjects') return route.path.startsWith('/subjects') || route.path.startsWith('/assessment') || route.path.startsWith('/report')
  return route.path === path
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  ElMessage.success('已退出登录')
  router.push('/login')
}

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background-color: var(--primary-color);
  color: white;
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: white;
}

.logo-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-md);
}

.logo-icon svg {
  width: 20px;
  height: 20px;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  letter-spacing: 0.5px;
}

.logo-subtitle {
  font-size: 11px;
  opacity: 0.8;
  margin: 0;
}

.nav-menu {
  display: flex;
  gap: 0;
  flex: 1;
  justify-content: center;
}

.nav-item {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  position: relative;
  transition: color 0.2s;
}

.nav-item:hover {
  color: white;
}

.nav-item.active {
  color: white;
  font-weight: 600;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -14px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  background-color: white;
  border-radius: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  background-color: rgba(255, 255, 255, 0.1);
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: rgba(255, 255, 255, 0.15);
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 13px;
  font-weight: 500;
}

.logout-text {
  font-size: 11px;
  opacity: 0.75;
}

.logout-icon {
  font-size: 14px;
  opacity: 0.7;
}

.app-main {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 24px;
}

.app-footer {
  text-align: center;
  padding: 16px;
  color: var(--text-secondary);
  font-size: 12px;
  background-color: var(--card-bg);
  border-top: 1px solid var(--border-light);
  margin-top: auto;
}

.footer-content {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
}

.footer-version {
  opacity: 0.6;
}

@media (max-width: 900px) {
  .logo-subtitle {
    display: none;
  }
  
  .nav-item {
    padding: 8px 12px;
    font-size: 13px;
  }
  
  .user-details {
    display: none;
  }
}

@media (max-width: 768px) {
  .header-content {
    padding: 12px 16px;
  }
  
  .logo-title {
    font-size: 16px;
  }
  
  .nav-menu {
    gap: 0;
  }
  
  .nav-item {
    padding: 6px 8px;
    font-size: 12px;
  }
}
</style>