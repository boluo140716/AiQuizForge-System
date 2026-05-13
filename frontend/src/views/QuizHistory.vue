<template>
  <div class="quiz-history-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>答题历史</h2>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon total-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总测验数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon done-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.completed }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon avg-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.avgRate }}%</div>
            <div class="stat-label">平均正确率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon best-icon">
            <el-icon><Trophy /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.best }}</div>
            <div class="stat-label">最佳得分</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 测验列表 -->
    <div v-loading="loading" class="quiz-list">
      <el-empty v-if="!loading && quizList.length === 0" description="还没有测验记录">
        <el-button type="primary" @click="$router.push('/notes')">去创建笔记</el-button>
      </el-empty>

      <div v-else>
        <el-card
          v-for="item in quizList"
          :key="item.id"
          class="quiz-item"
          shadow="hover"
        >
          <div class="quiz-item-main">
            <div class="quiz-info">
              <h4 class="note-title">{{ item.note_title }}</h4>
              <div class="quiz-meta">
                <el-tag :type="statusType(item.status)" size="small">
                  {{ statusLabel(item.status) }}
                </el-tag>
                <span class="question-num">{{ item.question_count }} 题</span>
                <span class="create-date">{{ item.created_at?.slice(0, 10) }}</span>
              </div>
            </div>

            <div class="quiz-stats">
              <div class="stat-item">
                <span class="stat-num">{{ item.attempt_count }}</span>
                <span class="stat-text">答题次数</span>
              </div>
              <div class="stat-item best">
                <span class="stat-num">{{ item.best_score }}</span>
                <span class="stat-text">最佳得分</span>
              </div>
              <div class="stat-item rate">
                <span class="stat-num">{{ bestRate(item) }}%</span>
                <span class="stat-text">最佳正确率</span>
              </div>
            </div>

            <div class="quiz-actions">
              <el-button
                v-if="item.status === 'completed' && item.attempt_count > 0"
                type="primary"
                size="small"
                @click="$router.push(`/quiz/${item.id}`)"
              >
                <el-icon><Pointer /></el-icon>
                再次答题
              </el-button>
              <el-button
                v-if="item.status === 'completed' && item.attempt_count > 0"
                size="small"
                @click="$router.push(`/quiz/${item.id}/review`)"
              >
                <el-icon><View /></el-icon>
                查看回顾
              </el-button>
              <el-button
                v-if="item.status === 'completed' && item.attempt_count > 0"
                size="small"
                @click="viewAttempts(item)"
              >
                <el-icon><List /></el-icon>
                答题记录
              </el-button>
              <el-button
                v-if="item.status === 'processing'"
                size="small"
                :loading="true"
                disabled
              >
                生成中...
              </el-button>
              <el-tag v-if="item.status === 'failed'" type="danger" size="small">
                {{ item.error_message || '生成失败' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Document, CircleCheck, TrendCharts, Trophy,
  Pointer, View, List
} from '@element-plus/icons-vue'
import { getQuizHistory } from '@/api'

const router = useRouter()
const loading = ref(false)
const quizList = ref([])

const stats = computed(() => {
  const list = quizList.value
  const completed = list.filter(q => q.status === 'completed' && q.attempt_count > 0)

  let totalRate = 0
  let rateCount = 0
  let bestScore = 0

  completed.forEach(q => {
    if (q.best_score > bestScore) bestScore = q.best_score
    if (q.question_count > 0) {
      totalRate += (q.best_score / q.question_count) * 100
      rateCount++
    }
  })

  return {
    total: list.length,
    completed: completed.length,
    avgRate: rateCount > 0 ? (totalRate / rateCount).toFixed(0) : 0,
    best: bestScore
  }
})

const statusType = (status) => {
  const map = { processing: 'warning', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const statusLabel = (status) => {
  const map = { processing: '生成中', completed: '已完成', failed: '生成失败' }
  return map[status] || status
}

const bestRate = (item) => {
  if (item.question_count > 0 && item.best_score > 0) {
    return ((item.best_score / item.question_count) * 100).toFixed(0)
  }
  return 0
}

const viewAttempts = (item) => {
  router.push(`/quiz/${item.id}/review`)
}

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await getQuizHistory()
    quizList.value = res.data
  } catch (e) {
    ElMessage.error('获取答题历史失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchHistory)
</script>

<style scoped>
.quiz-history-page {
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
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

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #fff;
}

.total-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.done-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.avg-icon {
  background: linear-gradient(135deg, #409eff 0%, #53a8ff 100%);
}

.best-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #fbbc24 100%);
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

.quiz-list {
  min-height: 300px;
}

.quiz-item {
  margin-bottom: 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.quiz-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.quiz-item-main {
  display: flex;
  align-items: center;
  gap: 24px;
}

.quiz-info {
  flex: 1;
  min-width: 0;
}

.note-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quiz-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.question-num,
.create-date {
  font-size: 13px;
  color: #909399;
}

.quiz-stats {
  display: flex;
  gap: 24px;
  padding: 0 24px;
  border-left: 1px solid #e4e7ed;
  border-right: 1px solid #e4e7ed;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #667eea;
}

.stat-item.best .stat-num {
  color: #67c23a;
}

.stat-item.rate .stat-num {
  color: #e6a23c;
}

.stat-text {
  font-size: 12px;
  color: #909399;
}

.quiz-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 100px;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}
</style>