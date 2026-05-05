<template>
  <div>
    <el-button @click="$router.back()" style="margin-bottom: 16px;">← 返回</el-button>

    <el-form :model="form" label-position="top">
      <el-form-item label="标题">
        <el-input v-model="form.title" placeholder="请输入笔记标题" />
      </el-form-item>

      <el-form-item label="所属笔记本">
        <el-select v-model="form.notebook" placeholder="请选择笔记本">
          <el-option
            v-for="nb in store.notebooks"
            :key="nb.id"
            :label="nb.name"
            :value="nb.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="内容（支持 Markdown）">
        <div ref="editorRef" style="height: 500px;" />
      </el-form-item>

      <el-form-item label="标签（用逗号分隔）">
        <el-input v-model="tagInput" placeholder="例如：django, vue, python" />
      </el-form-item>

      <div style="margin-top: 20px;">
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ isEdit ? '保存修改' : '创建笔记' }}
        </el-button>
        <el-button v-if="isEdit" type="danger" @click="handleDelete" :loading="deleting">
          删除笔记
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotebookStore } from '@/stores/notebook'
import { createNote, getNoteDetail, updateNote, deleteNote } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
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

// 初始化编辑器
onMounted(async () => {
  // 确保笔记本列表已加载（用于下拉选择）
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

  // 创建编辑器（无代码高亮插件，稳定优先）
  if (editorRef.value) {
    editor = new Editor({
      el: editorRef.value,
      initialValue: form.content_md,
      previewStyle: 'vertical',
      height: '500px'
    })
  }
})

onBeforeUnmount(() => {
  if (editor) {
    editor.destroy()
  }
})

// 保存笔记
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

// 删除笔记
const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定删除这篇笔记吗？', '警告', { type: 'warning' })
    deleting.value = true
    await deleteNote(route.params.id)
    ElMessage.success('笔记已删除')
    router.push('/notes')
  } catch {
    // 用户取消
  } finally {
    deleting.value = false
  }
}
</script>