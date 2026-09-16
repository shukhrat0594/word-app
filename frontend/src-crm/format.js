// Ko'rsatish formatlari.
//
// Pul HAR DOIM shu yerdan o'tadi: ekranda "660000" va "660 000 so'm"
// aralashib ketsa, admin raqamlarni solishtira olmaydi.

/** 660000 -> "660 000". Manfiy son "-260 000" bo'lib chiqadi. */
export function pul(qiymat) {
  const son = Number(qiymat ?? 0);
  if (!Number.isFinite(son)) return "—";
  return son.toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

/** Balans uchun: musbat bo'lsa "+" bilan — oldindan to'langani ko'rinsin. */
export function balansMatn(qiymat) {
  const son = Number(qiymat ?? 0);
  return son > 0 ? `+${pul(son)}` : pul(son);
}

export function balansSinfi(qiymat) {
  const son = Number(qiymat ?? 0);
  if (son < 0) return "rang-qarzdor";
  if (son > 0) return "rang-oldindan";
  return "rang-tolandi";
}

/** "2026-09-11" -> "11.09.2026" */
export function sana(qiymat) {
  if (!qiymat) return "—";
  const [y, o, k] = String(qiymat).slice(0, 10).split("-");
  return `${k}.${o}.${y}`;
}

/** "2026-09-01" -> "2026-09" (oy tanlagich va sarlavhalar uchun) */
export function oyQiymati(qiymat) {
  return String(qiymat ?? "").slice(0, 7);
}

/** Joriy oy — "2026-09" */
export function joriyOy() {
  const b = new Date();
  return `${b.getFullYear()}-${String(b.getMonth() + 1).padStart(2, "0")}`;
}

/** Oldingi/keyingi oy: siljit("2026-09", -1) -> "2026-08" */
export function siljit(oy, qadam) {
  const [y, o] = oy.split("-").map(Number);
  const sana = new Date(y, o - 1 + qadam, 1);
  return `${sana.getFullYear()}-${String(sana.getMonth() + 1).padStart(2, "0")}`;
}

const OY_NOMLARI = {
  uz: ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
       "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"],
  ru: ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
  en: ["January", "February", "March", "April", "May", "June",
       "July", "August", "September", "October", "November", "December"],
};

export function oyNomi(oy, til = "uz") {
  const [y, o] = String(oy).split("-").map(Number);
  const nomlar = OY_NOMLARI[til] || OY_NOMLARI.uz;
  return `${nomlar[o - 1]} ${y}`;
}

/** ISO vaqt -> "16.09.2026 14:05" (SoffCRM'dagi "Yaratilgan vaqt" ustuni) */
export function vaqt(qiymat) {
  if (!qiymat) return "—";
  const d = new Date(qiymat);
  if (Number.isNaN(d.getTime())) return "—";
  // Mahalliy vaqt — `toISOString` UTC berib, yarim tundan keyingi
  // yozuvni oldingi kunga surib yuborardi.
  const ik = (n) => String(n).padStart(2, "0");
  return `${ik(d.getDate())}.${ik(d.getMonth() + 1)}.${d.getFullYear()} ${ik(d.getHours())}:${ik(d.getMinutes())}`;
}
