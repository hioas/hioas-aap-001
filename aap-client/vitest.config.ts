import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

// 测试环境用纯 @vitejs/plugin-vue（vite-plugin-uni 只在 uni 构建时生效），
// uni.* 全局 API 由 tests/setup.ts 打桩。
export default defineConfig({
  plugins: [vue() as never],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['tests/setup.ts'],
    include: ['tests/**/*.spec.ts'],
    css: false,
    testTimeout: 15000,
    reporters: ['default']
  }
})
