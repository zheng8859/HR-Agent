// 简历上传与评分卡展示的纯逻辑（前端校验复刻后端 validate_upload 规则，仅做体验优化）。

export const RESUME_ALLOWED_TYPES = ['pdf', 'doc', 'docx']
export const RESUME_MAX_SIZE_MB = 10

/**
 * 前端文件校验：扩展名 + 大小。返回 { ok, ext? } 或 { ok:false, error }。
 * 真正校验仍在后端（CLAUDE.md 六.2），此处仅提前给出与后端一致的提示。
 * @param {string} filename
 * @param {number} size 字节数
 * @param {{ allowedTypes?: string[], maxSizeMb?: number }} [opts]
 */
export function validateResumeFile(filename, size, opts = {}) {
  const allowed = opts.allowedTypes ?? RESUME_ALLOWED_TYPES
  const maxSizeMb = opts.maxSizeMb ?? RESUME_MAX_SIZE_MB
  const name = String(filename || '')
  const dot = name.lastIndexOf('.')
  if (dot < 0) return { ok: false, error: '不支持的文件格式' }
  const ext = name.slice(dot + 1).toLowerCase()
  if (!allowed.includes(ext)) return { ok: false, error: `不支持的文件格式：${ext}` }
  if (size > maxSizeMb * 1024 * 1024) {
    return { ok: false, error: `文件大小超过限制（${maxSizeMb}MB）` }
  }
  return { ok: true, ext }
}

/**
 * 维度得分百分比（0-100），用于评分卡进度条；max<=0 或非法值返回 0。
 * @param {number} score
 * @param {number} max
 */
export function dimensionPct(score, max) {
  const s = Number(score)
  const m = Number(max)
  if (!Number.isFinite(s) || !Number.isFinite(m) || m <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((s / m) * 100)))
}
