import http from './http'

// 统计看板（HR 管理员角色可见）
export function getDashboard() {
  return http.get('/stats/dashboard')
}

export function getTrend(days = 30) {
  return http.get('/stats/trend', { params: { days } })
}

export function getActivities(limit = 10) {
  return http.get('/stats/activities', { params: { limit } })
}
