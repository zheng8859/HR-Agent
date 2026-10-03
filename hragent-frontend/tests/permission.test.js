import { test } from 'node:test'
import assert from 'node:assert/strict'

import { HR_ADMIN_ROLES, isHrAdmin, isSuperuser } from '../src/utils/permission.js'

test('HR_ADMIN_ROLES 含三个管理角色且不含 employee', () => {
  assert.deepEqual([...HR_ADMIN_ROLES].sort(), ['admin', 'hr_manager', 'hr_specialist'].sort())
  assert.equal(HR_ADMIN_ROLES.includes('employee'), false)
})

test('isHrAdmin 仅 HR 管理员角色为真', () => {
  assert.equal(isHrAdmin({ role: 'admin' }), true)
  assert.equal(isHrAdmin({ role: 'hr_manager' }), true)
  assert.equal(isHrAdmin({ role: 'hr_specialist' }), true)
  assert.equal(isHrAdmin({ role: 'employee' }), false)
  assert.equal(isHrAdmin(null), false)
  assert.equal(isHrAdmin(undefined), false)
  assert.equal(isHrAdmin({}), false)
})

test('isSuperuser 仅 is_superuser === true 时为真', () => {
  assert.equal(isSuperuser({ is_superuser: true }), true)
  assert.equal(isSuperuser({ is_superuser: false }), false)
  assert.equal(isSuperuser({ role: 'admin', is_superuser: false }), false)
  assert.equal(isSuperuser(null), false)
  assert.equal(isSuperuser(undefined), false)
})
