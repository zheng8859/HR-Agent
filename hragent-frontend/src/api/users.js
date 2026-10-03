import http from './http'

// 用户管理（仅超管）
export function listUsers() {
  return http.get('/users')
}

export function createUser(payload) {
  return http.post('/users', payload)
}

export function getUser(id) {
  return http.get(`/users/${id}`)
}

export function updateUser(id, payload) {
  return http.put(`/users/${id}`, payload)
}

export function deleteUser(id) {
  return http.delete(`/users/${id}`)
}
