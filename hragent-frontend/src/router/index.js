import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/jd-generator',
    children: [
      {
        path: 'jd-generator',
        name: 'jd-generator',
        component: () => import('@/views/JDGeneratorView.vue'),
        meta: { title: 'JD 生成' },
      },
      {
        path: 'scoring-criteria',
        name: 'scoring-criteria',
        component: () => import('@/views/ScoringCriteriaView.vue'),
        meta: { title: '评分标准' },
      },
      {
        path: 'resume-screening',
        name: 'resume-screening',
        component: () => import('@/views/ResumeScreeningView.vue'),
        meta: { title: '简历筛选' },
      },
      {
        path: 'interview',
        name: 'interview',
        component: () => import('@/views/SmartInterviewView.vue'),
        meta: { title: '智能面试' },
      },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/KnowledgeManagementView.vue'),
        meta: { title: '知识库管理' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'jd-generator' }
  }
  return true
})

export default router
