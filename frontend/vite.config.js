import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/video_feed': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/evidence_files': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        rewriteWsOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            if (['ECONNABORTED', 'ECONNRESET', 'EPIPE', 'ETIMEDOUT'].includes(err?.code)) return;
            console.warn('[vite ws proxy]', err?.message || err);
          });
          proxy.on('proxyReqWsError', (err, _req, _socket) => {
            if (['ECONNABORTED', 'ECONNRESET', 'EPIPE', 'ETIMEDOUT'].includes(err?.code)) return;
            console.warn('[vite ws proxy socket]', err?.message || err);
          });
        },
      },

    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
