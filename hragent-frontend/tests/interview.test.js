import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  INTERVIEW_SECTION_TITLES,
  parsePlanSections,
} from '../src/utils/interview.js'

test('七要素分区标题顺序正确', () => {
  assert.deepEqual(INTERVIEW_SECTION_TITLES, [
    '面试目标',
    '面试流程',
    '核心问题',
    '追问建议',
    '考察维度',
    '评分建议',
    '候选人风险点',
  ])
})

test('parsePlanSections 解析出七个分区', () => {
  const content = [
    '## 面试目标',
    '评估匹配度',
    '',
    '## 面试流程',
    '自我介绍后技术面',
    '',
    '## 核心问题',
    '1. 问题一',
    '2. 问题二',
    '',
    '## 追问建议',
    '追问细节',
    '',
    '## 考察维度',
    '技能与项目',
    '',
    '## 评分建议',
    '沿用五维度',
    '',
    '## 候选人风险点',
    '项目经验偏浅',
  ].join('\n')

  const sections = parsePlanSections(content)
  assert.equal(sections.length, 7)
  assert.deepEqual(
    sections.map((s) => s.title),
    INTERVIEW_SECTION_TITLES,
  )
  assert.equal(sections[0].body, '评估匹配度')
  assert.equal(sections[2].body, '1. 问题一\n2. 问题二')
})

test('parsePlanSections 核心问题编号保留', () => {
  const sections = parsePlanSections('## 核心问题\n1. 甲\n2. 乙')
  assert.deepEqual(sections, [{ title: '核心问题', body: '1. 甲\n2. 乙' }])
})

test('parsePlanSections 空内容返回空数组', () => {
  assert.deepEqual(parsePlanSections(''), [])
  assert.deepEqual(parsePlanSections(null), [])
  assert.deepEqual(parsePlanSections(undefined), [])
})

test('parsePlanSections 无分区标题返回空数组', () => {
  assert.deepEqual(parsePlanSections('普通文本\n没有分区'), [])
})
