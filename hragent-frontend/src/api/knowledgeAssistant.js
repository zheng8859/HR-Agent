import http from './http'

// 知识问答（读操作）：POST /knowledge-assistant/ask
export function askQuestion(question, knowledgeBaseId) {
  const payload = { question }
  if (knowledgeBaseId) payload.knowledge_base_id = knowledgeBaseId
  return http.post('/knowledge-assistant/ask', payload)
}
