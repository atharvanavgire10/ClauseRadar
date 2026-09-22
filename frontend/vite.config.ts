import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Production assets are served by Django/WhiteNoise from /static/ (the
  // Vercel build copies dist output into the Django template/static tree).
  // The dev server honors base as well, so local development is unaffected.
  base: '/static/',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
