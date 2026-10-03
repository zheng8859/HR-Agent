import http from './http'
import { createSSEDecoder } from '@/utils/sse'
import { tokenStorage, buildAuthHeader } from '@/utils/token'

// 意图识别（非流式）
export function intent(payload) {
  return http.post('/intent', payload)
}

// 会话 CRUD（所有权隔离由后端保证）
export function listConversations() {
  return http.get('/conversations')
}

export function createConversation(title) {
  return http.post('/conversations', { title })
}

export function getConversation(id) {
  return http.get(`/conversations/${id}`)
}

export function deleteConversation(id) {
  return http.delete(`/conversations/${id}`)
}

export function sendFeedback(messageId, score) {
  return http.post('/chat/feedback', { message_id: messageId, score })
}

// SSE 流式（POST 需 fetch 手动解析 text/event-stream，EventSource 仅支持 GET）。
async function streamSSE(url, payload, { onEvent, signal }) {
  const token = tokenStorage.get()
  const resp = await fetch(`/api/v1${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeader(token) },
    body: JSON.stringify(payload),
    signal,
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`请求失败（${resp.status}）${text ? `：${text}` : ''}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  const sse = createSSEDecoder()
  const emit = (ev) => {
    let data = null
    try {
      data = ev.data ? JSON.parse(ev.data) : null
    } catch {
      data = ev.data
    }
    onEvent({ event: ev.event, data })
  }
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    for (const ev of sse.push(decoder.decode(value, { stream: true }))) emit(ev)
  }
  for (const ev of sse.push(decoder.decode())) emit(ev)
}

// 对话流：thinking → plan → delta → final
export function streamChat(payload, opts) {
  return streamSSE('/chat', payload, opts)
}

// 任务流：progress → delta → artifact → final
export function streamAgent(payload, opts) {
  return streamSSE('/agent', payload, opts)
}
