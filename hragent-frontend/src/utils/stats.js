// 系统管理展示格式化纯逻辑
export const ROLE_LABELS = {
  admin: '超级管理员',
  hr_manager: 'HR 负责人',
  hr_specialist: 'HR 专员',
  employee: '普通员工',
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || role || '—'
}

// 环比增减格式化：null/undefined/NaN → '—'，正数带 +，负数带 -，0 → '0'
export function formatGrowth(growth) {
  if (growth === null || growth === undefined || Number.isNaN(growth)) return '—'
  const n = Number(growth)
  if (n > 0) return `+${n}`
  if (n < 0) return `${n}`
  return '0'
}
