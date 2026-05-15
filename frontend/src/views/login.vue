<template>
  <div class="login-container">
    <div class="login-bg"></div>
    <el-card class="login-card">
      <div class="card-header">
        <h2>欢迎回来</h2>
        <p class="subtitle">登录 QuizForge，继续你的学习之旅</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            clearable
            autofocus
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :prefix-icon="Lock"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="handleLogin"
            :loading="loading"
            :disabled="loading"
            class="login-btn"
          >
            {{ loading ? '登录中...' : '立即登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="footer-tip">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await axios.post('/api/v1/auth/login/', {
        username: form.username,
        password: form.password
      })

      // 存储令牌
      localStorage.setItem('access_token', res.data.access)
      localStorage.setItem('refresh_token', res.data.refresh)
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access}`

      ElMessage.success('登录成功')
      router.push('/')
    } catch (error) {
      const detail = error.response?.data?.detail
      if (detail) {
        ElMessage.error(detail)
      } else {
        ElMessage.error('登录失败，请检查用户名和密码')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #f5f5f7;
  z-index: 0;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 400px;
  padding: 10px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  background: #ffffff;
}

.card-header {
  text-align: center;
  margin-bottom: 30px;
}

.card-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #86868b;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  background: #1d1d1f !important;
  border: none !important;
  transition: all 0.3s ease;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.login-btn:disabled {
  opacity: 0.7;
}

.footer-tip {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #86868b;
}

.footer-tip a {
  color: #1d1d1f;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.footer-tip a:hover {
  text-decoration: underline;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #1d1d1f;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  padding: 4px 12px;
}

:deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1);
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .login-container {
    padding: 16px;
  }

  .login-card {
    width: 100%;
    max-width: 400px;
  }

  .card-header h2 {
    font-size: 22px;
  }

  .card-header {
    margin-bottom: 20px;
  }
}
</style>