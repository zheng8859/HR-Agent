import http from './http'

// 新建知识库（写操作）
export function createKB(payload) {
  return http.post('/knowledge-base', payload)
}

// 知识库列表（读）
export function listKBs() {
  return http.get('/knowledge-base')
}

// 编辑知识库（写操作）
export function updateKB(id, payload) {
  return http.put(`/knowledge-base/${id}`, payload)
}

// 删除知识库（写操作，含文档则 409）
export function deleteKB(id) {
  return http.delete(`/knowledge-base/${id}`)
}
