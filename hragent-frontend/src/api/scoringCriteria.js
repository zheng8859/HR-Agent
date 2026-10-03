import http from './http'

export function generateScoring(payload) {
  return http.post('/scoring-criteria/generate', payload)
}

export function listScoring() {
  return http.get('/scoring-criteria')
}

export function createScoring(payload) {
  return http.post('/scoring-criteria', payload)
}

export function updateScoring(id, payload) {
  return http.put(`/scoring-criteria/${id}`, payload)
}

export function changeScoringStatus(id, status) {
  return http.patch(`/scoring-criteria/${id}/status`, null, { params: { status } })
}

export function deleteScoring(id) {
  return http.delete(`/scoring-criteria/${id}`)
}
