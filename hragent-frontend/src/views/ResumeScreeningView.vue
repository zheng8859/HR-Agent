<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listJDs } from '@/api/jobDescription'
import { listScoring } from '@/api/scoringCriteria'
import {
  uploadResume,
  evaluateResume,
  listResumes,
  updateResumeStatus,
  exportResume,
} from '@/api/resumeEvaluation'
import { validateResumeFile, dimensionPct, RESUME_ALLOWED_TYPES } from '@/utils/resume'

const STATUS_META = {
  pending: { label: '待人工复核', type: 'info' },
  interview: { label: '进入面试', type: 'success' },
  rejected: { label: '淘汰', type: 'danger' },
}
const STATUS_OPTIONS = [
  { value: 'pending', label: '待人工复核' },
  { value: 'interview', label: '进入面试' },
  { value: 'rejected', label: '淘汰' },
]

const acceptStr = RESUME_ALLOWED_TYPES.map((t) => `.${t}`).join(',')

const jds = ref([])
const standards = ref([])
const evaluations = ref([])

const selectedJdId = ref(null)
const selectedCriteriaId = ref(null)
const selectedId = ref(null)

const uploading = ref(false)
const evaluating = ref(false)

const uploadedFile = reactive({ original_filename: '', file_type: '', resume_content: '' })

const selected = computed(() => evaluations.value.find((e) => e.id === selectedId.value) || null)
const selectedJd = computed(() => jds.value.find((j) => j.id === selectedJdId.value) || null)
const canEvaluate = computed(
  () => Boolean(uploadedFile.resume_content) && Boolean(selectedJdId.value),
)

function resetUpload() {
  uploadedFile.original_filename = ''
  uploadedFile.file_type = ''
  uploadedFile.resume_content = ''
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
    const [jdRes, scRes, evRes] = await Promise.all([listJDs(), listScoring(), listResumes()])
    jds.value = jdRes.data
    standards.value = scRes.data
    evaluations.value = evRes.data
    if (!selectedId.value && evaluations.value.length) selectedId.value = evaluations.value[0].id
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

async function handleFile(file) {
  if (!file) return
  const check = validateResumeFile(file.name, file.size)
  if (!check.ok) {
    ElMessage.error(check.error)
    return
  }
  uploading.value = true
  try {
    const { data } = await uploadResume(file)
    uploadedFile.original_filename = data.original_filename
    uploadedFile.file_type = data.file_type
    uploadedFile.resume_content = data.resume_content
    ElMessage.success('简历已解析，请选择岗位后智能评估')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

function onUploadChange(uploadFile) {
  handleFile(uploadFile.raw)
}

async function handleEvaluate() {
  if (!uploadedFile.resume_content) {
    ElMessage.warning('请先上传简历')
    return
  }
  if (!selectedJdId.value) {
    ElMessage.warning('请先选择要评估的岗位 JD')
    return
  }
  evaluating.value = true
  try {
    const { data } = await evaluateResume({
      resume_content: uploadedFile.resume_content,
      job_description_id: selectedJdId.value,
      scoring_criteria_id: selectedCriteriaId.value || null,
      original_filename: uploadedFile.original_filename || null,
      file_type: uploadedFile.file_type || null,
    })
    evaluations.value.unshift(data)
    selectedId.value = data.id
    resetUpload()
    ElMessage.success('评估完成，请人工复核评分')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '评估失败')
  } finally {
    evaluating.value = false
  }
}

async function handleStatusChange(record, status) {
  try {
    const { data } = await updateResumeStatus(record.id, status)
    Object.assign(record, data)
    ElMessage.success('候选人状态已更新')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态更新失败')
  }
}

function buildReport(exp) {
  const lines = []
  lines.push('候选人评估报告')
  lines.push('================')
  lines.push(`姓名：${exp.candidate_name || '未命名'}`)
  lines.push(`应聘岗位：${exp.candidate_position || '-'}`)
  lines.push(`综合得分：${exp.total_score ?? '-'}`)
  lines.push(`评估状态：${STATUS_META[exp.status]?.label || exp.status}`)
  lines.push('')
  lines.push('【维度得分】')
  for (const d of exp.dimensions || []) {
    lines.push(`- ${d.name}：${d.score} / ${d.max} 分`)
    lines.push(`  理由：${d.reason || '-'}`)
  }
  lines.push('')
  lines.push('【简历文本】')
  lines.push(exp.text || '')
  return lines.join('\n')
}

async function handleExport(record) {
  try {
    const { data } = await exportResume(record.id)
    const blob = new Blob([buildReport(data)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `候选报告-${data.candidate_name || record.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('报告已导出')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导出失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="resume-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">简历筛选</h2>
        <p class="page-sub">上传简历，绑定岗位 JD 触发 AI 智能评估；AI 出初稿，人做决定</p>
      </div>
    </div>

    <!-- 上传与评估配置 -->
    <el-card class="bind-bar" shadow="never">
      <div class="bind-row">
        <el-upload
          class="upload-zone"
          drag
          action="#"
          :auto-upload="false"
          :show-file-list="false"
          :accept="acceptStr"
          :disabled="uploading"
          :on-change="onUploadChange"
        >
          <div class="upload-inner">
            <span class="upload-icon" :class="{ loading: uploading }">
              {{ uploading ? '…' : '⬆' }}
            </span>
            <div class="upload-text">
              <div class="upload-title">
                {{
                  uploading
                    ? '解析中…'
                    : uploadedFile.original_filename
                      ? `已选择：${uploadedFile.original_filename}`
                      : '点击或拖拽简历上传'
                }}
              </div>
              <div class="upload-hint">支持 PDF / DOC / DOCX，≤10MB</div>
            </div>
          </div>
        </el-upload>

        <div class="bind-info">
          <span class="bind-label">岗位 JD：</span>
          <el-select
            v-model="selectedJdId"
            placeholder="选择要评估的 JD（必选）"
            filterable
            style="width: 260px"
          >
            <el-option v-for="jd in jds" :key="jd.id" :label="jd.title" :value="jd.id" />
          </el-select>

          <span class="bind-label">评分标准：</span>
          <el-select
            v-model="selectedCriteriaId"
            placeholder="可选"
            clearable
            filterable
            style="width: 220px"
          >
            <el-option v-for="sc in standards" :key="sc.id" :label="sc.title" :value="sc.id" />
          </el-select>

          <el-button type="primary" :loading="evaluating" :disabled="!canEvaluate" @click="handleEvaluate">
            智能评估
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 候选人列表 -->
    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="list-head">
          <div class="list-title">
            <span>候选人评估</span>
            <el-tag size="small" type="info" effect="plain">{{ evaluations.length }} 份</el-tag>
          </div>
          <el-button
            size="small"
            :disabled="!selected"
            @click="handleExport(selected)"
          >
            导出报告
          </el-button>
        </div>
      </template>

      <el-empty
        v-if="!evaluations.length"
        description="暂无评估记录，请先上传简历并完成智能评估"
        :image-size="90"
      />

      <el-table
        v-else
        :data="evaluations"
        highlight-current-row
        class="candidate-table"
        @current-change="(row) => (selectedId = row?.id ?? null)"
      >
        <el-table-column label="候选人" min-width="160">
          <template #default="{ row }">
            <div class="candidate-cell">
              <span class="candidate-avatar">{{ avatarChar(row.candidate_name) }}</span>
              <span class="candidate-name">{{ row.candidate_name || '未命名' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="应聘岗位" min-width="160">
          <template #default="{ row }">{{ row.candidate_position || '-' }}</template>
        </el-table-column>
        <el-table-column label="工作年限" width="100">
          <template #default="{ row }">{{ row.work_years != null ? `${row.work_years}年` : '-' }}</template>
        </el-table-column>
        <el-table-column label="学历" width="100">
          <template #default="{ row }">{{ row.education_level || '-' }}</template>
        </el-table-column>
        <el-table-column label="毕业院校" min-width="160">
          <template #default="{ row }">{{ row.school || '-' }}</template>
        </el-table-column>
        <el-table-column label="AI 综合得分" width="130" align="center">
          <template #default="{ row }">
            <span class="row-score" :style="{ color: scoreColor(row.total_score) }">
              {{ row.total_score ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="评估状态" width="140">
          <template #default="{ row }">
            <el-select
              :model-value="row.status"
              size="small"
              @change="(v) => handleStatusChange(row, v)"
            >
              <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 评分卡 -->
    <el-card v-if="selected" class="scorecard" shadow="never">
      <div class="scorecard-head">
        <div class="scorecard-identity">
          <span class="scorecard-avatar">{{ avatarChar(selected.candidate_name) }}</span>
          <div>
            <div class="scorecard-name">
              {{ selected.candidate_name || '未命名' }}
              <span v-if="selected.candidate_position"> · {{ selected.candidate_position }}</span>
            </div>
            <div class="scorecard-meta">
              评估时间：{{ new Date(selected.created_at).toLocaleString() }}
            </div>
          </div>
        </div>
        <div class="scorecard-total">
          <span class="total-num" :style="{ color: scoreColor(selected.total_score) }">
            {{ selected.total_score ?? '-' }}
          </span>
          <span class="total-unit">分 综合评级</span>
        </div>
      </div>

      <div class="dimension-grid">
        <div v-for="(d, index) in selected.evaluation_metrics || []" :key="index" class="dim-card">
          <div class="dim-head">
            <span class="dim-name">{{ d.name }}</span>
            <span class="dim-score">{{ d.score }} <span class="dim-max">/ {{ d.max }} 分</span></span>
          </div>
          <div class="dim-bar">
            <div class="dim-bar-fill" :style="{ width: `${dimensionPct(d.score, d.max)}%` }" />
          </div>
          <div class="dim-reason"><span class="dim-reason-label">研判依据：</span>{{ d.reason || '-' }}</div>
        </div>
      </div>

      <div class="scorecard-foot">
        <span class="scorecard-tip">AI 出初稿，人做决定。请人工复核维度分后更新候选人状态。</span>
        <div class="scorecard-actions">
          <el-select :model-value="selected.status" size="small" @change="(v) => handleStatusChange(selected, v)">
            <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-button size="small" @click="handleExport(selected)">导出报告</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.resume-page {
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

.bind-bar {
  margin-bottom: 16px;
}

.bind-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.upload-zone {
  flex: 1;
  min-width: 300px;
}

.upload-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.upload-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #e6f0fc;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.upload-icon.loading {
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.4;
  }
}

.upload-text {
  text-align: left;
}

.upload-title {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

.bind-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.bind-label {
  color: #606266;
  font-weight: 500;
  font-size: 13px;
}

.list-card {
  margin-bottom: 16px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.list-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #303133;
}

.candidate-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.candidate-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e6f0fc;
  color: #409eff;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.candidate-name {
  font-weight: 500;
  color: #303133;
}

.row-score {
  font-size: 16px;
  font-weight: 700;
}

.scorecard {
  border-left: 3px solid #7b61ff;
}

.scorecard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f0f0;
}

.scorecard-identity {
  display: flex;
  align-items: center;
  gap: 12px;
}

.scorecard-avatar {
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
}

.scorecard-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.scorecard-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.scorecard-total {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.total-num {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.total-unit {
  font-size: 12px;
  color: #909399;
}

.dimension-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
  padding: 16px 0;
}

.dim-card {
  background: #f8f9fb;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
}

.dim-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.dim-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.dim-score {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
}

.dim-max {
  font-size: 11px;
  font-weight: 400;
  color: #909399;
}

.dim-bar {
  height: 6px;
  background: #eef1f6;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 8px;
}

.dim-bar-fill {
  height: 100%;
  background: #409eff;
  border-radius: 999px;
}

.dim-reason {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}

.dim-reason-label {
  font-weight: 500;
  color: #303133;
}

.scorecard-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.scorecard-tip {
  font-size: 12px;
  color: #909399;
}

.scorecard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
