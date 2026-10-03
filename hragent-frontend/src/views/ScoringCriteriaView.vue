<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  generateScoring,
  listScoring,
  createScoring,
  updateScoring,
  deleteScoring,
} from '@/api/scoringCriteria'
import { listJDs } from '@/api/jobDescription'
import { checkBalance } from '@/utils/balance'

const STATUS_META = {
  draft: { label: '草稿', type: 'info' },
  active: { label: '已锁定', type: 'success' },
  archived: { label: '已归档', type: 'info' },
}

const jds = ref([])
const selectedJdId = ref(null)
const savedStandards = ref([])
const generating = ref(false)
const editingId = ref(null)

const draft = reactive({
  title: '',
  content: '',
  job_title: '',
  total_score: 100,
  dimensions: [],
})

const balance = computed(() => checkBalance(draft.dimensions, draft.total_score))
const selectedJd = computed(() => jds.value.find((j) => j.id === selectedJdId.value))

function emptyDimension() {
  return { name: '', description: '', max_score: 0 }
}

function applyGenerated(g) {
  draft.title = g.title || ''
  draft.content = g.content || ''
  draft.job_title = g.job_title || ''
  draft.total_score = g.total_score ?? 100
  draft.dimensions = (g.dimensions || []).map((d) => ({
    name: d.name || '',
    description: d.description || '',
    max_score: Number(d.max_score ?? d.weight ?? 0),
  }))
}

function resetDraft() {
  draft.title = ''
  draft.content = ''
  draft.job_title = ''
  draft.total_score = 100
  draft.dimensions = []
  editingId.value = null
}

async function loadData() {
  try {
    const [jdRes, scRes] = await Promise.all([listJDs(), listScoring()])
    jds.value = jdRes.data
    savedStandards.value = scRes.data
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

async function handleGenerate() {
  if (!selectedJdId.value) {
    ElMessage.warning('请先选择要关联的 JD')
    return
  }
  const jd = selectedJd.value
  if (!jd) {
    ElMessage.warning('未找到所选 JD')
    return
  }
  generating.value = true
  try {
    const { data } = await generateScoring({ job_title: jd.title, content: jd.content || '' })
    applyGenerated(data)
    ElMessage.success('已生成评分维度，请人工确认权重')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

function addDimension() {
  draft.dimensions.push(emptyDimension())
}

function removeDimension(index) {
  if (draft.dimensions.length <= 1) {
    ElMessage.warning('至少需要保留一个评估维度')
    return
  }
  draft.dimensions.splice(index, 1)
}

function toPayload(status) {
  return {
    title: draft.title || `${draft.job_title || '未命名'} 评分标准`,
    content: draft.content || '',
    job_title: draft.job_title || null,
    total_score: draft.total_score,
    scoring_dimensions: draft.dimensions.map((d) => ({
      name: d.name,
      weight: Number(d.max_score),
      max_score: Number(d.max_score),
      description: d.description,
    })),
    job_description_id: selectedJdId.value,
    status,
  }
}

async function handleSave(status) {
  if (!draft.dimensions.length) {
    ElMessage.warning('请先生成评分维度')
    return
  }
  try {
    if (editingId.value) {
      await updateScoring(editingId.value, toPayload(status))
      ElMessage.success('评分标准已更新')
    } else {
      await createScoring(toPayload(status))
      ElMessage.success(status === 'active' ? '评分标准已锁定并生效' : '评分标准已保存为草稿')
    }
    resetDraft()
    await loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

function handleEdit(sc) {
  editingId.value = sc.id
  draft.title = sc.title || ''
  draft.content = sc.content || ''
  draft.job_title = sc.job_title || ''
  draft.total_score = sc.total_score ?? 100
  draft.dimensions = (sc.scoring_dimensions || []).map((d) => ({
    name: d.name || '',
    description: d.description || '',
    max_score: Number(d.max_score ?? d.weight ?? 0),
  }))
  if (sc.job_description_id) selectedJdId.value = sc.job_description_id
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function handleDelete(sc) {
  try {
    await ElMessageBox.confirm('确认删除此评分标准？该操作无法撤销。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    await deleteScoring(sc.id)
    ElMessage.success('已删除')
    if (editingId.value === sc.id) resetDraft()
    await loadData()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="scoring-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">评分标准生成</h2>
        <p class="page-sub">针对已发布岗位定义 AI 简历智能评估维度与权重，权重经人工核准后方可生效</p>
      </div>
      <div class="head-actions">
        <el-button :loading="generating" @click="handleGenerate">重新生成</el-button>
        <el-button type="primary" :disabled="!balance.isBalanced" @click="handleSave('active')">
          保存并锁定标准
        </el-button>
      </div>
    </div>

    <!-- 关联 JD -->
    <el-card class="bind-bar" shadow="never">
      <div class="bind-row">
        <div class="bind-info">
          <span class="bind-label">已绑定岗位 JD：</span>
          <el-select
            v-model="selectedJdId"
            placeholder="选择要关联的 JD"
            filterable
            clearable
            style="width: 320px"
            @change="resetDraft"
          >
            <el-option v-for="jd in jds" :key="jd.id" :label="jd.title" :value="jd.id" />
          </el-select>
          <el-button type="primary" :loading="generating" :disabled="!selectedJdId" @click="handleGenerate">
            生成评分标准
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 人工确认提示条 -->
    <el-alert
      v-if="draft.dimensions.length"
      class="confirm-alert"
      :type="balance.isBalanced ? 'success' : 'warning'"
      :closable="false"
      show-icon
    >
      <template #title>
        {{
          balance.isBalanced
            ? '权重配比校验通过，可保存并锁定本标准。'
            : `权重合计 ${balance.scoreSum} 分，与总分 ${draft.total_score} 分不一致（差 ${Math.abs(balance.difference)} 分），请人工确认权重配比后再锁定。`
        }}
      </template>
    </el-alert>

    <!-- 维度配置卡片 -->
    <el-card class="dimension-card" shadow="never">
      <template #header>
        <div class="dimension-head">
          <div>
            <el-tag type="info" effect="plain" size="small">AI 生成 · 待确认</el-tag>
            <span class="dimension-title">评分维度与权重配置</span>
          </div>
          <div class="total-chip">
            总分上限：<strong>{{ draft.total_score }}</strong> 分
          </div>
        </div>
      </template>

      <el-empty
        v-if="!draft.dimensions.length"
        description="选择 JD 后点击「生成评分标准」"
        :image-size="80"
      />

      <div v-for="(dim, index) in draft.dimensions" :key="index" class="dim-row">
        <div class="dim-index">{{ index + 1 }}</div>
        <div class="dim-fields">
          <el-input v-model="dim.name" placeholder="维度名称" class="dim-name" />
          <el-input v-model="dim.description" placeholder="考察内容与要点说明" class="dim-desc" />
        </div>
        <div class="dim-score">
          <el-input-number
            v-model="dim.max_score"
            :min="0"
            :max="draft.total_score"
            controls-position="right"
          />
          <span class="score-unit">分</span>
        </div>
        <el-button link type="danger" @click="removeDimension(index)">删除</el-button>
      </div>

      <el-button class="add-dim" @click="addDimension">+ 添加自定义评估维度</el-button>

      <div class="balance-bar">
        <span :class="balance.isBalanced ? 'ok' : 'bad'">
          当前权重合计：<strong>{{ balance.scoreSum }}</strong> / {{ draft.total_score }} 分
        </span>
        <div class="balance-actions">
          <el-button size="small" :disabled="!draft.dimensions.length" @click="handleSave('draft')">
            保存为草稿
          </el-button>
          <el-button
            size="small"
            type="primary"
            :disabled="!balance.isBalanced || !draft.dimensions.length"
            @click="handleSave('active')"
          >
            确认锁定本标准
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 说明卡片 -->
    <el-row :gutter="16" class="info-row">
      <el-col :span="8">
        <el-card shadow="never">
          <strong>合规性与客观性</strong>
          <p>已自动过滤性别、年龄、地域等可能导致歧视的禁用特征。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <strong>AI 自动初筛准则</strong>
          <p>锁定标准后，进入投递管道的简历将以该标准进行评分与排位。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <strong>全链路留痕可溯</strong>
          <p>每一次维度增删及分值调优均记录入审计日志。</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 已保存评分标准 -->
    <el-card class="saved-card" shadow="never">
      <template #header>
        <span>已保存评分标准（{{ savedStandards.length }}）</span>
      </template>
      <el-empty v-if="!savedStandards.length" description="暂无已保存评分标准" :image-size="60" />
      <div v-for="sc in savedStandards" :key="sc.id" class="sc-item">
        <div class="sc-item-main">
          <span class="sc-title">{{ sc.title }}</span>
          <el-tag :type="STATUS_META[sc.status]?.type || 'info'" size="small">
            {{ STATUS_META[sc.status]?.label || sc.status }}
          </el-tag>
        </div>
        <div class="sc-actions">
          <el-button link type="primary" size="small" @click="handleEdit(sc)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(sc)">删除</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.scoring-page {
  min-height: 100%;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
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

.head-actions {
  display: flex;
  gap: 8px;
}

.bind-bar {
  margin-bottom: 16px;
}

.bind-row {
  display: flex;
  align-items: center;
}

.bind-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.bind-label {
  color: #606266;
  font-weight: 500;
}

.confirm-alert {
  margin-bottom: 16px;
}

.dimension-card {
  margin-bottom: 16px;
  border-left: 3px solid #7b61ff;
}

.dimension-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dimension-title {
  margin-left: 8px;
  font-weight: 600;
  color: #303133;
}

.total-chip {
  color: #606266;
  font-size: 13px;
}

.total-chip strong {
  color: #409eff;
  font-size: 16px;
}

.dim-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #f8f9fb;
  margin-bottom: 10px;
}

.dim-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e6f0fc;
  color: #409eff;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.dim-fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dim-name {
  max-width: 240px;
}

.dim-score {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.score-unit {
  color: #909399;
  font-size: 13px;
}

.add-dim {
  width: 100%;
  margin-top: 4px;
}

.balance-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: #f2f6fc;
}

.ok {
  color: #67c23a;
}

.bad {
  color: #f56c6c;
}

.balance-actions {
  display: flex;
  gap: 8px;
}

.info-row {
  margin-bottom: 16px;
}

.info-row p {
  margin: 6px 0 0;
  color: #909399;
  font-size: 12px;
}

.sc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 4px;
  border-bottom: 1px solid #f0f0f0;
}

.sc-item:last-child {
  border-bottom: none;
}

.sc-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sc-title {
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sc-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>
