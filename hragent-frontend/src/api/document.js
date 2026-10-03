import http from './http'

// 上传文档（multipart：file + knowledge_base_id，写操作）
export function uploadDocument(file, knowledgeBaseId) {
  const form = new FormData()
  form.append('file', file)
  if (knowledgeBaseId) form.append('knowledge_base_id', knowledgeBaseId)
  return http.post('/documents/upload', form)
}

// 文档列表（读，按 knowledge_base_id 过滤 + user_id 隔离）
export function listDocuments(knowledgeBaseId) {
  return http.get('/documents', {
    params: knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : {},
  })
}

// 查看切片（读）
export function getDocumentChunks(id) {
  return http.get(`/documents/${id}/chunks`)
}

// 重新处理（写操作）
export function reprocessDocument(id) {
  return http.post(`/documents/${id}/reprocess`)
}

// 删除文档（写操作）
export function deleteDocument(id) {
  return http.delete(`/documents/${id}`)
}
