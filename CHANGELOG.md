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

## 2026-09-23 — CRM endi o'quv markazining asosiy boshqaruv joyi

- **O'quvchilar, guruhlar va xodimlar endi CRM'da qo'shiladi.** Saytda
  (admin va owner menyusida) "Guruhlar" va "Xodimlar" yo'q — ular CRM'ga
  ko'chdi; "Talabalar" saytga xos amallar (qurilma, panellar) uchun qoldi.
  Saytda mashqlar qoladi, o'qituvchi esa o'z guruhlarini va davomatni
  avvalgidek saytda ko'radi.
- **Lidlar bo'limi qo'shildi.** Kelgan so'rovlar kanban ustunlarida
  turadi ("Yangi lidlar", "Beginner", "Rus tili"... — ustunlarni o'zingiz
  yaratasiz), kartochkani sichqoncha bilan boshqa ustunga sudrash
  mumkin. Har lidda qayerdan kelgani, qulay vaqti, izohlar, eslatma va
  o'zgarishlar tarixi bor. "Guruhga qo'shish" tugmasi liddan o'quvchi
  yaratadi va sayt uchun login-parol beradi.
- **Yangi o'quvchi qo'shish** — CRM'ning "Talabalar" bo'limida. Login va
  parol bo'sh qoldirilsa, o'zi yaratiladi va bir marta ko'rsatiladi.
  O'quvchini qora ro'yxatga olish, arxivlash, parolini tiklash va
  beyjigini chop etish ham shu yerda.
- **Guruh qo'shish CRM'da**: kurs, filial, toq/juft kunlar (har kunga
  alohida vaqt va xona), 3 tagacha o'qituvchi — har biriga foizda yoki
  "har dars uchun" haq. Xona band bo'lsa, guruh saqlanmaydi va sababi
  aytiladi.
- **Guruh ichida**: davomatni CRM'dan belgilash (keldi / kelmadi /
  sababli), darsni boshqa kunga ko'chirish yoki qo'shimcha dars, baholar
  (1–5, 1–10 yoki 100 ball), muddatli chegirmalar ("3 oy 400 000",
  "1 oy tekin"), guruhdan chiqarish.
- **Xodimlar va rollar**: xodim kartasida filial, oylik, foiz ulushi,
  ishga olingan sana. Kassir, marketolog va boshqa rollar CRM'ga faqat
  o'ziga ruxsat berilgan bo'limlar bilan kiradi. "Yangi rol yaratish"da
  har bir bo'lim va amal alohida belgilanadi.
- **Bosh sahifa**: 12 ta ko'rsatkich (faol lidlar, qarzdorlar, sinov
  darsidagilar, to'lovi yaqinlar va h.k.) va "Markaz foydaliligi".
  Raqamlar boshida yashirin turadi — "Raqamlarni ko'rish" tugmasi bilan
  ochiladi. Vaqti kelgan eslatmalaringiz ham shu yerda chiqadi.
- **To'lovda usul tanlanadi**: naqd, karta, Click, Payme, yagona QR-kod,
  o'tkazma yoki voucher.
- **Lidlar bo'limlarga (doskalarga) ajraladi** ("LEADS", "LEADS uzb"...),
  har birining o'z ustunlari bor; ustunni guruhga bog'lash mumkin.
  Lidda "harorat" (issiq/iliq/sovuq), yoshi va "Bog'lana olmadi" holati
  bor. Lidlar, o'quvchilar, guruhlar, xodimlar va davomat Excel'ga
  yuklab olinadi; o'quvchilarni Excel orqali qo'shish mumkin.
- **Guruhda**: dars mavzulari, "hammasi keldi" tugmasi, sinovdagilarni
  bir bosishda faollashtirish, guruhdan chiqqanlar ro'yxati (sababi
  bilan). Chegirma summada yoki foizda beriladi, "0 oy" — doimiy.
- **O'quvchi kartasida**: saytga kirgan-kirmagani, ota-ona hisobi,
  o'rtacha baho va o'quvchi tarixi. Qarzdorlikni izoh bilan tuzatish
  mumkin (faqat owner).
- **Yangi hisobotlar**: to'lovlar (usul va kun bo'yicha), lidlar (manba
  va konversiya), ketgan o'quvchilar, bitiruvchilar. Xodimlar davomati
  va "Harakatlar tarixi" (kim, qachon, nimani o'zgartirdi) qo'shildi.
- **Lid kartochkasida "⋯" menyu**: eslatma, boshqa filial yoki bo'limga
  ko'chirish, guruhga yoki **yig'ilayotgan guruhga** qo'shish (lid
  navbatda turadi, to'lov ochilmaydi). Bosh sahifadagi "Yangi guruhga
  qabul" shularni sanaydi.
- **O'quvchi kartasidagi dars taqvimida** davomat va baho ham ko'rinadi,
  katakni bosib davomat belgilanadi (o'ng tugma — sababli), oylar
  bo'yicha o'tish mumkin. O'quvchilar ro'yxatida "Baho" va "Keyingi
  to'lov" ustunlari. Dars jadvalida kurs, o'quvchilar soni va xona
  sig'imi ko'rinadi; bosh sahifada moliya oyini tanlash mumkin.
- **Lavozim rollarini ham tahrirlash mumkin.** Xodimlar sahifasidagi
  "Rollar" jadvalida endi Administrator, Kassir, Marketolog, Kuzatuvchi,
  O'qituvchi va boshqa lavozimlar ham turadi — ✎ bosib, ular qaysi
  bo'lim va amallarni ko'rishini belgilaysiz.
- **Ruxsatlar qat'iylashdi.** Rolni faqat "Rollar" ruxsati borlar
  tahrirlaydi va xodimga beradi; hech kim o'z rolini o'zi o'zgartira
  olmaydi; boshqa xodimning parolini faqat administrator tiklaydi.
  Administratorga cheklangan rol berilsa, cheklov endi ishlaydi.
- **Pul himoyasi**: o'tgan oylar uchun chegirmani faqat owner beradi;
  owner qo'lda tuzatgan qarz summasi chegirma yoki muzlatishda qayta
  hisoblanib ketmaydi. Oyligini ko'rmaydigan xodim tahrirlaganda oylik
  endi 0 ga tushib qolmaydi.
- **Darsni ko'chirganda** davomat, mavzu va baholar ham yangi kunga
  ko'chadi; o'tgan kunga, darsi bor kunga yoki guruh tugaganidan keyinga
  ko'chirib bo'lmaydi.
- Talabalar ro'yxatida "Arxivdagilar" filtri — arxivlangan o'quvchini
  shu yerdan qaytarish mumkin. Marketolog lidni guruhga qo'sha oladi.
  Saytda admin menyusiga "Talabalar" qaytdi (qurilma tiklash, panellar).
- Guruh a'zolari jadvalida **"Boshlanish uniti"** — o'quvchi saytdagi
  Kurslar bo'limida qaysi Unit'dan boshlashini CRM'dan tanlaysiz.
- **Faqat CRM xodimlari** (kassir, marketolog, kuzatuvchi va h.k.) saytga
  kirsa, menyuda faqat Bosh sahifa va Profil ko'rinadi — mashqlar,
  o'yinlar va reyting ko'rinmaydi.
- **Xodimni filial(lar)ga biriktirish.** Xodim kartasida bir nechta
  filialni belgilash mumkin. Filial biriktirilgan administrator, kassir
  va boshqa xodimlar CRM'da faqat o'z filiallarining guruhlari,
  o'quvchilari, lidlari, to'lovlari va hisobotlarini ko'radi. Filial
  biriktirilmagan xodim hozircha hamma filialni ko'radi. Guruhsiz
  o'quvchi va filiali belgilanmagan lid hammaga ko'rinadi.
- **Lidlarning qora ro'yxati hamma filialga ko'rinadi** — bir filialda
  qora ro'yxatga olingan mijoz boshqasida qayta yozilmasin. Boshqa
  filialning lidini faqat ko'rish mumkin, o'zgartirish o'sha filialda.
- **Lid doskalari filialga bog'lanadi**: filial xodimi o'z filiali
  doskalarini va umumiy doskalarni ko'radi. Umumiy doska va ustunni
  faqat filialga bog'lanmagan xodim o'zgartiradi yoki o'chiradi.
- Ikki filialda o'qiydigan o'quvchining kartasida balans umumiy
  ko'rinadi va yonida "boshqa filialda ham hisobi bor" belgisi chiqadi;
  boshqa filialning to'lovlari esa ko'rinmaydi.
- **Xodim qo'shish va lavozimni o'zgartirish** — faqat owner yoki
  administrator. Administrator o'z ismi, telefoni va parolini o'zi
  o'zgartira oladi (lavozim, filial va oylikni — yo'q).
- O'quvchining narxi va sanalarini guruhni tahrirlash ruxsati bor xodim
  o'zgartiradi; holatini (sinov/faol/muzlatish) guruhga o'quvchi
  qo'shadigan xodim ham o'zgartira oladi.
- Owner qo'lda belgilagan oyga chegirma tegmaydi — endi bu haqda
  ogohlantirish chiqadi.
- **Owner CRM'da CEO** — unga hech qanday cheklov yo'q. CEO lavozimi
  endi boshqa xodimga berilmaydi. Kurs narxlari va filiallar ro'yxatini
  filialga biriktirilgan xodim faqat ko'radi.

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
