import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:1455',
        changeOrigin: true,
        ws: true,  // 启用 WebSocket 代理
      },
      '/auth': {
        target: 'http://localhost:1455',
        changeOrigin: true,
      },
    },
  },
})
