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

## 2026-08-09 — Rollar va panel ruxsatlari

- **Foydalanuvchining roli endi faqat u YARATILAYOTGANDA tanlanadi va
  keyin o'zgarmaydi.** Bitta odamga ikki xil rol kerak bo'lsa — unga
  alohida profil ochib beriladi. Sabab: rol o'zgarganda unga bog'liq
  narsalar (masalan ota-ona bilan bog'lanish, ko'rinadigan panellar
  ro'yxati) mos kelmay qolardi. Qoida Django admin panelida ham amal
  qiladi.
- **"Panel ruxsati" ro'yxati endi foydalanuvchi roliga qarab chiqadi.**
  Avval hamma uchun bir xil 13 panel ko'rsatilardi — jumladan o'sha rol
  hech qachon ko'rmaydigan panellar ham. Masalan ota-onaga "Kurslar"ni
  belgilash mumkin edi, lekin ta'siri yo'q edi. Endi ro'yxatda faqat
  haqiqatan ishlaydigan panellar turadi, tugmada esa nechtadan
  belgilangani ko'rinadi ("5/6"). "Bosh sahifa" va "Profil" har doim
  ochiq — ular ro'yxatda yo'q.
- **Admin ham nomaqbul profil rasmini o'chira oladi** — "Talabalar" va
  "Xodimlar" bo'limlarida rasm ustiga bosib. Avval bu faqat owner
  ko'radigan "Foydalanuvchilar" sahifasida bor edi. Sabab yozish
  shartligi va rasm egasiga ogohlantirish borishi o'zgarmadi.
  O'qituvchiga bu imkoniyat berilmagan.
- **"Ko'rish rejimi"ga Ota-ona qo'shildi** — owner endi ota-ona nima
  ko'rishini ham sinab ko'ra oladi.
- "Foydalanuvchilar" sahifasi tezroq ochiladi — avval har bir
  foydalanuvchi uchun bazaga alohida murojaat ketardi.

## 2026-08-09 — Profil rasmi va bildirishnomalar

- **Chap menyu tepasida endi markaz nomi emas, sizning rasmingiz va
  ism-familiyangiz turadi.** Ustiga bosilsa to'g'ridan-to'g'ri o'z
  profilingiz ochiladi. Markaz nomi sahifa sarlavhasida qolgan.
- **Profil rasmini faqat egasi qo'ya oladi.** Ilgari owner va admin
  boshqa foydalanuvchiga rasm qo'yishi mumkin edi — bu olib tashlandi,
  rasm shaxsiy narsa.
- **Nomaqbul rasmni owner yoki admin o'chirib tashlashi mumkin, lekin
  sababini yozishi shart.** Sabab rasm egasiga "Ogohlantirish" xabari
  bo'lib boradi, ya'ni odam rasmi nega yo'qolganini biladi. Sababsiz
  o'chirib bo'lmaydi.
- **Bildirishnoma qo'ng'irog'i endi hamma foydalanuvchiga ko'rinadi** —
  avval faqat owner'da bor edi. Har kim faqat o'ziga kelgan xabarni
  ko'radi.
- Rasm yuklashda chegara qo'yildi: 2 MB gacha va haqiqatan rasm
  bo'lishi kerak. Rasm almashtirilganda eskisi serverdan o'chiriladi
  (avval yig'ilib qolardi).

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
