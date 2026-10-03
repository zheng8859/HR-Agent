<script setup>
import { reactive, ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  parseRequirement,
  listJDs,
  createJD,
  updateJD,
  changeJDStatus,
  deleteJD,
  streamJD,
} from '@/api/jobDescription'

const STATUS_META = {
  draft: { label: '草稿', type: 'info' },
  published: { label: '启用', type: 'success' },
  archived: { label: '已归档', type: 'info' },
}

const emptyDraft = () => ({
  title: '',
  department: '',
  location: '',
  salary_range: '',
  experience_level: '',
  education: '',
  job_type: '',
  skillsText: '',
  content: '',
  requirements: [],
})

const description = ref('')
const draft = reactive(emptyDraft())
const generating = ref(false)
const parsing = ref(false)
const savedJds = ref([])
const editingId = ref(null)
let controller = null

const charCount = computed(() => (draft.content || '').length)
const hasDraft = computed(() => Boolean(draft.content || draft.title))

function skillsToArray() {
  return draft.skillsText
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function applyDraft(d) {
  draft.title = d.title || ''
  draft.department = d.department || ''
  draft.location = d.location || ''
  draft.salary_range = d.salary_range || ''
  draft.experience_level = d.experience_level || ''
  draft.education = d.education || ''
  draft.job_type = d.job_type || ''
  draft.skillsText = Array.isArray(d.skills) ? d.skills.join(', ') : d.skills || ''
  draft.content = d.content || ''
  draft.requirements = Array.isArray(d.requirements) ? d.requirements : []
}

function resetDraft() {
  Object.assign(draft, emptyDraft())
  description.value = ''
  editingId.value = null
}

async function loadList() {
  try {
    const { data } = await listJDs()
    savedJds.value = data
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

async function handleParse() {
  if (!description.value.trim()) {
    ElMessage.warning('请先输入一句话描述')
    return
  }
  parsing.value = true
  try {
    const { data } = await parseRequirement(description.value.trim())
    if (data.title) draft.title = data.title
    ElMessage.success('已解析并回填岗位名称')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解析失败')
  } finally {
    parsing.value = false
  }
}

function buildGeneratePayload() {
  const p = {}
  if (description.value.trim()) p.description = description.value.trim()
  if (draft.title.trim()) p.title = draft.title.trim()
  if (draft.department.trim()) p.department = draft.department.trim()
  if (draft.location.trim()) p.location = draft.location.trim()
  if (draft.salary_range.trim()) p.salary_range = draft.salary_range.trim()
  if (draft.experience_level.trim()) p.experience_level = draft.experience_level.trim()
  if (draft.education.trim()) p.education = draft.education.trim()
  if (draft.job_type.trim()) p.job_type = draft.job_type.trim()
  const skills = skillsToArray()
  if (skills.length) p.skills = skills
  return p
}

async function handleGenerate() {
  if (!draft.title.trim() && !description.value.trim()) {
    ElMessage.warning('请填写岗位名称或一句话描述')
    return
  }
  generating.value = true
  draft.content = ''
  controller = new AbortController()
  try {
    await streamJD(buildGeneratePayload(), {
      signal: controller.signal,
      onEvent(ev) {
        if (ev.event === 'thinking') return
        if (ev.event === 'delta') {
          try {
            draft.content += JSON.parse(ev.data)
          } catch {
            draft.content += ev.data
          }
          return
        }
        if (ev.event === 'final') {
          applyDraft(JSON.parse(ev.data))
        } else if (ev.event === 'error') {
          let msg = ev.data
          try {
            msg = JSON.parse(ev.data)
          } catch {
            /* 保留原文 */
          }
          ElMessage.error(typeof msg === 'string' ? msg : '生成失败，请重试')
        }
      },
    })
  } catch (e) {
    if (e?.name !== 'AbortError') ElMessage.error(e.message || '生成失败，请重试')
  } finally {
    generating.value = false
    controller = null
  }
}

async function handleSave() {
  if (!draft.title.trim() || !draft.content.trim()) {
    ElMessage.warning('保存需要岗位名称与正文')
    return
  }
  const payload = {
    title: draft.title,
    content: draft.content,
    department: draft.department || null,
    location: draft.location || null,
    salary_range: draft.salary_range || null,
    experience_level: draft.experience_level || null,
    education: draft.education || null,
    job_type: draft.job_type || null,
    skills: skillsToArray(),
    requirements: draft.requirements,
  }
  try {
    if (editingId.value) {
      await updateJD(editingId.value, payload)
      ElMessage.success('JD 已更新')
    } else {
      await createJD(payload)
      ElMessage.success('JD 已保存为草稿')
    }
    resetDraft()
    await loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

function handleEdit(jd) {
  editingId.value = jd.id
  applyDraft(jd)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function handleStatus(jd, status) {
  try {
    await changeJDStatus(jd.id, status)
    ElMessage.success('状态已更新')
    await loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(jd) {
  try {
    await ElMessageBox.confirm('确认删除此 JD？该操作无法撤销。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    await deleteJD(jd.id)
    ElMessage.success('已删除')
    if (editingId.value === jd.id) resetDraft()
    await loadList()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(loadList)
onBeforeUnmount(() => {
  if (controller) controller.abort()
})
</script>

<template>
  <div class="jd-page">
    <el-row :gutter="20">
      <!-- 左列：输入与管理 -->
      <el-col :xs="24" :lg="10">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="bar" />
              <span>岗位需求</span>
              <el-tag size="small" type="primary" effect="plain">智能提炼与自动补全</el-tag>
            </div>
          </template>

          <div class="field-label">一句话描述</div>
          <el-input
            v-model="description"
            type="textarea"
            :rows="3"
            placeholder="例如：急招一名有 5 年经验的高级前端工程师，负责中台系统与微前端架构"
          />
          <el-button
            class="mt-8"
            size="small"
            :loading="parsing"
            @click="handleParse"
          >
            解析填充字段
          </el-button>

          <el-divider>或手动填写下列字段</el-divider>

          <el-form label-position="top" size="default">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="岗位名称" required>
                  <el-input v-model="draft.title" placeholder="岗位名称" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="部门">
                  <el-input v-model="draft.department" placeholder="部门" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="工作地点">
                  <el-input v-model="draft.location" placeholder="工作地点" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="薪资范围">
                  <el-input v-model="draft.salary_range" placeholder="薪资范围" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="经验要求">
                  <el-input v-model="draft.experience_level" placeholder="经验要求" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="学历要求">
                  <el-input v-model="draft.education" placeholder="学历要求" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="岗位类型">
                  <el-input v-model="draft.job_type" placeholder="岗位类型" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="技能标签">
                  <el-input v-model="draft.skillsText" placeholder="逗号分隔" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <el-button type="primary" class="w-full" :loading="generating" @click="handleGenerate">
            {{ generating ? '正在智能生成...' : '生成 JD' }}
          </el-button>
        </el-card>

        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="bar" />
              <span>已保存 JD（{{ savedJds.length }}）</span>
            </div>
          </template>
          <el-empty v-if="!savedJds.length" description="暂无已保存 JD" :image-size="60" />
          <div v-for="jd in savedJds" :key="jd.id" class="jd-item">
            <div class="jd-item-main">
              <span class="jd-title">{{ jd.title }}</span>
              <el-tag :type="STATUS_META[jd.status]?.type || 'info'" size="small">
                {{ STATUS_META[jd.status]?.label || jd.status }}
              </el-tag>
            </div>
            <div class="jd-actions">
              <el-button link type="primary" size="small" @click="handleEdit(jd)">编辑</el-button>
              <el-button
                v-if="jd.status !== 'published'"
                link
                type="success"
                size="small"
                @click="handleStatus(jd, 'published')"
              >
                启用
              </el-button>
              <el-button
                v-if="jd.status === 'published'"
                link
                type="info"
                size="small"
                @click="handleStatus(jd, 'archived')"
              >
                归档
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(jd)">删除</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右列：AI 初稿预览 -->
      <el-col :xs="24" :lg="14">
        <el-card class="section-card preview-card" shadow="never">
          <template #header>
            <div class="preview-head">
              <div class="preview-title">
                <el-tag type="info" effect="plain" size="small">
                  AI 生成 · {{ generating ? '生成中' : '待确认' }}
                </el-tag>
                <span class="jd-title-text">JD 初稿预览{{ draft.title ? ' - ' + draft.title : '' }}</span>
              </div>
              <span class="char-count">字数：{{ charCount }}</span>
            </div>
          </template>

          <div v-if="generating" class="generating-tip">
            <span class="spinner" />
            正在生成 JD 初稿，请稍候...
          </div>

          <el-input
            v-model="draft.content"
            type="textarea"
            :rows="18"
            placeholder="生成结果将展示在此，可直接编辑"
            resize="vertical"
          />

          <div v-if="hasDraft" class="preview-actions">
            <el-button type="primary" @click="handleSave">
              {{ editingId ? '保存修改' : '确认保存' }}
            </el-button>
            <el-button @click="resetDraft">清空</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.jd-page {
  min-height: 100%;
}

.section-card {
  margin-bottom: 16px;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.bar {
  width: 6px;
  height: 16px;
  background: #409eff;
  border-radius: 3px;
  display: inline-block;
}

.field-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
}

.mt-8 {
  margin-top: 8px;
}

.w-full {
  width: 100%;
  margin-top: 12px;
}

.jd-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 4px;
  border-bottom: 1px solid #f0f0f0;
}

.jd-item:last-child {
  border-bottom: none;
}

.jd-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.jd-title {
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jd-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.preview-card {
  border-left: 3px solid #7b61ff;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.jd-title-text {
  font-weight: 600;
  color: #303133;
}

.char-count {
  font-size: 12px;
  color: #909399;
}

.generating-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #409eff;
  font-size: 13px;
  margin-bottom: 10px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #d3e4ff;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
