<template>
  <div class="home-container">
    <!-- 侧边栏：笔记本 -->
    <aside class="sidebar">
      <h3>我的笔记本</h3>
      <el-button type="primary" @click="showAddDialog" style="width:100%; margin-bottom:12px">
        + 新建笔记本
      </el-button>
      <el-menu
        :default-active="String(store.currentNotebookId)"
        @select="handleSelect"
      >
        <el-menu-item
          v-for="nb in validNotebooks"
          :key="nb.id"
          :index="String(nb.id)"
        >
          <span>{{ nb.name }}</span>
          <el-tag size="small" round>{{ nb.note_count }}</el-tag>
          <el-button
            size="small"
            type="danger"
            circle
            :icon="Delete"
            @click.stop="handleDelete(nb.id)"
            style="margin-left: auto"
          />
        </el-menu-item>
      </el-menu>
      <p v-if="validNotebooks.length === 0" style="color: #999; padding: 12px;">
        暂无笔记本，请创建一个
      </p>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 新建笔记本对话框 -->
    <el-dialog v-model="dialogVisible" title="新建笔记本">
      <el-input v-model="newNotebookName" placeholder="请输入笔记本名称" />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotebookStore } from '@/stores/notebook'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const store = useNotebookStore()
const router = useRouter()

const dialogVisible = ref(false)
const newNotebookName = ref('')

// 只渲染有效笔记本
const validNotebooks = computed(() =>
  store.notebooks.filter(n => n && n.id)
)

onMounted(async () => {
  await store.fetchNotebooks()
  console.log('笔记本列表已加载：', store.notebooks) 
})

const showAddDialog = () => {
  newNotebookName.value = ''
  dialogVisible.value = true
}

const handleAdd = async () => {
  if (!newNotebookName.value.trim()) {
    ElMessage.warning('请输入笔记本名称')
    return
  }
  try {
    await store.addNotebook(newNotebookName.value.trim())
    dialogVisible.value = false
    // 创建后强制刷新列表，避免脏数据
    await store.fetchNotebooks()
    ElMessage.success('笔记本已创建')
  } catch (e) {
    ElMessage.error('创建失败，请检查后端日志')
  }
}

const handleSelect = (id) => {
  store.setCurrentNotebook(Number(id))
  router.push(`/notes?notebook=${id}`)
}

const handleDelete = async (id) => {
  try {
    await store.removeNotebook(id)
    ElMessage.success('笔记本已删除')
    router.push('/')
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.home-container {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: 280px;
  background: #f5f7fa;
  padding: 20px 16px;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
}
.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
.el-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>