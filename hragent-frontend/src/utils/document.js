// 知识库文档纯逻辑：状态元数据、文件大小/时间格式化、扩展名提取。

// 文档四态 → 展示标签与 Element Plus tag 类型（与后端 DocumentStatus 一致）
export const DOCUMENT_STATUS_META = {
  uploaded: { label: '已上传', type: 'info' },
  processing: { label: '处理中', type: 'warning' },
  processed: { label: '已处理', type: 'success' },
  failed: { label: '处理失败', type: 'danger' },
}

/** 把字节数格式化为人类可读大小。null/undefined/NaN 返回 '-'。 */
export function formatFileSize(bytes) {
  if (bytes == null || Number.isNaN(Number(bytes))) return '-'
  const n = Number(bytes)
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

/** 提取文件扩展名（大写）；无扩展名返回空串。 */
export function fileExtension(filename) {
  if (typeof filename !== 'string' || !filename.includes('.')) return ''
  return filename.split('.').pop().toUpperCase()
}

/**
 * 格式化上传时间：今天显示「今天 HH:mm」，否则显示「YYYY-MM-DD」。
 * 空值/非法日期返回 '-'。`now` 可注入以便测试。
 */
export function formatUploadTime(isoString, now = new Date()) {
  if (!isoString) return '-'
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return '-'
  if (d.toDateString() === now.toDateString()) {
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `今天 ${hh}:${mm}`
  }
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
