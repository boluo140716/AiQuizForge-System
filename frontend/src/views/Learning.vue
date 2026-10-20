<template>
  <div class="learning-page">
    <div class="learning-head">
      <p class="qf-eyebrow">分析 / 学习分析</p>
      <h2 class="qf-title">学习分析</h2>
    </div>

    <el-card class="review-card">
      <div class="review-header">
        <div>
          <span class="review-title">今日复习</span>
          <span class="review-count">{{ dueCount }} 题到期</span>
        </div>
        <el-button
          type="primary"
          :loading="reviewing"
          :disabled="dueCount === 0"
          @click="startReview"
        >
          开始复习
        </el-button>
      </div>
    </el-card>

    <el-empty
      v-if="!loading && mastery.length === 0"
      description="还没有学习数据，先做一次测验吧"
    />

    <template v-else>
      <el-row :gutter="20">
        <el-col :xs="24" :md="12">
          <el-card class="chart-card">
            <template #header><span>知识点掌握度</span></template>
            <div ref="radarRef" class="chart"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card class="chart-card">
            <template #header><span>答题正确率曲线</span></template>
            <div ref="lineRef" class="chart"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-card class="weak-card">
        <template #header>
          <div class="weak-header">
            <span>薄弱知识点（掌握度 &lt; 50%）</span>
            <el-button type="primary" :loading="starting" @click="startAdaptive">
              针对练习
            </el-button>
          </div>
        </template>

        <el-table v-if="weakKps.length" :data="weakKps">
          <el-table-column prop="kp_name" label="知识点" />
          <el-table-column label="掌握度" width="180">
            <template #default="{ row }">
              <el-progress :percentage="Math.round(row.p_mastery * 100)" :stroke-width="10" />
            </template>
          </el-table-column>
          <el-table-column prop="attempts" label="作答次数" width="100" />
          <el-table-column prop="correct" label="答对次数" width="100" />
        </el-table>
        <el-empty v-else description="没有薄弱知识点，继续保持！" :image-size="80" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import {
  getMastery, getLearningCurve, generateAdaptiveQuiz,
  getReviewDue, startReviewPractice,
} from '@/api'

const router = useRouter()
const mastery = ref([])
const curve = ref([])
const loading = ref(true)
const starting = ref(false)
const reviewing = ref(false)
const dueCount = ref(0)
const radarRef = ref(null)
const lineRef = ref(null)
let radarChart = null
let lineChart = null

const weakKps = computed(() =>
  mastery.value
    .filter(m => m.p_mastery < 0.5)
    .sort((a, b) => a.p_mastery - b.p_mastery)
)

const renderRadar = () => {
  if (!radarRef.value || mastery.value.length === 0) return
  if (!radarChart) radarChart = echarts.init(radarRef.value)
  radarChart.setOption({
    color: ['#1F5C4A'],
    tooltip: {},
    radar: {
      indicator: mastery.value.map(m => ({ name: m.kp_name, max: 1 })),
      radius: '62%',
      splitNumber: 4,
      axisName: { color: '#6E7A73', fontSize: 11 },
      splitLine: { lineStyle: { color: '#D5DDD6' } },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0)', 'rgba(31,92,74,0.03)'] } },
      axisLine: { lineStyle: { color: '#D5DDD6' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: mastery.value.map(m => Number(m.p_mastery.toFixed(3))),
        name: '掌握度',
        areaStyle: { color: 'rgba(31,92,74,0.16)' },
        lineStyle: { width: 2, color: '#1F5C4A' },
        itemStyle: { color: '#1F5C4A' },
      }],
    }],
  })
}

const renderLine = () => {
  if (!lineRef.value) return
  if (!lineChart) lineChart = echarts.init(lineRef.value)
  lineChart.setOption({
    color: ['#1F5C4A'],
    tooltip: {
      trigger: 'axis',
      formatter: params => `第 ${params[0].axisValue} 次：${params[0].data}%`,
    },
    grid: { left: 44, right: 20, top: 30, bottom: 34 },
    xAxis: {
      type: 'category',
      data: curve.value.map(r => r.index),
      name: '答题次数',
      axisLine: { lineStyle: { color: '#D5DDD6' } },
      axisLabel: { color: '#6E7A73' },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#6E7A73' },
      splitLine: { lineStyle: { color: '#E2E8E3' } },
    },
    series: [{
      type: 'line',
      data: curve.value.map(r => Math.round(r.correct_rate * 100)),
      smooth: true,
      symbolSize: 6,
      lineStyle: { width: 2, color: '#1F5C4A' },
      itemStyle: { color: '#1F5C4A' },
      areaStyle: { color: 'rgba(31,92,74,0.12)' },
    }],
  })
}

const load = async () => {
  loading.value = true
  try {
    const [m, c, d] = await Promise.all([
      getMastery(), getLearningCurve(), getReviewDue(),
    ])
    mastery.value = m.data.mastery || []
    curve.value = c.data.curve || []
    dueCount.value = d.data.due_count || 0
    await nextTick()
    renderRadar()
    renderLine()
  } catch (e) {
    ElMessage.error('加载学习数据失败')
  } finally {
    loading.value = false
  }
}

const startAdaptive = async () => {
  starting.value = true
  try {
    const res = await generateAdaptiveQuiz({ count: 5 })
    router.push('/quiz/' + res.data.practice_quiz_id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '暂无可练习的题目')
  } finally {
    starting.value = false
  }
}

const startReview = async () => {
  reviewing.value = true
  try {
    const res = await startReviewPractice(10)
    router.push('/quiz/' + res.data.practice_quiz_id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '暂无可复习的题目')
  } finally {
    reviewing.value = false
  }
}

const handleResize = () => {
  radarChart?.resize()
  lineChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  lineChart?.dispose()
})
</script>

<style scoped>
.learning-page {
  padding: 24px;
}
.page-title {
  margin: 0 0 20px;
}
.chart-card {
  margin-bottom: 20px;
}
.chart {
  width: 100%;
  height: 360px;
}
.weak-card {
  margin-top: 4px;
}
.weak-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.review-card {
  margin-bottom: 20px;
}
.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.review-title {
  font-weight: 600;
  margin-right: 12px;
}
.review-count {
  color: #909399;
  font-size: 14px;
}
</style>

<style scoped>
/* ===== study desk ===== */
.learning-page {
  padding: 0;
}

.learning-head {
  margin-bottom: 24px;
}

.chart-card,
.weak-card,
.review-card {
  position: relative;
  border: 1px solid var(--qf-line);
  border-radius: 3px;
  background: var(--qf-surface);
  box-shadow: none;
}

.chart-card::before,
.weak-card::before,
.review-card::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 18px;
  width: 48px;
  height: 4px;
  background: var(--qf-primary);
}

.review-card::before {
  background: var(--qf-accent);
}

.chart {
  height: 340px;
}

.weak-header {
  font-weight: 700;
}

.review-title {
  font-weight: 800;
  letter-spacing: -0.02em;
}

.review-count {
  font-family: var(--qf-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--qf-muted);
}

@media (max-width: 768px) {
  .learning-page {
    padding: 0;
  }

  .chart {
    height: 280px;
  }
}
</style>
