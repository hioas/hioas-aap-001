import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

/**
 * 管理端是**桌面 Web**（PRD 13 §0：载体 Vue3 + Element Plus + ECharts），
 * 与 aap-client（uni-app 小程序/H5）不是同一套构建，因此独立工程。
 *
 * dev 端口 5174：供应商端 dev server 占 5173，两个端要能同时开、同屏对照。
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    // 后端同源代理：前端一律用相对路径 /api/v1，避免把基址写死进代码
    proxy: {
      '/api': {
        target: process.env.AAP_API_TARGET || 'http://127.0.0.1:8084',
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.spec.ts'],
    server: { deps: { inline: ['element-plus'] } }
  }
});
