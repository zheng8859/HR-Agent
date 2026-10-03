<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listKBs } from '@/api/knowledgeBase'
import { askQuestion } from '@/api/knowledgeAssistant'
import { SUGGESTED_QUESTIONS, isRefusal, isLowConfidence, confidencePercent } from '@/utils/qa'

const kbs = ref([])
const selectedKbId = ref(null)
const messages = ref([]) // { role: 'user'|'assistant', text?, response? }
const question = ref('')
const asking = ref(false)
const scrollRef = ref(null)

const canRegenerate = computed(
  () => !asking.value && messages.value.some((m) => m.role === 'user'),
)

async function loadKbs() {
  try {
    const { data } = await listKBs()
    kbs.value = data
  } catch {
    /* 列表加载失败不阻断页面 */
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

async function runAsk(q) {
  asking.value = true
  try {
    const { data } = await askQuestion(q, selectedKbId.value || null)
    messages.value.push({ role: 'assistant', response: data })
    scrollToBottom()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提问失败，请稍后重试')
  } finally {
    asking.value = false
  }
}

function sendQuestion(text) {
  const q = (text ?? question.value).trim()
  if (!q) {
    ElMessage.warning('请输入问题内容')
    return
  }
  question.value = ''
  messages.value.push({ role: 'user', text: q })
  scrollToBottom()
  runAsk(q)
}

function handleSend() {
  sendQuestion()
}

function fillQuestion(q) {
  question.value = q
}

function regenerate() {
  const last = [...messages.value].reverse().find((m) => m.role === 'user')
  if (last) runAsk(last.text)
}

function clearChat() {
  messages.value = []
}

onMounted(loadKbs)
</script>

<template>
  <div class="qa-page">
    <div class="page-head">
      <div>
        <h2 class="page-title">知识问答</h2>
        <p class="page-sub">基于企业文档检索回答，附带溯源依据，不凭空捏造</p>
      </div>
      <div class="page-actions">
        <span class="bind-label">知识库域：</span>
        <el-select v-model="selectedKbId" clearable placeholder="全部知识库" style="width: 260px">
          <el-option v-for="k in kbs" :key="k.id" :label="k.name" :value="k.id" />
        </el-select>
      </div>
    </div>

    <el-card class="chat-card" shadow="never">
      <div ref="scrollRef" class="chat-scroll">
        <!-- 空态示例问题引导 -->
        <div v-if="!messages.length" class="guide">
          <div class="guide-head">
            <h3>还不知道从哪问起？</h3>
            <p>试试这些高频员工咨询问题，点击即可快速填入：</p>
          </div>
          <div class="guide-questions">
            <el-button v-for="q in SUGGESTED_QUESTIONS" :key="q" round @click="fillQuestion(q)">
              💡 {{ q }}
            </el-button>
          </div>
        </div>

        <!-- 消息流 -->
        <template v-else>
          <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
            <div v-if="m.role === 'user'" class="msg-user">
              <div class="bubble user-bubble">{{ m.text }}</div>
              <div class="avatar user-avatar">我</div>
            </div>

            <div v-else class="msg-assistant">
              <div class="avatar ai-avatar">AI</div>
              <div class="assistant-body">
                <!-- 资料不足拒答态 -->
                <div v-if="isRefusal(m.response)" class="bubble refusal-bubble">
                  <span class="refusal-mark">资料不足</span>
                  <span class="refusal-text">{{ m.response.answer }}</span>
                </div>

                <!-- 有依据 / 低置信度 -->
                <div v-else class="bubble answer-bubble">
                  <div class="answer-meta">
                    <span class="answer-label">企业政策解答小助手</span>
                    <el-tag
                      :type="isLowConfidence(m.response) ? 'warning' : 'success'"
                      size="small"
                      effect="plain"
                    >
                      置信度 {{ confidencePercent(m.response.confidence) }}
                    </el-tag>
                  </div>
                  <p class="answer-text">{{ m.response.answer }}</p>
                  <el-alert
                    v-if="isLowConfidence(m.response)"
                    title="置信度较低，答案仅供参考，请核对原文依据"
                    type="warning"
                    :closable="false"
                    show-icon
                  />
                  <el-collapse
                    v-if="m.response.document_chunks && m.response.document_chunks.length"
                    class="source-collapse"
                  >
                    <el-collapse-item :title="`来源依据（${m.response.document_chunks.length}）`" name="sources">
                      <div v-for="(c, ci) in m.response.document_chunks" :key="ci" class="source-item">
                        <div class="source-head">
                          <span class="source-name">{{ c.document_name }}</span>
                          <span class="source-sim">{{ confidencePercent(c.similarity) }}</span>
                        </div>
                        <p class="source-text">{{ c.chunk_text }}</p>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </el-card>

    <div class="input-bar">
      <div class="input-actions">
        <el-button link type="danger" :disabled="!messages.length" @click="clearChat">清空对话</el-button>
        <el-button link type="primary" :disabled="!canRegenerate" @click="regenerate">重新生成</el-button>
      </div>
      <div class="input-row">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          maxlength="2000"
          show-word-limit
          placeholder="请输入你的政策或制度疑问，例如：年假折算方法、调休审批时限..."
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button type="primary" class="send-btn" :loading="asking" :disabled="asking" @click="handleSend">
          发送问题
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.qa-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
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
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.bind-label {
  color: #606266;
  font-weight: 500;
  font-size: 13px;
}

.chat-card {
  flex: 1;
}

.chat-scroll {
  min-height: 360px;
  max-height: calc(100vh - 320px);
  overflow-y: auto;
  padding: 4px;
}

.guide {
  padding: 24px 8px;
}

.guide-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #303133;
}

.guide-head p {
  margin: 0 0 16px;
  color: #909399;
  font-size: 13px;
}

.guide-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.msg-row {
  margin-bottom: 18px;
}

.msg-user {
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
  gap: 10px;
}

.user-bubble {
  background: #d3e4ff;
  color: #191c1f;
  border-radius: 12px 12px 4px 12px;
  max-width: 70%;
}

.msg-assistant {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.user-avatar {
  background: #0060a9;
  border-radius: 50%;
}

.ai-avatar {
  background: #5b3cdd;
}

.assistant-body {
  flex: 1;
  min-width: 0;
}

.bubble {
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.7;
}

.answer-bubble {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.refusal-bubble {
  background: #f4f4f5;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  color: #606266;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.refusal-mark {
  font-weight: 600;
  color: #303133;
}

.refusal-text {
  color: #606266;
}

.answer-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f7fa;
}

.answer-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.answer-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
}

.source-collapse {
  margin-top: 12px;
  border: none;
}

.source-item {
  padding: 8px 0;
  border-bottom: 1px solid #f5f7fa;
}

.source-item:last-child {
  border-bottom: none;
}

.source-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.source-name {
  font-weight: 500;
  color: #303133;
  font-size: 13px;
}

.source-sim {
  color: #67c23a;
  font-size: 12px;
  font-weight: 600;
}

.source-text {
  margin: 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-all;
}

.input-bar {
  margin-top: 16px;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-bottom: 8px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.send-btn {
  height: 56px;
  flex-shrink: 0;
}
</style>
