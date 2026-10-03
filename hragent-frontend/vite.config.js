import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      // 后端路由即 /api/v1/...，无需 rewrite；透传 SSE 与 JSON
      '/api': {
        // 用 127.0.0.1 而非 localhost：Windows 下 localhost 会优先解析为 IPv6 ::1，
        // 而 ::1:8000 被 Docker 的 chemai-backend 容器占用，导致代理打到错误后端。
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
