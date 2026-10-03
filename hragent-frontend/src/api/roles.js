import http from './http'

// 角色管理（仅超管）
export function listRoles() {
  return http.get('/roles')
}

export function createRole(payload) {
  return http.post('/roles', payload)
}

export function updateRole(id, payload) {
  return http.put(`/roles/${id}`, payload)
}

export function deleteRole(id) {
  return http.delete(`/roles/${id}`)
}
