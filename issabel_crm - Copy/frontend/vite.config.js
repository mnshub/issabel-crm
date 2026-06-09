import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    host: '0.0.0.0',
    watch: {
      usePolling: true // Crucial for instant Windows-to-Linux container file refresh tracking
    }
  }
})