import { test } from 'node:test'
import assert from 'node:assert/strict'

import { sumScores, checkBalance } from '../src/utils/balance.js'

const dims = (vals) => vals.map((v) => ({ name: 'x', weight: v, max_score: v, description: '' }))

test('sumScores 求和 max_score', () => {
  assert.equal(sumScores(dims([40, 30, 20, 10])), 100)
})

test('sumScores 缺失 max_score 回退 weight，非法值按 0', () => {
  assert.equal(sumScores([{ weight: 25, max_score: null }, { max_score: 75 }]), 100)
  assert.equal(sumScores([{ weight: 'abc' }]), 0)
})

test('checkBalance 配平', () => {
  const r = checkBalance(dims([40, 30, 20, 10]), 100)
  assert.equal(r.isBalanced, true)
  assert.equal(r.scoreSum, 100)
  assert.equal(r.difference, 0)
})

test('checkBalance 不配平返回差值（不修正）', () => {
  const r = checkBalance(dims([40, 30, 20, 20]), 100) // 110
  assert.equal(r.isBalanced, false)
  assert.equal(r.scoreSum, 110)
  assert.equal(r.difference, -10)
})

test('checkBalance 空维度', () => {
  const r = checkBalance([], 100)
  assert.equal(r.isBalanced, false)
  assert.equal(r.scoreSum, 0)
  assert.equal(r.difference, 100)
})
