import { test } from 'node:test'
import assert from 'node:assert/strict'

import { createTokenStorage, buildAuthHeader, TOKEN_KEY } from '../src/utils/token.js'

function fakeStorage() {
  const map = new Map()
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
  }
}

test('createTokenStorage 存取与清空', () => {
  const s = createTokenStorage(fakeStorage())
  assert.equal(s.get(), '')
  s.set('abc')
  assert.equal(s.get(), 'abc')
  s.clear()
  assert.equal(s.get(), '')
})

test('createTokenStorage 异常 storage 不抛错', () => {
  const bad = createTokenStorage({
    getItem: () => {
      throw new Error('denied')
    },
    setItem: () => {
      throw new Error('denied')
    },
    removeItem: () => {
      throw new Error('denied')
    },
  })
  assert.equal(bad.get(), '')
  assert.doesNotThrow(() => bad.set('x'))
  assert.doesNotThrow(() => bad.clear())
})

test('buildAuthHeader 有 token 加 Bearer，无 token 为空对象', () => {
  assert.deepEqual(buildAuthHeader('tok'), { Authorization: 'Bearer tok' })
  assert.deepEqual(buildAuthHeader(''), {})
  assert.deepEqual(buildAuthHeader(null), {})
})

test('TOKEN_KEY 约定为 hra_token', () => {
  assert.equal(TOKEN_KEY, 'hra_token')
})
