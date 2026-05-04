<template>
  <div class="home">
    <h1>欢迎来到 QuizForge</h1>
    <p>你已成功登录！</p>
    <el-button @click="logout">退出登录</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  delete axios.defaults.headers.common['Authorization']
  ElMessage.success('已退出')
  router.push('/login')
}
</script>