<template>
  <div class="note-list-page">
    <div class="page-header">
      <h2>我的笔记</h2>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="store.currentNotebookId"
          placeholder="全部笔记"
          clearable
          @change="handleNotebookChange"
          style="width: 180px;"
        >
          <el-option
            v-for="nb in notebooks"
            :key="nb.id"
            :label="nb.name"
            :value="nb.id"
          />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索笔记..."
          clearable
          @input="debouncedFetch"
          style="width: 260px; margin-left: 12px;"
          :prefix-icon="Search"
        />
      </div>
      <el-button type="primary" @click="$router.push('/notes/new')">
        <el-icon><Plus /></el-icon>
        新建笔记
      </el-button>
    </div>

    <!-- 笔记卡片列表 -->
    <div v-loading="loading" class="notes-container">
      <el-row :gutter="20">
        <el-col
          v-for="note in notes"
          :key="note.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
          style="margin-bottom: 20px;"
        >
          <el-card
            shadow="hover"
            class="note-card"
            @click="$router.push(`/notes/${note.id}/edit`)"
          >
            <div class="note-card-header">
              <h3 class="note-title">{{ note.title }}</h3>
              <el-dropdown
                trigger="click"
                @command="(cmd) => handleNoteCommand(cmd, note)"
                @click.stop
              >
                <el-icon class="more-icon"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="delete">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <p class="note-meta">
              <el-tag size="small" type="info">{{ note.notebook_name }}</el-tag>
              <span class="date">{{ note.updated_at?.slice(0, 10) }}</span>
            </p>
            <div class="note-tags" v-if="note.tags?.length">
              <el-tag
                v-for="tag in note.tags.slice(0, 3)"
                :key="tag"
                size="small"
                type="info"
                effect="plain"
              >
                {{ tag }}
              </el-tag>
              <el-tag v-if="note.tags.length > 3" size="small" type="info">
                +{{ note.tags.length - 3 }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty
        v-if="!loading && notes.length === 0"
        description="还没有笔记，去创建第一篇吧"
      >
        <el-button type="primary" @click="$router.push('/notes/new')">
          创建笔记
        </el-button>
      </el-empty>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="fetchNotes"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled } from '@element-plus/icons-vue'
import { useNotebookStore } from '@/stores/notebook'
import { getNotes, deleteNote, getNotebooks } from '@/api'

const router = useRouter()
const route = useRoute()
const store = useNotebookStore()

const notes = ref([])
const notebooks = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 12
const searchKeyword = ref('')

// 获取笔记本列表
const fetchNotebooks = async () => {
  try {
    const res = await getNotebooks()
    notebooks.value = res.data.results || res.data
  } catch (e) {
    console.error('获取笔记本失败', e)
  }
}

// 获取笔记列表
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
  } catch (e) {
    ElMessage.error('获取笔记失败')
  } finally {
    loading.value = false
  }
}

// 防抖搜索
let debounceTimer = null
const debouncedFetch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    fetchNotes()
  }, 300)
}

// 切换笔记本
const handleNotebookChange = () => {
  page.value = 1
  fetchNotes()
}

// 笔记操作
const handleNoteCommand = async (cmd, note) => {
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除笔记「${note.title}」吗？`,
        '删除确认',
        { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
      )
      await deleteNote(note.id)
      ElMessage.success('删除成功')
      fetchNotes()
    } catch (e) {
      // 用户取消删除
    }
  }
}

onMounted(() => {
  fetchNotebooks()
  fetchNotes()
})

watch(() => route.query.notebook, () => {
  store.setCurrentNotebook(Number(route.query.notebook) || null)
  page.value = 1
  fetchNotes()
}, { immediate: true })
</script>

<style scoped>
.note-list-page {
  min-height: 100vh;
  padding: 24px;
  position: relative;
  background: #ffffff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 24px;
  transition: all 0.3s ease;
  background: #1d1d1f;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.user-info:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.user-avatar {
  background: rgba(255, 255, 255, 0.3);
  color: #fff;
  font-weight: 600;
}

.username {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.dropdown-arrow {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar :deep(.el-select .el-input__wrapper),
.toolbar :deep(.el-input .el-input__wrapper) {
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.toolbar :deep(.el-button) {
  background: #1d1d1f;
  border: none;
  border-radius: 24px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.toolbar :deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.notes-container {
  min-height: 400px;
}

.note-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 16px;
  border: none;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.note-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.note-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.note-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.more-icon {
  color: #909399;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.more-icon:hover {
  background: #f5f5f7;
  color: #1d1d1f;
}

.note-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 12px;
  font-size: 12px;
  color: #909399;
}

.note-meta :deep(.el-tag) {
  background: rgba(0, 0, 0, 0.06);
  border-color: rgba(0, 0, 0, 0.1);
  color: #86868b;
}

.date {
  margin-left: auto;
}

.note-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.note-tags :deep(.el-tag) {
  background: rgba(0, 0, 0, 0.06);
  border-color: rgba(0, 0, 0, 0.1);
  color: #86868b;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.pagination-wrap :deep(.el-pagination) {
  background: #fff;
  padding: 12px 20px;
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

:deep(.el-empty) {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

:deep(.el-dropdown-menu) {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

:deep(.el-dropdown-menu__item) {
  color: #1d1d1f;
}

:deep(.el-dropdown-menu__item:hover) {
  background: rgba(0, 0, 0, 0.06);
  color: #1d1d1f;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .note-list-page {
    padding: 16px;
  }

  .page-header {
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;
  }

  .header-left h2 {
    font-size: 22px;
  }

  .toolbar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    margin-bottom: 20px;
  }

  .toolbar-left {
    flex-direction: column;
    width: 100%;
    gap: 12px;
  }

  .toolbar-left :deep(.el-select) {
    width: 100% !important;
  }

  .toolbar-left :deep(.el-input) {
    width: 100% !important;
    margin-left: 0 !important;
  }

  .toolbar > :deep(.el-button) {
    width: 100%;
  }

  .note-card:hover {
    transform: translateY(-3px);
  }
}
</style>
