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

async function refreshQil() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return false;
  const res = await fetch(apiManzil("/api/token/refresh/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  tokenlarniSaqla({ access: data.access });
  return true;
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
