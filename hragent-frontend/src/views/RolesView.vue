<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listRoles, createRole, updateRole, deleteRole } from '@/api/roles'

const roles = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = ref({ name: '', description: '' })

function openCreate() {
  editingId.value = null
  form.value = { name: '', description: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = { name: row.name, description: row.description || '' }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.name.trim()) {
    ElMessage.warning('角色名称必填')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.value.name.trim(), description: form.value.description || null }
    if (editingId.value) {
      await updateRole(editingId.value, payload)
      ElMessage.success('角色已更新')
    } else {
      await createRole(payload)
      ElMessage.success('角色已创建')
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
  if (row.is_builtin) {
    ElMessage.warning('内置角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除角色「${row.name}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteRole(row.id)
    ElMessage.success('角色已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function formatTime(s) {
  if (!s) return '—'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  try {
    const { data } = await listRoles()
    roles.value = data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="roles-page">
    <div class="page-head">
      <div>
        <h2 class="page-title">角色管理</h2>
        <p class="page-sub">预置 4 个内置角色，可按需扩展自定义角色（如培训管理员）</p>
      </div>
      <el-button type="primary" @click="openCreate">新建角色</el-button>
    </div>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="roles" style="width: 100%">
        <el-table-column label="名称" min-width="160">
          <template #default="{ row }">
            <span class="role-name">{{ row.name }}</span>
            <el-tag v-if="row.is_builtin" size="small" type="info" effect="plain" class="builtin-tag">内置</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="240">
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="200">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="right">
          <template #default="{ row }">
            <el-button link type="primary" :disabled="row.is_builtin" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :disabled="row.is_builtin" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新建角色'" width="480px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：培训管理员" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="角色职责说明（可选）" />
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
.roles-page {
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

.role-name {
  margin-right: 6px;
}

.builtin-tag {
  margin-left: 6px;
}
</style>
