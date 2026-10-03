import { test } from 'node:test'
import assert from 'node:assert/strict'

import { parseSSEBlock, createSSEDecoder } from '../src/utils/sse.js'

test('parseSSEBlock 解析 event 与 data', () => {
  assert.deepEqual(parseSSEBlock('event: thinking\ndata: "正在生成"'), {
    event: 'thinking',
    data: '"正在生成"',
  })
})

test('parseSSEBlock 忽略注释与未知字段', () => {
  assert.deepEqual(parseSSEBlock(': ping\nevent: delta\ndata: 内容'), {
    event: 'delta',
    data: '内容',
  })
})

test('decoder 完整事件序列 thinking/delta/final', () => {
  const dec = createSSEDecoder()
  const stream = [
    'event: thinking\ndata: "..."\n\n',
    'event: delta\ndata: "你好"\n\n',
    'event: delta\ndata: "世界"\n\n',
    'event: final\ndata: {"title":"x"}\n\n',
  ].join('')
  const events = dec.push(stream)
  assert.deepEqual(
    events.map((e) => e.event),
    ['thinking', 'delta', 'delta', 'final'],
  )
  assert.equal(events[3].data, '{"title":"x"}')
})

test('decoder 跨分块事件被正确拼接', () => {
  const dec = createSSEDecoder()
  // 一个事件被切成三块，中间无空行，末尾才有 \n\n
  const first = dec.push('event: delta\nda')
  assert.equal(first.length, 0)
  const second = dec.push('ta: "分')
  assert.equal(second.length, 0)
  const third = dec.push('块内容"\n\n')
  assert.equal(third.length, 1)
  assert.deepEqual(third[0], { event: 'delta', data: '"分块内容"' })
})

test('decoder 一个 chunk 含多个事件', () => {
  const dec = createSSEDecoder()
  const events = dec.push('event: delta\ndata: "a"\n\nevent: final\ndata: {}\n\n')
  assert.equal(events.length, 2)
  assert.equal(events[0].event, 'delta')
  assert.equal(events[1].event, 'final')
})
