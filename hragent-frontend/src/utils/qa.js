// 知识问答纯逻辑：示例问题、拒答/低置信度判定、置信度格式化。

// 空态示例问题：降低「第一句问什么」门槛
export const SUGGESTED_QUESTIONS = [
  '出差一线城市的住宿报销上限是多少？',
  '年假休假规则与司龄是如何对应的？',
  '试用期转正需要提交哪些材料？',
]

// 低置信度阈值：有答案但置信度偏低需提示核对原文
export const LOW_CONFIDENCE_THRESHOLD = 0.5

/** 是否为「资料不足」拒答态（后端 answered=false）。 */
export function isRefusal(response) {
  return !!response && response.answered === false
}

/** 是否有答案但置信度偏低（answered=true 且 confidence < 阈值）。 */
export function isLowConfidence(response) {
  return (
    !!response &&
    response.answered === true &&
    response.confidence < LOW_CONFIDENCE_THRESHOLD
  )
}

/** 置信度 → 百分比字符串（0.96 → "96%"）；非法值返回 "--"。 */
export function confidencePercent(confidence) {
  if (confidence == null || Number.isNaN(Number(confidence))) return '--'
  return `${Math.round(Number(confidence) * 100)}%`
}
