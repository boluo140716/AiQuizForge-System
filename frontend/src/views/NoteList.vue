<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h2>笔记列表</h2>
      <el-button type="primary" @click="$router.push('/notes/new')">+ 新建笔记</el-button>
    </div>

    <!-- 搜索框 -->
    <el-input v-model="searchKeyword" placeholder="搜索笔记标题或内容" clearable @input="fetchNotes" style="margin-bottom: 16px; width: 300px;" />

    <!-- 笔记卡片列表 -->
    <el-row :gutter="16">
      <el-col v-for="note in notes" :key="note.id" :span="8" style="margin-bottom: 16px;">
        <el-card shadow="hover" @click="$router.push(`/notes/${note.id}/edit`)">
          <h3>{{ note.title }}</h3>
          <p style="color: #999; font-size: 13px;">
            笔记本：{{ note.notebook_name }} &nbsp;|&nbsp;
            {{ note.updated_at?.slice(0, 10) }}
          </p>
          <el-tag v-for="tag in note.tags" :key="tag" size="small" style="margin-right: 4px;">
            {{ tag }}
          </el-tag>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && notes.length === 0" description="暂无笔记，去创建第一篇吧" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      @current-change="fetchNotes"
      style="margin-top: 24px; justify-content: center;"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useNotebookStore } from '@/stores/notebook'
import { getNotes } from '@/api'

const route = useRoute()
const store = useNotebookStore()

const notes = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 10
const searchKeyword = ref('')

const fetchNotes = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize
    }
    if (store.currentNotebookId) {
      params.notebook = store.currentNotebookId
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const res = await getNotes(params)
    const data = res.data
    notes.value = data.results || data
    total.value = data.count || (Array.isArray(data) ? data.length : 0)
  } finally {
    loading.value = false
  }
}

onMounted(fetchNotes)

watch(() => route.query.notebook, () => {
  store.setCurrentNotebook(Number(route.query.notebook) || null)
  page.value = 1
  fetchNotes()
}, { immediate: true })
</script>