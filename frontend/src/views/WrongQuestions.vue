<template>
  <div class="wrong-questions-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>错题本</h2>
      <div class="header-actions">
        <el-button
          type="warning"
          :disabled="wrongList.length === 0"
          @click="handleRePractice"
        >
          <el-icon><RefreshRight /></el-icon>
          错题重练
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon wrong-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ wrongList.length }}</div>
            <div class="stat-label">错题总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon quiz-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ quizCount }}</div>
            <div class="stat-label">涉及测验</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon book-icon">
            <el-icon><Notebook /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ notebookCount }}</div>
            <div class="stat-label">涉及笔记本</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon repeat-icon">
            <el-icon><Refresh /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ mostWrongCount }}</div>
            <div class="stat-label">最高错题次数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-select
        v-model="filterQuizId"
        placeholder="按测验筛选"
        clearable
        @change="fetchWrongQuestions"
        style="width: 180px;"
      >
        <el-option
          v-for="quiz in quizOptions"
          :key="quiz.id"
          :label="quiz.note_title"
          :value="quiz.id"
        />
      </el-select>
      <el-select
        v-model="filterNotebookId"
        placeholder="按笔记本筛选"
        clearable
        @change="fetchWrongQuestions"
        style="width: 180px; margin-left: 12px;"
      >
        <el-option
          v-for="nb in notebookOptions"
          :key="nb.id"
          :label="nb.name"
          :value="nb.id"
        />
      </el-select>
      <el-select
        v-model="filterTag"
        placeholder="按标签筛选"
        clearable
        @change="fetchWrongQuestions"
        style="width: 180px; margin-left: 12px;"
      >
        <el-option
          v-for="tag in tagOptions"
          :key="tag"
          :label="tag"
          :value="tag"
        />
      </el-select>
    </div>

    <!-- 错题列表 -->
    <div v-loading="loading" class="wrong-list">
      <el-empty v-if="!loading && wrongList.length === 0" description="暂无错题记录，继续加油！" />

      <div v-else>
        <el-card
          v-for="item in wrongList"
          :key="item.id"
          class="wrong-item"
          shadow="hover"
        >
          <div class="wrong-item-header">
            <div class="wrong-info">
              <el-tag type="danger" size="small">错误 {{ item.wrong_count }} 次</el-tag>
              <span class="note-title">{{ item.note_title }}</span>
              <el-tag size="small" type="info">{{ item.notebook_name }}</el-tag>
            </div>
            <el-button
              type="danger"
              size="small"
              text
              @click="handleRemove(item.id)"
            >
              <el-icon><Delete /></el-icon>
              移除
            </el-button>
          </div>

          <h4 class="question-stem">{{ item.question_stem }}</h4>

          <div class="question-options">
            <div
              v-for="(opt, idx) in item.question_options"
              :key="idx"
              :class="['option', {
                correct: item.question_answer === opt,
                wrong: item.user_answer === opt
              }]"
            >
              {{ opt }}
              <el-icon v-if="item.question_answer === opt" class="correct-icon"><Check /></el-icon>
              <el-icon v-else-if="item.user_answer === opt" class="wrong-icon"><Close /></el-icon>
            </div>
          </div>

          <div class="wrong-meta">
            <span>你的答案：{{ item.user_answer }}</span>
            <span>正确答案：{{ item.question_answer }}</span>
            <span>错题时间：{{ item.last_wrong_at?.slice(0, 10) }}</span>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="fetchWrongQuestions"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, WarningFilled, Document, Notebook, Refresh, Delete, Check, Close, RefreshRight
} from '@element-plus/icons-vue'
import { getWrongQuestions, removeWrongQuestion, rePracticeWrong, getNotebooks, getWrongQuestionTags } from '@/api'

const router = useRouter()

const loading = ref(false)
const wrongList = ref([])
const page = ref(1)
const pageSize = 10
const total = ref(0)

const filterQuizId = ref(null)
const filterNotebookId = ref(null)
const filterTag = ref(null)
const quizOptions = ref([])
const notebookOptions = ref([])
const tagOptions = ref([])

const quizCount = computed(() => {
  const ids = new Set(wrongList.value.map(w => w.quiz_id))
  return ids.size
})

const notebookCount = computed(() => {
  const ids = new Set(wrongList.value.map(w => w.notebook_id))
  return ids.size
})

const mostWrongCount = computed(() => {
  if (wrongList.value.length === 0) return 0
  return Math.max(...wrongList.value.map(w => w.wrong_count))
})

const fetchWrongQuestions = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize
    }
    if (filterQuizId.value) params.quiz_id = filterQuizId.value
    if (filterNotebookId.value) params.notebook_id = filterNotebookId.value
    if (filterTag.value) params.tag = filterTag.value

    const res = await getWrongQuestions(params)
    const data = res.data
    wrongList.value = data.results || data
    total.value = data.count || wrongList.value.length

    // 提取测验选项
    const quizMap = new Map()
    wrongList.value.forEach(w => {
      if (w.quiz_id && !quizMap.has(w.quiz_id)) {
        quizMap.set(w.quiz_id, { id: w.quiz_id, note_title: w.note_title })
      }
    })
    quizOptions.value = Array.from(quizMap.values())
  } catch (e) {
    ElMessage.error('获取错题列表失败')
  } finally {
    loading.value = false
  }
}

const fetchNotebooks = async () => {
  try {
    const res = await getNotebooks()
    notebookOptions.value = res.data.results || res.data
  } catch (e) {
    console.error('获取笔记本失败', e)
  }
}

const fetchTags = async () => {
  try {
    const res = await getWrongQuestionTags()
    tagOptions.value = res.data.tags || []
  } catch (e) {
    console.error('获取标签失败', e)
  }
}

const handleRemove = async (wrongId) => {
  try {
    await ElMessageBox.confirm('确定要从错题本中移除这道题吗？', '提示', {
      type: 'warning'
    })
    await removeWrongQuestion(wrongId)
    ElMessage.success('已移除')
    fetchWrongQuestions()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('移除失败')
    }
  }
}

const handleRePractice = async () => {
  try {
    const res = await rePracticeWrong({
      limit: 5,
      quiz_id: filterQuizId.value || undefined,
      notebook_id: filterNotebookId.value || undefined,
      tag: filterTag.value || undefined
    })

    const practiceQuizId = res.data.practice_quiz_id
    ElMessage.success('即将开始错题重练')
    router.push('/quiz/' + practiceQuizId)
  } catch (e) {
    if (e.response?.status === 404) {
      ElMessage.warning('错题本为空')
    } else {
      ElMessage.error('获取错题失败')
    }
  }
}

onMounted(() => {
  fetchWrongQuestions()
  fetchNotebooks()
  fetchTags()
})
</script>

<style scoped>
.wrong-questions-page {
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

.header-actions {
  margin-left: auto;
}

.header-actions :deep(.el-button--warning) {
  background: #e6a23c;
  border: none;
  border-radius: 20px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
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
}

.wrong-icon {
  background: #f56c6c;
  color: #fff;
}

.quiz-icon {
  background: #1d1d1f;
  color: #fff;
}

.book-icon {
  background: #86868b;
  color: #fff;
}

.repeat-icon {
  background: #e6a23c;
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
}

.stat-label {
  font-size: 14px;
  color: #86868b;
}

.filter-bar {
  display: flex;
  margin-bottom: 20px;
}

.wrong-list {
  min-height: 300px;
}

.wrong-item {
  margin-bottom: 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.wrong-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.wrong-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.wrong-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.note-title {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
}

.question-stem {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
  line-height: 1.5;
}

.question-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.option {
  padding: 8px 16px;
  background: #f5f5f7;
  border-radius: 8px;
  font-size: 14px;
  color: #86868b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.option.correct {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
  font-weight: 500;
}

.option.wrong {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.correct-icon {
  color: #67c23a;
}

.option.wrong .wrong-icon {
  color: #f56c6c;
}

.wrong-meta {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #86868b;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .wrong-questions-page {
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

  .header-actions {
    margin-left: 0;
    width: 100%;
  }

  .header-actions :deep(.el-button) {
    width: 100%;
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

  .filter-bar {
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .filter-bar :deep(.el-select) {
    width: 100% !important;
    margin-left: 0 !important;
  }

  .wrong-info {
    flex-wrap: wrap;
    gap: 8px;
  }

  .wrong-meta {
    flex-direction: column;
    gap: 4px;
  }

  .question-stem {
    font-size: 15px;
  }

  .question-options {
    gap: 6px;
  }

  .option {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
