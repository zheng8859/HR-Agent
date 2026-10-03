<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser } from '@/api/users'
import { ROLE_LABELS, roleLabel } from '@/utils/stats'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = ref({})

const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))

function resetForm() {
  form.value = {
    username: '',
    email: '',
    password: '',
    full_name: '',
    phone: '',
    department: '',
    position: '',
    employee_id: '',
    role: 'employee',
    is_active: true,
  }
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    username: row.username,
    email: row.email,
    password: '',
    full_name: row.full_name || '',
    phone: row.phone || '',
    department: row.department || '',
    position: row.position || '',
    employee_id: row.employee_id || '',
    role: row.role,
    is_active: row.is_active,
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.username.trim() || !form.value.email.trim()) {
    ElMessage.warning('用户名与邮箱必填')
    return
  }
  if (!editingId.value && !form.value.password) {
    ElMessage.warning('新建用户需设置初始密码')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      const payload = { ...form.value }
      if (!payload.password) delete payload.password
      await updateUser(editingId.value, payload)
      ElMessage.success('用户已更新')
    } else {
      await createUser(form.value)
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户「${row.username}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteUser(row.id)
    ElMessage.success('用户已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function load() {
  loading.value = true
  try {
    const { data } = await listUsers()
    users.value = data.items || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="users-page">
    <div class="page-head">
      <div>
        <h2 class="page-title">用户管理</h2>
        <p class="page-sub">管理企业用户账号、部门职位与角色，账号仅由超管在此创建</p>
      </div>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="users" style="width: 100%">
        <el-table-column label="用户名" min-width="130">
          <template #default="{ row }">{{ row.username }}</template>
        </el-table-column>
        <el-table-column label="姓名" min-width="110">
          <template #default="{ row }">{{ row.full_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email }}</template>
        </el-table-column>
        <el-table-column label="部门" min-width="120">
          <template #default="{ row }">{{ row.department || '—' }}</template>
        </el-table-column>
        <el-table-column label="职位" min-width="120">
          <template #default="{ row }">{{ row.position || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">{{ roleLabel(row.role) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新建用户'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="登录账号" maxlength="255" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" placeholder="user@example.com" maxlength="255" />
        </el-form-item>
        <el-form-item :label="editingId ? '重置密码' : '初始密码'" :required="!editingId">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingId ? '留空表示不修改' : '至少 6 位'"
            maxlength="72"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" placeholder="真实姓名" maxlength="255" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="手机号" maxlength="64" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="如：人力资源部" maxlength="255" />
        </el-form-item>
        <el-form-item label="职位">
          <el-input v-model="form.position" placeholder="如：招聘专员" maxlength="255" />
        </el-form-item>
        <el-form-item label="员工编号">
          <el-input v-model="form.employee_id" placeholder="工号" maxlength="64" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="saving" @click="submit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.users-page {
  min-height: 100%;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.page-sub {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}
</style>
