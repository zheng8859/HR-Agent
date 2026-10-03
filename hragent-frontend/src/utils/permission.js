// 菜单权限纯逻辑（权限真门在后端，前端仅做显隐优化）
export const HR_ADMIN_ROLES = ['admin', 'hr_manager', 'hr_specialist']

export function isHrAdmin(user) {
  return Boolean(user && HR_ADMIN_ROLES.includes(user.role))
}

export function isSuperuser(user) {
  return Boolean(user && user.is_superuser === true)
}
