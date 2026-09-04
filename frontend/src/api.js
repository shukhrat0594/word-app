// Backend API qatlami — JWT localStorage'da, 401 bo'lsa refresh urinadi.

// Production'da (Render) frontend va backend alohida domenlarda — backend
// manzili build paytida VITE_API_URL orqali beriladi. Local dev'da bo'sh
// qoladi va so'rovlar Vite proxy (vite.config.js) orqali Django'ga boradi.
const API_BAZA = import.meta.env.VITE_API_URL || "";

export function apiManzil(yol) {
  return `${API_BAZA}${yol}`;
}

// Backend'dan kelgan nisbiy media URL (/media/...) uchun — production'da
// backend domeni bilan to'ldiriladi. To'liq (http...) URL o'zgarmaydi.
export function mediaManzil(url) {
  if (!url) return url;
  return url.startsWith("/") ? `${API_BAZA}${url}` : url;
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

/** Serverga "chiqdim" deb aytadi — refresh kalit DARHOL bekor qilinadi.
 *
 * 2026-09-03, foydalanuvchi topib bergan muammo: avval "Chiqish" faqat
 * shu brauzerdagi kalitlarni tozalardi, server esa bilmasdi va kalit
 * o'z muddatigacha AMALDA qolardi ("qolib ketgan seans").
 *
 * Natija KUTILMAYDI va xato YUTILADI: chiqib ketishga hech narsa
 * to'sqinlik qilmasligi kerak — so'rov muvaffaqiyatsiz bo'lsa ham
 * mahalliy tozalash baribir bajariladi. Server tomonda esa kalit
 * eng ko'p bir kunda o'zi eskiradi. */
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

// 2026-08-12: hisobni boshqalar bilan bo'lishmaslik uchun — har login
// so'roviga shu brauzerga xos tasodifiy ID qo'shib yuboriladi
// (backend: `accounts/views.py: XodimLoginView`/`_qurilma_tekshir`).
// Birinchi loginda backend shu ID'ni "asosiy qurilma" qilib saqlaydi,
// keyingi safar mos kelmasa kirish rad etiladi. Tokenlar kabi
// localStorage'da — brauzer o'zgarsa yoki kesh tozalansa yangi ID
// generatsiya bo'ladi (bu ATAYLAB shunday: "boshqa qurilma" aynan shu
// orqali aniqlanadi).
export function qurilmaIdOl() {
  let id = localStorage.getItem("qurilma_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("qurilma_id", id);
  }
  return id;
}

// 2026-07-30 bug: PARALLEL_SAHIFA_SONI kabi bir vaqtda bir nechta so'rov
// ketganda, access token muddati tugagan payt HAMMASI bir vaqtda 401 oladi
// va har biri MUSTAQIL refresh chaqirardi — backendda ROTATE_REFRESH_TOKENS +
// BLACKLIST_AFTER_ROTATION yoqilgani uchun faqat BIRINCHI refresh muvaffaqiyatli
// bo'lardi (eski refresh-tokenni bloklab), qolganlari eski (endi bloklangan)
// token bilan urinib 401 olardi va foydalanuvchini beixtiyor logout qilardi.
// Shuning uchun bir vaqtdagi barcha 401'lar BITTA umumiy refresh-so'rovni
// kutadi (dedup) — parallel refresh chaqiruvi umuman bo'lmaydi.
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
      // 2026-08-14 BUG TUZATILDI (foydalanuvchi topib berdi: "mock test
      // vaqtida chiqib ketmasligi kerak"): backend ROTATE_REFRESH_TOKENS
      // yoqilgani uchun har yangilashda YANGI refresh token ham qaytaradi
      // va ESKISINI blacklist qiladi. Avval bu yerda faqat `access`
      // saqlanardi — eski (endi bekor qilingan) refresh token
      // localStorage'da qolib ketardi. Birinchi yangilanish (30 daqiqada)
      // muvaffaqiyatli o'tardi, lekin IKKINCHI marta (taxminan 60-daqiqada)
      // eski refresh token bilan urinib, majburan logout bo'lardi — aynan
      // uzoq davom etadigan Mock test kabi holatlarda. Endi yangi
      // `refresh`ni ham saqlaymiz.
      tokenlarniSaqla({ access: data.access, refresh: data.refresh });
      return true;
    } finally {
      refreshVadasi = null;
    }
  })();
  return refreshVadasi;
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
    tokenlarniTozala();
    window.location.href = "/login";
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

// Autentifikatsiyalangan fayl (masalan audio stream) — <audio src> to'g'ridan
// to'g'ri so'rov yubora olmaydi (Authorization header qo'shilmaydi), shuning
// uchun blob sifatida olib, vaqtinchalik object URL yaratamiz.
export async function apiBlobUrl(yol) {
  const sorov = () =>
    fetch(apiManzil(yol), {
      headers: tokenOl() ? { Authorization: `Bearer ${tokenOl()}` } : {},
    });

  let res = await sorov();
  if (res.status === 401 && (await refreshQil())) {
    res = await sorov();
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

// Autentifikatsiyalangan faylni brauzerga YUKLAB OLISH (masalan backup ZIP,
// 2026-08-15) — oddiy <a href> ishlamaydi (Authorization header kerak),
// shuning uchun blob qilib olib, vaqtinchalik <a download> orqali "Saqlash"
// dialogini ochamiz.
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
    tokenlarniTozala();
    window.location.href = "/login";
    throw new Error("401");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data?.detail || detail;
    } catch {
      // javob JSON emas (masalan muvaffaqiyatli fayl oqimi) — o'zgarishsiz
    }
    const e = new Error(detail);
    e.status = res.status;
    throw e;
  }

  // Fayl nomi. 2026-09-03: avval faqat `filename=` o'qilardi — u ASCII
  // bo'lishi shart, shuning uchun o'zbekcha/kirill nomlar pastki chiziqqa
  // aylanib ketardi. Endi avval RFC 5987 shakli (`filename*=UTF-8''...`)
  // tekshiriladi — server haqiqiy nomni aynan shu yerda yuboradi.
  const disposition = res.headers.get("Content-Disposition") || "";
  const utf8Mos = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  const oddiyMos = disposition.match(/filename="?([^";]+)"?/);
  let nomi = "yuklab-olindi";
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

// Fayl yuklash (masalan markaz logotipi) — Content-Type'ni brauzer o'zi
// (multipart boundary bilan) qo'yishi kerak, shuning uchun JSON.stringify
// qilinmaydi va header qo'lda belgilanmaydi.
export async function apiForm(yol, { method = "POST", formData } = {}) {
  const sorov = () =>
    fetch(apiManzil(yol), {
      method,
      headers: tokenOl() ? { Authorization: `Bearer ${tokenOl()}` } : {},
      body: formData,
    });

  let res = await sorov();
  if (res.status === 401 && (await refreshQil())) {
    res = await sorov();
  }
  if (res.status === 401) {
    tokenlarniTozala();
    window.location.href = "/login";
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
