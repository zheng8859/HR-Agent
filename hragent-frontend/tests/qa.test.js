import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  SUGGESTED_QUESTIONS,
  isRefusal,
  isLowConfidence,
  confidencePercent,
} from '../src/utils/qa.js'

test('SUGGESTED_QUESTIONS 非空且为字符串数组', () => {
  assert.ok(Array.isArray(SUGGESTED_QUESTIONS))
  assert.ok(SUGGESTED_QUESTIONS.length > 0)
  assert.ok(SUGGESTED_QUESTIONS.every((q) => typeof q === 'string' && q.length > 0))
})

test('isRefusal 仅 answered=false 判为拒答', () => {
  assert.equal(isRefusal({ answered: false }), true)
  assert.equal(isRefusal({ answered: true, confidence: 0.9 }), false)
  assert.equal(isRefusal(null), false)
})

test('isLowConfidence 仅 answered=true 且置信度低于阈值', () => {
  assert.equal(isLowConfidence({ answered: true, confidence: 0.2 }), true)
  assert.equal(isLowConfidence({ answered: true, confidence: 0.9 }), false)
  // 拒答态不算低置信度
  assert.equal(isLowConfidence({ answered: false, confidence: 0 }), false)
})

test('confidencePercent 四舍五入为百分比字符串，非法值返回 --', () => {
  assert.equal(confidencePercent(0.96), '96%')
  assert.equal(confidencePercent(0.964), '96%')
  assert.equal(confidencePercent(0), '0%')
  assert.equal(confidencePercent(null), '--')
  assert.equal(confidencePercent(undefined), '--')
  assert.equal(confidencePercent('not-a-number'), '--')
})
