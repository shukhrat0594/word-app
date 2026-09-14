// CRM backend API qatlami.
//
// Bu fayl `src/api.js` dan NUSXA (2026-09-14) — ataylab, import EMAS.
// Sabab (TZ 1.1): umumiy fayl bo'lsa, LMS uchun qilingan o'zgarish CRM'ni
// kutilmaganda buzadi va aksincha. Fayl kichik va mustaqil, takror kod bu
// yerda bog'liqlikdan arzonroq.
//
// NUSXALASHDA MOSLANGAN JOYLAR (asl faylda `/login` edi):
//   401 -> `/crm` ga qaytariladi, LMS loginiga EMAS. Aks holda admin
//   birinchi token eskirishida o'zini LMS kirish oynasida topardi.
//
// localStorage kalitlari (`access`, `refresh`, `qurilma_id`) ATAYLAB
// LMS bilan BIR XIL: ikkala ilova bir xil origin'da, ya'ni LMS'ga kirgan
// admin `/crm`ga o'tganda qaytadan login qilmaydi va qurilma limiti ikki
// marta yeyilmaydi.

const API_BAZA = import.meta.env.VITE_API_URL || "";

export function apiManzil(yol) {
  return `${API_BAZA}${yol}`;
}

export function tokenOl() {
  return localStorage.getItem("access");
}

export function tokenlarniSaqla({ access, refresh }) {
  localStorage.setItem("access", access);
  if (refresh) localStorage.setItem("refresh", refresh);
}

export function tokenlarniTozala() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

// Hisobni bo'lishmaslik uchun — har login so'roviga shu brauzerga xos
// tasodifiy ID qo'shiladi (backend: `accounts.views.XodimLoginView`).
// Kalit LMS bilan bir xil, ya'ni CRM yangi qurilma sifatida sanalmaydi.
export function qurilmaIdOl() {
  let id = localStorage.getItem("qurilma_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("qurilma_id", id);
  }
  return id;
}

/** Serverga "chiqdim" deb aytadi — refresh kalit darhol bekor qilinadi.
 *  Natija KUTILMAYDI va xato YUTILADI: chiqib ketishga hech narsa
 *  to'sqinlik qilmasligi kerak. */
export async function serverdaChiqish() {
  const refresh = localStorage.getItem("refresh");
  const access = tokenOl();
  if (!access) return;
  try {
    await fetch(apiManzil("/api/chiqish/"), {
      method: "POST",
      headers: { Authorization: `Bearer ${access}`, "Content-Type": "application/json" },
      body: JSON.stringify(refresh ? { refresh } : {}),
    });
  } catch {
    // sokin — chiqish baribir davom etadi
  }
}

// Bir vaqtda ketgan bir nechta so'rov 401 olsa, hammasi BITTA umumiy
// refresh-so'rovni kutadi. Backendda ROTATE_REFRESH_TOKENS +
// BLACKLIST_AFTER_ROTATION yoqilgani uchun parallel refresh birinchisidan
// boshqasini bloklab, foydalanuvchini beixtiyor logout qilardi.
let refreshVadasi = null;

async function refreshQil() {
  if (refreshVadasi) return refreshVadasi;
  refreshVadasi = (async () => {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) return false;
    try {
      const res = await fetch(apiManzil("/api/token/refresh/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      // Yangi `refresh`ni ham saqlaymiz — eskisi blacklist qilinadi.
      tokenlarniSaqla({ access: data.access, refresh: data.refresh });
      return true;
    } finally {
      refreshVadasi = null;
    }
  })();
  return refreshVadasi;
}

// 2026-09-14, Shuhrat topgan xato: tokensiz `/crm/moliya` ochilganda
// sahifa CHEKSIZ qayta yuklanardi. Sabab — 401 kelganda bu funksiya
// `/crm` ga yo'naltirardi, u yerda esa o'sha so'rov qaytadan ketib yana
// 401 olardi. Endi ikkita to'siq bor:
//   1) bir sahifa yuklanishida FAQAT BIR MARTA yo'naltiradi (parallel
//      so'rovlar navbatma-navbat yo'naltirmasin);
//   2) allaqachon `/crm` da bo'lsak, umuman yo'naltirmaydi — `App.jsx`
//      token yo'qligini ko'rib kirish oynasini o'zi chizadi.
let qaytarildi = false;

function kirishGaQaytar() {
  tokenlarniTozala();
  if (qaytarildi) return;
  qaytarildi = true;
  // LMS'ning `/login` sahifasiga EMAS — CRM o'z kirish oynasini
  // ko'rsatadi (`App.jsx`).
  if (window.location.pathname.replace(/\/+$/, "") !== "/crm") {
    window.location.href = "/crm";
  }
}

export async function api(yol, options = {}) {
  const sorov = () =>
    fetch(apiManzil(yol), {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(tokenOl() ? { Authorization: `Bearer ${tokenOl()}` } : {}),
        ...options.headers,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

  let res = await sorov();
  if (res.status === 401 && (await refreshQil())) {
    res = await sorov();
  }
  if (res.status === 401) {
    kirishGaQaytar();
    throw new Error("401");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const e = new Error(data?.detail || `HTTP ${res.status}`);
    e.status = res.status;
    e.data = data;
    throw e;
  }
  return data;
}

// Autentifikatsiyalangan faylni yuklab olish (Excel eksport) — oddiy
// <a href> ishlamaydi, chunki Authorization sarlavhasi kerak.
export async function apiFayluniYuklab(yol) {
  const sorov = () =>
    fetch(apiManzil(yol), {
      headers: tokenOl() ? { Authorization: `Bearer ${tokenOl()}` } : {},
    });

  let res = await sorov();
  if (res.status === 401 && (await refreshQil())) {
    res = await sorov();
  }
  if (res.status === 401) {
    kirishGaQaytar();
    throw new Error("401");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data?.detail || detail;
    } catch {
      // javob JSON emas — o'zgarishsiz
    }
    const e = new Error(detail);
    e.status = res.status;
    throw e;
  }

  // Fayl nomi: avval RFC 5987 shakli (o'zbekcha nomlar uchun), keyin oddiysi.
  const disposition = res.headers.get("Content-Disposition") || "";
  const utf8Mos = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  const oddiyMos = disposition.match(/filename="?([^";]+)"?/);
  let nomi = "yuklab-olindi.xlsx";
  if (utf8Mos) {
    try {
      nomi = decodeURIComponent(utf8Mos[1]);
    } catch {
      nomi = oddiyMos ? oddiyMos[1] : nomi;
    }
  } else if (oddiyMos) {
    nomi = oddiyMos[1];
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomi;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
