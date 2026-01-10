import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import envCompatible from 'vite-plugin-env-compatible';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    envCompatible({
      // Map REACT_APP_* to VITE_* for compatibility
      prefix: 'REACT_APP_',
    }),
  ],
  server: {
    port: 3000,
    host: true,
    proxy: {
      // Proxy API requests to backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Explicitly set target for browser compatibility
    // TypeScript's target is 'esnext' which doesn't downlevel code,
    // so Vite needs to handle transpilation for older browsers
    target: 'es2020', // Supports modern browsers (Chrome 80+, Firefox 75+, Safari 14+)
  },
  // Vitest configuration
  test: {
    globals: true,
    // Using happy-dom instead of jsdom for better performance (faster test execution)
    // happy-dom is lighter and sufficient for most React component tests.
    // If you need more complete DOM APIs (e.g., FormData, Blob), consider switching to jsdom.
    environment: 'happy-dom',
    setupFiles: './src/setupTests.ts',
    css: true,
    testTimeout: 10000, // Some dropdown tests need more time
  },
});
