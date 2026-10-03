<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/auth'
import { streamChat, listConversations, getConversation } from '@/api/agent'
import { createJD } from '@/api/jobDescription'

const router = useRouter()
const auth = useAuthStore()
const isHr = computed(() => auth.isHrAdmin)

const conversations = ref([])
const currentId = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const scrollRef = ref(null)
let abortCtrl = null

// 后端 route（如 recruitment.jd）→ 前端路由
const ROUTE_MAP = {
  'recruitment.jd': '/jd-generator',
  'recruitment.scoring': '/scoring-criteria',
  'recruitment.resume': '/resume-screening',
  'recruitment.interview': '/interview',
}

// 建议按钮：部分映射跳转路由，其余回填输入（agent-ui §建议按钮）
const SUGGESTION_ROUTES = {
  保存并发布JD: '/jd-generator',
  生成评分标准: '/scoring-criteria',
  查看JD: '/jd-generator',
  保存修改: '/jd-generator',
  查看评分标准: '/scoring-criteria',
  上传简历: '/resume-screening',
  查看评估结果: '/resume-screening',
  查看面试方案: '/interview',
  导出方案: '/interview',
}

// 角色快捷芯片（agent-ui §角色快捷芯片）：HR 展示招聘芯片，employee 仅通用
const chips = computed(() =>
  isHr.value
    ? ['帮我写一份 JD', '筛选这批简历', '生成面试方案', '查一下年假规定']
    : ['查一下年假规定', '你好，你能做什么？'],
)

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function jump(route) {
  const path = typeof route === 'string' ? ROUTE_MAP[route] || route : null
  if (path) router.push(path)
}

function stepClass(status) {
  return { completed: 'done', running: 'running', failed: 'failed' }[status] || 'pending'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadConversations() {
  try {
    const { data } = await listConversations()
    conversations.value = data
  } catch {
    /* 401 由拦截器处理 */
  }
}

function newConversation() {
  currentId.value = null
  messages.value = []
  input.value = ''
}

async function selectConversation(conv) {
  currentId.value = conv.id
  try {
    const { data } = await getConversation(conv.id)
    messages.value = (data.messages || []).map((m) => {
      const agent = m.context && m.context.agent_response
      return {
        id: m.id,
        role: m.role,
        content: m.content || '',
        steps: (agent && agent.steps) || [],
        artifacts: (agent && agent.artifacts) || [],
        suggestions: (agent && agent.suggestions) || [],
        requiresConfirmation: !!(agent && agent.requires_confirmation),
      }
    })
    scrollToBottom()
  } catch {
    ElMessage.error('会话加载失败')
  }
}

async function sendText(text) {
  const content = (text != null ? text : input.value).trim()
  if (!content || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', content })
  const assistant = { role: 'assistant', content: '', steps: [], artifacts: [], suggestions: [], streaming: true }
  messages.value.push(assistant)
  scrollToBottom()

  sending.value = true
  abortCtrl = new AbortController()
  const payload = { message: content }
  if (currentId.value) payload.conversation_id = currentId.value

  try {
    await streamChat(payload, {
      signal: abortCtrl.signal,
      onEvent: ({ event, data }) => {
        if (event === 'plan' && data) {
          assistant.steps = data.steps || []
        } else if (event === 'delta' && data) {
          assistant.content += data.content || ''
          scrollToBottom()
        } else if (event === 'final' && data) {
          assistant.content = data.message || assistant.content
          assistant.steps = data.steps || []
          assistant.artifacts = data.artifacts || []
          assistant.suggestions = data.suggestions || []
          assistant.requiresConfirmation = !!data.requires_confirmation
          assistant.streaming = false
          if (data.conversation_id) currentId.value = data.conversation_id
        }
      },
    })
  } catch (e) {
    if (e.name !== 'AbortError') {
      assistant.content = assistant.content || `请求失败：${e.message}`
      assistant.streaming = false
    }
  } finally {
    sending.value = false
    abortCtrl = null
    assistant.streaming = false
    scrollToBottom()
    loadConversations()
  }
}

function handleChip(text) {
  sendText(text)
}

function handleSuggestion(s) {
  const path = SUGGESTION_ROUTES[s]
  if (path) router.push(path)
  else input.value = s
}

function confirmSave(artifact) {
  createJD(artifact.draft || {})
    .then(() => {
      ElMessage.success('JD 已保存到「JD 生成」页')
      router.push('/jd-generator')
    })
    .catch((e) => ElMessage.error(e.response?.data?.detail || '保存失败'))
}

function confirmDelete(candidate) {
  sendText(`确认删除 ${candidate.title}`)
}

onMounted(loadConversations)
onBeforeUnmount(() => {
  if (abortCtrl) abortCtrl.abort()
})
</script>

<template>
  <div class="agent-page">
    <!-- 会话历史 -->
    <aside class="conv-panel">
      <div class="conv-head">
        <el-button type="primary" class="new-btn" @click="newConversation">新建对话</el-button>
      </div>
      <div class="conv-list">
        <div
          v-for="c in conversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === currentId }"
          @click="selectConversation(c)"
        >
          <div class="conv-title">{{ c.title || '未命名会话' }}</div>
          <div class="conv-time">{{ formatTime(c.updated_at) }}</div>
        </div>
        <div v-if="!conversations.length" class="conv-empty">暂无历史会话</div>
      </div>
    </aside>

    <!-- 主对话区 -->
    <section class="chat-panel">
      <div ref="scrollRef" class="chat-scroll">
        <div v-if="!messages.length" class="chat-empty">
          <div class="empty-title">你好，我是 HR Agent</div>
          <div class="empty-sub">我可以帮你生成 JD、评估简历、生成面试方案，或回答企业知识</div>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <!-- 用户气泡 -->
          <div v-if="m.role === 'user'" class="bubble user">{{ m.content }}</div>

          <!-- AI 回复 -->
          <template v-else>
            <div class="bubble ai">
              <span v-if="m.streaming && !m.content" class="thinking">正在思考…</span>
              <span v-else class="ai-text">{{ m.content || '（空回复）' }}</span>
            </div>

            <!-- 执行步骤时间轴（进度折叠） -->
            <div v-if="m.steps && m.steps.length" class="steps-card">
              <div class="steps-title">执行步骤</div>
              <div v-for="s in m.steps" :key="s.id" class="step">
                <span class="dot" :class="stepClass(s.status)" />
                <span class="step-title">{{ s.title }}</span>
                <span v-if="s.detail" class="step-detail">{{ s.detail }}</span>
              </div>
            </div>

            <!-- 内嵌工具面板（按产物类型切换） -->
            <div v-for="(a, ai) in m.artifacts" :key="ai" class="artifact-card">
              <template v-if="a.type === 'jd_confirm'">
                <div class="artifact-badge">AI 生成 · 待确认</div>
                <div class="artifact-title">{{ (a.draft && a.draft.title) || 'JD 初稿' }}</div>
                <div class="artifact-meta">
                  <span v-if="a.draft && a.draft.location">地点：{{ a.draft.location }}</span>
                  <span v-if="a.draft && a.draft.salary_range">薪资：{{ a.draft.salary_range }}</span>
                  <span v-if="a.draft && a.draft.experience_level">经验：{{ a.draft.experience_level }}</span>
                  <span v-if="a.draft && a.draft.education">学历：{{ a.draft.education }}</span>
                </div>
                <div class="artifact-content">{{ a.draft && a.draft.content }}</div>
                <div class="artifact-actions">
                  <el-button type="primary" size="small" @click="confirmSave(a)">确认保存</el-button>
                  <el-button size="small" @click="jump(a.route)">跳转功能页</el-button>
                </div>
              </template>

              <template v-else-if="a.type === 'resume_upload_request' || a.type === 'resume_screening_results'">
                <div class="artifact-badge">简历评估</div>
                <div class="artifact-content">
                  {{ a.message || '请上传简历（PDF/DOC/DOCX）并选择匹配的 JD 完成评估。' }}
                </div>
                <div class="artifact-actions">
                  <el-button type="primary" size="small" @click="jump(a.route)">跳转简历筛选页</el-button>
                </div>
              </template>

              <template v-else-if="a.type === 'interview_plan_execute'">
                <div class="artifact-badge">面试方案</div>
                <div class="artifact-title">{{ a.candidate_name || '候选人' }}</div>
                <div class="artifact-content">{{ a.content }}</div>
                <div class="artifact-actions">
                  <el-button type="primary" size="small" @click="jump(a.route)">跳转智能面试页</el-button>
                </div>
              </template>

              <template v-else-if="a.type === 'delete_resource_candidates'">
                <div class="artifact-badge">删除确认</div>
                <div v-if="a.candidates && a.candidates.length" class="del-list">
                  <div v-for="c in a.candidates" :key="c.id" class="del-row">
                    <span class="del-title">{{ c.title }}</span>
                    <el-button type="danger" size="small" @click="confirmDelete(c)">确认删除</el-button>
                  </div>
                </div>
                <div v-else class="artifact-content">未找到可删除的资源。</div>
              </template>

              <template v-else-if="a.type === 'delete_resource_result'">
                <div class="artifact-badge">已删除</div>
                <div class="artifact-content">{{ a.deleted }}</div>
              </template>

              <template v-else>
                <div class="artifact-badge">任务</div>
                <div v-if="a.message" class="artifact-content">{{ a.message }}</div>
                <div v-if="a.route" class="artifact-actions">
                  <el-button size="small" @click="jump(a.route)">跳转功能页</el-button>
                </div>
              </template>
            </div>

            <!-- 建议按钮 -->
            <div v-if="m.suggestions && m.suggestions.length" class="suggestions">
              <el-button
                v-for="s in m.suggestions"
                :key="s"
                size="small"
                plain
                @click="handleSuggestion(s)"
              >{{ s }}</el-button>
            </div>
          </template>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-panel">
        <div class="chips">
          <el-button
            v-for="c in chips"
            :key="c"
            size="small"
            class="chip"
            @click="handleChip(c)"
          >{{ c }}</el-button>
        </div>
        <div class="input-row">
          <el-input
            v-model="input"
            type="textarea"
            :rows="1"
            autosize
            placeholder="输入对话或指令，例如：生成产品经理的 JD…"
            @keydown.enter.exact.prevent="sendText()"
          />
          <el-button type="primary" :loading="sending" @click="sendText()">发送</el-button>
        </div>
        <div class="input-hint">内容由 HR Agent 生成，操作前请复核关键业务要求。</div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.agent-page {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
}

.conv-panel {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.conv-head {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.new-btn {
  width: 100%;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.conv-item {
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.conv-item:hover {
  background: #f5f7fa;
}

.conv-item.active {
  background: #ecf5ff;
}

.conv-title {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-item.active .conv-title {
  color: #409eff;
}

.conv-time {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.conv-empty {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-empty {
  text-align: center;
  margin-top: 80px;
  color: #909399;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.empty-sub {
  font-size: 13px;
  margin-top: 8px;
}

.msg {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
}

.msg.user {
  align-items: flex-end;
}

.msg.assistant {
  align-items: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.bubble.user {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  color: #303133;
}

.bubble.ai {
  background: #fff;
  border: 1px solid #ebeef5;
  color: #303133;
}

.thinking {
  color: #909399;
  font-size: 13px;
}

.steps-card {
  margin-top: 10px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 16px;
  width: 100%;
  max-width: 560px;
}

.steps-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #909399;
}

.dot.done {
  background: #67c23a;
}

.dot.running {
  background: #409eff;
}

.dot.failed {
  background: #f56c6c;
}

.step-title {
  font-size: 13px;
  color: #303133;
}

.step-detail {
  font-size: 12px;
  color: #909399;
}

.artifact-card {
  margin-top: 10px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-left: 3px solid #7b61ff;
  border-radius: 8px;
  padding: 14px 16px;
  width: 100%;
  max-width: 560px;
}

.artifact-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: #f3f0ff;
  color: #5b45c7;
  margin-bottom: 8px;
}

.artifact-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.artifact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.artifact-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
}

.artifact-actions {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f2f6fc;
}

.del-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.del-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.del-title {
  font-size: 13px;
  color: #303133;
}

.suggestions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.input-panel {
  background: #fff;
  border-top: 1px solid #e4e7ed;
  padding: 12px 20px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.input-row .el-textarea {
  flex: 1;
}

.input-hint {
  margin-top: 8px;
  text-align: center;
  font-size: 11px;
  color: #c0c4cc;
}
</style>
