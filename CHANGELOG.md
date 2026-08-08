# O'zgarishlar tarixi

Bu fayl **ilova ichidagi xabarnomaning manbasi**: har reliz uchun eng
yuqoridagi bo'lim owner'ga bildirishnoma bo'lib boradi
(`accounts.relizlar.relizlarni_sinxronla`).

Shuning uchun matn **odam tilida** yozilsin — commit sarlavhasi emas.
"Kurslarga PDF orqali mashq yuklash qo'shildi" ✓, emas
"Kurslar: rasm-fon rejimi (PDF/rasm/ZIP)" ✗.

Format (qat'iy, parser shunga tayanadi):

```
## <sana YYYY-MM-DD> — <qisqa sarlavha>

- band
- band
```

---

## 2026-08-08 — Kurslarga PDF yuklash va ota-ona roli

- Kurslar bo'limiga **PDF orqali mashq yuklash** qo'shildi. Darslik
  sahifasi rasm holida qoladi, javob yoziladigan joylarga kataklar
  ustidan qo'yiladi — kitobdagi ko'rinish buzilmaydi.
- Kataklar joyini AI emas, rasmning o'zi bo'yicha aniqlaydigan qilindi:
  javob chiziqchalari piksel aniqligida topiladi.
- Mashq kataklarini rasm ustida **sudrab tuzatish** imkoni qo'shildi:
  joyini o'zgartirish, yangi katak qo'shish, o'chirish, kenglikni
  sozlash.
- Bitta darslikning mashqlari endi **sahifa tartibida** joylashadi
  (avval turli sahifalardagi bir xil raqamli mashqlar aralashib
  ketardi).
- Sahifa pastidagi sahifa raqami va unit nomi endi mashq deb
  hisoblanmaydi.
- Bir xil audio ikki mashqqa yuklansa **ikkinchi nusxa saqlanmaydi** —
  qaysi mashqda borligi ko'rsatiladi.
- Owner'ga **hamma panellar** ko'rinadigan bo'ldi (avval Davomat,
  O'yinlar, Tarix, Reyting ko'rinmasdi).
- **Ota-ona roli** endi ilovadan tanlanadi (avval faqat Django admin
  panelidan qo'yish mumkin edi).
