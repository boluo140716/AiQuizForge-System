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
            <div ref="editorRef" class="editor-wrapper" />
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
            <el-button type="warning" :loading="generating" @click="showQuizCountDialog = true" size="large">
              <el-icon><MagicStick /></el-icon>
              生成测验
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
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotebookStore } from '@/stores/notebook'
import { createNote, getNoteDetail, updateNote, deleteNote, generateQuiz, getQuizStatus } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, MagicStick } from '@element-plus/icons-vue'
import Editor from '@toast-ui/editor'
import '@toast-ui/editor/dist/toastui-editor.css'

const route = useRoute()
const router = useRouter()
const store = useNotebookStore()

const isEdit = !!route.params.id
const editorRef = ref(null)
let editor = null

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
  if (editor) {
    contentLength.value = editor.getMarkdown().length
  }
}

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

  if (editorRef.value) {
    editor = new Editor({
      el: editorRef.value,
      initialValue: form.content_md,
      previewStyle: 'vertical',
      height: '500px',
      events: {
        change: () => updateContentLength()
      }
    })
    updateContentLength()
  }
})

onBeforeUnmount(() => {
  if (editor) {
    editor.destroy()
  }
})

const handleSave = async () => {
  if (!form.title.trim() || !editor.getMarkdown().trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  saving.value = true
  try {
    const data = {
      title: form.title,
      notebook: form.notebook,
      content_md: editor.getMarkdown(),
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
  pendingQuizGeneration = true
  showQuizCountDialog.value = false
}

const doGenerateQuiz = async () => {
  try{
    generating.value = true
    const res = await generateQuiz(route.params.id, quizCountToGenerate.value)
    currentQuizId.value = res.data.quiz_id

    ElMessage.success('测验生成中，请稍候...')

    // 轮询检查生成状态
    let pollCount = 0
    const MAX_POLL = 60
    const pollStatus = async () => {
      pollCount++
      try {
        const statusRes = await getQuizStatus(currentQuizId.value)
        const quiz = statusRes.data

        if (quiz.status === 'completed') {
          ElMessage.success('测验生成完成！正在跳转...')
          router.push('/quiz/' + currentQuizId.value)
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
        ElMessage.error('检查生成状态失败:'+(e.response?.data?.detail || e.message || '网络错误'))
      }
      generating.value = false
    }

    setTimeout(pollStatus, 2000)
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