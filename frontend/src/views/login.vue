<template>
  <div class="auth-shell">
    <aside class="auth-aside qf-canvas">
      <div class="auth-brand">
        <span class="auth-mark">QF</span>
        <span class="auth-brand-name">QuizForge</span>
      </div>

      <div class="auth-thesis">
        <p class="qf-eyebrow">QUIZFORGE / 01</p>
        <h1>把笔记<br />变成会追问你的题。</h1>
        <p class="auth-lede">
          记录、出题、答题、复习——一条属于你自己的学习闭环。
        </p>
      </div>

      <div class="auth-foot">笔记 · 测验 · 掌握 · 复习</div>
    </aside>

    <main class="auth-main">
      <div class="auth-card">
        <p class="qf-eyebrow">账户 / 登录</p>
        <h2>欢迎回来</h2>
        <p class="auth-sub">继续你的学习进度</p>

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
      </div>
    </main>
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

<style scoped>
/* ===== study desk auth ===== */
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  background: var(--qf-paper);
}

.auth-aside {
  position: relative;
  padding: 42px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-right: 1px solid var(--qf-line);
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auth-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  background: var(--qf-ink);
  color: var(--qf-paper);
  font-family: var(--qf-mono);
  font-size: 12px;
  font-weight: 700;
}

.auth-brand-name {
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--qf-ink);
}

.auth-thesis h1 {
  margin: 0 0 18px;
  font-size: clamp(34px, 4.4vw, 64px);
  line-height: 1.02;
  letter-spacing: -0.045em;
  font-weight: 800;
  color: var(--qf-ink);
}

.auth-lede {
  max-width: 34ch;
  margin: 0;
  color: var(--qf-ink-soft);
  font-size: 15px;
  line-height: 1.7;
}

.auth-foot {
  font-family: var(--qf-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--qf-muted);
}

.auth-main {
  display: grid;
  place-items: center;
  padding: 32px;
}

.auth-card {
  position: relative;
  width: min(400px, 100%);
  padding: 34px 32px;
  background: var(--qf-surface);
  border: 1px solid var(--qf-line);
  border-radius: 3px;
}

.auth-card::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 24px;
  width: 56px;
  height: 4px;
  background: var(--qf-accent);
}

.auth-card h2 {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--qf-ink);
}

.auth-sub {
  margin: 0 0 24px;
  color: var(--qf-muted);
  font-size: 13px;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  background: var(--qf-primary) !important;
  border-color: var(--qf-primary) !important;
}

.footer-tip {
  margin-top: 18px;
  text-align: center;
  font-size: 13px;
  color: var(--qf-muted);
}

.footer-tip a {
  margin-left: 4px;
  color: var(--qf-primary);
  font-weight: 700;
  text-decoration: none;
}

.footer-tip a:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-aside {
    display: none;
  }

  .auth-main {
    padding: 20px;
  }
}
</style>