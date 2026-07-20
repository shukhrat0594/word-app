// Rasmiy IELTS vaqt me'yorlari (soniyada). R/L/W/S taymerlarida bitta
// umumiy manba — bosilganda shu vaqtdan teskari sanoqqa o'tish uchun.
// Speaking'da rasmiy jamoat vaqti yo'q (imtihonchi boshqaradi) — taxminiy
// amaliy me'yor qo'yilgan.
export function standartVaqt(bolim, tur) {
  if (bolim === "reading") return 60 * 60;
  if (bolim === "listening") return 30 * 60;
  if (bolim === "writing") return tur === "task1" ? 20 * 60 : 40 * 60;
  if (bolim === "speaking") return { part1: 5 * 60, part2: 4 * 60, part3: 5 * 60 }[tur] || 5 * 60;
  return 60 * 60;
}
