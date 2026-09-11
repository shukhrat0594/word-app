// Rasmiy IELTS vaqt me'yorlari (soniyada). R/L/W taymerlarida bitta
// umumiy manba — bosilganda shu vaqtdan teskari sanoqqa o'tish uchun.
// Speaking bu yerda YO'Q: 2026-09-11 dan boshlab speaking'da taymer
// umuman ko'rsatilmaydi (rasmiy IELTS'da ham vaqtni imtihonchi
// boshqaradi), shuning uchun uning me'yori ham kerak emas.
export function standartVaqt(bolim, tur) {
  if (bolim === "reading") return 60 * 60;
  if (bolim === "listening") return 30 * 60;
  if (bolim === "writing") return tur === "task1" ? 20 * 60 : 40 * 60;
  return 60 * 60;
}
