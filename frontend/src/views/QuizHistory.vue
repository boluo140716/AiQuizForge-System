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
                v-if="item.status === 'completed'"
                type="primary"
                size="small"
                @click="$router.push('/quiz/' + item.id)"
              >
                <el-icon><Pointer /></el-icon>
                {{ item.attempt_count > 0 ? '再次答题' : '开始答题' }}
              </el-button>
              <el-button
                v-if="item.status === 'completed' && item.attempt_count > 0"
                size="small"
                @click="$router.push('/quiz/' + item.id + '/review')"
              >
                <el-icon><View /></el-icon>
                查看回顾
              </el-button>
              <el-button
                v-if="item.status === 'completed'"
                size="small"
                type="danger"
                :loading="deletingQuizId === item.id"
                :disabled="deletingQuizId !== null && deletingQuizId !== item.id"
                @click="handleDeleteQuiz(item, 'completed')"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
              <el-button
                v-if="item.status === 'processing'"
                size="small"
                :loading="true"
                disabled
              >
                生成中...
              </el-button>
              <el-button
                v-if="item.status === 'processing'"
                size="small"
                type="danger"
                :loading="cancellingQuizId === item.id"
                :disabled="cancellingQuizId !== null && cancellingQuizId !== item.id"
                @click="handleCancelQuiz(item)"
              >
                取消并删除
              </el-button>
              <div v-if="item.status === 'failed'" class="failed-row">
                <el-tag type="danger" size="small">
                  {{ item.error_message || '生成失败' }}
                </el-tag>
                <el-button
                  size="small"
                  type="danger"
                  :loading="deletingQuizId === item.id"
                  :disabled="deletingQuizId !== null && deletingQuizId !== item.id"
                  @click="handleDeleteQuiz(item, 'failed')"
                >
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Document, CircleCheck, TrendCharts, Trophy,
  Pointer, View, Delete
} from '@element-plus/icons-vue'
import { getQuizHistory, cancelQuizGeneration, deleteQuiz } from '@/api'

const loading = ref(false)
const quizList = ref([])
const cancellingQuizId = ref(null)
const deletingQuizId = ref(null)

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

// 删除测验
const handleDeleteQuiz = async (item, status) => {
  const msg = status === 'completed'
    ? '确定要删除该测验吗？删除后答题记录和错题本数据也会被清空，无法恢复'
    : '确定要删除该已取消的测验吗？删除后数据无法恢复'

  try {
    await ElMessageBox.confirm(msg, '删除确认', {
      confirmButtonText: '确定删除', cancelButtonText: '返回', type: 'warning'
    })
  } catch {
    return
  }

  deletingQuizId.value = item.id
  try {
    await deleteQuiz(item.id)
    // 直接从列表中移除该条目
    const idx = quizList.value.findIndex(q => q.id === item.id)
    if (idx !== -1) quizList.value.splice(idx, 1)
    ElMessage.success('删除成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    deletingQuizId.value = null
  }
}

// 取消并删除生成中的测验
const handleCancelQuiz = async (item) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消并删除该测验吗？删除后数据无法恢复',
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '返回', type: 'warning' }
    )
  } catch {
    return
  }

  cancellingQuizId.value = item.id
  try {
    await cancelQuizGeneration(item.id)
    // 直接从列表中移除该条目
    const idx = quizList.value.findIndex(q => q.id === item.id)
    if (idx !== -1) quizList.value.splice(idx, 1)
    ElMessage.success('删除成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    cancellingQuizId.value = null
  }
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
  background: #f5f5f7;
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
  color: #1d1d1f;
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
  background: #1d1d1f;
}

.done-icon {
  background: #67c23a;
}

.avg-icon {
  background: #86868b;
}

.best-icon {
  background: #e6a23c;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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
  color: #1d1d1f;
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
  border-left: 1px solid #e0e0e0;
  border-right: 1px solid #e0e0e0;
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
  color: #1d1d1f;
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

.failed-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-button--primary) {
  background: #1d1d1f;
  border: none;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .quiz-history-page {
    padding: 12px;
  }

  .page-header {
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  .page-header h2 {
    font-size: 18px;
  }

  .stats-row {
    margin-bottom: 16px;
  }

  .stats-row :deep(.el-row) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .stats-row :deep(.el-col) {
    flex: 0 0 100% !important;
    max-width: 100% !important;
    margin-bottom: 12px;
    padding-left: 0 !important;
    padding-right: 0 !important;
  }

  .stat-value {
    font-size: 24px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    font-size: 20px;
    border-radius: 10px;
  }

  .quiz-item-main {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .quiz-stats {
    flex-direction: row;
    justify-content: space-around;
    gap: 8px;
    padding: 16px 0;
    border-left: none;
    border-right: none;
    border-top: 1px solid #e0e0e0;
    border-bottom: 1px solid #e0e0e0;
  }

  .stat-num {
    font-size: 18px;
  }

  .quiz-actions {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
    min-width: auto;
  }

  .quiz-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .note-title {
    font-size: 15px;
    white-space: normal;
  }
}
</style>
