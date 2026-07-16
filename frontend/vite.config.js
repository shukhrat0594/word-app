import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev rejimda /api so'rovlari Django'ga (8000) yo'naltiriladi —
// CORS shart emas, frontend faqat 3000-portda ishlaydi.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
})
