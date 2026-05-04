<template>
  <div class="register-container">
    <el-card class="register-card">
      <h2>注册 QuizForge</h2>
      <el-form :model="form" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码"></el-input>
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.password2" type="password" show-password placeholder="请再次输入密码"></el-input>
        </el-form-item>
        <el-button type="primary" @click="handleRegister" :loading="loading" style="width:100%">注册</el-button>
      </el-form>
      <p class="tip">已有账号？<router-link to="/login">去登录</router-link></p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const form = reactive({
  username: '',
  email: '',
  password: '',
  password2: ''
})
const loading = ref(false)

const handleRegister = async () => {
  if (!form.username || !form.email || !form.password || !form.password2) {
    ElMessage.warning('请填写所有字段')
    return
  }
  if (form.password !== form.password2) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    await axios.post('/api/v1/auth/register/', {
      username: form.username,
      email: form.email,
      password: form.password,
      password2: form.password2
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    const data = error.response?.data
    if (data) {
      const messages = []
      for (const key in data) {
        messages.push(...[].concat(data[key]))
      }
      ElMessage.error(messages.join(', '))
    } else {
      ElMessage.error('注册失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}
.register-card {
  width: 400px;
}
.tip {
  margin-top: 16px;
  text-align: center;
}
</style>