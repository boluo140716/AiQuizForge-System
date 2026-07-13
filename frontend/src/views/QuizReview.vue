<template>
  <div class="review-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>测验回顾</h2>
      <el-tag :type="statusType" size="default">{{ statusLabel }}</el-tag>
    </div>

    <div v-loading="loading" class="review-content">
      <!-- 测验概览 -->
      <el-card v-if="review" class="overview-card">
        <div class="overview-header">
          <div>
            <h3>{{ review.note_title }}</h3>
            <p class="overview-meta">
              {{ review.question_count }} 题 · {{ review.quiz_id && '测验 #' + review.quiz_id }}
            </p>
          </div>
          <div v-if="review.last_attempt" class="overview-score">
            <div class="score-circle" :class="scoreClass">
              <span class="score-val">{{ review.last_attempt.correct_rate ? (review.last_attempt.correct_rate * 100).toFixed(0) : 0 }}</span>
              <span class="score-unit">分</span>
            </div>
            <span class="score-detail">{{ review.last_attempt.score }} / {{ review.last_attempt.total }}</span>
          </div>
        </div>
      </el-card>

      <!-- 题目回顾 -->
      <div v-if="review && review.questions" class="questions-section">
        <div class="section-header">
          <h3>题目与答案</h3>
          <el-button size="small" @click="showAttempts = true">
            <el-icon><List /></el-icon>
            查看所有答题记录 ({{ attempts.length }})
          </el-button>
        </div>

        <el-card
          v-for="(q, idx) in review.questions"
          :key="q.id"
          class="question-card"
        >
          <div class="q-header">
            <span class="q-num">第 {{ idx + 1 }} 题</span>
            <el-tag
              v-if="lastAnswerFor(q.id)"
              :type="lastAnswerFor(q.id).is_right ? 'success' : 'danger'"
              size="small"
            >
              上次{{ lastAnswerFor(q.id).is_right ? '正确' : '错误' }}
            </el-tag>
          </div>

          <h4 class="q-stem">{{ q.stem }}</h4>

          <div class="q-options">
            <div
              v-for="(opt, oi) in q.options"
              :key="oi"
            :class="['q-option', {
              correct: q.answer === optionLetters[oi],
              wrong: lastAnswerFor(q.id)?.selected === optionLetters[oi] && !lastAnswerFor(q.id)?.is_right
            }]"
          >
            <div class="opt-badge">{{ optionLetters[oi] }}</div>
            <span class="opt-text">{{ opt }}</span>
            <el-icon v-if="q.answer === optionLetters[oi]" class="opt-icon right"><CircleCheck /></el-icon>
            <el-icon v-else-if="lastAnswerFor(q.id)?.selected === optionLetters[oi]" class="opt-icon wrong"><CircleClose /></el-icon>
            </div>
          </div>

          <div v-if="q.explanation" class="q-explanation">
            <el-icon><InfoFilled /></el-icon>
            <div>
              <strong>解析：</strong>{{ q.explanation }}
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 答题记录弹窗 -->
    <el-dialog v-model="showAttempts" title="答题记录" width="640px" top="5vh">
      <div v-if="attempts.length === 0" style="text-align: center; padding: 24px; color: #909399;">
        暂无答题记录
      </div>
      <div v-else>
        <div
          v-for="(att, idx) in attempts"
          :key="att.id"
          class="attempt-item"
        >
          <div class="attempt-header">
            <el-tag :type="att.correct_rate >= 0.8 ? 'success' : att.correct_rate >= 0.6 ? 'warning' : 'danger'" size="small">
              第 {{ attempts.length - idx }} 次
            </el-tag>
            <span class="attempt-score">{{ att.score }} / {{ att.total }}</span>
            <span class="attempt-rate">正确率 {{ (att.correct_rate * 100).toFixed(0) }}%</span>
            <span class="attempt-date">{{ att.completed_at?.slice(0, 16).replace('T', ' ') }}</span>
          </div>
          <div class="attempt-detail">
            <div
              v-for="item in att.answers_detail"
              :key="item.question_id"
              :class="['mini-question', item.is_right ? 'right' : 'wrong']"
            >
              <span class="mini-stem">{{ item.stem?.slice(0, 40) }}{{ item.stem?.length > 40 ? '...' : '' }}</span>
              <span :class="['mini-result', item.is_right ? 'text-success' : 'text-danger']">
                {{ item.is_right ? '✓' : '✗' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showAttempts = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, List, CircleCheck, CircleClose, InfoFilled
} from '@element-plus/icons-vue'
import { getQuizReview, getQuizAttempts } from '@/api'

const route = useRoute()
const quizId = computed(() => route.params.id)

const loading = ref(false)
const review = ref(null)
const attempts = ref([])
const showAttempts = ref(false)

const optionLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

const statusType = computed(() => {
  if (!review.value) return 'info'
  return review.value.last_attempt ? 'success' : 'warning'
})

const statusLabel = computed(() => {
  if (!review.value) return ''
  return review.value.last_attempt ? '已完成' : '未答题'
})

const scoreClass = computed(() => {
  if (!review.value?.last_attempt) return ''
  const rate = review.value.last_attempt.correct_rate
  if (rate >= 0.8) return 'excellent'
  if (rate >= 0.6) return 'good'
  return 'needs-improvement'
})

const lastAnswerFor = (questionId) => {
  if (!review.value?.last_attempt?.answers_detail) return null
  return review.value.last_attempt.answers_detail.find(a => a.question_id === questionId)
}

const fetchReview = async () => {
  loading.value = true
  try {
    const [reviewRes, attemptRes] = await Promise.all([
      getQuizReview(quizId.value),
      getQuizAttempts(quizId.value).catch(() => ({ data: [] }))
    ])
    review.value = reviewRes.data
    attempts.value = Array.isArray(attemptRes.data) ? attemptRes.data : (attemptRes.data.results || [])
  } catch (e) {
    ElMessage.error('获取回顾数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchReview)
</script>

<style scoped>
.review-page {
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
  flex: 1;
}

.review-content {
  max-width: 860px;
  margin: 0 auto;
}

.overview-card {
  margin-bottom: 24px;
  border-radius: 16px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.overview-header h3 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.overview-meta {
  margin: 0;
  font-size: 14px;
  color: #86868b;
}

.overview-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.score-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
}

.score-circle.excellent {
  background: #67c23a;
  color: #fff;
}

.score-circle.good {
  background: #e6a23c;
  color: #fff;
}

.score-circle.needs-improvement {
  background: #f56c6c;
  color: #fff;
}

.score-val {
  font-size: 24px;
  font-weight: 700;
}

.score-unit {
  font-size: 11px;
  opacity: 0.8;
}

.score-detail {
  font-size: 14px;
  color: #86868b;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.question-card {
  margin-bottom: 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.question-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.q-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.q-num {
  font-size: 13px;
  color: #86868b;
  font-weight: 500;
}

.q-stem {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
  line-height: 1.6;
}

.q-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.q-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #f5f5f7;
  border-radius: 10px;
  font-size: 14px;
  color: #86868b;
  transition: all 0.2s ease;
}

.q-option.correct {
  background: rgba(103, 194, 58, 0.08);
  color: #67c23a;
  font-weight: 500;
}

.q-option.wrong {
  background: rgba(245, 108, 108, 0.08);
  color: #f56c6c;
}

.opt-badge {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.q-option.correct .opt-badge {
  background: #67c23a;
  color: #fff;
}

.q-option.wrong .opt-badge {
  background: #f56c6c;
  color: #fff;
}

.opt-icon {
  margin-left: auto;
  font-size: 16px;
}

.opt-icon.right {
  color: #67c23a;
}

.opt-icon.wrong {
  color: #f56c6c;
}

.q-explanation {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px 16px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 10px;
  font-size: 14px;
  color: #86868b;
  line-height: 1.6;
}

.q-explanation .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

/* 答题记录弹窗 */
.attempt-item {
  padding: 16px;
  background: #f5f5f7;
  border-radius: 12px;
  margin-bottom: 12px;
}

.attempt-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.attempt-score {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.attempt-rate {
  font-size: 14px;
  color: #86868b;
}

.attempt-date {
  margin-left: auto;
  font-size: 12px;
  color: #c0c4cc;
}

.attempt-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mini-question {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
}

.mini-question.right {
  border-left: 3px solid #67c23a;
}

.mini-question.wrong {
  border-left: 3px solid #f56c6c;
}

.mini-stem {
  color: #86868b;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

:deep(.el-dialog) {
  border-radius: 16px;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .review-page {
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

  .review-content {
    max-width: 100%;
  }

  :deep(.el-dialog) {
    width: 94vw !important;
    max-width: 640px !important;
  }

  .overview-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .overview-header h3 {
    font-size: 18px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .section-header h3 {
    font-size: 16px;
  }

  .question-card {
    margin-bottom: 12px;
  }

  .q-stem {
    font-size: 15px;
  }

  .attempt-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .attempt-date {
    margin-left: 0;
    width: 100%;
  }

  .attempt-score {
    font-size: 14px;
  }
}
</style>
