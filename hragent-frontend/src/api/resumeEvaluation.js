import http from './http'

// 简历上传：multipart（axios 依据 FormData 自动设置 boundary，勿手写 Content-Type）
export function uploadResume(file) {
  const form = new FormData()
  form.append('file', file)
  return http.post('/resume-evaluation/upload', form)
}

export function evaluateResume(payload) {
  return http.post('/resume-evaluation/evaluate', payload)
}

export function listResumes() {
  return http.get('/resume-evaluation')
}

export function updateResumeStatus(id, status) {
  return http.patch(`/resume-evaluation/${id}/status`, null, { params: { status } })
}

export function exportResume(id) {
  return http.get(`/resume-evaluation/${id}/export`)
}
