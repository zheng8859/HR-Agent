import { test } from 'node:test'
import assert from 'node:assert/strict'

import { ROLE_LABELS, roleLabel, formatGrowth } from '../src/utils/stats.js'

test('roleLabel 已知角色返回中文名', () => {
  assert.equal(roleLabel('admin'), '超级管理员')
  assert.equal(roleLabel('hr_manager'), 'HR 负责人')
  assert.equal(roleLabel('hr_specialist'), 'HR 专员')
  assert.equal(roleLabel('employee'), '普通员工')
})

test('roleLabel 未知角色回退原值，空值回退占位', () => {
  assert.equal(roleLabel('培训管理员'), '培训管理员')
  assert.equal(roleLabel(''), '—')
  assert.equal(roleLabel(null), '—')
  assert.equal(roleLabel(undefined), '—')
})

test('formatGrowth 正数带 +，负数带 -，0 为 0，空值 —', () => {
  assert.equal(formatGrowth(3), '+3')
  assert.equal(formatGrowth(1), '+1')
  assert.equal(formatGrowth(0), '0')
  assert.equal(formatGrowth(-2), '-2')
  assert.equal(formatGrowth(null), '—')
  assert.equal(formatGrowth(undefined), '—')
  assert.equal(formatGrowth(NaN), '—')
})
