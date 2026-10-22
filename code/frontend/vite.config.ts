import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5273,
    proxy: {
      // 开发环境将 /api 代理到后端
      '/api': 'http://127.0.0.1:8999',
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 5274,
    proxy: {
      // 本地预览构建产物时同样代理 /api 到后端
      '/api': 'http://127.0.0.1:8999',
    },
  },
})
