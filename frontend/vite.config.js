import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api/ requests to Django backend in development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // FIX: credentials (cookies) are forwarded
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('Proxy error:', err)
          })
        },
      },
      // Proxy auth endpoints too
      '/accounts': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,  // Disable in production for performance
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          react: ['react', 'react-dom'],
          router: ['react-router-dom'],
          vendor: ['axios', 'zustand'],
        },
      },
    },
  },
  // Prevent VITE_* env vars from being logged in the terminal
  envPrefix: 'VITE_',
})

