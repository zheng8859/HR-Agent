import http from './http'
import { createSSEDecoder } from '@/utils/sse'
import { tokenStorage, buildAuthHeader } from '@/utils/token'

export function generateJD(payload) {
  return http.post('/job-descriptions/generate', payload)
}

export function parseRequirement(text) {
  return http.post('/job-descriptions/parse', { text })
}

export function listJDs() {
  return http.get('/job-descriptions')
}

export function createJD(payload) {
  return http.post('/job-descriptions', payload)
}

export function updateJD(id, payload) {
  return http.put(`/job-descriptions/${id}`, payload)
}

export function changeJDStatus(id, status) {
  return http.patch(`/job-descriptions/${id}/status`, null, { params: { status } })
}

export function deleteJD(id) {
  return http.delete(`/job-descriptions/${id}`)
}

// SSE 流式生成：POST 需用 fetch 手动读取 text/event-stream（EventSource 仅支持 GET）。
export async function streamJD(payload, { onEvent, signal }) {
  const token = tokenStorage.get()
  const resp = await fetch('/api/v1/job-descriptions/generate-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeader(token) },
    body: JSON.stringify(payload),
    signal,
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`生成失败（${resp.status}）${text ? `：${text}` : ''}`)
  }
  const reader = resp.body.getReader()
  const textDecoder = new TextDecoder()
  const sse = createSSEDecoder()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    for (const ev of sse.push(textDecoder.decode(value, { stream: true }))) onEvent(ev)
  }
  for (const ev of sse.push(textDecoder.decode())) onEvent(ev)
}
