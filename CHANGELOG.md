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

## 2026-10-09 — Ota-onaga "darsga keldi" va test natijalari darhol boradi

- **"Darsga keldi" xabari.** Ota-ona endi farzandi darsga kelganini ham
  bilib turadi — xuddi "kelmadi" va "kechikdi" kabi, davomat belgilangandan
  5 daqiqa keyin. CRM → Ota-ona nazorati → Sozlamalar'da "Keldi" katagi bilan
  o'chirib qo'yish mumkin.
- **IELTS test, Writing/Speaking va Vocabulary natijasi — darhol.** Talaba
  IELTS Listening/Reading testini yechsa, Writing yoki Speaking'dan bahosi
  chiqsa yoki Kurslardagi Vocabulary mashqini bajarsa, ota-onaga 5–10 daqiqada
  alohida xabar boradi (band yoki foiz bilan). Vocabulary'ni bir necha marta
  tekshirsa — har unit uchun kuniga bitta xabar, oxirgi natija bilan.
- **Har biri uchun tanlov.** Sozlamalarda har natija turi uchun "Darhol",
  "Kunlik yig'mada" (kechki yig'ma xabarda) yoki "O'chiq" tanlanadi. Kunlik
  yig'maning kunlari va soati avvalgidek sozlanadi; Vocabulary yig'mada endi
  "Mashqlar"dan alohida qatorda ko'rinadi.

## 2026-10-08 — Ota-ona botiga IELTS to'liq test natijalari ham qo'shildi

- **Kunlik natijalar xabarida endi Listening va Reading ham bor.**
  Avval faqat bajargan mashqlar foizi va Writing/Speaking bahosi
  ko'rinardi — talaba IELTS to'liq testini (masalan Cambridge
  to'plamidan) topshirsa, uning Listening/Reading bandi ota-onaga
  bormasdi. Endi ular ham Writing/Speaking kabi alohida qator bilan
  ko'rsatiladi.

---

## 2026-10-05 — CRM: talaba kartasidan ota-ona hisobi ochish

- **Talaba kartasidagi "Ota-ona hisobi" bo'limida endi profil ochish
  mumkin.** Avval faqat ota-ona telefoni/ismi matn maydon sifatida
  saqlanardi — saytga kiradigan haqiqiy hisobni esa faqat owner
  "Foydalanuvchilar" sahifasidan yarata olardi.
- **Yangi profil** — ism va telefon kiritiladi, login/parol avtomatik
  yaratiladi (bir martalik ko'rsatiladi, yozib olish kerak).
- **Boshqa farzandga ulash** — bitta ota-onada bir nechta farzand
  bo'lishi mumkin: ikkinchi o'quvchini qidirib, birinchisining
  ota-ona hisobiga ulaysiz — ikkalasi ham bitta hisobdan kuzatiladi.

## 2026-10-05 — Ota-onalar uchun Telegram bot

- **Yangi Telegram bot — @UtmostParentsBot.** Ota-ona botga kirib telefon
  raqamini ulashadi va farzandiga avtomatik ulanadi (raqam CRM'dagi
  ota-ona telefoniga mos kelsa). Mos kelmasa, farzandning ism-familiyasi
  va tug'ilgan sanasini yozadi; aniqlab bo'lmasa, so'rov adminlarga
  boradi.
- **CRM → "Ota-ona nazorati" bo'limi:** ota-onalar so'rovlarini ulash yoki
  rad etish, ulangan ota-onalar ro'yxati (kerak bo'lsa uzish) va
  xabarlar sozlamasi — qaysi xabarlar, qaysi kunlari va soatda, tunda
  xabar yubormaslik vaqti.
- **Ota-onaga avtomatik xabarlar:** farzand darsga kelmasa, kechiksa
  (sababli kelmaganini ham yoqish mumkin); to'lov qabul qilinganda;
  qarzdorlik eslatmasi (standart — har dushanba 10:00 da); kunlik
  natijalar — bajargan mashqlari, Writing va Speaking bahosi
  (standart — har kuni 19:00 da, hech narsa qilmagan kuni xabar
  kelmaydi).
- Admin davomat yoki to'lovni adashib kiritib, bir necha daqiqa ichida
  tuzatsa, ota-onaga xato xabar bormaydi. Qarzni orada to'lab qo'ygan
  ota-onaga eslatma bormaydi.
- Qaysi xabarlar borishini faqat markaz hal qiladi — ota-ona ularni
  o'chira olmaydi. **Ota-ona botni bloklab qo'ysa, adminlarga 🔔
  bildirishnoma keladi**, CRM'dagi ro'yxatda esa u "Botni bloklagan"
  deb ko'rinadi — u bilan boshqa yo'l bilan bog'lanish mumkin.
- Saytdagi 🔔 bildirishnoma bosilganda kerakli sahifa ochiladi.

## 2026-09-29 — Lidlar: qora ro'yxat va arxiv tuzatildi

- **Qora ro'yxat har qanday filialda to'liq ko'rinadi.** Sarlavhada
  filial tanlangan bo'lsa ham (masalan Gor-Park) boshqa filialda qora
  ro'yxatga olingan lidlar chiqadi — avval "Qora ro'yxat (9)" deb turib,
  ro'yxat bo'sh ko'rinardi.
- **Guruhga qo'shilgan lidlar "Arxiv"da turmaydi.** "Arxiv"da endi faqat
  rad etilgan lidlar; sinov darsiga yoki guruhga qo'shilganlari yangi
  "O'quvchi bo'lganlar" ko'rinishida. O'quvchining o'zi esa "Talabalar"da.
- Boshqa doska yoki filial ustunidagi lid arxiv / qora ro'yxat
  ko'rinishida endi "Yangi lidlar" ustunida chiqadi, yo'qolib qolmaydi.

## 2026-09-28 — Qarzdorlik, davomat va o'quvchi natijalari

- **Davomat katagi bosilganda variantlar chiqadi:** keldi, kechikdi,
  kelmadi, sababli yoki tozalash — avvalgidek bir necha marta bosib
  kerakli belgiga yetish shart emas. "Kechikdi" kelganlar soniga
  kiradi. O'quvchi kartasidagi taqvimda ham xuddi shunday.
- **Guruh davomatida "Arxivdagi o'quvchilar"** tugmasi — guruhdan
  chiqqan o'quvchining o'sha oydagi davomatini ko'rish mumkin (faqat
  ko'rish uchun).
- Guruh a'zolari, davomat va baholar jadvallarida **tartib raqami (№)**.
- **General kursdagi o'quvchi kartasida har bir Unit bo'yicha uy
  vazifasi:** nechta mashq bajarilgani, necha foizi to'g'ri va necha
  foizi noto'g'ri, Unit o'tilganmi.
- **Bosh sahifada "To'lov qo'shish" tugmasi.** "To'lovi yaqin"
  kartochkasi olib tashlandi.
- **Qora ro'yxatdagi o'quvchilar Lidlar → "Qora ro'yxat"da ham
  ko'rinadi** — hamma filial administratorlariga.
- O'quvchi kartasidagi "Sayt holati" endi to'g'ri: saytda mashq
  qilayotgan o'quvchi "Saytga kirgan" bo'lib ko'rinadi.

- **Bosh sahifadagi "Qarzdorlar" va "Qolgan qarzlar" endi Talabalar →
  "Qarzdorlar" ro'yxati bilan doim bir xil.** Qarzdor — balansi minusda
  bo'lgan o'quvchi. Avval bir oyga ortiqcha to'langan pul boshqa oy
  qarzini yopmasdi va bosh sahifa qarzdor ko'rsatsa ham ro'yxat bo'sh
  chiqardi.
- Guruhdan chiqqan yoki arxivlangan, lekin qarzi qolgan o'quvchi ham
  "Qarzdorlar" ro'yxatida chiqadi ("arxiv" belgisi bilan).
- **Filial tanlangan bo'lsa**, balans va qarzdorlik faqat shu filialning
  hisob va to'lovlari bo'yicha hisoblanadi.
- **Balans ko'rinishi:** qarzdor bo'lsa minus bilan qizil rangda,
  ortiqcha to'lagan bo'lsa yashil rangda (belgisiz).

## 2026-09-26 — CRM'da yangi kurs qo'shish

- **"Narxlar" sahifasida "Kurs qo'shish" tugmasi.** Fanni tanlaysiz (yoki
  yangi fan nomini yozasiz), kurs nomi va oylik narxini kiritasiz —
  kurs darhol narxlar ro'yxatida va guruh yaratish oynasidagi "Kurs"
  ro'yxatida paydo bo'ladi.
- Kurs saytdagi "Kurslar" bo'limiga ham qo'shiladi va darslari
  qo'shilguncha u yerda "tez orada" bo'lib turadi.
- **Kursni tahrirlash va o'chirish.** Har kurs qatorida "Tahrirlash"
  (nomini tuzatish) va "O'chirish" tugmalari bor. O'chirishdan oldin
  tasdiqlash so'raladi. Faqat bo'sh va hech qaysi guruhda ishlatilmagan
  kursni o'chirish mumkin — ichida darslari bor (Beginner, IELTS kabi)
  yoki guruhi bor kursda tugma yopiq: aks holda darslar va o'quvchi
  natijalari ham o'chib ketardi.

## 2026-09-25 — O'chirilgan foydalanuvchini 7 kun ichida tiklash mumkin

- **Foydalanuvchi o'chirilganda darhol yo'qolib ketmaydi.** U saytga kira
  olmaydi va hamma ro'yxatdan chiqadi, lekin 7 kun davomida
  "Foydalanuvchilar → O'chirilganlar" bo'limida turadi. "Tiklash"
  bosilsa hammasi bilan birga qaytadi: guruhlari, davomati, natijalari,
  XP'si, CRM'dagi to'lovlari va paroli ham. 7 kun o'tgach butunlay
  o'chadi (muddatni kutmasdan "Butunlay o'chirish" ham mumkin).
- **O'chirish tugmasi endi ogohlantiradi**: nima yo'qolishini, 7 kun
  ichida tiklash mumkinligini aytadi va ketgan o'quvchini o'chirish
  o'rniga CRM'da arxivlashni maslahat beradi.
- O'chirilgan administratorni faqat owner ko'radi va tiklaydi.
- **CRM o'quvchisi saytdan o'chirilmaydi.** Uning uchun "O'chirish"
  faqat saytga kirishini yopadi (paroli olib tashlanadi, ochiq
  seanslari yopiladi) — guruhlari, to'lovlari va tarixi CRM'da qoladi.
  Kirishni qayta ochish uchun "Parol o'rnatish" bilan yangi parol
  berasiz. Oynada buni oldindan ko'rasiz: "Saytga kirishni yopish".

## 2026-09-25 — CRM: qarzni tuzatish, eslatma xabarnomalari

- **Qarzni tuzatish mumkin.** O'quvchi kartasidagi "To'lov tarixi"da
  qarz qatorida "Tahrirlash" tugmasi bor: summani o'zgartirib, izoh
  yozasiz ("sentabr oyida 7 ta dars uchun"). Izoh majburiy va to'lov
  tarixida ko'rinib turadi. Bu "Qarzdorlik yozuvlari" ruxsati bor
  xodimlarga (administrator) ochiq.
- **Eslatmalar xabarnoma bo'lib chiqadi.** Sarlavhada 🔔 qo'ng'iroqcha —
  vaqti kelgan eslatmalar soni bilan. Bosganda ro'yxat ochiladi: "Lidga
  o'tish" o'sha lid kartasini ochadi, "Bajarildi" eslatmani ro'yxatdan
  olib tashlaydi. Bosh sahifadagi "Vaqti kelgan eslatmalar"da ham shu
  tugmalar bor.
- **Guruhdagi o'quvchi ismini bosib** uning kartasiga o'tasiz.
- **Bosh sahifa soddalashdi**: "Qarzdorlar" ro'yxati (u "Qarzdorlar"
  kartochkasidan ochiladi) va "Ogohlantirishlar" bloki olib tashlandi —
  boshqa guruhga ko'chirilgan o'quvchini "saytda guruhdan chiqarilgan"
  deb ko'rsatib adashtirardi. Sozlanmagan guruhlar haqidagi eslatma endi
  Guruhlar sahifasining tepasida.

## 2026-09-25 — CRM: guruh sahifasi, ketish sabablari va hisoboti

- **Har guruhning o'z sahifasi bor.** Dars jadvalidagi guruh bosilganda
  endi alohida sahifa ochiladi: chapda guruh ma'lumoti (kurs, dars
  kunlari, xona, o'qituvchi, narx), o'ngda davomat oylar bo'yicha,
  pastda o'quvchilar ro'yxati. Guruhlar ro'yxatida guruh nomini bosib
  ham shu sahifaga o'tiladi.
- **O'quvchi ustida ⋮ tugmasi**: to'lov qabul qilish, boshqa guruhga
  ko'chirish, guruhdan chiqarish, "Bitirdi" va "Lidlarga qaytarish".
  Xuddi shu menyu o'quvchi kartasidagi har guruhda ham bor.
- **Guruhdan chiqarishda sabab so'raladi** (narx, natija, o'qituvchi,
  dars jadvali, joylashuv yoki boshqa) va izoh yoziladi. Muzlatishda esa
  sana va izoh so'raladi.
- **O'quvchini arxivlashda ham sabab so'raladi** va u barcha
  guruhlaridan shu sabab bilan chiqariladi — endi arxivdagi o'quvchiga
  to'lov hisoblanmaydi va u "Ketish hisoboti"da ko'rinadi. Arxivdan
  chiqarilganda guruhga o'zi qaytmaydi, uni kerakli guruhga qo'shasiz.
- **"Ketish hisoboti"** (Hisobotlar → Ketganlar): nechta o'quvchi
  ketgani, ketish foizi, yo'qotilgan daromad, o'rtacha necha oy o'qigani,
  kunlar bo'yicha grafik, asosiy sabablar, boshqa guruhga o'tganlar va
  chegirmaning ta'siri. Pastda ketganlar ro'yxati kurs, guruh, o'qituvchi
  va sabab bo'yicha filtr bilan. Kursni bitirgan va boshqa guruhga
  o'tgan o'quvchi "ketgan" hisoblanmaydi.
- **Bosh sahifadagi kartochkalar kerakli ro'yxatni darhol ochadi**:
  "Qarzdorlar" — faqat qarzdor o'quvchilar, "Sinov darsida" —
  sinovdagilar, "Muzlatilgan" — muzlatilganlar, "Shu oy ketganlar" —
  ketish hisoboti.
- **Lidni arxivlash yoki qora ro'yxatga olishda sabab so'raladi**
  ("Kelaman deb kelmadi", "Raqobatchiga ketdi", "Boshqa filialga
  yuborildi" yoki o'z izohingiz). Endi bir bosishda tasodifan qora
  ro'yxatga tushib qolmaydi. Lid tarixida "Arxivlandi — sabab" deb
  aniq yoziladi.
- **Lidni o'chirib bo'lmaydi** — SoffCRM'dagidek faqat sabab bilan
  arxivlanadi, kerak bo'lsa arxivdan qaytariladi. Shunda lid qayerdan
  kelgani va nega ketgani yo'qolmaydi.
- **Saytda ochilgan, CRM'da sozlanmagan guruhlar** endi Guruhlar
  ro'yxatida ham ko'rinadi ("Faqat sozlanmaganlar" belgisi bilan
  ajratish mumkin). Bosh sahifadagi ogohlantirishdagi guruh nomini bosib,
  darhol sozlashga o'tasiz.

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
- **Qora ro'yxat (lidlar va o'quvchilar) hamma filialga ko'rinadi** —
  bir filialda qora ro'yxatga olingan mijoz boshqasida qayta yozilmasin.
  Boshqa filialning lidi yoki o'quvchisini faqat ko'rish mumkin,
  o'zgartirish o'sha filialda.
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
