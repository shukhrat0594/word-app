import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const yol = (nisbiy) => fileURLToPath(new URL(nisbiy, import.meta.url))

// ── CRM marshruti (2026-09-14) ───────────────────────────────────────
// CRM — LMS'dan alohida ilova (frontend/crm.html + frontend/src-crm/).
// Vite ikkalasini bitta konteynerda, ikkita mustaqil bundle qilib yig'adi.
//
// MUAMMO: Vite'ning standart `appType: "spa"` rejimida `htmlFallback`
// middleware'i topilmagan yo'lni HAR DOIM `/index.html`ga yo'naltiradi.
// Natijada:
//     /crm          -> crm.html topiladi           ✅
//     /crm/moliya   -> crm/moliya.html yo'q -> LMS ✗
// Ya'ni CRM ichida F5 bosilishi bilan admin LMS'ga tushib qolardi.
// Railway'da ham `vite preview` ishlatilgani uchun prodda bir xil.
//
// YECHIM: `/crm` bilan boshlanadigan barcha so'rovlarni `/crm.html`ga
// qayta yozamiz — dev serverda ham, preview (prod) serverda ham.
// `/api/crm/...` TEGILMAYDI, chunki u `/api` bilan boshlanadi.
//
// CRM olib tashlansa — shu plagin va `build.rollupOptions` blokini
// o'chirish yetarli (tmp/plans/moliya-tz.md, 8-band).
function crmMarshrut() {
  const qaytaYoz = (req, _res, next) => {
    const manzil = (req.url || '').split('?')[0]
    if (manzil === '/crm' || manzil.startsWith('/crm/')) {
      req.url = '/crm.html'
    }
    next()
  }
  return {
    name: 'crm-marshrut',
    // Ataylab hook TANASIDA (qaytarilgan funksiyada emas) — shunda
    // middleware Vite'ning o'z middleware'laridan OLDIN turadi va
    // htmlFallback'gacha ishlaydi.
    configureServer(server) {
      server.middlewares.use(qaytaYoz)
    },
    configurePreviewServer(server) {
      server.middlewares.use(qaytaYoz)
    },
  }
}

// Dev rejimda /api so'rovlari Django'ga (8000) yo'naltiriladi —
// CORS shart emas, frontend faqat 3000-portda ishlaydi.
export default defineConfig({
  plugins: [react(), crmMarshrut()],
  build: {
    rollupOptions: {
      input: {
        lms: yol('./index.html'),
        crm: yol('./crm.html'),
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
  // Railway.app'da `vite preview` bilan xizmat qilinganda (railway.json)
  // — Vite domendan kelgan so'rovni "Blocked request" bilan rad etadi,
  // chunki Railway domeni ("*.up.railway.app") standart ravishda ruxsat
  // etilgan ro'yxatda emas (faqat localhost). Bu — statik HTML/JS
  // beruvchi server, maxfiy ma'lumot yo'q, shuning uchun barcha host
  // ruxsat etiladi.
  preview: {
    allowedHosts: true,
  },
})
