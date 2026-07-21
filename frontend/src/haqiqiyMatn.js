// "Haqiqiy mashq" (talaba o'zi javob yozadigan/gapiradigan) rejimida savol
// matnidan faqat asl savolni (va Speaking Part2/3'da "Part 3 savollari"ni)
// qoldirib, o'quv-yordamchi bo'limlarni ("[Struktura]", "[Foydali iboralar]")
// olib tashlaydi — ular faqat "Namunaviy" (o'qish uchun) rejimida ko'rinadi.
// AI'ga yuboriladigan `savol_matni`ga tegilmaydi — bu FAQAT ko'rinish uchun.
const YORDAMCHI_SARLAVHALAR = ["struktura", "foydali iboralar"];

export function haqiqiyMatnniOl(matn) {
  if (!matn) return matn;
  const belgiIndex = matn.search(/\n\[[^\]]+\]\n/);
  if (belgiIndex === -1) return matn.trim();

  const asosiy = matn.slice(0, belgiIndex).trim();
  const qolgan = matn.slice(belgiIndex);

  const bolimlar = [...qolgan.matchAll(/\[([^\]]+)\]\n([\s\S]*?)(?=\n\[[^\]]+\]|$)/g)];
  const saqlanadigan = bolimlar
    .filter(([, sarlavha]) => !YORDAMCHI_SARLAVHALAR.includes(sarlavha.trim().toLowerCase()))
    .map(([butun]) => butun.trim());

  return [asosiy, ...saqlanadigan].filter(Boolean).join("\n\n");
}
