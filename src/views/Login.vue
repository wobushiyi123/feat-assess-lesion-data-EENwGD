<template>
  <div class="login-container">
    <div class="login-bg-decoration">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
      <div class="bg-circle bg-circle-4"></div>
    </div>
    <div class="login-box" :class="{ shake: shake }">
      <div class="login-header">
        <div class="login-logo">
          <svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="8" y="14" width="14" height="36" rx="3" fill="var(--primary-color)"/>
            <rect x="23" y="8" width="14" height="44" rx="3" fill="var(--primary-color)"/>
            <rect x="38" y="20" width="14" height="30" rx="3" fill="var(--primary-color)"/>
          </svg>
        </div>
        <h1>RECIST病灶评估系统</h1>
        <p>智能肿瘤疗效评估平台</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <div class="input-group">
            <span class="input-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </span>
            <el-input v-model="form.username" placeholder="用户名" size="large" />
          </div>
        </el-form-item>
        <el-form-item prop="password">
          <div class="input-group">
            <span class="input-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </span>
            <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="handleLogin" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="login-btn">
            <el-icon v-if="loading"><Loading /></el-icon>
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { authApi } from '../api'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const shake = ref(false)
const form = ref({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  try {
    await formRef.value.validate()
  } catch {
    shake.value = true
    setTimeout(() => shake.value = false, 500)
    return
  }
  
  loading.value = true
  try {
    const res = await authApi.login(form.value.username, form.value.password)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    console.error(e)
    shake.value = true
    setTimeout(() => shake.value = false, 500)
    ElMessage.error('登录失败：用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
}

.login-box {
  background: white;
  border-radius: var(--radius-lg);
  padding: 60px 80px;
  width: 100%;
  max-width: 520px;
  box-shadow: var(--shadow-lg);
  position: relative;
  z-index: 10;
  animation: slideUp 0.5s ease;
  border: 1px solid var(--border-light);
}

.login-box.shake {
  animation: shake 0.5s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-10px); }
  40% { transform: translateX(10px); }
  60% { transform: translateX(-8px); }
  80% { transform: translateX(8px); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-header {
  text-align: center;
  margin-bottom: 48px;
}

.login-logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-light);
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
}

.login-logo svg {
  width: 32px;
  height: 32px;
}

.login-header h1 {
  font-size: 24px;
  color: var(--text-primary);
  margin-bottom: 8px;
  font-weight: 700;
  letter-spacing: 1px;
}

.login-header p {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.input-group {
  display: flex;
  align-items: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-normal);
  background: #fafafa;
  width: 100%;
  height: 48px;
}

.input-group:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
  background: white;
}

.input-icon {
  width: 48px;
  height: 100%;
  font-size: 18px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-right: 1px solid var(--border-light);
  background: white;
}

.input-icon svg {
  width: 18px;
  height: 18px;
}

.input-group :deep(.el-input__wrapper) {
  box-shadow: none !important;
  border: none !important;
  background: transparent !important;
  padding: 0 16px;
}

.input-group :deep(.el-input__inner) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  height: 48px;
  line-height: 48px;
}

.el-form-item {
  margin-bottom: 24px;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--radius-md);
  background: var(--primary-gradient);
  border: none;
  transition: all var(--transition-normal);
  margin-top: 8px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.3);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

@media (max-width: 600px) {
  .login-container {
    padding: 20px;
  }

  .login-box {
    padding: 40px 28px;
    max-width: 100%;
  }

  .login-header {
    margin-bottom: 32px;
  }
}
</style>