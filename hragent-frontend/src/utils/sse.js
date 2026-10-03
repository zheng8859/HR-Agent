// SSE 流解析工具：生成接口是 POST，无法用 EventSource，需手动按帧解析 text/event-stream。
// 后端事件格式：`event: <type>\ndata: <json>\n\n`（data 为单行 JSON）。

/**
 * 解析一段完整事件（不含结尾空行）为 { event, data }。
 * @param {string} block 例如 "event: delta\ndata: \"你好\""
 */
export function parseSSEBlock(block) {
  const result = { event: null, data: [] }
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      result.event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      // SSE 规范：data 字段前缀后可跟一个空格，去掉该空格
      result.data.push(line.slice(5).replace(/^ /, ''))
    }
  }
  return { event: result.event, data: result.data.join('\n') }
}

/**
 * 增量 SSE 解码器：累积分块，按空行分帧返回完整事件。
 * 跨分块的事件会保留在内部缓冲，直至收到结尾空行。
 */
export function createSSEDecoder() {
  let buffer = ''
  return {
    push(chunk) {
      buffer += chunk
      const events = []
      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        const parsed = parseSSEBlock(block)
        if (parsed.event) events.push(parsed)
      }
      return events
    },
  }
}
