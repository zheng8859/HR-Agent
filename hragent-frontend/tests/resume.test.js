import { test } from 'node:test'
import assert from 'node:assert/strict'

import { validateResumeFile, dimensionPct, RESUME_ALLOWED_TYPES, RESUME_MAX_SIZE_MB } from '../src/utils/resume.js'

test('允许类型为 pdf/doc/docx', () => {
  assert.deepEqual(RESUME_ALLOWED_TYPES, ['pdf', 'doc', 'docx'])
  assert.equal(RESUME_MAX_SIZE_MB, 10)
})

test('validateResumeFile 拒绝非法扩展名', () => {
  assert.equal(validateResumeFile('resume.txt', 1024).ok, false)
})

test('validateResumeFile 拒绝超限文件', () => {
  assert.equal(validateResumeFile('resume.pdf', 11 * 1024 * 1024).ok, false)
})

test('validateResumeFile 接受合法大写扩展名并归一化', () => {
  const r = validateResumeFile('Resume.PDF', 1024)
  assert.equal(r.ok, true)
  assert.equal(r.ext, 'pdf')
})

test('validateResumeFile 接受 docx', () => {
  assert.equal(validateResumeFile('a.docx', 1024).ext, 'docx')
})

test('validateResumeFile 无扩展名拒绝', () => {
  assert.equal(validateResumeFile('resume', 1024).ok, false)
})

test('dimensionPct 正常百分比', () => {
  assert.equal(dimensionPct(16, 20), 80)
})

test('dimensionPct max<=0 或非法返回 0', () => {
  assert.equal(dimensionPct(16, 0), 0)
  assert.equal(dimensionPct(16, 'abc'), 0)
})

test('dimensionPct 越界夹取到 0-100', () => {
  assert.equal(dimensionPct(120, 100), 100)
  assert.equal(dimensionPct(-5, 100), 0)
})
