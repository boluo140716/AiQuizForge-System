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
      <!-- 顶部用户入口 -->
      <div class="header-right">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="36" :src="userAvatar" class="user-avatar">
              {{ userInitial }}
            </el-avatar>
            <span class="username">{{ userDisplayName }}</span>
            <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人主页
              </el-dropdown-item>
              <el-dropdown-item command="quizHistory">
                <el-icon><List /></el-icon>
                答题历史
              </el-dropdown-item>
              <el-dropdown-item command="wrong">
                <el-icon><Warning /></el-icon>
                错题本
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

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
import { Delete, User, ArrowDown, SwitchButton, List, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCurrentUser } from '@/api'
import axios from 'axios'

const store = useNotebookStore()
const router = useRouter()

const dialogVisible = ref(false)
const newNotebookName = ref('')
const userName = ref('用户')
const userDisplayName = ref('')
const userEmail = ref('')
const userAvatar = ref('')

// 计算用户首字母（无头像时回退）
const userInitial = computed(() => {
  return userDisplayName.value?.charAt(0)?.toUpperCase() || 'U'
})

// 只渲染有效笔记本
const validNotebooks = computed(() =>
  store.notebooks.filter(n => n && n.id)
)

onMounted(async () => {
  await store.fetchNotebooks()
  await fetchUserInfo()
})

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    const res = await getCurrentUser()
    userName.value = res.data.username
    userDisplayName.value = res.data.display_name || res.data.username
    userEmail.value = res.data.email || ''
    userAvatar.value = res.data.avatar || ''
  } catch (e) {
    console.error('获取用户信息失败', e)
  }
}

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

// 用户菜单操作
const handleCommand = async (cmd) => {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'quizHistory') {
    router.push('/quiz-history')
  } else if (cmd === 'wrong') {
    router.push('/wrong-questions')
  } else if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
        confirmButtonText: '确定', cancelButtonText: '取消', type: 'info'
      })
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      delete axios.defaults.headers.common['Authorization']
      router.push('/login')
    } catch (e) {
      // 用户取消退出
    }
  }
}
</script>

<style scoped>
.home-container {
  display: flex;
  height: 100vh;
  background: #ffffff;
}

.sidebar {
  width: 280px;
  height: 100vh;
  padding: 20px 16px;
  overflow-y: auto;
  background: #ffffff;
  border-right: 1px solid #e0e0e0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.sidebar h3 {
  color: #1d1d1f;
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px;
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

.header-right {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.header-right .user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: #1d1d1f;
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.header-right .user-info:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.header-right .user-avatar {
  background: rgba(255, 255, 255, 0.3);
  color: #fff;
  font-weight: 600;
}

.header-right .username {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.header-right .dropdown-arrow {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
}

.sidebar :deep(.el-button) {
  background: #1d1d1f;
  border: none;
  color: #fff;
  font-weight: 500;
  border-radius: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.sidebar :deep(.el-button:hover) {
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.sidebar :deep(.el-menu) {
  background: transparent;
  border: none;
}

.sidebar :deep(.el-menu-item) {
  color: #86868b;
  border-radius: 16px;
  margin-bottom: 10px;
  transition: all 0.3s ease;
  padding: 14px 16px;
  background: #f5f5f7;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar :deep(.el-menu-item:hover),
.sidebar :deep(.el-menu-item.is-active) {
  background: #1d1d1f;
  color: #fff;
  transform: translateX(4px);
}

.sidebar :deep(.el-menu-item.is-active .el-tag) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

.sidebar :deep(.el-tag) {
  background: rgba(0, 0, 0, 0.06);
  border-color: rgba(0, 0, 0, 0.1);
  color: #86868b;
  font-weight: 500;
}

.sidebar :deep(.el-button.is-circle) {
  background: #fff;
  border: 1px solid #e0e0e0;
  color: #86868b;
  width: 34px;
  height: 34px;
  padding: 0;
  transition: all 0.3s ease;
}

.sidebar :deep(.el-menu-item:hover .el-button.is-circle),
.sidebar :deep(.el-menu-item.is-active .el-button.is-circle) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

.sidebar :deep(.el-button.is-circle:hover) {
  background: #fef2f2;
  border-color: #feb2b2;
  color: #f56565;
  transform: scale(1.1);
}

.sidebar :deep(.el-menu-item:hover .el-button.is-circle:hover),
.sidebar :deep(.el-menu-item.is-active .el-button.is-circle:hover) {
  background: rgba(245, 101, 101, 0.8);
  border-color: rgba(245, 101, 101, 0.8);
  color: #fff;
}

.sidebar p {
  color: #86868b;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  position: relative;
}

:deep(.el-dialog) {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  background: #fff;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .home-container {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
  }

  .sidebar {
    width: 100%;
    height: auto;
    max-height: 40vh;
    overflow-y: auto;
    padding: 16px;
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  }

  .sidebar h3 {
    font-size: 18px;
    margin-bottom: 12px;
  }

  .main-content {
    overflow-y: visible;
    padding: 16px;
  }

  .header-right {
    margin-bottom: 16px;
  }

  :deep(.el-dialog) {
    width: 92vw !important;
    max-width: 500px !important;
  }
}
</style>