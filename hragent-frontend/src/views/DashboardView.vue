<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getDashboard, getTrend, getActivities } from '@/api/stats'
import { formatGrowth } from '@/utils/stats'

const overview = ref([])
const recruitment = ref({
  resume_evaluation_total: 0,
  resume_evaluation_recent: 0,
  pending_interview_count: 0,
  interview_plan_total: 0,
})
const conversation = ref({ conversation_total: 0, conversation_recent: 0 })
const activities = ref([])
const loading = ref(false)

const chartEl = ref(null)
let chart = null

const ACTIVITY_TYPE_LABELS = {
  jd: '岗位描述',
  resume: '简历评估',
  interview: '面试方案',
  conversation: '对话',
}

function formatTime(s) {
  if (!s) return '—'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString('zh-CN', { hour12: false })
}

function growthClass(g) {
  if (g === null || g === undefined || g === 0) return 'flat'
  return g > 0 ? 'up' : 'down'
}

function renderChart(trend) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['岗位描述', '简历评估', '面试方案', '对话'] },
    grid: { left: 40, right: 20, top: 48, bottom: 30 },
    xAxis: { type: 'category', data: trend.days },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '岗位描述', type: 'line', smooth: true, data: trend.series.jd },
      { name: '简历评估', type: 'line', smooth: true, data: trend.series.resume },
      { name: '面试方案', type: 'line', smooth: true, data: trend.series.interview },
      { name: '对话', type: 'line', smooth: true, data: trend.series.conversation },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    const [d, t, a] = await Promise.all([getDashboard(), getTrend(30), getActivities(10)])
    overview.value = d.data.overview || []
    recruitment.value = d.data.recruitment
    conversation.value = d.data.conversation
    activities.value = a.data || []
    renderChart(t.data)
  } catch {
    /* 加载失败不阻断页面 */
  } finally {
    loading.value = false
  }
}

onMounted(load)
onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<template>
  <div v-loading="loading" class="dashboard-page">
    <div class="page-head">
      <div>
        <h2 class="page-title">数据看板</h2>
        <p class="page-sub">招聘与知识对话核心指标概览、近 30 天趋势与最近动态</p>
      </div>
    </div>

    <!-- 概览卡 -->
    <div class="overview-grid">
      <el-card v-for="o in overview" :key="o.key" class="ov-card" shadow="never">
        <div class="ov-label">{{ o.label }}</div>
        <div class="ov-value">{{ o.value }}</div>
        <div class="ov-growth" :class="growthClass(o.growth)">环比 {{ formatGrowth(o.growth) }}</div>
      </el-card>
    </div>

    <!-- 招聘 / 对话统计 -->
    <div class="stats-grid">
      <el-card shadow="never">
        <template #header><span class="card-title">招聘统计</span></template>
        <div class="stat-row"><span>简历评估总数</span><b>{{ recruitment.resume_evaluation_total }}</b></div>
        <div class="stat-row"><span>近 30 天简历评估</span><b>{{ recruitment.resume_evaluation_recent }}</b></div>
        <div class="stat-row"><span>待处理面试</span><b>{{ recruitment.pending_interview_count }}</b></div>
        <div class="stat-row"><span>面试方案总数</span><b>{{ recruitment.interview_plan_total }}</b></div>
      </el-card>
      <el-card shadow="never">
        <template #header><span class="card-title">对话统计</span></template>
        <div class="stat-row"><span>会话总数</span><b>{{ conversation.conversation_total }}</b></div>
        <div class="stat-row"><span>近 30 天会话</span><b>{{ conversation.conversation_recent }}</b></div>
      </el-card>
    </div>

    <!-- 趋势图 -->
    <el-card shadow="never" class="block-card">
      <template #header><span class="card-title">近 30 天趋势</span></template>
      <div ref="chartEl" class="chart" />
    </el-card>

    <!-- 最近活动 -->
    <el-card shadow="never">
      <template #header><span class="card-title">最近活动</span></template>
      <el-empty v-if="!activities.length" description="暂无活动" :image-size="80" />
      <el-table v-else :data="activities" style="width: 100%">
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ ACTIVITY_TYPE_LABELS[row.type] || row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容" min-width="240">
          <template #default="{ row }">{{ row.title }}</template>
        </el-table-column>
        <el-table-column label="时间" width="200">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-page {
  min-height: 100%;
}

.page-head {
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.page-sub {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.ov-card {
  text-align: center;
}

.ov-label {
  color: #909399;
  font-size: 13px;
}

.ov-value {
  font-size: 30px;
  font-weight: 600;
  color: #303133;
  margin: 8px 0;
}

.ov-growth {
  font-size: 12px;
  color: #909399;
}

.ov-growth.up {
  color: #67c23a;
}

.ov-growth.down {
  color: #f56c6c;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  color: #606266;
  font-size: 13px;
  border-bottom: 1px solid #f5f7fa;
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-row b {
  color: #303133;
  font-size: 16px;
}

.block-card {
  margin-bottom: 16px;
}

.chart {
  height: 320px;
}

@media (max-width: 900px) {
  .overview-grid,
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
