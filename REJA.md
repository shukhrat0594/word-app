# LMS + AI Platform — Umumiy reja (yakuniy)

**Loyiha:** Ingliz tili o'quv markazi uchun LMS platforma, AI Writing/Speaking integratsiyasi bilan
**TZ:** `C:\Users\Shuk\Desktop\LMS_TZ_yangilangan.docx`
**Jamoa:** Shuxrat + Claude (tashqi dasturchisiz)
**Loyiha joyi:** `D:\shuk\Проекты\claude ai\LMS`

---

## 0-bosqich: Tayyorgarlik (1 hafta)

- [x] TZ tayyor (`LMS_TZ_yangilangan.docx`)
- [x] Claude API kalit olindi, $5 kredit qo'shildi
- [x] Writing AI sinovdan o'tkazildi (ishlayapti)
- [ ] Contabo Cloud VPS 20 (1 oylik) sotib olish
- [ ] Domen nomi tanlash/sotib olish
- [x] Git repository — mavjud `https://github.com/shukhrat0594/word-app` qayta ishlatiladi (B1'da tozalanadi va LMS kodi push qilinadi)
- [x] Jamoa aniqlandi — tashqi dasturchisiz, Shuxrat + Claude

## 1. Texnik stack

| Qism | Yechim |
|---|---|
| Backend | Django |
| Baza | PostgreSQL |
| Frontend | React |
| Video | YouTube (unlisted) |
| Bildirishnoma | Telegram Bot API (keyingi fazaga o'tkazildi) |
| Writing AI | Claude Haiku 4.5 (arzon) + Claude Sonnet 5 (kuchli) — ikkala tarif |
| Speaking AI | Azure Speech (talaffuz) + ixtiyoriy Claude qo'shimchasi (mazmun/til sifati) |
| Hosting | Contabo Cloud VPS 20 — 1 oylik (test) → keyin 6/12 oy + Auto Backup |

## 2. Biznes model

### AI xarajatni ajratish
- **Hamkor o'quv markazi talabalari** — bepul, markaz o'z API kalitini kiritadi, o'zi to'laydi. **Markaz tanlaydi: Claude yoki Gemini** (2026-07-15 qo'shildi) — markaz sozlamalarida provayder tanlanadi, mos kalit kiritiladi
- **Individual pullik foydalanuvchilar** — platforma o'z API kalitidan foydalanadi (asosiy: Gemini 3.1 Flash Lite, quyidagi tahlilga asosan)
- Har biri uchun alohida API kalit — sarfni ajratib kuzatish uchun
- Backend **provider-agnostic** qilib quriladi (`AIProvider` interfeysi) — Claude va Gemini bir xil interfeys ortida, markaz/platforma xohlagan providerni tanlaydi

### AI Provider tanlovi — sinov natijalari (2026-07-15)

5 ta model Writing AI vazifasida (bir xil insho, bir xil mezonlar) sinovdan o'tkazildi:

| Model | Overall Band | Xatolar topildi | So'z kamligini payqadi | JSON | Bepul limit/kun |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 6.0 | 11 | ❌ | ✅ | — (pullik) |
| Gemini 3.5 Flash | 5.5 | 9 | ✅ | ✅ | 20 |
| Gemini 3 Flash Preview | 5.0 | 10 | ✅ | ✅ | 20 |
| Gemini 3.1 Flash Lite (eski prompt) | 6.5 | 6 | ❌ | ✅ | 500 |
| **Gemini 3.1 Flash Lite (yaxshilangan prompt)** | 5.5 | **15** | ✅ | ✅ | **500** |
| Gemma 4 26B | 5.5 | — (javob uzildi) | ❌ | ❌ | ? |

**Muhim topilma — prompt sifati modelni "kuchaytiradi":** Gemini 3.1 Flash Lite'ga (1) so'z sonini sanashni majburiy qilib, IELTS 250-so'z jarimasini aniq tushuntirib, (2) xatolarni to'liq (birortasini tashlab ketmasdan) sanashni so'rab prompt yaxshilanganda — natija 6 ta xatodan **15 ta xatoga** (barcha modellardan ko'p!) va so'z sonini to'g'ri payqashga o'tdi. Bu — eng arzon/saxiy limitli (500/kun bepul) modelni eng sifatli natijaga olib chiqdi.

**Yakuniy tanlov:** dev va asosiy ishlatish uchun **Gemini 3.1 Flash Lite + v4 prompt**. Bu prompt barcha providerlar uchun standart bo'ladi (Claude'da ham sifatni oshiradi).

**Prompt evolyutsiyasi (v1→v4):**
- v1: oddiy baholash — so'z sonini/uzunlik jarimasini payqamadi
- v2: so'z sanash majburiy + xatolarni to'liq sanash talabi qo'shildi — 6→15 xato, so'z jarimasi to'g'ri ishladi
- v3: band tavsiflari + `analysis` (fikrlash zanjiri) + `strengths` + o'z-o'zini tekshirish qo'shildi — lekin xato formati chalkashib, token narxi 2x oshdi
- **v4 (yakuniy):** v2'ning aniq "xato -> to'g'risi (sabab)" formati + v3'ning `analysis`/`strengths` foydali qo'shimchalari birlashtirildi, band tavsiflari qisqartirildi (token tejash)

**Bilib qo'yilgan model chegarasi:** Lite model **qo'shma egalarni** (compound subject, masalan "smartphones and internet") grammatik tahlilda to'liq to'g'ri tushunmasligi va bir xil turdagi xatoni matnning turli joylarida alohida-alohida (joyini ko'rsatib) ajrata olmasligi — v2/v3/v4'ning barchasida takrorlandi, bu **prompt emas, modelning tahlil chuqurligi chegarasi**. Shu sababli **Chuqurroq tahlil (kuchli model)** tarifi mavjud — nozik grammatik holatlar uchun.

### Writing AI — ikki tarif (yakuniy, 2026-07-15 nomlash bilan tasdiqlangan)
| Tarif nomi | Model | Narx | Taxminiy xarajat | Marja |
|---|---|---|---|---|
| **Tezkor tahlil** | Claude Haiku 4.5 | 500 so'm | ~39 so'm | ~92% |
| **Chuqurroq tahlil** | Claude Sonnet 5 | 1000 so'm | ~77 so'm | ~92% |

### Speaking AI — uch tarif (yakuniy, 2026-07-14 tasdiqlangan)

Standart Speaking javob davomiyligi: **2 daqiqa** audio.

| Tarif nomi | Tarkib | Narx | Taxminiy xarajat | Marja | Izoh |
|---|---|---|---|---|---|
| **Matn rejimi** | Faqat Claude Haiku (talaba matn kiritadi, audio yo'q) | **500 so'm** | ~34 so'm | ~93% | Talaffuz baholanmaydi — faqat mazmun/grammatika/lug'at. Mikrofonsiz mashq uchun |
| **Tezkor tahlil** | Azure (talaffuz/ravonlik/urg'u) + Claude Haiku (mazmun) | **900 so'm** | ~557 so'm | ~38% | To'liq audio-asoslangan baho |
| **Chuqurroq tahlil** | Azure + Claude Sonnet 5 | **1200 so'm** | ~590 so'm | ~51% | Eng chuqur tahlil |

*(2026-07-15: "Tezkor tahlil" narxi 800→900 so'm ga o'zgartirildi va marja qayta hisoblandi — avvalgi "~44%" xato edi, foyda narxga emas xarajatga nisbatan hisoblangan ekan; to'g'ri formula — foyda/narx.)*

> **Muhim:** Azure yolg'iz (talaffuzsiz Claude'siz) tarif **taklif qilinmaydi** — chunki IELTS Speaking 4 mezondan iborat (Fluency&Coherence, Lexical Resource, Grammatical Range, Pronunciation), Azure faqat Pronunciation va Fluency'ning "yetkazish" qismini biladi, qolganini (Coherence, Lexical, Grammar) bilmaydi. Shuning uchun Speaking baho har doim Azure+Claude combo bo'lishi kerak (Matn rejimi bundan mustasno — u alohida, talaffuzsiz mashq vositasi).

### Listening/Reading — mashq turlari va kunlik bepul limit (yangilangan, 2026-07-15)

**Qoida:** har bir mashq **turidan** kuniga **1 tadan bepul** (tur soniga qarab umumiy son o'zgaradi — quyida 5 tur bilan misol).

**Listening — 5 tur:** Multiple Choice, Fill in the Blanks, Matching, True/False/Not Given, Short Answer
**Reading — 5 tur:** Multiple Choice, Fill in the Blanks, Matching Headings, True/False/Not Given, Short Answer

| | Bepul (kuniga) | Limit tugagach |
|---|---|---|
| Listening (5 tur × 1) | **5 ta** | 500 so'm = yana har turdan 1 tadan, **+5 ta** |
| Reading (5 tur × 1) | **5 ta** | 500 so'm = yana har turdan 1 tadan, **+5 ta** |

*Narx/mashq o'zgarmadi (100 so'm/mashq) — faqat "quti hajmi" 2 tadan → 1 tadan kichraydi, narx mutanosib ravishda 1000→500 so'm bo'ladi.*

*Bu — Writing/Speaking'dan farqli: bu yerda AI xarajati yo'q (avtomatik test, to'g'ri/noto'g'ri tekshiruv), shuning uchun 500 so'm deyarli **sof foyda** (server xarajati e'tiborga olinmaydigan darajada kichik). Bu narx — xarajatni qoplash emas, balki foydalanish limitini boshqarish/monetizatsiya usuli.*

*Backend'da qoida moslashuvchan qilib qurilishi kerak — "har tur × 1" formulasi, mashq turlari soni kelajakda o'zgarsa (ko'paysa/kamaysa) ham avtomatik moslashishi uchun (qattiq kodlangan "5" raqami emas).*

**Xarajat manbalari:** Claude — platform.claude.com rasmiy narxi; Azure — azure.microsoft.com rasmiy narxi (Speech-to-Text $1/soat + Pronunciation Assessment prosody $0.30/soat); Kurs — CBU rasmiy kursi 1 USD = 12,065.49 so'm, 1 EUR = 13,754.66 so'm (15.07.2026).

### "IELTS Boost" Paket — 10,000 so'm, 7 kun amal qiladi (yakuniy, 2026-07-14 tasdiqlangan)

**Tarkibi (2026-07-15 yangilangan — fixed taqsimot o'rniga erkin tanlov):**
- 10 ta Reading (5 tur × 2 — MC, Fill in blanks, Matching Headings, T/F/NG, Short Answer)
- 10 ta Listening (5 tur × 2 — MC, Fill in blanks, Matching, T/F/NG, Short Answer)
- **5 ta** Speaking — **Chuqurroq tahlil** (Azure+Sonnet). Talaba har safar Part 1, 2 yoki 3'dan qaysi birini xohlasa, o'shani tanlab yuboradi (B8.1 qoidasi — fixed taqsimot yo'q)
- **5 ta** Writing — **Chuqurroq tahlil** (Sonnet). Talaba har safar Task 1 yoki Task 2'dan qaysi birini xohlasa, o'shani tanlab yuboradi

**Muhim:** paket davomida (7 kun) talabaning **kunlik bepul Reading/Listening limiti** (5 tur × 1 = 5+5/kun) ham **parallel ravishda davom etadi** — paket bunga qo'shimcha, uni almashtirmaydi.

| | Summa |
|---|---|
| Alohida sotilsa (jami qiymat) | 13,000 so'm |
| **Paket narxi** | **10,000 so'm** |
| Talaba tejaydi | 3,000 so'm (~23% chegirma) |
| Bizning xarajatimiz (Azure+Claude, faqat Speaking+Writing — L/R bepul) | 3,335 so'm |
| **Bizning sof foydamiz** | **6,665 so'm** |
| **Marja** | **~66.7%** |

**Muddat asoslanishi (2026-07-15 yangilangan — Speaking/Writing 5+5ga o'zgargani va L/R kunlik bepul limit 5+5ga tushirilgani hisobga olindi):** faqat paket mashqlari (30 ta: R100+L80+S75+W175 daqiqa) — ~430 daqiqa (~7.2 soat), 7 kunga taqsimlansa ~61 daq/kun. Agar talaba kunlik bepul L/R'ni ham to'liq ishlatsa (~1.5 soat/kun) — jami ~17.7 soat/7 kun (~2.5 soat/kun). 7 kun 5 kunga nisbatan yukni yengillashtiradi va paketning ishlatilmay qolish xavfini kamaytiradi.

### "Arzon Paket" — 5,000 so'm, 5 kun amal qiladi (yakuniy, 2026-07-14 tasdiqlangan)

Premium ("IELTS Boost") paketning kirish darajasidagi (entry-level) versiyasi — arzonroq tariflar bilan.

**Tarkibi:**
- 15 ta Reading (5 tur × 3)
- 15 ta Listening (5 tur × 3)
- 3 ta Writing — **Chuqurroq tahlil** (Sonnet). **Talaba har safar Task 1 yoki Task 2'dan qaysi birini xohlasa, o'shani tanlab yuboradi** (fixed taqsimot yo'q, erkin tanlov)
- 3 ta Speaking — **Matn rejimi** (Haiku, audio yo'q). **Talaba har safar Part 1, 2 yoki 3'dan qaysi birini xohlasa, o'shani tanlab yuboradi**

**Muhim:** paket davomida (5 kun) talabaning kunlik bepul Reading/Listening limiti ham parallel davom etadi.

| | Summa |
|---|---|
| Alohida sotilsa (jami qiymat, R/L 1.5× standart top-up narxida hisoblangan) | 7,500 so'm |
| **Paket narxi** | **5,000 so'm** |
| Talaba tejaydi | 2,500 so'm (~33% chegirma) |
| Bizning xarajatimiz (Writing Sonnet + Speaking Matn/Haiku, R/L bepul) | 333 so'm |
| **Bizning sof foydamiz** | **4,667 so'm** |
| **Marja** | **~93.3%** |

**Muddat asoslanishi:** jami ~36 ta mashq, ~6.5 soat vaqt (Reading ~150 daq, Listening ~120 daq, Writing ~90 daq, Speaking-matn ~30 daq), 5 kunga taqsimlansa ~78 daqiqa/kun.

### Daromad/foyda misoli — 50 pullik talaba, 1 oy (yakuniy, 2026-07-14 tasdiqlangan)

**Taxminlar (1 talaba/oyiga):** Writing 12 ta (70% Haiku / 30% Sonnet = 8.4/3.6), Speaking 12 ta (6 Matn / 4 Oddiy / 2 Premium), Listening+Reading jami 4,000 so'm (kamdan-kam limitdan oshadi — 2 ta to'liq L+R kuniga 4-5 soat oladi). Server — Contabo VPS 20, 1 oylik ≈ 103,160 so'm/oy (barcha foydalanuvchilar orasida taqsimlanadi).

| Xizmat | Hisob | Daromad | Xarajat |
|---|---|---|---|
| Writing — Haiku (70%) | 8.4 × 500 so'm | 4,200 so'm | 328 so'm |
| Writing — Sonnet (30%) | 3.6 × 1000 so'm | 3,600 so'm | 277 so'm |
| Speaking — Matn | 6 × 500 so'm | 3,000 so'm | 204 so'm |
| Speaking — Oddiy | 4 × 800 so'm | 3,200 so'm | 2,228 so'm |
| Speaking — Premium | 2 × 1200 so'm | 2,400 so'm | 1,180 so'm |
| Listening + Reading | jami | 4,000 so'm | ~0 so'm |
| **1 talaba jami** | | **20,400 so'm** | **4,217 so'm** |

| 50 talaba, 1 oy | Summa |
|---|---|
| Jami daromad (50 × 20,400) | 1,020,000 so'm |
| AI/Azure xarajati (50 × 4,217) | −210,850 so'm |
| Yalpi foyda | 809,150 so'm |
| Server xarajati (VPS, 1 oylik) | −103,160 so'm |
| **Sof foyda (taxminiy)** | **≈ 705,990 so'm/oy** (~14,100 so'm/talaba) |

*Bu — taxminiy stsenariy. Real foydalanish chastotasi MVP ishga tushgach aniqlashtiriladi. To'lov tizimi komissiyasi (~1-2%, Payme/Click) hali hisobga olinmagan (2-faza).*

### "Konstruktor" Paket — 3-chi paket turi (yakuniy, 2026-07-15 tasdiqlangan)

Fixed (tayyor) paketlardan farqli — foydalanuvchi **o'zi tanlaydi**, qaysi elementdan nechta oladi.

**Tanlanadigan elementlar (har biriga miqdor kiritiladi, 0 = kiritilmaydi):**

| Element | Miqdor kiritilsa nima beriladi | AI tarifi tanlovi |
|---|---|---|
| **R** (Reading) | son × (5 turdan 1 tadan bundle) | — (AI yo'q) |
| **L** (Listening) | son × (5 turdan 1 tadan bundle) | — (AI yo'q) |
| **W T1** (Writing Task 1) | son × 1 ta | Tezkor tahlil (Haiku) / Chuqurroq tahlil (Sonnet) |
| **W T2** (Writing Task 2) | son × 1 ta | Tezkor tahlil (Haiku) / Chuqurroq tahlil (Sonnet) |
| **S P1** (Speaking Part 1) | son × 1 ta | Matn rejimi / Tezkor tahlil / Chuqurroq tahlil |
| **S P2** (Speaking Part 2) | son × 1 ta | Matn rejimi / Tezkor tahlil / Chuqurroq tahlil |
| **S P3** (Speaking Part 3) | son × 1 ta | Matn rejimi / Tezkor tahlil / Chuqurroq tahlil |

**Qo'shimcha tanlov:** Paket muddati — **3 / 5 / 7 kun** (foydalanuvchi tanlaydi, narxga ta'sir qilmaydi — faqat foydalanish oynasi).

**Minimal xarid:** tanlangan elementlarning **umumiy narxi kamida 5,000 so'm** bo'lishi shart — aks holda xarid yakunlanmaydi.

**Konstruktor narxlari (chegirmali, standalone narxdan arzon):**

| Element | Standalone narx | Konstruktor narxi | Xarajat | Marja (konstruktorda) |
|---|---|---|---|---|
| R — 1 birlik (5 turdan 1 tadan) | 500 so'm | **350 so'm** | ~0 so'm | ~100% |
| L — 1 birlik (5 turdan 1 tadan) | 500 so'm | **350 so'm** | ~0 so'm | ~100% |
| W T1/T2 — Tezkor tahlil (Haiku) | 500 so'm | **400 so'm** | ~39 so'm | ~90% |
| W T1/T2 — Chuqurroq tahlil (Sonnet) | 1,000 so'm | **800 so'm** | ~77 so'm | ~90% |
| S P1/P2/P3 — Matn rejimi | 500 so'm | **400 so'm** | ~34 so'm | ~91.5% |
| S P1/P2/P3 — Tezkor tahlil | 900 so'm | **800 so'm** | ~557 so'm | ~30.4% |
| S P1/P2/P3 — Chuqurroq tahlil | 1,200 so'm | **1,000 so'm** | ~590 so'm | ~41% |

*Izoh: "S — Tezkor tahlil" marjasi (30.4%) boshqalarga nisbatan tor, chunki Azure audio xarajati (~523 so'm) narxning katta qismini oladi — bu Speaking'ning tabiiy xususiyati, xato emas.*

---

## 1-bosqich: Backend — to'liq (taxminan 6-8 hafta)

Har bir bosqich Django Admin + DRF orqali **frontendsiz** tekshiriladi.

| # | Bosqich | Nima qilinadi | Tekshirish usuli |
|---|---|---|---|
| **B1** ✅ | Loyiha skeleti | Django 6.0.7 + DRF + django-cors-headers, `.env` (python-decouple), DB — SQLite local / PostgreSQL-ready (dj-database-url, `DATABASE_URL` orqali VPS'da almashtiriladi) | `runserver` ishladi (HTTP 200), Admin sahifasi ishladi (302 login'ga). Git: `word-app` repo tozalanib, Django skeleti push qilindi |
| **B2** ✅ | Foydalanuvchi/rol/Markaz tizimi | Administrator/O'qituvchi/Talaba, har bir foydalanuvchi **Markaz**ga biriktiriladi, Auth (JWT, `/api/token/`). **Markaz sozlamalarida AI provayder tanlovi** (Claude yoki Gemini) + mos API kalit maydoni — Fernet bilan shifrlangan (`accounts/fields.py`, `django-cryptography` Django 6'ga mos kelmagani uchun o'zimiz yozdik) | Admin panelda foydalanuvchi/markaz yaratish, provayder tanlab kalit kiritish (bazada shifrlangan holda saqlanishi tekshirildi), `/api/token/` orqali JWT login ishladi — hammasi tasdiqlandi |
| **B3** | Kurslar va Kontent (Private/Public) | Kurs/Dars/Material modellari — matn, video, **audio (Listening uchun)**. Material turi: Shaxsiy (Private) / Umumiy (Public). Lug'at va lug'at asosidagi o'yinlar — Umumiy turga misol | Admin panelda material (jumladan audio dars) yaratib, turini tekshirish |
| **B3.1** | Umumiy kontent — ochilish sharti | Markaz ma'lum miqdorda umumiy material kiritgandan keyin — boshqa markazlarning umumiy materiallarini **ko'rish huquqi** ochiladi (o'qituvchi/admin darajasida). Alohida shart bajarilgach — o'sha markaz **talabalari** umumiy materiallardan **foydalanish huquqi**ga ega bo'ladi | Chegaralarni sozlab, ochilish/yopilishini tekshirish |
| **B4** | Testlar/Mashqlar — **Listening va Reading (har biri 5 tur)** | Har ikkalasida: Multiple Choice, Fill in the Blanks, Matching (Listening'da oddiy Matching, Reading'da Matching Headings), True/False/Not Given, Short Answer — avtomatik tekshiriladi (AI shart emas) | Har 5 turdan test yaratib, avtomatik natijani tekshirish |
| **B4.1** | Listening/Reading — kunlik limit | Qoida: **har mashq turidan kuniga 1 tadan bepul** (5 tur × 1 = 5 ta/kun, Listening va Reading uchun alohida-alohida). Limit tugagach — **500 so'm** evaziga yana har turdan 1 tadan (**+5 ta**) ochiladi. Qoida moslashuvchan — tur soni o'zgarsa avtomatik moslashadi (qattiq kodlanmagan). Kunlik hisoblagich har kuni 00:00'da qayta tiklanadi | Limitni tugatib, to'lov qilib, +5 ta ochilishini tekshirish |
| **B5** | Writing AI | **Provider-agnostic** (`AIProvider` interfeysi — Claude va Gemini bir xil ortida). Tezkor tahlil (500 so'm) + Chuqurroq tahlil (1000 so'm), ichida platforma uchun **Gemini 3.1 Flash Lite (v2 prompt)**, markaz o'zi tanlagan providerga (Claude/Gemini) qarab almashadi. Ikki toifa API kalit (markaz/pullik) | Har ikki providerda insho yuborib solishtirish, markaz provayder almashtirsa to'g'ri ishlashini tekshirish |
| **B6** | Monitoring va Statistika | Progress, ko'nikmalar diagrammasi ma'lumotlari | Statistika API'ni tekshirish |
| **B7** | Gamifikatsiya (backend) | XP, Leaderboard, Badge logikasi | Ball/reyting hisobini tekshirish |
| **B8** | Speaking AI | Azure hisobi ochiladi (talaffuz — provayderdan mustaqil, har doim Azure), mazmun tahlili **provider-agnostic** (Claude/Gemini). Uch tarif: Matn rejimi (500 so'm), Tezkor tahlil (900 so'm), Chuqurroq tahlil (1200 so'm) | Har uch tarifni ikkala providerda sinab, narx/xarajatni tekshirish |
| **B8.1** | Writing/Speaking — turini oldindan tanlash shart emas | Talaba faqat **AI tarifini** (Tezkor/Chuqurroq/Matn) tanlaydi, keyin **istalgan turdagi** (Task 1/Task 2, Part 1/2/3) matn/audio yuboradi — tizim oldindan "qaysi tur" deb so'ramaydi, **nima yuborilsa o'shani tekshiradi** (AI prompt kontekstdan turini aniqlab, mos mezon bilan baholaydi). Bu qoida barcha paketlarga (Arzon, IELTS Boost, Konstruktor) baravar tegishli | Turli xil (Task1/Task2 aralash) matnlar yuborib, har biri to'g'ri baholanishini tekshirish |
| **B9** | Konstruktor paket | Foydalanuvchi R/L/W-T1/W-T2/S-P1/S-P2/S-P3'dan miqdor va AI tarifini o'zi tanlaydigan modul, muddat 3/5/7 kun | Turli kombinatsiyalarda narx to'g'ri hisoblanishini tekshirish |

VPS'ga deploy — B1 tugagach yoki server tayyor bo'lganda amalga oshiriladi.

> **Git repo (2026-07-15):** LMS uchun `https://github.com/shukhrat0594/word-app` qayta ishlatiladi (StudyCards jonli emas, foydalanuvchisiz). B1'da: repo tarkibi tozalanadi, Django skeleti push qilinadi. Eski materiallar (5,454 so'z, Grammar/Reading/Listening/Writing/Speaking mashqlari, 12 audio fayl) va butun StudyCards kodi `D:\shuk\Проекты\claude ai\word-app-backup`ga to'liq (git tarixi bilan) zaxiralab qo'yilgan. Bu materiallar keyinchalik LMS'ning mini-o'yinlar/lug'at moduliga import qilinadi.

> **B3.1 haqida eslatma:** Bu — to'liq multi-tenant SaaS (3-faza, alohida domen/branding) emas, balki **bitta platforma ichida** markazlar orasida kontent almashish tizimi. Bu hoziroq (B bosqichida) amalga oshiriladi, chunki `markaz_id` asosidagi ma'lumot ajratish allaqachon reja qilingan edi.

## 2-bosqich: Frontend — dizayn va kod (taxminan 5-6 hafta)

| # | Bosqich | Nima qilinadi |
|---|---|---|
| F1 | UI/UX dizayn (Figma) | Dashboard, monitoring paneli, talaba/o'qituvchi/admin interfeyslari. Ranglar/shrift CSS o'zgaruvchilarida. **Markaz logotipini yuklash imkoniyati** (branding uchun alohida joy) |
| F2 | Asosiy sahifalar | Login, dashboard — Backend API'larga ulanadi |
| F3 | Writing AI interfeysi | Insho kiritish, tarif tanlash (Tezkor tahlil/Chuqurroq tahlil), natija ko'rish sahifasi |
| F4 | Speaking AI interfeysi | Audio yozib olish moduli, tarif tanlash (Matn rejimi/Tezkor tahlil/Chuqurroq tahlil), xato so'zlarni qizil/yashil rangda ko'rsatish |
| F5 | Gamifikatsiya UI | Leaderboard, XP, badge ko'rinishi |
| F6 | Konstruktor paket UI | R/L/W-T1/W-T2/S-P1/S-P2/S-P3 miqdor tanlash, AI tarifi tanlash, muddat (3/5/7 kun) tanlash, real-vaqtda narx hisoblash |

## 3-bosqich: QA va yakunlash (1 hafta)

- To'liq tizim testdan o'tkaziladi
- MVP mijozga/foydalanuvchilarga taqdim etiladi

---

## Keyingi fazalar (MVP'dan keyin, hozir emas)

| Faza | Nima | Qachon |
|---|---|---|
| — | **Telegram bot bildirishnoma** | Vaqt qisqarsa, MVP'dan keyin qo'shiladi (B bosqichlaridan olib tashlandi) |
| 2-faza | To'lov integratsiyasi (Payme/Click) | MVP'dan keyin |
| 3-faza | Multi-tenant SaaS (o'z domeni, to'liq branding) | Biznes talab qilganda |
| 4-faza | Native mobil ilova (agar PWA yetmasa) | Kerak bo'lsa |
| 5-faza | Cloudflare R2'ga o'tish (katta hajm uchun) | Foydalanuvchi ko'paysa |
