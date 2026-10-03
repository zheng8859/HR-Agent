import http from './http'

// 生成面试方案：绑定一条已完成简历评估（写操作）
export function generatePlan(resumeEvaluationId) {
  return http.post('/interview-plans/generate', { resume_evaluation_id: resumeEvaluationId })
}

// 重新生成方案（写操作）
export function regeneratePlan(id) {
  return http.post(`/interview-plans/${id}/regenerate`)
}

// 方案列表（读，按 user_id 过滤）
export function listPlans() {
  return http.get('/interview-plans')
}

// 方案详情（读）
export function getPlan(id) {
  return http.get(`/interview-plans/${id}`)
}

// 编辑保存（写操作）
export function updatePlan(id, payload) {
  return http.put(`/interview-plans/${id}`, payload)
}

// 导出：md/txt 文件（blob，后端已带 UTF-8 BOM）
export function exportPlan(id, format = 'md') {
  return http.get(`/interview-plans/${id}/export`, {
    params: { format },
    responseType: 'blob',
  })
}
