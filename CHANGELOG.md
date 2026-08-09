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

## 2026-08-09 — Ota-ona profili va profil rasmi

- **Ota-onaga farzand biriktirish** endi ilovadan qilinadi (avval faqat
  Django admin panelidan). Bitta ota-onaga bir nechta farzand
  biriktirsa bo'ladi, lekin bitta bola faqat bitta ota-onaga —
  boshqasiga biriktirilgan talaba ro'yxatda tanlanmaydigan bo'lib
  ko'rinadi.
- **Ota-ona endi farzandining barcha mashq natijalarini ko'radi** —
  Reading, Listening, Writing, Speaking va Kurslar bo'yicha, avvalgi
  umumiy statistikaga qo'shimcha. Boshqa bolaning natijasi ko'rinmaydi.
- **Profil rasmi** qo'shildi. Har kim o'z rasmini "Profil" sahifasidan
  qo'yadi yoki o'chiradi; owner va admin boshqa foydalanuvchilarnikini
  "Foydalanuvchilar" sahifasidan qo'ya oladi.

## 2026-08-08 — Writing baholash aniqligi

- **Writing baholash ancha adolatli bo'ldi.** Ilgari xatosiz, lekin
  oddiy tilda yozilgan insho eng yuqori ballni olardi — endi bunday
  ish o'z darajasiga yaqin baholanadi. Yuqori ball uchun til boyligi
  ham talab qilinadi.
- Baholash **20-30 barobar tezlashdi**: Task 1 tekshiruvi ilgari 2-4
  daqiqa ketardi, endi 15 soniyagacha.
- Writing tekshirishda vaqti-vaqti bilan chiqadigan "AI xizmatida
  kutilmagan xato" kamayadi — vaqtinchalik uzilishlarda tizim o'zi
  qayta uradi.

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
