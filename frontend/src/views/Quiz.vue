<template>
  <div class="quiz-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>测验答题</h2>
      <div class="quiz-info">
        <el-tag type="info">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</el-tag>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 答题卡片 -->
    <div v-else-if="!submitted && questions.length > 0" class="quiz-content">
      <el-card class="question-card">
        <div class="question-header">
          <el-tag type="warning" size="small">选择题</el-tag>
          <span class="question-id">#{{ currentIndex + 1 }}</span>
        </div>
        <h3 class="question-stem">{{ currentQuestion.stem }}</h3>
        <div class="options-list">
          <div
            v-for="(option, idx) in currentQuestion.options"
            :key="idx"
            :class="['option-item', { selected: selectedAnswers[currentQuestion.id] === optionLetters[idx] }]"
            @click="selectAnswer(currentQuestion.id, optionLetters[idx])"
          >
            <div class="option-badge">{{ optionLetters[idx] }}</div>
            <span class="option-text">{{ option }}</span>
          </div>
        </div>
      </el-card>

      <!-- 导航按钮 -->
      <div class="navigation">
        <el-button
          :disabled="currentIndex === 0"
          @click="prevQuestion"
        >
          <el-icon><ArrowLeft /></el-icon>
          上一题
        </el-button>
        <div class="page-dots">
          <span
            v-for="(_, idx) in questions"
            :key="idx"
            :class="['dot', { active: idx === currentIndex, answered: answeredQuestions.has(idx) }]"
            @click="goToQuestion(idx)"
          />
        </div>
        <el-button
          v-if="currentIndex < questions.length - 1"
          type="primary"
          @click="nextQuestion"
        >
          下一题
          <el-icon><ArrowRight /></el-icon>
        </el-button>
        <el-button
          v-else
          type="success"
          :disabled="answeredCount < questions.length"
          @click="submitQuiz"
        >
          提交答案
        </el-button>
      </div>
    </div>

    <!-- 空状态（题目加载完成但没有题目） -->
    <div v-else-if="showEmptyState" class="empty-wrap">
      <el-empty description="没有可作答的题目，请返回重试">
        <el-button type="primary" @click="router.back()">返回</el-button>
      </el-empty>
    </div>

    <!-- 提交中 -->
    <div v-else-if="submitting" class="submitting-wrap">
      <el-icon class="is-loading"><Loading /></el-icon>
      <p>正在提交答案...</p>
    </div>

    <!-- 答题结果 -->
    <div v-else-if="submitted && result" class="result-content">
      <el-card class="result-card">
        <div class="result-header">
          <div class="score-circle" :class="scoreClass">
            <span class="score-value">{{ result.score }}</span>
            <span class="score-total">/ {{ result.total }}</span>
          </div>
          <div class="result-info">
            <h3>答题完成！</h3>
            <p class="correct-rate">正确率：{{ (result.correct_rate * 100).toFixed(0) }}%</p>
          </div>
        </div>

        <el-divider />

        <!-- 答题详情 -->
        <div class="answers-review">
          <h4>答题详情</h4>
          <div
            v-for="(item, idx) in result.answers_detail"
            :key="idx"
            :class="['review-item', { correct: item.is_right, wrong: !item.is_right }]"
          >
            <div class="review-header">
              <el-tag :type="item.is_right ? 'success' : 'danger'" size="small">
                {{ item.is_right ? '正确' : '错误' }}
              </el-tag>
              <span class="review-num">第 {{ idx + 1 }} 题</span>
            </div>
            <p class="review-stem">{{ item.stem }}</p>
            <div class="review-options">
              <div v-for="(opt, oi) in item.options" :key="oi" class="review-option"
                :class="{
                  correct: item.correct === optionLetters[oi],
                  wrong: item.selected === optionLetters[oi] && !item.is_right
                }"
              >
                {{ optionLetters[oi] }}. {{ opt }}
                <el-icon v-if="item.correct === optionLetters[oi]"><Check /></el-icon>
                <el-icon v-else-if="item.selected === optionLetters[oi] && !item.is_right"><Close /></el-icon>
              </div>
            </div>
            <div v-if="!item.is_right && item.explanation" class="review-explanation">
              <el-icon><InfoFilled /></el-icon>
              解析：{{ item.explanation }}
            </div>
          </div>
        </div>

        <div class="result-actions">
          <el-button @click="$router.push('/')">返回首页</el-button>
          <el-button type="primary" @click="retryQuiz">重新答题</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeRouteLeave } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ArrowRight, Loading, Check, Close, InfoFilled
} from '@element-plus/icons-vue'
import { getQuizQuestions, submitQuizAnswers } from '@/api'

const route = useRoute()
const router = useRouter()
const quizId = computed(() => route.params.id)

const loading = ref(true)
const submitting = ref(false)
const questions = ref([])
const selectedAnswers = ref({})
const currentIndex = ref(0)
const submitted = ref(false)
const result = ref(null)

const currentQuestion = computed(() => questions.value[currentIndex.value] || {})
const answeredQuestions = computed(() => {
  const set = new Set()
  Object.keys(selectedAnswers.value).forEach(qid => {
    if (selectedAnswers.value[qid] == null) return
    const idx = questions.value.findIndex(q => q.id == qid)
    if (idx !== -1) set.add(idx)
  })
  return set
})
const answeredCount = computed(() => answeredQuestions.value.size)

const optionLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

const scoreClass = computed(() => {
  if (!result.value) return ''
  const rate = result.value.correct_rate
  if (rate >= 0.8) return 'excellent'
  if (rate >= 0.6) return 'good'
  return 'needs-improvement'
})

const fetchQuestions = async () => {
  loading.value = true
  try {
    const res = await getQuizQuestions(quizId.value)
    questions.value = res.data
    // 初始化答案对象
    questions.value.forEach(q => {
      selectedAnswers.value[q.id] = null
    })
  } catch (e) {
    ElMessage.error('获取题目失败，请稍后重试')
    setTimeout(() => router.back(), 1500)
  } finally {
    loading.value = false
  }
}

// 题目加载完成后展示空状态（后端可能没有题目，或格式不匹配）
const showEmptyState = computed(() => !loading.value && !submitted.value && questions.value.length === 0)

const selectAnswer = (questionId, option) => {
  selectedAnswers.value[questionId] = option
}

const prevQuestion = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

const nextQuestion = () => {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
  }
}

const goToQuestion = (idx) => {
  currentIndex.value = idx
}

const submitQuiz = async () => {
  if (answeredCount.value < questions.value.length) {
    ElMessage.warning('请完成所有题目后再提交')
    return
  }

  submitting.value = true
  try {
    const answers = Object.entries(selectedAnswers.value)
      .filter(([_, selected]) => selected != null)
      .map(([questionId, selected]) => ({
        question_id: parseInt(questionId),
        selected
      }))

    const res = await submitQuizAnswers(quizId.value, answers)
    result.value = res.data
    submitted.value = true
    ElMessage.success('提交成功')
  } catch (e) {
    ElMessage.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

const retryQuiz = () => {
  submitted.value = false
  result.value = null
  selectedAnswers.value = {}
  questions.value.forEach(q => {
    selectedAnswers.value[q.id] = null
  })
  currentIndex.value = 0
}

onMounted(fetchQuestions)

onBeforeRouteLeave((to, from, next) => {
  if (!submitted.value && Object.keys(selectedAnswers.value).some(k => selectedAnswers.value[k] != null)) {
    ElMessageBox.confirm('你有未提交的答案，确定要离开吗？', '提示', {
      confirmButtonText: '离开',
      cancelButtonText: '继续答题',
      type: 'warning'
    }).then(() => next()).catch(() => next(false))
  } else {
    next()
  }
})
</script>

<style scoped>
.quiz-page {
  min-height: 100vh;
  background: #f5f5f7;
  padding: 24px;
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

.quiz-info {
  margin-left: auto;
}

.loading-wrap {
  max-width: 800px;
  margin: 40px auto;
  padding: 24px;
  background: #fff;
  border-radius: 16px;
}

.quiz-content {
  max-width: 800px;
  margin: 0 auto;
}

.question-card {
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.question-card :deep(.el-card__body) {
  padding: 32px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.question-id {
  color: #909399;
  font-size: 14px;
}

.question-stem {
  margin: 0 0 24px;
  font-size: 18px;
  font-weight: 500;
  color: #1d1d1f;
  line-height: 1.6;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: #f5f5f7;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.option-item:hover {
  background: #e8e8ed;
  border-color: #1d1d1f;
}

.option-item.selected {
  background: #e8e8ed;
  border-color: #1d1d1f;
}

.option-badge {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 8px;
  font-weight: 600;
  color: #1d1d1f;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.option-item.selected .option-badge {
  background: #1d1d1f;
  color: #fff;
}

.option-text {
  flex: 1;
  font-size: 15px;
  color: #1d1d1f;
}

.navigation {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 32px;
  padding: 20px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.page-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d2d2d7;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dot.active {
  background: #1d1d1f;
  transform: scale(1.2);
}

.dot.answered {
  background: #86868b;
}

.submitting-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #86868b;
}

.submitting-wrap .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.result-content {
  max-width: 800px;
  margin: 0 auto;
}

.result-card {
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.result-card :deep(.el-card__body) {
  padding: 32px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 32px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f5f7;
  flex-shrink: 0;
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

.score-value {
  font-size: 36px;
  font-weight: 700;
}

.score-total {
  font-size: 16px;
  opacity: 0.8;
}

.result-info h3 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}

.correct-rate {
  margin: 0;
  font-size: 16px;
  color: #1d1d1f;
  font-weight: 500;
}

.answers-review {
  margin-top: 24px;
}

.answers-review h4 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.review-item {
  padding: 20px;
  background: #f5f5f7;
  border-radius: 12px;
  margin-bottom: 16px;
  border-left: 4px solid #e0e0e0;
}

.review-item.correct {
  border-left-color: #67c23a;
  background: rgba(103, 194, 58, 0.05);
}

.review-item.wrong {
  border-left-color: #f56c6c;
  background: rgba(245, 108, 108, 0.05);
}

.review-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.review-num {
  color: #909399;
  font-size: 13px;
}

.review-stem {
  margin: 0 0 12px;
  font-size: 15px;
  color: #1d1d1f;
}

.review-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-option {
  padding: 8px 12px;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  color: #86868b;
}

.review-option.correct {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
  font-weight: 500;
}

.review-option.wrong {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.review-explanation {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  color: #86868b;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.review-explanation .el-icon {
  color: #86868b;
  margin-top: 2px;
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

.result-actions .el-button {
  padding: 12px 32px;
  border-radius: 12px;
}

:deep(.el-button--primary) {
  background: #1d1d1f;
  border: none;
}

:deep(.el-button--success) {
  background: #67c23a;
  border: none;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .quiz-page {
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

  .quiz-info {
    margin-left: 0;
    width: 100%;
    order: 3;
  }

  .question-card :deep(.el-card__body) {
    padding: 20px 16px;
  }

  .question-stem {
    font-size: 16px;
    margin-bottom: 16px;
  }

  .option-item {
    padding: 14px 16px;
    gap: 12px;
  }

  .option-badge {
    width: 28px;
    height: 28px;
    font-size: 13px;
  }

  .option-text {
    font-size: 14px;
  }

  .dot {
    width: 16px;
    height: 16px;
    padding: 14px;
    background-clip: content-box;
  }

  .page-dots {
    gap: 2px;
  }

  .navigation {
    padding: 16px;
    gap: 10px;
  }

  .result-card :deep(.el-card__body) {
    padding: 20px 16px;
  }

  .result-header {
    flex-direction: column;
    align-items: center;
    gap: 20px;
    text-align: center;
  }

  .score-circle {
    width: 100px;
    height: 100px;
  }

  .score-value {
    font-size: 30px;
  }

  .result-info h3 {
    font-size: 20px;
  }

  .result-actions {
    flex-wrap: wrap;
    gap: 12px;
  }

  .result-actions .el-button {
    flex: 1;
    min-width: 120px;
    padding: 10px 20px;
  }
}
</style>