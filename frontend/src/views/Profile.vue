<template>
  <div class="profile-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <el-button text @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2>个人主页</h2>
    </div>

    <!-- 用户信息卡片 -->
    <el-card class="profile-card" v-loading="loading">
      <div class="user-header">
        <div class="avatar-upload-wrapper" @click="triggerUpload" title="点击更换头像">
          <el-avatar :size="80" :src="avatarUrl" class="user-avatar" v-loading="avatarUploading">
            {{ avatarFallback }}
          </el-avatar>
          <div class="avatar-overlay">
            <el-icon><Camera /></el-icon>
          </div>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/jpeg,image/png"
            style="display: none"
            @change="handleAvatarChange"
          />
        </div>
        <div class="user-info">
          <div class="username-row" @click.stop>
            <template v-if="editingName">
              <el-input
                v-model="nameEditValue"
                ref="nameInputRef"
                maxlength="50"
                class="name-edit-input"
                @keyup.enter="saveDisplayName"
                @blur="saveDisplayName"
                @keyup.escape="cancelEditName"
              />
            </template>
            <h1 v-else class="username" @click="startEditName" title="点击修改昵称">
              {{ profile?.display_name || profile?.username }}
            </h1>
          </div>
          <p class="email">{{ profile?.email || '未设置邮箱' }}</p>
          <p class="join-date">加入于 {{ profile?.date_joined?.slice(0, 10) }}</p>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="$router.push('/notes')">
          <div class="stat-icon notes-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_notes || 0 }}</div>
            <div class="stat-label">总笔记数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="$router.push('/quiz-history')">
          <div class="stat-icon quiz-icon">
            <el-icon><List /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_quizzes || 0 }}</div>
            <div class="stat-label">总测验数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="$router.push('/wrong-questions')">
          <div class="stat-icon wrong-icon">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ profile?.total_wrong_questions || 0 }}</div>
            <div class="stat-label">错题数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon rate-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ ((profile?.avg_correct_rate || 0) * 100).toFixed(0) }}%</div>
            <div class="stat-label">平均正确率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学习进度 -->
    <el-card class="progress-card">
      <h3>学习概览</h3>
      <div class="progress-item">
        <span class="progress-label">笔记完成度</span>
        <el-progress
          :percentage="notesProgress"
          :stroke-width="10"
          :color="'#1d1d1f'"
        />
      </div>
      <div class="progress-item">
        <span class="progress-label">测验参与度</span>
        <el-progress
          :percentage="quizProgress"
          :stroke-width="10"
          :color="'#86868b'"
        />
      </div>
      <div class="progress-item">
        <span class="progress-label">错题纠正率</span>
        <el-progress
          :percentage="wrongProgress"
          :stroke-width="10"
          :color="'#f56c6c'"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ArrowLeft, Document, List, Warning, TrendCharts, Camera } from '@element-plus/icons-vue'
import { getUserProfile, updateProfile } from '@/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const profile = ref(null)
const fileInputRef = ref(null)
const avatarUploading = ref(false)

const avatarUrl = computed(() => profile.value?.avatar || '')
const avatarFallback = computed(() => profile.value?.username?.charAt(0)?.toUpperCase() || 'U')

const notesProgress = computed(() => {
  const total = profile.value?.total_notes || 0
  return Math.min(total * 10, 100)
})

const quizProgress = computed(() => {
  const total = profile.value?.total_quizzes || 0
  return Math.min(total * 20, 100)
})

const wrongProgress = computed(() => {
  const wrong = profile.value?.total_wrong_questions || 0
  const total = profile.value?.total_quizzes || 1
  if (total === 0) return 100
  return Math.max(100 - (wrong / total * 100), 0)
})

const fetchProfile = async () => {
  loading.value = true
  try {
    const res = await getUserProfile()
    profile.value = res.data
  } catch (e) {
    ElMessage.error('获取个人资料失败')
  } finally {
    loading.value = false
  }
}

const editingName = ref(false)
const nameEditValue = ref('')
const nameInputRef = ref(null)
const nameSaving = ref(false)

const startEditName = () => {
  nameEditValue.value = profile.value?.display_name || profile.value?.username || ''
  editingName.value = true
  nextTick(() => nameInputRef.value?.focus())
}

const saveDisplayName = async () => {
  if (!editingName.value) return
  const val = nameEditValue.value.trim()
  editingName.value = false
  if (!val) return
  if (val === (profile.value?.display_name || profile.value?.username)) return

  nameSaving.value = true
  try {
    const formData = new FormData()
    formData.append('display_name', val)
    const res = await updateProfile(formData)
    profile.value = { ...profile.value, display_name: res.data.display_name, avatar: res.data.avatar }
    ElMessage.success('昵称已更新')
  } catch (e) {
    ElMessage.error(e.response?.data?.display_name?.[0] || '修改失败')
  } finally {
    nameSaving.value = false
  }
}

const cancelEditName = () => {
  editingName.value = false
}

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const handleAvatarChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  const ext = file.name.split('.').pop().toLowerCase()
  if (!['jpg', 'jpeg', 'png'].includes(ext)) {
    ElMessage.error('仅支持 JPG/PNG 格式图片')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('头像文件不能超过 2MB')
    return
  }

  avatarUploading.value = true
  try {
    const formData = new FormData()
    formData.append('avatar', file)
    const res = await updateProfile(formData)
    profile.value = { ...profile.value, avatar: res.data.avatar, display_name: res.data.display_name }
    ElMessage.success('头像已更新')
  } catch (err) {
    const detail = err.response?.data?.avatar?.[0] || err.response?.data?.detail || '上传失败'
    ElMessage.error(typeof detail === 'string' ? detail : '上传失败')
  } finally {
    avatarUploading.value = false
    e.target.value = ''
  }
}

onMounted(fetchProfile)
</script>

<style scoped>
.profile-page {
  padding: 24px;
  min-height: 100vh;
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
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
}

.profile-card {
  margin-bottom: 24px;
  border-radius: 16px;
}

.user-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.user-avatar {
  background: #1d1d1f;
  color: #fff;
  font-size: 32px;
  font-weight: 600;
}

.avatar-upload-wrapper {
  position: relative;
  cursor: pointer;
  display: inline-block;
  border-radius: 50%;
  flex-shrink: 0;
  line-height: 0;
  transition: transform 0.3s ease;
}

.avatar-upload-wrapper:hover {
  transform: scale(1.06);
}

.avatar-upload-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-upload-wrapper :deep(.el-avatar) {
  transition: filter 0.3s ease;
}

.avatar-upload-wrapper:hover :deep(.el-avatar) {
  filter: brightness(0.85);
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.avatar-overlay .el-icon {
  font-size: 22px;
  color: #fff;
}

.user-info .username {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  cursor: pointer;
  transition: color 0.2s;
}

.user-info .username:hover {
  color: #86868b;
}

.username-row {
  display: inline-flex;
  align-items: center;
}

.name-edit-input {
  max-width: 240px;
  margin-bottom: 8px;
}

.user-info .email {
  margin: 0 0 4px;
  font-size: 14px;
  color: #86868b;
}

.user-info .join-date {
  margin: 0;
  font-size: 13px;
  color: #c0c4cc;
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

.stat-card.clickable {
  cursor: pointer;
  transition: all 0.3s ease;
}

.stat-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
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

.notes-icon {
  background: #1d1d1f;
  color: #fff;
}

.quiz-icon {
  background: #86868b;
  color: #fff;
}

.wrong-icon {
  background: #f56c6c;
  color: #fff;
}

.rate-icon {
  background: #1d1d1f;
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

.progress-card {
  border-radius: 16px;
}

.progress-card h3 {
  margin: 0 0 20px;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.progress-item {
  margin-bottom: 20px;
}

.progress-item:last-child {
  margin-bottom: 0;
}

.progress-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #86868b;
}

/* ============ Mobile: <= 768px ============ */
@media (max-width: 768px) {
  .profile-page {
    padding: 12px;
  }

  .page-header {
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }

  .page-header h2 {
    font-size: 20px;
  }

  .user-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 16px;
  }

  .user-avatar {
    width: 64px;
    height: 64px;
    font-size: 26px;
  }

  .user-info .username {
    font-size: 20px;
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

  .stat-card.clickable:hover {
    transform: translateY(-2px);
  }

  .progress-card {
    padding: 16px;
  }

  .progress-card h3 {
    font-size: 16px;
  }

  .progress-label {
    font-size: 13px;
  }

  .avatar-upload-wrapper:hover {
    transform: none;
  }
}
</style>