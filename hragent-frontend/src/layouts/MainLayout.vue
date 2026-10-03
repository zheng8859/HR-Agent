<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { fetchMe } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activePath = computed(() => route.path)
const title = computed(() => route.meta?.title || 'HR Agent')
const userLabel = computed(() => auth.user?.username || auth.user?.full_name || '未登录')

onMounted(async () => {
  if (auth.token && !auth.user) {
    try {
      const { data } = await fetchMe()
      auth.setUser(data)
    } catch {
      /* 401 由拦截器处理跳登录 */
    }
  }
})

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <span class="brand-dot" />
        <div class="brand-text">
          <div class="brand-name">HR Agent</div>
          <div class="brand-sub">企业人力智能化平台</div>
        </div>
      </div>
      <el-menu :default-active="activePath" router class="menu">
        <el-sub-menu index="recruit">
          <template #title>智能招聘</template>
          <el-menu-item index="/jd-generator">JD 生成</el-menu-item>
          <el-menu-item index="/scoring-criteria">评分标准</el-menu-item>
          <el-menu-item index="/resume-screening">简历筛选</el-menu-item>
          <el-menu-item index="/interview">智能面试</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="knowledge">
          <template #title>知识助理</template>
          <el-menu-item index="/knowledge">知识库管理</el-menu-item>
          <el-menu-item index="/knowledge-qa">知识问答</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="system" disabled>
          <template #title>系统管理</template>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="crumb">智能招聘 / {{ title }}</span>
        <div class="header-right">
          <el-tag size="small" effect="plain">{{ userLabel }}</el-tag>
          <el-button link type="primary" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  height: 100%;
}

.aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.brand-dot {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #e6f0fc;
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
  line-height: 1.2;
}

.brand-sub {
  font-size: 10px;
  color: #909399;
}

.menu {
  border-right: none;
  flex: 1;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.crumb {
  color: #606266;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
