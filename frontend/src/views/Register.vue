<template>
  <div class="register-container">
    <div class="register-bg"></div>
    <el-card class="register-card">
      <div class="card-header">
        <h2>注册 QuizForge</h2>
        <p class="subtitle">开启你的智能学习之旅</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="handleRegister"
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
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱（可选）"
            :prefix-icon="Message"
            clearable
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码（至少8位）"
            :prefix-icon="Lock"
            clearable
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="password2">
          <el-input
            v-model="form.password2"
            type="password"
            show-password
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="handleRegister"
            :loading="loading"
            :disabled="loading"
            class="register-btn"
          >
            {{ loading ? '注册中...' : '立即注册' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="footer-tip">
        已有账号？<router-link to="/login">立即登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { User, Message, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  password2: ''
})

// 自定义校验：确认密码
const validatePassword2 = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3-20 个字符', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要 8 位', trigger: 'blur' }
  ],
  password2: [
    { validator: validatePassword2, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const payload = {
        username: form.username,
        password: form.password,
        password2: form.password2
      }
      // 只在有值时发送 email
      if (form.email) {
        payload.email = form.email
      }

      await axios.post('/api/v1/auth/register/', payload)
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } catch (error) {
      const data = error.response?.data
      if (data) {
        // 处理后端返回的字段错误
        const messages = []
        for (const key in data) {
          const fieldName = {
            username: '用户名',
            password: '密码',
            email: '邮箱'
          }[key] || key
          const fieldErrors = [].concat(data[key])
          messages.push(`${fieldName}: ${fieldErrors.join(', ')}`)
        }
        ElMessage.error(messages.join('；'))
      } else {
        ElMessage.error('注册失败，请稍后重试')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.register-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #f5f5f7;
  z-index: 0;
}

.register-card {
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

.register-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  background: #1d1d1f !important;
  border: none !important;
  transition: all 0.3s ease;
}

.register-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.register-btn:disabled {
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
  .register-container {
    padding: 16px;
  }

  .register-card {
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