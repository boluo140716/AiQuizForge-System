<template>
  <div class="note-edit-page">
    <div class="edit-container">
      <el-button @click="$router.back()" class="back-btn">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>

      <el-card class="edit-card">
        <template #header>
          <div class="card-header">
            <p class="qf-eyebrow">{{ isEdit ? '笔记 / 编辑' : '笔记 / 新建' }}</p>
            <h2>{{ isEdit ? '编辑笔记' : '创建笔记' }}</h2>
          </div>
        </template>

        <el-form :model="form" label-position="top" class="edit-form">
          <el-form-item label="标题">
            <el-input
              v-model="form.title"
              placeholder="请输入笔记标题"
              size="large"
            />
          </el-form-item>

          <el-form-item label="所属笔记本">
            <el-select v-model="form.notebook" placeholder="请选择笔记本" size="large" style="width: 100%">
              <el-option
                v-for="nb in store.notebooks"
                :key="nb.id"
                :label="nb.name"
                :value="nb.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item>
            <template #label>
              内容（支持 Markdown）
              <span class="label-hint">建议不超过 3000 字</span>
            </template>
            <MarkdownEditor v-model="form.content_md" />
            <div class="content-count">共 {{ contentLength }} 字</div>
          </el-form-item>

          <el-form-item label="标签（用逗号分隔）">
            <el-input
              v-model="tagInput"
              size="large"
              placeholder="用逗号分隔，如：Python, Django, 后端"
            />
          </el-form-item>

          <div v-if="isEdit" class="quiz-action">
            <el-button type="warning" :disabled="generating" @click="showQuizCountDialog = true" size="large">
              <el-icon v-if="generating" class="qf-spin"><Loading /></el-icon>
              <el-icon v-else><MagicStick /></el-icon>
              {{ generating ? '生成中…' : '生成测验' }}
            </el-button>
            <el-button type="success" :loading="generating" @click="handleAdaptivePractice" size="large">
              自适应练习
            </el-button>
          </div>

          <div class="form-actions">
            <el-button type="primary" @click="handleSave" :loading="saving" size="large" class="save-btn">
              {{ isEdit ? '保存修改' : '创建笔记' }}
            </el-button>
            <el-button v-if="isEdit" type="danger" @click="handleDelete" :loading="deleting" size="large">
              删除笔记
            </el-button>
          </div>
        </el-form>
      </el-card>
    </div>

    <!-- 题目数量选择对话框 -->
    <el-dialog v-model="showQuizCountDialog" title="生成测验" width="360px" @closed="onQuizCountDialogClosed">
      <el-form label-position="top">
        <el-form-item label="题目数量">
          <el-slider
            v-model="quizCountToGenerate"
            :min="1"
            :max="10"
            :step="1"
            show-stops
            :marks="{ 1: '1', 5: '5', 10: '10' }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuizCountDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGenerateQuiz">开始生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotebookStore } from '@/stores/notebook'
import { createNote, getNoteDetail, updateNote, deleteNote, generateQuiz, getQuizStatus, generateAdaptiveQuiz } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, MagicStick, Loading } from '@element-plus/icons-vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const route = useRoute()
const router = useRouter()
const store = useNotebookStore()

const isEdit = !!route.params.id

const form = reactive({
  title: '',
  notebook: store.currentNotebookId || null,
  content_md: ''
})
const tagInput = ref('')
const saving = ref(false)
const deleting = ref(false)
const generating = ref(false)
const currentQuizId = ref(null)
const contentLength = ref(0)
const showQuizCountDialog = ref(false)
const quizCountToGenerate = ref(5)
let pendingQuizGeneration = false
let idempotencyKey = ''          // 本次"生成测验"意图的唯一编号（幂等键）

const newIdempotencyKey = () =>
  (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)

const onQuizCountDialogClosed = async () => {
  if (!pendingQuizGeneration) return
  pendingQuizGeneration = false
  try {
    await ElMessageBox.confirm('是否以此笔记内容生成测验？', '生成测验', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    await doGenerateQuiz()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err?.response?.data?.detail || '生成失败')
    }
    generating.value = false
  }
}

const updateContentLength = () => {
  contentLength.value = (form.content_md || '').length
}

watch(() => form.content_md, updateContentLength)

onMounted(async () => {
  await store.fetchNotebooks()

  if (isEdit) {
    try {
      const res = await getNoteDetail(route.params.id)
      form.title = res.data.title
      form.notebook = res.data.notebook
      form.content_md = res.data.content_md
      tagInput.value = (res.data.tags || []).join(', ')
    } catch {
      ElMessage.error('笔记不存在')
      router.push('/')
      return
    }
  }

  updateContentLength()
})

const handleSave = async () => {
  if (!form.title.trim() || !(form.content_md || '').trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  saving.value = true
  try {
    const data = {
      title: form.title,
      notebook: form.notebook,
      content_md: form.content_md,
      tags: tagInput.value.split(',').map(t => t.trim()).filter(Boolean)
    }
    if (isEdit) {
      await updateNote(route.params.id, data)
      ElMessage.success('笔记已保存')
    } else {
      await createNote(data)
      ElMessage.success('笔记已创建')
    }
    router.push('/notes')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定删除这篇笔记吗？', '警告', { type: 'warning' })
    deleting.value = true
    await deleteNote(route.params.id)
    ElMessage.success('笔记已删除')
    router.push('/notes')
  } catch (e) {
    // 用户取消删除
  } finally {
    deleting.value = false
  }
}

const handleGenerateQuiz = async () => {
  // 每次点击"生成测验"生成一个新的幂等键：
  // 同一次点击产生的重复/重试请求，后端只会创建一个测验。
  idempotencyKey = newIdempotencyKey()
  pendingQuizGeneration = true
  showQuizCountDialog.value = false
}

const handleAdaptivePractice = async () => {
  try {
    generating.value = true
    const res = await generateAdaptiveQuiz({
      note_id: Number(route.params.id),
      count: quizCountToGenerate.value,
    })
    router.push('/quiz/' + res.data.practice_quiz_id)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '自适应练习生成失败')
  } finally {
    generating.value = false
  }
}

const pollQuizProgress = (quizId) => {
  let pollCount = 0
  const MAX_POLL = 60
  const pollStatus = async () => {
    pollCount++
    try {
      const statusRes = await getQuizStatus(quizId)
      const quiz = statusRes.data

      if (quiz.status === 'completed') {
        ElMessage.success('测验生成完成！正在跳转...')
        router.push('/quiz/' + quizId)
          .catch(err => ElMessage.error('跳转失败：' + (err.message || '路由错误')))
        return
      } else if (quiz.status === 'failed') {
        ElMessage.error('测验生成失败：' + (quiz.error_message || '未知错误'))
      } else if (pollCount >= MAX_POLL) {
        ElMessage.error('测验生成超时，请刷新页面重试')
      } else {
        setTimeout(pollStatus, 2000)
        return
      }
    } catch (e) {
      // 网络错误：重试而不是直接停止（避免 Celery 慢导致失败）
      if (pollCount < MAX_POLL) {
        setTimeout(pollStatus, 2000)
        return
      }
      ElMessage.error('检查生成状态失败:' + (e.response?.data?.detail || e.message || '网络错误'))
    }
    generating.value = false
  }
  setTimeout(pollStatus, 2000)
}

const watchQuizProgress = (quizId) => {
  // EventSource 不能带自定义请求头，所以 token 通过 query 参数传
  const token = localStorage.getItem('access_token') || ''
  const url = `/api/v1/quizzes/${quizId}/stream/?token=${encodeURIComponent(token)}`
  let es = null
  let finished = false

  const finish = () => {
    if (finished) return
    finished = true
    try { if (es) es.close() } catch (e) { /* ignore */ }
    generating.value = false
  }

  try {
    es = new EventSource(url)
  } catch (e) {
    pollQuizProgress(quizId)
    return
  }

  es.onmessage = (event) => {
    let data
    try { data = JSON.parse(event.data) } catch (e) { return }
    const stage = data.stage
    if (stage === 'done' || stage === 'completed') {
      ElMessage.success('测验生成完成！正在跳转...')
      finish()
      router.push('/quiz/' + quizId).catch(err => ElMessage.error('跳转失败：' + (err.message || '路由错误')))
    } else if (stage === 'failed') {
      ElMessage.error('测验生成失败：' + (data.message || '未知错误'))
      finish()
    }
  }

  es.onerror = () => {
    // SSE 异常时回退到轮询，保证功能可用
    finish()
    pollQuizProgress(quizId)
  }
}

const doGenerateQuiz = async () => {
  try{
    generating.value = true
    const res = await generateQuiz(route.params.id, quizCountToGenerate.value, idempotencyKey)
    currentQuizId.value = res.data.quiz_id

    ElMessage.success('测验生成中，请稍候...')
    watchQuizProgress(currentQuizId.value)
  } catch (err) {
    ElMessage.error('生成测验失败:'+(err.response?.data?.detail || err.message || '网络错误'))
    generating.value = false
  }
}
</script>

<style scoped>
.note-edit-page {
  min-height: 100vh;
  padding: 24px;
  position: relative;
  background: #f5f5f7;
}

.edit-container {
  max-width: 900px;
  margin: 0 auto;
}

.back-btn {
  background: #1d1d1f;
  border: none;
  color: #fff;
  border-radius: 24px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.back-btn:hover {
  transform: translateX(-4px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.edit-card {
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: none;
}

.edit-card :deep(.el-card__header) {
  border-bottom: 1px solid #f0f0f0;
  padding: 20px 24px;
}

.edit-card :deep(.el-card__body) {
  padding: 24px;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}

.edit-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #1d1d1f;
  font-size: 15px;
}

.edit-form :deep(.el-input__wrapper),
.edit-form :deep(.el-select .el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 16px;
  background: #f5f5f7;
  box-shadow: none;
  border: 1px solid #e0e0e0;
  transition: all 0.3s ease;
}

.edit-form :deep(.el-input__wrapper:hover),
.edit-form :deep(.el-select .el-input__wrapper:hover) {
  border-color: #1d1d1f;
}

.edit-form :deep(.el-input__wrapper.is-focus),
.edit-form :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}

.editor-wrapper {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

.label-hint {
  font-size: 12px;
  font-weight: 400;
  color: #86868b;
  margin-left: 8px;
}

.content-count {
  margin-top: 8px;
  font-size: 13px;
  color: #86868b;
  text-align: right;
}

.quiz-action {
  margin-bottom: 24px;
}

.quiz-action :deep(.el-button--warning) {
  background: #e6a23c;
  border: none;
  border-radius: 24px;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.quiz-action :deep(.el-button--warning:hover) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.form-actions {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}

.save-btn {
  background: #1d1d1f;
  border: none;
  border-radius: 24px;
  font-weight: 600;
  font-size: 16px;
  padding: 12px 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.save-btn:disabled {
  opacity: 0.7;
}

.form-actions :deep(.el-button--danger) {
  background: #f56c6c;
  border: none;
  border-radius: 24px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.form-actions :deep(.el-button--danger:hover) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .note-edit-page {
    padding: 12px;
  }

  .edit-container {
    max-width: 100%;
  }

  .edit-card :deep(.el-card__header) {
    padding: 16px;
  }

  .edit-card :deep(.el-card__body) {
    padding: 16px;
  }

  .card-header h2 {
    font-size: 20px;
  }

  .editor-wrapper :deep(.toastui-editor-defaultUI) {
    height: 350px !important;
  }

  .form-actions {
    flex-direction: column;
    gap: 12px;
  }

  .save-btn {
    width: 100%;
    padding: 12px 20px;
  }

  .form-actions :deep(.el-button--danger) {
    width: 100%;
  }

  .back-btn {
    margin-bottom: 12px;
  }
}
</style>

<style scoped>
/* ===== note sheet ===== */
.note-edit-page {
  padding: 0;
  background: transparent;
}

.back-btn {
  background: transparent;
  border: 1px solid var(--qf-line);
  color: var(--qf-ink-soft);
  border-radius: 3px;
  box-shadow: none;
}

.back-btn:hover {
  transform: none;
  background: var(--qf-surface);
  border-color: var(--qf-primary);
  color: var(--qf-primary);
  box-shadow: none;
}

.edit-card {
  position: relative;
  border: 1px solid var(--qf-line);
  border-radius: 3px;
  box-shadow: none;
}

.edit-card::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 22px;
  width: 56px;
  height: 4px;
  background: var(--qf-accent);
}

.edit-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--qf-line);
  padding: 22px 26px;
}

.edit-card :deep(.el-card__body) {
  padding: 26px;
}

.card-header h2 {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.edit-form :deep(.el-form-item__label) {
  font-family: var(--qf-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--qf-muted);
}

.edit-form :deep(.el-input__wrapper),
.edit-form :deep(.el-select .el-input__wrapper) {
  border-radius: 3px;
  padding: 4px 12px;
  background: var(--qf-surface);
  box-shadow: 0 0 0 1px var(--qf-line) inset;
  border: none;
}

.edit-form :deep(.el-input__wrapper.is-focus),
.edit-form :deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--qf-primary) inset;
}

.editor-wrapper {
  border: 1px solid var(--qf-line);
  border-radius: 3px;
}

.quiz-action :deep(.el-button--warning) {
  border-radius: 3px;
  font-weight: 700;
  box-shadow: none;
}

.quiz-action :deep(.el-button--warning:hover) {
  transform: none;
  box-shadow: none;
}

.save-btn {
  border-radius: 3px;
  box-shadow: none;
}

.save-btn:hover:not(:disabled) {
  transform: none;
  box-shadow: none;
}

.form-actions :deep(.el-button--danger) {
  border-radius: 3px;
  box-shadow: none;
}

.form-actions :deep(.el-button--danger:hover) {
  transform: none;
  box-shadow: none;
}

.qf-spin {
  animation: qf-spin 0.9s linear infinite;
}

@keyframes qf-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>