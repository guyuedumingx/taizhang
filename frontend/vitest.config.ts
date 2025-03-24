import { defineConfig } from 'vitest/config';
import * as path from 'path';

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    include: ['./tests/**/*.test.ts'],
    testTimeout: 10000, // 设置更长的超时时间，因为要进行真实的 API 调用
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}); 