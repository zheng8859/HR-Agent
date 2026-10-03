import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  DOCUMENT_STATUS_META,
  formatFileSize,
  formatUploadTime,
  fileExtension,
} from '../src/utils/document.js'

test('DOCUMENT_STATUS_META 四态齐全', () => {
  assert.deepEqual(Object.keys(DOCUMENT_STATUS_META).sort(), [
    'failed',
    'processed',
    'processing',
    'uploaded',
  ])
  assert.equal(DOCUMENT_STATUS_META.processed.label, '已处理')
  assert.equal(DOCUMENT_STATUS_META.failed.type, 'danger')
})

test('formatFileSize 单位换算', () => {
  assert.equal(formatFileSize(null), '-')
  assert.equal(formatFileSize(undefined), '-')
  assert.equal(formatFileSize(512), '512 B')
  assert.equal(formatFileSize(1024), '1.0 KB')
  assert.equal(formatFileSize(850 * 1024), '850.0 KB')
  assert.equal(formatFileSize(3.2 * 1024 * 1024), '3.20 MB')
})

test('fileExtension 提取大写扩展名', () => {
  assert.equal(fileExtension('差旅管理办法 v3.2.pdf'), 'PDF')
  assert.equal(fileExtension('note.TXT'), 'TXT')
  assert.equal(fileExtension('noext'), '')
  assert.equal(fileExtension(''), '')
  assert.equal(fileExtension(null), '')
})

test('formatUploadTime 今天显示时分', () => {
  const now = new Date('2026-10-03T12:00:00')
  assert.equal(formatUploadTime('2026-10-03T09:05:00', now), '今天 09:05')
})

test('formatUploadTime 非今天显示日期', () => {
  const now = new Date('2026-10-03T12:00:00')
  assert.equal(formatUploadTime('2026-10-01T16:30:00', now), '2026-10-01')
})

test('formatUploadTime 空值返回占位', () => {
  assert.equal(formatUploadTime(null), '-')
  assert.equal(formatUploadTime('invalid-date'), '-')
})
