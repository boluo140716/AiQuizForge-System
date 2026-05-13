<template>
  <div class="profile-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>个人主页</h2>
    </div>

    <!-- 用户信息卡片 -->
    <el-card class="profile-card" v-loading="loading">
      <div class="user-header">
        <el-avatar :size="80" class="user-avatar">
          {{ profile?.username?.charAt(0)?.toUpperCase() || 'U' }}
        </el-avatar>
        <div class="user-info">
          <h1 class="username">{{ profile?.username }}</h1>
          <p class="email">{{ profile?.email || '未设置邮箱' }}</p>
          <p class="join-date">加入于 {{ profile?.date_joined?.slice(0, 10) }}</p>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon notes-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_notes || 0 }}</div>
            <div class="stat-label">总笔记数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="$router.push('/quiz-history')">
          <div class="stat-icon quiz-icon">
            <el-icon><List /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_quizzes || 0 }}</div>
            <div class="stat-label">总测验数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="$router.push('/wrong-questions')">
          <div class="stat-icon wrong-icon">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_wrong_questions || 0 }}</div>
            <div class="stat-label">错题数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon rate-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ ((profile?.avg_correct_rate || 0) * 100).toFixed(0) }}%</div>
            <div class="stat-label">平均正确率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学习进度 -->
    <el-card class="progress-card">
      <h3>学习概览</h3>
      <div class="progress-item">
        <span class="progress-label">笔记完成度</span>
        <el-progress
          :percentage="notesProgress"
          :stroke-width="10"
          :color="'#667eea'"
        />
      </div>
      <div class="progress-item">
        <span class="progress-label">测验参与度</span>
        <el-progress
          :percentage="quizProgress"
          :stroke-width="10"
          :color="'#764ba2'"
        />
      </div>
      <div class="progress-item">
        <span class="progress-label">错题纠正率</span>
        <el-progress
          :percentage="wrongProgress"
          :stroke-width="10"
          :color="'#f56c6c'"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, Document, List, Warning, TrendCharts } from '@element-plus/icons-vue'
import { getUserProfile } from '@/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const profile = ref(null)

const notesProgress = computed(() => {
  const total = profile.value?.total_notes || 0
  return Math.min(total * 10, 100)
})

const quizProgress = computed(() => {
  const total = profile.value?.total_quizzes || 0
  return Math.min(total * 20, 100)
})

const wrongProgress = computed(() => {
  const wrong = profile.value?.total_wrong_questions || 0
  const total = profile.value?.total_quizzes || 1
  if (total === 0) return 100
  return Math.max(100 - (wrong / total * 100), 0)
})

const fetchProfile = async () => {
  loading.value = true
  try {
    const res = await getUserProfile()
    profile.value = res.data
  } catch (e) {
    ElMessage.error('获取个人资料失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchProfile)
</script>

<style scoped>
.profile-page {
  padding: 24px;
  min-height: 100vh;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.profile-card {
  margin-bottom: 24px;
  border-radius: 16px;
}

.user-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 32px;
  font-weight: 600;
}

.user-info .username {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.user-info .email {
  margin: 0 0 4px;
  font-size: 14px;
  color: #909399;
}

.user-info .join-date {
  margin: 0;
  font-size: 13px;
  color: #c0c4cc;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-card.clickable {
  cursor: pointer;
  transition: all 0.3s ease;
}

.stat-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.notes-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.quiz-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
}

.wrong-icon {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: #fff;
}

.rate-icon {
  background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.progress-card {
  border-radius: 16px;
}

.progress-card h3 {
  margin: 0 0 20px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.progress-item {
  margin-bottom: 20px;
}

.progress-item:last-child {
  margin-bottom: 0;
}

.progress-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}
</style>