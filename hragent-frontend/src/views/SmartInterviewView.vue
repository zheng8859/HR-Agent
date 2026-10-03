<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listResumes } from '@/api/resumeEvaluation'
import {
  generatePlan,
  regeneratePlan,
  listPlans,
  updatePlan,
  exportPlan,
} from '@/api/interviewPlan'
import { parsePlanSections } from '@/utils/interview'

const router = useRouter()

const STATUS_META = {
  pending: { label: '待人工复核', type: 'info' },
  interview: { label: '进入面试', type: 'success' },
  rejected: { label: '淘汰', type: 'danger' },
}

const evaluations = ref([])
const plans = ref([])
const selectedEvaluationId = ref(null)

const generating = ref(false)
const saving = ref(false)
const regenerating = ref(false)
const editing = ref(false)
const draftContent = ref('')

// 仅已完成简历评估（total_score 非空）的候选人进入面试方案候选
const candidates = computed(() => evaluations.value.filter((e) => e.total_score != null))
const selectedEvaluation = computed(
  () => candidates.value.find((c) => c.id === selectedEvaluationId.value) || null,
)
const currentPlan = computed(
  () => plans.value.find((p) => p.resume_evaluation_id === selectedEvaluationId.value) || null,
)
const sections = computed(() => parsePlanSections(currentPlan.value?.content || ''))

function candidateLabel(c) {
  const name = c.candidate_name || '未命名'
  const pos = c.candidate_position ? ` · ${c.candidate_position}` : ''
  const score = c.total_score != null ? ` · 综合评分 ${c.total_score}分` : ''
  return `候选人：${name}${pos}${score}`
}

function scoreColor(score) {
  if (score == null) return '#909399'
  if (score >= 75) return '#67C23A'
  if (score >= 50) return '#E6A23C'
  return '#F56C6C'
}

function avatarChar(name) {
  return (name || '候').trim().charAt(0) || '候'
}

async function loadData() {
  try {
    const [evRes, planRes] = await Promise.all([listResumes(), listPlans()])
    evaluations.value = evRes.data
    plans.value = planRes.data
    if (!selectedEvaluationId.value && candidates.value.length) {
      selectedEvaluationId.value = candidates.value[0].id
    }
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

// 切换候选人时退出编辑态并清空草稿
watch(selectedEvaluationId, () => {
  editing.value = false
  draftContent.value = currentPlan.value?.content || ''
})

function startEdit() {
  draftContent.value = currentPlan.value?.content || ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function handleGenerate() {
  if (!selectedEvaluation.value) return
  generating.value = true
  try {
    await generatePlan(selectedEvaluation.value.id)
    await loadData()
    ElMessage.success('面试方案已生成，候选人状态已置为进入面试')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

async function handleRegenerate() {
  if (!currentPlan.value) return
  regenerating.value = true
  try {
    const { data } = await regeneratePlan(currentPlan.value.id)
    const idx = plans.value.findIndex((p) => p.id === data.id)
    if (idx >= 0) plans.value[idx] = data
    ElMessage.success('方案已重新生成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重新生成失败')
  } finally {
    regenerating.value = false
  }
}

async function handleSave() {
  if (!currentPlan.value) return
  saving.value = true
  try {
    const { data } = await updatePlan(currentPlan.value.id, {
      content: draftContent.value,
      candidate_name: selectedEvaluation.value?.candidate_name || null,
    })
    const idx = plans.value.findIndex((p) => p.id === data.id)
    if (idx >= 0) plans.value[idx] = data
    editing.value = false
    ElMessage.success('方案已保存')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleExport(format) {
  if (!currentPlan.value) return
  try {
    const { data } = await exportPlan(currentPlan.value.id, format)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `面试方案-${currentPlan.value.candidate_name || '候选人'}.${format}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('方案已导出')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导出失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="interview-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">智能面试</h2>
        <p class="page-sub">选择已完成评估的候选人，AI 生成专属结构化面试方案；AI 出初稿，人定终稿</p>
      </div>
    </div>

    <!-- 候选人选择栏 -->
    <el-card class="select-bar" shadow="never">
      <div class="select-row">
        <div class="select-main">
          <span class="bind-label">候选人：</span>
          <el-select
            v-model="selectedEvaluationId"
            :disabled="!candidates.length"
            placeholder="选择已完成评估的候选人"
            filterable
            style="width: 360px"
          >
            <el-option
              v-for="c in candidates"
              :key="c.id"
              :label="candidateLabel(c)"
              :value="c.id"
            />
          </el-select>
          <span class="select-hint">（注：仅可选择已完成简历评估的候选人）</span>
        </div>
        <el-button
          type="primary"
          :loading="generating"
          :disabled="!selectedEvaluation || generating"
          @click="handleGenerate"
        >
          生成面试方案
        </el-button>
      </div>
    </el-card>

    <!-- 空态：无已完成评估候选人 -->
    <el-card v-if="!candidates.length" class="empty-card" shadow="never">
      <el-empty
        description="暂无已完成简历评估的候选人，请先完成简历评估流程"
        :image-size="110"
      >
        <el-button type="primary" @click="router.push({ name: 'resume-screening' })">
          去简历筛选页
        </el-button>
      </el-empty>
    </el-card>

    <!-- 空态：已选候选人但尚未生成方案 -->
    <el-card v-else-if="!currentPlan" class="empty-card" shadow="never">
      <el-empty
        :description="`尚未为「${selectedEvaluation?.candidate_name || '该候选人'}」生成面试方案`"
        :image-size="110"
      >
        <el-button
          type="primary"
          :loading="generating"
          :disabled="generating"
          @click="handleGenerate"
        >
          生成面试方案
        </el-button>
      </el-empty>
    </el-card>

    <!-- 方案卡片 -->
    <template v-else>
      <el-card class="plan-card" shadow="never">
        <div class="plan-head">
          <div class="plan-identity">
            <el-tag type="info" effect="plain" round>AI 生成 · 待确认</el-tag>
            <h3 class="plan-title">
              结构化面试方案 — {{ currentPlan.candidate_name || selectedEvaluation?.candidate_name || '候选人' }}
              <span v-if="currentPlan.candidate_position || selectedEvaluation?.candidate_position" class="plan-pos">
                （{{ currentPlan.candidate_position || selectedEvaluation?.candidate_position }}）
              </span>
            </h3>
          </div>
          <div v-if="selectedEvaluation" class="plan-score">
            综合评分：
            <strong :style="{ color: scoreColor(selectedEvaluation.total_score) }">
              {{ selectedEvaluation.total_score ?? '-' }}
            </strong>
            分
          </div>
        </div>

        <!-- 候选人快照 -->
        <div class="snapshot">
          <span class="snap-avatar">{{ avatarChar(currentPlan.candidate_name || selectedEvaluation?.candidate_name) }}</span>
          <div class="snap-info">
            <div class="snap-name">
              {{ currentPlan.candidate_name || selectedEvaluation?.candidate_name || '未命名' }}
              <el-tag
                v-if="selectedEvaluation"
                size="small"
                :type="STATUS_META[selectedEvaluation.status]?.type || 'info'"
                effect="plain"
              >
                {{ STATUS_META[selectedEvaluation.status]?.label || selectedEvaluation.status }}
              </el-tag>
            </div>
            <div class="snap-meta">
              {{ selectedEvaluation?.candidate_position || '-' }}
              <template v-if="selectedEvaluation?.work_years != null"> · {{ selectedEvaluation.work_years }}年经验</template>
              <template v-if="selectedEvaluation?.education_level"> · {{ selectedEvaluation.education_level }}</template>
            </div>
          </div>
        </div>

        <!-- 编辑态 -->
        <el-input
          v-if="editing"
          v-model="draftContent"
          type="textarea"
          :rows="18"
          placeholder="编辑面试方案（markdown）"
        />

        <!-- 七要素分区展示 -->
        <div v-else class="section-list">
          <div v-for="s in sections" :key="s.title" class="section-card">
            <div class="section-head">
              <span class="section-bar" />
              <span class="section-title">{{ s.title }}</span>
            </div>
            <pre class="section-body">{{ s.body || '（暂无内容）' }}</pre>
          </div>
        </div>
      </el-card>

      <!-- 操作栏 -->
      <el-card class="action-bar" shadow="never">
        <div class="action-row">
          <template v-if="!editing">
            <el-button :disabled="regenerating" @click="startEdit">在线编辑方案</el-button>
            <el-button :loading="regenerating" :disabled="regenerating" @click="handleRegenerate">
              重新生成
            </el-button>
          </template>
          <template v-else>
            <el-button :loading="saving" :disabled="saving" type="primary" @click="handleSave">保存</el-button>
            <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
          </template>
          <span class="action-spacer" />
          <el-button @click="handleExport('md')">导出 Markdown</el-button>
          <el-button @click="handleExport('txt')">导出 TXT</el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.interview-page {
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

.select-bar {
  margin-bottom: 16px;
}

.select-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.select-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.bind-label {
  color: #606266;
  font-weight: 500;
  font-size: 13px;
}

.select-hint {
  color: #909399;
  font-size: 12px;
}

.empty-card {
  margin-bottom: 16px;
}

.plan-card {
  margin-bottom: 16px;
  border-left: 3px solid #7b61ff;
}

.plan-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.plan-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.plan-title {
  margin: 0;
  font-size: 17px;
  color: #303133;
}

.plan-pos {
  font-size: 14px;
  font-weight: 400;
  color: #606266;
}

.plan-score {
  font-size: 13px;
  color: #909399;
}

.snapshot {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8f9fb;
  border-radius: 8px;
  margin: 16px 0;
}

.snap-avatar {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #e6f0fc;
  color: #409eff;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.snap-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snap-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.snap-meta {
  font-size: 12px;
  color: #909399;
}

.section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.section-bar {
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: #409eff;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-body {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.action-bar {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-spacer {
  flex: 1;
}
</style>
