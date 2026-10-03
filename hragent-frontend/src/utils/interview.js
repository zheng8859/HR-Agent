// 面试方案纯逻辑：方案 markdown 七分区解析（与后端 format_plan 渲染约定一致）。

// 方案七要素分区标题（顺序即展示顺序）
export const INTERVIEW_SECTION_TITLES = [
  '面试目标',
  '面试流程',
  '核心问题',
  '追问建议',
  '考察维度',
  '评分建议',
  '候选人风险点',
]

/**
 * 把方案 markdown（`## 标题` 分区）解析为 `[{ title, body }]` 列表。
 * 未命中 `## ` 标题的文本被忽略；空/非字符串内容返回空数组。
 * @param {string | null | undefined} content
 * @returns {{ title: string, body: string }[]}
 */
export function parsePlanSections(content) {
  if (typeof content !== 'string' || !content.trim()) return []
  const sections = []
  const lines = content.split(/\r?\n/)
  let current = null
  for (const line of lines) {
    const m = line.match(/^##\s+(.+)$/)
    if (m) {
      if (current) sections.push(current)
      current = { title: m[1].trim(), body: [] }
    } else if (current) {
      current.body.push(line)
    }
  }
  if (current) sections.push(current)
  return sections.map((s) => ({ title: s.title, body: s.body.join('\n').trim() }))
}
