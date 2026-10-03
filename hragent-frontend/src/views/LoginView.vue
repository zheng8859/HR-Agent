<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/auth'
import { login, fetchMe } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await login(form.username, form.password)
    auth.setAuth(data.access_token)
    try {
      const me = await fetchMe()
      auth.setUser(me.data)
    } catch {
      /* 用户信息获取失败不影响登录 */
    }
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/jd-generator'
    router.push(redirect)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名或密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="always">
      <div class="login-head">
        <h2>HR Agent</h2>
        <p>企业人力智能化平台</p>
      </div>
      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #e6f0fc 0%, #f5f7fa 60%);
}

.login-card {
  width: 380px;
}

.login-head {
  text-align: center;
  margin-bottom: 16px;
}

.login-head h2 {
  margin: 0;
  color: #409eff;
}

.login-head p {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}

.login-btn {
  width: 100%;
}
</style>
