<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKBs, createKB, updateKB, deleteKB } from '@/api/knowledgeBase'
import {
  uploadDocument,
  listDocuments,
  getDocumentChunks,
  reprocessDocument,
  deleteDocument,
} from '@/api/document'
import {
  DOCUMENT_STATUS_META,
  formatFileSize,
  formatUploadTime,
  fileExtension,
} from '@/utils/document'

const kbs = ref([])
const selectedKbId = ref(null)
const documents = ref([])
const loading = ref(false)
const uploading = ref(false)

// 新建/编辑知识库弹窗
const kbDialogVisible = ref(false)
const kbSaving = ref(false)
const kbForm = ref({ name: '', description: '', is_public: false, is_searchable: true })

// 切片弹窗
const chunksVisible = ref(false)
const chunks = ref([])
const chunksTitle = ref('')

const fileInput = ref(null)

const selectedKb = computed(() => kbs.value.find((k) => k.id === selectedKbId.value) || null)
const totalChunks = computed(() =>
  documents.value.reduce((sum, d) => sum + (d.chunk_count || 0), 0),
)
const hasPending = computed(() =>
  documents.value.some((d) => d.status === 'uploaded' || d.status === 'processing'),
)

let pollTimer = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function schedulePoll() {
  stopPolling()
  if (hasPending.value) {
    pollTimer = setInterval(async () => {
      await loadDocuments()
      if (!hasPending.value) stopPolling()
    }, 3000)
  }
}

async function loadKbs() {
  try {
    const { data } = await listKBs()
    kbs.value = data
    if (!selectedKbId.value && data.length) selectedKbId.value = data[0].id
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

async function loadDocuments() {
  if (!selectedKbId.value) {
    documents.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await listDocuments(selectedKbId.value)
    documents.value = data
    schedulePoll()
  } catch {
    /* 失败不阻断页面 */
  } finally {
    loading.value = false
  }
}

function openKbDialog() {
  kbForm.value = { name: '', description: '', is_public: false, is_searchable: true }
  kbDialogVisible.value = true
}

async function submitKb() {
  if (!kbForm.value.name || !kbForm.value.name.trim()) {
    ElMessage.warning('知识库名称必填')
    return
  }
  kbSaving.value = true
  try {
    const { data } = await createKB({
      name: kbForm.value.name.trim(),
      description: kbForm.value.description || null,
      is_public: kbForm.value.is_public,
      is_searchable: kbForm.value.is_searchable,
    })
    kbDialogVisible.value = false
    await loadKbs()
    selectedKbId.value = data.id
    ElMessage.success('知识库已创建')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    kbSaving.value = false
  }
}

async function handleToggle(key, value) {
  if (!selectedKb.value) return
  const prev = selectedKb.value[key]
  // 乐观更新：开关立即反映（受控 el-switch 依赖数据变化）
  selectedKb.value[key] = value
  try {
    await updateKB(selectedKb.value.id, { [key]: value })
    ElMessage.success('已更新')
  } catch (e) {
    selectedKb.value[key] = prev
    ElMessage.error(e.response?.data?.detail || '更新失败')
  }
}

async function handleDeleteKb() {
  if (!selectedKb.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除知识库「${selectedKb.value.name}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteKB(selectedKb.value.id)
    selectedKbId.value = null
    await loadKbs()
    ElMessage.success('知识库已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!selectedKb.value) {
    ElMessage.warning('请先选择或新建知识库')
    return
  }
  uploading.value = true
  try {
    await uploadDocument(file, selectedKb.value.id)
    await loadDocuments()
    ElMessage.success('文档已上传')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleReprocess(row) {
  try {
    await reprocessDocument(row.id)
    await loadDocuments()
    ElMessage.success('已提交重新处理')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重新处理失败')
  }
}

async function handleViewChunks(row) {
  try {
    const { data } = await getDocumentChunks(row.id)
    chunks.value = data.chunks || []
    chunksTitle.value = row.original_filename || row.filename || '文档'
    chunksVisible.value = true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '切片加载失败')
  }
}

async function handleDeleteDocument(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除文档「${row.original_filename || row.filename}」吗？删除后不再可检索。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteDocument(row.id)
    await loadDocuments()
    ElMessage.success('文档已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

watch(selectedKbId, () => {
  loadDocuments()
})

onMounted(async () => {
  await loadKbs()
  await loadDocuments()
})

onUnmounted(stopPolling)
</script>

<template>
  <div class="kb-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h2 class="page-title">知识库管理</h2>
        <p class="page-sub">管理企业制度、政策规范与流程文档，支持自动化切片与向量化入库</p>
      </div>
      <div class="page-actions">
        <el-button :disabled="!selectedKb" :loading="uploading" @click="triggerUpload">
          上传文档
        </el-button>
        <el-button type="primary" @click="openKbDialog">新建知识库</el-button>
      </div>
      <input ref="fileInput" type="file" hidden accept=".pdf,.doc,.docx,.txt" @change="handleFileChange" />
    </div>

    <!-- 空态：无知识库 -->
    <el-card v-if="!kbs.length" class="empty-card" shadow="never">
      <el-empty description="暂无知识库，先创建一个知识库来收纳企业文档" :image-size="110">
        <el-button type="primary" @click="openKbDialog">新建知识库</el-button>
      </el-empty>
    </el-card>

    <template v-else>
      <!-- 知识库选择卡 -->
      <el-card class="kb-card" shadow="never">
        <div class="kb-select-row">
          <span class="bind-label">当前知识库：</span>
          <el-select v-model="selectedKbId" filterable style="width: 320px" placeholder="选择知识库">
            <el-option v-for="k in kbs" :key="k.id" :label="k.name" :value="k.id" />
          </el-select>
          <template v-if="selectedKb">
            <span class="kb-count">已处理文档 {{ selectedKb.document_count }} 份 · 切片 {{ totalChunks }} 个</span>
            <span class="action-spacer" />
            <el-button link type="danger" @click="handleDeleteKb">删除知识库</el-button>
          </template>
        </div>

        <div v-if="selectedKb" class="kb-meta">
          <p class="kb-desc">{{ selectedKb.description || '暂无描述' }}</p>
          <div class="kb-switches">
            <div class="switch-item">
              <span class="switch-label">公开状态</span>
              <el-switch
                :model-value="selectedKb.is_public"
                @update:model-value="(v) => handleToggle('is_public', v)"
              />
            </div>
            <div class="switch-item">
              <span class="switch-label">可搜索状态</span>
              <el-switch
                :model-value="selectedKb.is_searchable"
                @update:model-value="(v) => handleToggle('is_searchable', v)"
              />
            </div>
          </div>
        </div>
      </el-card>

      <!-- 文档表格卡 -->
      <el-card class="doc-card" shadow="never">
        <div class="doc-head">
          <h3 class="doc-title">文档列表</h3>
          <span class="doc-count">共 {{ documents.length }} 个文档</span>
          <span v-if="hasPending" class="polling-hint">处理中，自动刷新…</span>
        </div>

        <!-- 空态：无文档 -->
        <el-empty
          v-if="!documents.length && !loading"
          description="该知识库暂无文档，点击「上传文档」添加"
          :image-size="90"
        >
          <el-button type="primary" :disabled="!selectedKb" @click="triggerUpload">上传文档</el-button>
        </el-empty>

        <el-table v-else v-loading="loading" :data="documents" style="width: 100%">
          <el-table-column label="文档名称" min-width="220">
            <template #default="{ row }">
              <div class="doc-name">
                <span class="doc-ext">{{ fileExtension(row.original_filename) }}</span>
                <span class="doc-name-text">{{ row.original_filename || row.filename }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="110">
            <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="处理状态" width="120">
            <template #default="{ row }">
              <el-tooltip
                v-if="row.status === 'failed' && row.error_message"
                :content="row.error_message"
                placement="top"
              >
                <el-tag :type="DOCUMENT_STATUS_META[row.status]?.type || 'info'" effect="plain" size="small">
                  {{ DOCUMENT_STATUS_META[row.status]?.label || row.status }}
                </el-tag>
              </el-tooltip>
              <el-tag v-else :type="DOCUMENT_STATUS_META[row.status]?.type || 'info'" effect="plain" size="small">
                {{ DOCUMENT_STATUS_META[row.status]?.label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="切片数量" width="100">
            <template #default="{ row }">{{ row.chunk_count }}</template>
          </el-table-column>
          <el-table-column label="上传时间" width="120">
            <template #default="{ row }">{{ formatUploadTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="220" align="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'processed'"
                link
                type="primary"
                @click="handleViewChunks(row)"
              >
                查看切片
              </el-button>
              <el-button
                v-if="row.status === 'failed'"
                link
                type="primary"
                @click="handleReprocess(row)"
              >
                重新处理
              </el-button>
              <el-button link type="danger" @click="handleDeleteDocument(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 新建知识库弹窗 -->
    <el-dialog v-model="kbDialogVisible" title="新建知识库" width="480px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="kbForm.name" placeholder="如：员工手册" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="kbForm.description" type="textarea" :rows="3" placeholder="知识库用途说明（可选）" />
        </el-form-item>
        <el-form-item label="公开状态">
          <el-switch v-model="kbForm.is_public" />
        </el-form-item>
        <el-form-item label="可搜索状态">
          <el-switch v-model="kbForm.is_searchable" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbSaving" :disabled="kbSaving" @click="submitKb">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看切片弹窗 -->
    <el-dialog v-model="chunksVisible" :title="`切片预览 — ${chunksTitle}`" width="640px">
      <div v-if="chunks.length" class="chunks-list">
        <div v-for="(c, i) in chunks" :key="i" class="chunk-item">
          <span class="chunk-index">#{{ i + 1 }}</span>
          <span class="chunk-text">{{ c }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无切片" :image-size="80" />
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-page {
  min-height: 100%;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

.page-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.empty-card,
.kb-card {
  margin-bottom: 16px;
}

.kb-select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.bind-label {
  color: #606266;
  font-weight: 500;
  font-size: 13px;
}

.kb-count {
  color: #909399;
  font-size: 12px;
}

.action-spacer {
  flex: 1;
}

.kb-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}

.kb-desc {
  margin: 0;
  color: #606266;
  font-size: 13px;
  flex: 1;
}

.kb-switches {
  display: flex;
  gap: 24px;
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-label {
  color: #606266;
  font-size: 13px;
}

.doc-card {
  margin-bottom: 16px;
}

.doc-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.doc-title {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.doc-count {
  color: #909399;
  font-size: 12px;
}

.polling-hint {
  color: #e6a23c;
  font-size: 12px;
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-ext {
  padding: 1px 6px;
  border-radius: 3px;
  background: #f0f2f5;
  color: #909399;
  font-size: 11px;
  font-family: monospace;
  flex-shrink: 0;
}

.doc-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.chunk-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafbfc;
}

.chunk-index {
  color: #409eff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.chunk-text {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}
</style>
