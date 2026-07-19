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
| Talaba ro'yxatdan o'tishi | Google OAuth (Gmail, parolsiz) — B2.1 |
| Writing AI | Gemini 3.1 Flash Lite (asosiy, MVP'da yagona tarif) — Claude Sonnet 5 ("Chuqurroq tahlil") keyingi fazada qo'shiladi |
| Speaking AI | Azure Speech (talaffuz, har doim) + Gemini 3.1 Flash Lite (mazmun) — Claude Sonnet 5 ("Chuqurroq tahlil") keyingi fazada qo'shiladi |
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

**Bilib qo'yilgan model chegarasi:** Lite model **qo'shma egalarni** (compound subject, masalan "smartphones and internet") grammatik tahlilda to'liq to'g'ri tushunmasligi va bir xil turdagi xatoni matnning turli joylarida alohida-alohida (joyini ko'rsatib) ajrata olmasligi — v2/v3/v4'ning barchasida takrorlandi, bu **prompt emas, modelning tahlil chuqurligi chegarasi**. Shu sababli **Chuqurroq tahlil (kuchli model)** tarifi mo'ljallangan — nozik grammatik holatlar uchun (MVP'da emas, keyingi fazada qo'shiladi, "Keyingi fazalar" jadvaliga qarang).

### Writing AI — bitta tarif MVP'da (2026-07-15 yakuniy yangilangan)

**Muhim (2026-07-15):** dastlab "Tezkor tahlil"=Haiku / "Chuqurroq tahlil"=Sonnet ikki tarif rejalashtirilgan edi. Keyinchalik (1) Gemini 3.1 Flash Lite'ning rasmiy narxi ($0.25/1M input, $1.50/1M output, `ai.google.dev` tekshirildi) va 500 so'rov/kun bepul tieri Haiku'dan sezilarli arzonroq/saxiyroq chiqdi, (2) **Sonnet asosidagi "Chuqurroq tahlil" MVP'dan chiqarilib, keyingi fazaga o'tkazildi** (soddalik va xarajatsiz ishga tushish uchun). MVP'da Writing AI — **faqat Gemini asosida, bitta tarif**:

| Tarif nomi | Model | Narx | Taxminiy xarajat | Marja |
|---|---|---|---|---|
| **Tezkor tahlil** | Gemini 3.1 Flash Lite (v4 prompt) | **600 so'm** | **~0 so'm** (500/kun bepul tierda, ~815 talabagacha yetadi; undan keyin ~15 so'm/tekshiruv pullik tarifda) | **~100%** (bepul tierda) |
| ~~Chuqurroq tahlil~~ (Claude Sonnet 5) | — | — | ~77 so'm | *(keyingi fazada qaytadi)* |

### Speaking AI — ikki tarif MVP'da (2026-07-15 yakuniy yangilangan)

Standart Speaking javob davomiyligi: **2 daqiqa** audio. Sinov: `test_speaking_gemini.py` — Gemini 3.1 Flash Lite namunaviy IELTS Part 2 transkriptida 17 xato topdi, B8 arxitekturasi (Azure=Pronunciation, Gemini=qolgan 3 mezon) tasdiqlandi.

| Tarif nomi | Tarkib | Narx | Taxminiy xarajat | Marja | Izoh |
|---|---|---|---|---|---|
| **Matn rejimi** | Faqat Gemini 3.1 Flash Lite (talaba matn kiritadi, audio yo'q) | **600 so'm** | **~0 so'm** (bepul tierda) | **~100%** | Talaffuz baholanmaydi — faqat mazmun/grammatika/lug'at. Mikrofonsiz mashq uchun |
| **Tezkor tahlil** | Azure (talaffuz/ravonlik/urg'u) + Gemini 3.1 Flash Lite (mazmun) | **1000 so'm** | **~523 so'm** (faqat Azure, Gemini qismi ~0) | **~47.7%** | To'liq audio-asoslangan baho |
| ~~Chuqurroq tahlil~~ (Azure + Claude Sonnet 5) | — | — | ~590 so'm | — | *(keyingi fazada qaytadi)* |

*(2026-07-15: Haiku'dan Gemini'ga o'tildi (arzonroq, bepul tierda), narxlar 500→600 va 900→1000 so'mga oshirildi, Chuqurroq tahlil MVP'dan keyingi fazaga o'tkazildi.)*

> **Muhim:** Azure yolg'iz (talaffuzsiz Gemini'siz) tarif **taklif qilinmaydi** — chunki IELTS Speaking 4 mezondan iborat (Fluency&Coherence, Lexical Resource, Grammatical Range, Pronunciation), Azure faqat Pronunciation va Fluency'ning "yetkazish" qismini biladi, qolganini (Coherence, Lexical, Grammar) bilmaydi. Shuning uchun Speaking baho har doim Azure+Gemini combo bo'lishi kerak (Matn rejimi bundan mustasno — u alohida, talaffuzsiz mashq vositasi).

### Listening/Reading — mashq turlari va kunlik bepul limit (yangilangan, 2026-07-15)

**Qoida:** har bir mashq **turidan** kuniga **1 tadan bepul** (tur soniga qarab umumiy son o'zgaradi — quyida 5 tur bilan misol).

**Listening — 5 tur (2026-07-16 real IELTS formatiga moslashtirildi):** Multiple Choice, Fill in the Blanks (Form/Note/Table/Sentence completion oilasi), Matching, **Plan/Map/Diagram Labelling** (rasm asosida), Short Answer
**Reading — 5 tur:** Multiple Choice, Fill in the Blanks (Sentence/Summary completion oilasi), Matching Headings, True/False/Not Given, Short Answer

*(2026-07-16: Listening'dan True/False/Not Given olib tashlandi — bu tur real IELTS Listening'da uchramaydi (faqat Reading'da bor), o'rniga real turlardan Plan/Map/Diagram Labelling qo'shildi. Reading turlari real formatga to'liq mos, o'zgarmadi. Narxlar keyinroq qayta ko'rib chiqiladi.)*

| | Bepul (kuniga) | Limit tugagach |
|---|---|---|
| Listening (5 tur × 1) | **5 ta** | 500 so'm = yana har turdan 1 tadan, **+5 ta** |
| Reading (5 tur × 1) | **5 ta** | 500 so'm = yana har turdan 1 tadan, **+5 ta** |

*Narx/mashq o'zgarmadi (100 so'm/mashq) — faqat "quti hajmi" 2 tadan → 1 tadan kichraydi, narx mutanosib ravishda 1000→500 so'm bo'ladi.*

*Bu — Writing/Speaking'dan farqli: bu yerda AI xarajati yo'q (avtomatik test, to'g'ri/noto'g'ri tekshiruv), shuning uchun 500 so'm deyarli **sof foyda** (server xarajati e'tiborga olinmaydigan darajada kichik). Bu narx — xarajatni qoplash emas, balki foydalanish limitini boshqarish/monetizatsiya usuli.*

*Backend'da qoida moslashuvchan qilib qurilishi kerak — "har tur × 1" formulasi, mashq turlari soni kelajakda o'zgarsa (ko'paysa/kamaysa) ham avtomatik moslashishi uchun (qattiq kodlangan "5" raqami emas).*

**Xarajat manbalari:** Claude — platform.claude.com rasmiy narxi; Gemini — ai.google.dev/gemini-api/docs/pricing rasmiy narxi (Gemini 3.1 Flash Lite: $0.25/1M input, $1.50/1M output, 500 so'rov/kun bepul); Azure — azure.microsoft.com rasmiy narxi (Speech-to-Text $1/soat + Pronunciation Assessment prosody $0.30/soat); Kurs — CBU rasmiy kursi 1 USD = 12,065.49 so'm, 1 EUR = 13,754.66 so'm (15.07.2026).

### "IELTS Boost" Paket — 8,000 so'm, 7 kun amal qiladi (2026-07-15 Gemini asosida qayta qurildi)

**Muhim (2026-07-15):** Sonnet MVP'dan chiqarilgani sababli, paket tarkibi Chuqurroq tahlil (Sonnet) o'rniga **Tezkor tahlil (Gemini/Azure+Gemini)** ishlatadi. Bu narx va qiymatni pasaytirdi, lekin xarajatni ham keskin kamaytirdi.

**Tarkibi:**
- 10 ta Reading (5 tur × 2 — MC, Fill in blanks, Matching Headings, T/F/NG, Short Answer)
- 10 ta Listening (5 tur × 2 — MC, Fill in blanks, Matching, T/F/NG, Short Answer)
- **5 ta** Speaking — **Tezkor tahlil** (Azure+Gemini). Talaba har safar Part 1, 2 yoki 3'dan qaysi birini xohlasa, o'shani tanlab yuboradi (B8.1 qoidasi — fixed taqsimot yo'q)
- **5 ta** Writing — **Tezkor tahlil** (Gemini). Talaba har safar Task 1 yoki Task 2'dan qaysi birini xohlasa, o'shani tanlab yuboradi

**Muhim:** paket davomida (7 kun) talabaning **kunlik bepul Reading/Listening limiti** (5 tur × 1 = 5+5/kun) ham **parallel ravishda davom etadi** — paket bunga qo'shimcha, uni almashtirmaydi.

| Element | Miqdor | Narx/birlik | Jami |
|---|---|---|---|
| Reading | 10 ta (5 tur × 2) | 500 so'm/bundle | 1,000 so'm |
| Listening | 10 ta (5 tur × 2) | 500 so'm/bundle | 1,000 so'm |
| Speaking — Tezkor tahlil | 5 ta | 1000 so'm | 5,000 so'm |
| Writing — Tezkor tahlil | 5 ta | 600 so'm | 3,000 so'm |
| **Alohida sotilsa (jami qiymat)** | | | **10,000 so'm** |

| | Summa |
|---|---|
| **Paket narxi** | **8,000 so'm** |
| Talaba tejaydi | 2,000 so'm (**20% chegirma**) |
| Bizning xarajatimiz (5× Azure ~523 so'm, Gemini ~0) | 2,615 so'm |
| **Bizning sof foydamiz** | **5,385 so'm** |
| **Marja** | **~67.3%** |

**Muddat asoslanishi:** faqat paket mashqlari (30 ta: R100+L80+S75+W175 daqiqa) — ~430 daqiqa (~7.2 soat), 7 kunga taqsimlansa ~61 daq/kun. Agar talaba kunlik bepul L/R'ni ham to'liq ishlatsa (~1.5 soat/kun) — jami ~17.7 soat/7 kun (~2.5 soat/kun). 7 kun 5 kunga nisbatan yukni yengillashtiradi va paketning ishlatilmay qolish xavfini kamaytiradi.

### "Arzon Paket" — 5,000 so'm, 5 kun amal qiladi (2026-07-15 Gemini narxlariga qayta hisoblandi)

IELTS Boost'ning kirish darajasidagi (entry-level) versiyasi — arzonroq tariflar bilan. Tarkib o'zgarmadi, faqat Writing tarifi Chuqurroq(Sonnet)dan Tezkor(Gemini)ga o'tdi (Sonnet MVP'dan chiqarilgani sababli).

**Tarkibi:**
- 15 ta Reading (5 tur × 3)
- 15 ta Listening (5 tur × 3)
- 3 ta Writing — **Tezkor tahlil** (Gemini). **Talaba har safar Task 1 yoki Task 2'dan qaysi birini xohlasa, o'shani tanlab yuboradi** (fixed taqsimot yo'q, erkin tanlov)
- 3 ta Speaking — **Matn rejimi** (Gemini, audio yo'q). **Talaba har safar Part 1, 2 yoki 3'dan qaysi birini xohlasa, o'shani tanlab yuboradi**

**Muhim:** paket davomida (5 kun) talabaning kunlik bepul Reading/Listening limiti ham parallel davom etadi.

| | Summa |
|---|---|
| Alohida sotilsa (jami qiymat, R/L standart top-up narxida hisoblangan) | 6,600 so'm |
| **Paket narxi** | **5,000 so'm** |
| Talaba tejaydi | 1,600 so'm (**~24.2% chegirma**) |
| Bizning xarajatimiz (Writing+Speaking Gemini ~0, R/L bepul) | **~0 so'm** |
| **Bizning sof foydamiz** | **~5,000 so'm** |
| **Marja** | **~100%** |

**Muddat asoslanishi:** jami ~36 ta mashq, ~6.5 soat vaqt (Reading ~150 daq, Listening ~120 daq, Writing ~90 daq, Speaking-matn ~30 daq), 5 kunga taqsimlansa ~78 daqiqa/kun.

### Daromad/foyda misoli — 50 pullik talaba, 1 oy (2026-07-15 Gemini narxlariga qayta hisoblandi)

**Taxminlar (1 talaba/oyiga):** Writing 12 ta (MVP'da faqat Tezkor tahlil — Sonnet yo'q), Speaking 12 ta (6 Matn / 6 Tezkor — avvalgi "Premium" ulushi Tezkor'ga qo'shildi, chunki Chuqurroq MVP'da yo'q), Listening+Reading jami 4,000 so'm. Server — Contabo VPS 20, 1 oylik ≈ 103,160 so'm/oy. **Kunlik Gemini so'rovi tekshirildi: ~40/kun — 500/kun bepul limitning atigi ~8%i, ya'ni Gemini xarajati bu hajmda 0 so'm.**

| Xizmat | Hisob | Daromad | Xarajat |
|---|---|---|---|
| Writing — Tezkor tahlil (Gemini) | 12 × 600 so'm | 7,200 so'm | ~0 so'm |
| Speaking — Matn rejimi (Gemini) | 6 × 600 so'm | 3,600 so'm | ~0 so'm |
| Speaking — Tezkor tahlil (Azure+Gemini) | 6 × 1000 so'm | 6,000 so'm | 3,138 so'm |
| Listening + Reading | jami | 4,000 so'm | ~0 so'm |
| **1 talaba jami** | | **20,800 so'm** | **3,138 so'm** |

| 50 talaba, 1 oy | Summa |
|---|---|
| Jami daromad (50 × 20,800) | 1,040,000 so'm |
| AI/Azure xarajati (50 × 3,138) | −156,900 so'm |
| Yalpi foyda | 883,100 so'm |
| Server xarajati (VPS, 1 oylik) | −103,160 so'm |
| **Sof foyda (taxminiy)** | **≈ 779,940 so'm/oy** (~15,599 so'm/talaba) |

*Bu — taxminiy stsenariy (eski Haiku-asosli hisobdan +73,950 so'm/oy ko'proq, asosan Gemini'ning bepul tieri tufayli). Real foydalanish chastotasi MVP ishga tushgach aniqlashtiriladi. To'lov tizimi komissiyasi (~1-2%, Payme/Click) hali hisobga olinmagan (2-faza).*

### "AI Tarifi" Paket — 3-chi paket turi (2026-07-15 yakuniy, Konstruktor o'rniga soddalashtirildi)

**Tarix:** dastlab to'liq erkin "Konstruktor" (R/L/W/S'dan istalgan miqdor + istalgan AI tarifi) rejalashtirilgan edi. Sodda va tezroq ishga tushirish uchun bu **ikkita fixed tanlovga** soddalashtirildi — faqat Writing va Speaking'ning **Tezkor tahlil** tarifidan, faqat ikki hajm variantida. Reading/Listening bu paketga kirmaydi (ular alohida — kunlik bepul limit + top-up).

**Tanlov:** foydalanuvchi ikkitadan birini tanlaydi:
- **5W + 5S** — 5 ta Writing Tezkor tahlil + 5 ta Speaking Tezkor tahlil
- **10W + 10S** — 10 ta Writing Tezkor tahlil + 10 ta Speaking Tezkor tahlil

Ikkala holatda ham talaba har safar Task/Part turini erkin tanlab yuboradi (B8.1 qoidasi).

**Qo'shimcha tanlov:** Paket muddati — **3 / 5 / 7 kun** (foydalanuvchi tanlaydi, narxga ta'sir qilmaydi — faqat foydalanish oynasi).

| Tanlov | Standalone qiymat | **Paket narxi** | Chegirma | Xarajat | Sof foyda | Marja |
|---|---|---|---|---|---|---|
| **5W + 5S** | 8,000 so'm (5×600 + 5×1000) | **7,000 so'm** | 12.5% | 2,615 so'm (5× Azure) | 4,385 so'm | ~62.6% |
| **10W + 10S** | 16,000 so'm (10×600 + 10×1000) | **14,000 so'm** | 12.5% | 5,230 so'm (10× Azure) | 8,770 so'm | ~62.6% |

*Xarajat faqat Speaking miqdoriga bog'liq (Azure ~523 so'm/birlik) — Writing (Gemini) xarajati ~0 so'm.*

---

## 1-bosqich: Backend — to'liq (taxminan 6-8 hafta)

Har bir bosqich Django Admin + DRF orqali **frontendsiz** tekshiriladi.

| # | Bosqich | Nima qilinadi | Tekshirish usuli |
|---|---|---|---|
| **B1** ✅ | Loyiha skeleti | Django 6.0.7 + DRF + django-cors-headers, `.env` (python-decouple), DB — SQLite local / PostgreSQL-ready (dj-database-url, `DATABASE_URL` orqali VPS'da almashtiriladi) | `runserver` ishladi (HTTP 200), Admin sahifasi ishladi (302 login'ga). Git: `word-app` repo tozalanib, Django skeleti push qilindi |
| **B2** ✅ | Foydalanuvchi/rol/Markaz tizimi | Administrator/O'qituvchi/Talaba, har bir foydalanuvchi **Markaz**ga biriktiriladi, Auth (JWT, `/api/token/`). **Markaz sozlamalarida AI provayder tanlovi** (Claude yoki Gemini) + mos API kalit maydoni — Fernet bilan shifrlangan (`accounts/fields.py`, `django-cryptography` Django 6'ga mos kelmagani uchun o'zimiz yozdik) | Admin panelda foydalanuvchi/markaz yaratish, provayder tanlab kalit kiritish (bazada shifrlangan holda saqlanishi tekshirildi), `/api/token/` orqali JWT login ishladi — hammasi tasdiqlandi |
| **B2.1** ✅ | Guruh va Google OAuth | Talaba **Google OAuth** orqali ro'yxatdan o'tadi (Gmail akkount, parolsiz). Yangi **Guruh** modeli — nomi, Markaz FK, biriktirilgan **O'qituvchi** (admin tayinlaydi), **Talabalar** (admin guruhga qo'shadi). O'qituvchi/Admin akkountlari hamon admin tomonidan qo'lda yaratiladi. `academics` app: `Guruh` modeli + `m2m_changed` signal (talaba guruhga qo'shilganda markazsiz bo'lsa avtomatik biriktiriladi, boshqa markazga tegishli bo'lsa xato beradi) — shell orqali tekshirildi. `POST /api/auth/google/` (`google-auth`) — Google Cloud Console'da OAuth Client ID yaratildi (loyiha "Edu Center"), **haqiqiy Gmail akkount bilan to'liq sinaldi**: 200 status, JWT (access+refresh) qaytdi, foydalanuvchi to'g'ri yaratildi (email, ism-familiya Google'dan, rol=Talaba, markaz=None) | Talaba Google orqali kirib, admin uni guruhga va o'qituvchini guruhga biriktirganini tekshirish — **login qismi tasdiqlandi**, guruhga biriktirish keyingi qadam |
| **B2.2** ✅ | Davomat (soddalashtirilgan yo'qlama) | Dars jadvali/kalendar YO'Q — o'qituvchi guruh sahifasida kun bo'yicha **"kim keldi"** belgilaydi (Keldi/Kelmadi). `Davomat` modeli: sana + guruh + talaba + holat + belgilagan (admin saqlashda avtomatik). B6/B6.1'da ko'rsatiladi | Shell orqali tekshirildi: a'zo uchun yozuv yaratildi ✓, guruhga a'zo bo'lmagan talaba rad etildi ✓, bir kunda takroriy yozuv (unique constraint) rad etildi ✓. Admin ro'yxatda sana/guruh/holat filtrlari bor |
| **B3** ✅ | Kurslar va Kontent (Private/Public) | `content` app: **Kurs** (markaz FK) → **Dars** (tartibli) → **Material** (matn/video-YouTube ID/audio-fayl; Darsga ixtiyoriy bog'lanadi yoki mustaqil — lug'at kabi; Private/Public). **DarsFaollik** — talaba materialni ochgani/tugatgani (progress + B3.2 kirish logi + B6.1 asosi). Validatsiyalar: turiga mos kontent maydoni majburiy, material markazi dars markazi bilan mos bo'lishi shart | Shell orqali tekshirildi: 3 tur material yaratildi ✓, mustaqil (dars'siz) material ✓, bo'sh kontent rad etildi ✓, markaz nomuvofiqlik rad etildi ✓, faollik yozildi ✓ |
| **B3.1** ✅ | Umumiy kontent — ochilish sharti | Markaz **5 ta** Public material kiritgach (chegara `PUBLIC_UNLOCK_LIMIT` sozlamasida, qattiq kodlanmagan) — boshqa markazlarning Public materiallarini ko'rish **o'qituvchi/admin VA talabalar uchun bir vaqtda** ochiladi. `public_kontent_ochiqmi()` + `korinadigan_materiallar()` funksiyalari | Shell orqali tekshirildi: 0 va 4 ta Public'da yopiq ✓, 5 tada ochildi ✓, boshqa markaz Public'i ko'rindi ✓, boshqa markaz PRIVATE'i hech qachon ko'rinmadi ✓ |
| **B3.2** | Kontent himoyasi (tarqalishdan) | Mashqlar (Listening/Reading/Speaking/Writing) va AI feedback — faqat autentifikatsiyalangan API orqali, xom fayl/export endpoint yo'q. Audio — **signed, muddati tez tugaydigan URL** orqali stream (doimiy ommaviy link yo'q). Video — YouTube unlisted + embed-only player, **shaffof watermark** (talaba ismi/ID). Har foydalanuvchining kontentga kirishi **log** qilinadi, g'ayrioddiy tez/ko'p so'rov (skript bilan ommaviy yuklab olishga urinish) **rate-limit** bilan avtomatik bloklanadi. Talabaning **o'z tarixi/feedback'iga** istalgan payt kirish huquqi cheklanmaydi (faqat o'ziniki) | Signed URL muddati tugagach ishlamasligini, rate-limit chegara oshganda bloklashini, talaba o'z tarixini erkin ko'ra olishini tekshirish |
| **B4** ✅ | Testlar/Mashqlar — **Listening va Reading (har biri 5 tur, real IELTS formatida)** | `exercises` app: **Mashq** (bo'lim+tur+markaz+Private/Public, savollar JSONField'da — {"savol","variantlar","togri"}, "togri" ro'yxat ham bo'ladi) va **MashqYechim** (javoblar+ball+har savol natijasi). `BOLIM_TURLARI` mapping — tur qo'shilsa limit avtomatik moslashadi. `javoblarni_tekshir()` — barcha turlar uchun yagona, registr/bo'shliqqa sezgir emas. Validatsiya: tur bo'limga mosligi, Listening→audio, Reading→matn, Labelling→rasm majburiy. **Muhim:** API'da (B4.1) "togri" maydonlari talabaga yuborilmaydi (B3.2) | Shell orqali tekshirildi: 10 tur mashq yaratildi ✓, Listening+T/F/NG rad ✓, audio'siz Listening rad ✓, tekshirish (to'g'ri/noto'g'ri/yetishmagan javob) ✓, yechim saqlandi ✓ |
| **B4.1** ✅ | Listening/Reading — kunlik limit + talaba API | Qoida: **har turdan kuniga 1 tadan bepul**, limit tugagach 500 so'm = har turga +1 (**+5 ta**). `LimitTopUp` modeli + `kunlik_limit_holati()` (BOLIM_TURLARI'dan moslashuvchan, sana bo'yicha — 00:00'da avtomatik yangi kun). API: `GET /api/mashqlar/` (ro'yxat), `GET /api/mashqlar/<id>/` (savollar **"togri"siz** — B3.2), `POST /api/mashqlar/<id>/yechish/` (limit shu yerda, 429), `GET /api/limit/`, `POST /api/limit/topup/` (**hozircha to'lovsiz test rejimi — to'lov 2-fazada ulanadi**) | HTTP orqali tekshirildi: ro'yxat ✓, detail'da "togri" yo'q ✓, yechish natija qaytardi ✓, limit tugaganda 429 ✓, topup'dan keyin ochildi ✓, autentifikatsiyasiz 401 ✓ |
| **B5** ✅ | Writing AI | `assessment` app: **provider-agnostic** — `GeminiProvider`/`ClaudeProvider` bir xil interfeys, `provider_tanla()` (markaz kaliti bo'lsa markaz tanlovi, aks holda platforma `GEMINI_API_KEY`). v4 prompt + **B8.1: AI task turini (Task1/Task2) kontekstdan o'zi aniqlaydi** (`task_type` maydoni). `WritingTekshiruv` modeli (natija JSON + provider/model/token sarfi). API: `POST /api/writing/tekshirish/`, `GET /api/writing/tarix/` (faqat o'ziniki). To'lov 2-fazada — hozircha tekshiruvlar to'lovsiz yoziladi | Jonli sinaldi (Gemini 3.1 Flash Lite): qisqa matn 400 ✓, haqiqiy insho → task2 aniqlandi, band 5.5, 14 xato, 860/830 token ✓, tarix ✓, provider tanlash mantiqi (Claude/Gemini/kalitsiz) shell'da ✓ |
| **B6** ✅ | Monitoring va Statistika | `stats` app: `talaba_statistikasi()` servisi (B6.1 ota-ona ham qayta ishlatadi) — Writing dinamikasi (sana+band+task), L/R har tur bo'yicha yechildi/foiz, **ko'nikmalar radar ma'lumotlari** (writing_band/listening_foiz/reading_foiz/speaking_band — speaking B8'da), dars faolligi (boshlangan/tugatilgan), davomat (keldi/kelmadi). API: `GET /api/statistika/` (faqat o'ziniki) | HTTP orqali tekshirildi: Writing (band 5.5, dinamika) ✓, Reading 2/4=50% to'g'ri hisoblandi ✓, davomat keldi=1 ✓, bo'sh bo'limlar null ✓ |
| **B6.1** ✅ | Ota-ona nazorati | `User.Role`ga **"parent"** qo'shildi, `farzandlar` M2M (ko'p-ko'pga, admin panelda bog'lanadi — filter_horizontal). API: `GET /api/farzandlar/` (ro'yxat), `GET /api/farzandlar/<id>/statistika/` — B6 `talaba_statistikasi()` servisini qayta ishlatadi, **faqat o'qish**. Bir nechta farzand — ro'yxatdan tanlanadi | HTTP orqali tekshirildi: farzandlar ro'yxati ✓, farzand statistikasi (writing band 5.5 ko'rindi) ✓, bog'lanmagan talaba → 404 ✓, talaba roli so'rasa → 403 ✓ |
| **B7** ✅ | Gamifikatsiya (backend) | `gamification` app: **XP** — signallar orqali avtomatik (mashq +10, mukammal +5 bonus, writing +20, material tugatildi +5, davomat keldi +2; `XP_QOIDALARI` bir joyda), takror hodisaga bermaydi (UniqueConstraint). **Badge** — 6 ta (birinchi mashq/writing, mukammal, 100/500 XP, 5 kun davomat). API: `GET /api/gamifikatsiya/` (XP+badge+oxirgi hodisalar), `GET /api/leaderboard/` (umumiy top+o'z o'rni, har bir guruhi ichida alohida) | HTTP+shell'da tekshirildi: XP 10+5+2=17 to'g'ri ✓, takror saqlashda XP oshmadi ✓, badge'lar avtomatik berildi ✓, guruh va umumiy reyting to'g'ri tartibda ✓ |
| **B8** ⏳ | Speaking AI | **Matn rejimi (600 so'm) ✅ tayyor:** `SpeakingTekshiruv` modeli, Speaking prompt (3 mezon, Pronunciation'siz, **B8.1: Part turini AI aniqlaydi**), provider'lar refaktorlandi (`_generate` — Writing/Speaking bitta mexanizm), `POST /api/speaking/matn/` + tarix, paketdan S yechish, statistika (`speaking_band` radar'da) va XP (+20) ulandi. **Tezkor tahlil (1000 so'm, audio)** — **4-bosqichga (eng oxiriga) ko'chirildi** (2026-07-16, QA testidan keyin, Azure hisobi bilan) | Matn rejimi jonli sinaldi: part2 to'g'ri aniqlandi ✓, band 5.3 ✓, 8 xato ✓, tarix ✓, statistika speaking_band=5.3 ✓, XP +20 ✓ |
| **B8.1** | Writing/Speaking — turini oldindan tanlash shart emas | Talaba faqat **AI tarifini** (Tezkor/Matn) tanlaydi, keyin **istalgan turdagi** (Task 1/Task 2, Part 1/2/3) matn/audio yuboradi — tizim oldindan "qaysi tur" deb so'ramaydi, **nima yuborilsa o'shani tekshiradi** (AI prompt kontekstdan turini aniqlab, mos mezon bilan baholaydi). Bu qoida barcha paketlarga (Arzon, IELTS Boost, AI Tarifi) baravar tegishli | Turli xil (Task1/Task2 aralash) matnlar yuborib, har biri to'g'ri baholanishini tekshirish |
| **B9** ✅ | "AI Tarifi" paket | `packages` app: `PAKETLAR` katalogi (5x5=7,000 / 10x10=14,000 so'm), muddat 3/5/7 kun. API: `GET /api/paketlar/` (katalog), `POST /api/paketlar/xarid/` (**to'lovsiz test rejimi — Payme/Click 2-fazada**), `GET /api/paketlar/mening/` (qoldiq+muddat). Writing tekshiruvida aktiv paketdan avtomatik 1 W yechiladi (`paketdan_ishlat()`); Speaking yechish B8'da ulanadi | Tekshirildi: narxlar to'g'ri (7000/14000) ✓, noto'g'ri tur/muddat 400 ✓, W tugagach None ✓, muddati o'tgan paket aktiv emas ✓, jonli Writing'da paketdan yechildi (10→9) ✓ |

> **Xavfsizlik tuzatishlari (2026-07-17, foydalanuvchi so'rovi bo'yicha audit):** Aniqlangan bo'shliqlar tuzatildi: (1) **Parol validatsiyasi** — `accounts/views.py`dagi barcha parol qabul qiluvchi endpoint (Xodimlar, Markaz admin tayinlash, Profil parol o'zgartirish) endi Django'ning standart `validate_password()`sini chaqiradi (uzunlik, umumiylik, faqat-raqamlilik va h.k. tekshiradi) — avval faqat qo'lda "6 belgidan ko'p" tekshiruvi bor edi. (2) **Brute-force himoyasi** — `config/settings.py`da DRF throttling yoqildi (`anon: 100/min`, `user: 300/min`, maxsus `login: 10/min` — `/api/token/` uchun yangi `XodimLoginView`, Google login, parol o'zgartirish shu scope'da). (3) **JWT umr davri** — avval standart (sozlanmagan) edi, endi aniq belgilandi: access 30 daqiqa, refresh 7 kun, rotation + blacklist yoqilgan (`rest_framework_simplejwt.token_blacklist` ilovasi qo'shildi, migratsiya qilindi). (4) **Production xavfsizlik headerlari** — `DEBUG=False` bo'lganda (VPS'da) `SECURE_SSL_REDIRECT`/`SESSION_COOKIE_SECURE`/`HSTS` avtomatik yoqiladigan qilib sozlandi (local dev'ga ta'sir qilmaydi). **Hali qolgan (VPS bosqichida hal bo'ladi):** haqiqiy HTTPS sertifikat, `.env`da `DEBUG=False` qo'yilganini tekshirish. **Brauzerda tekshirildi:** zaif parol (`12345`) rad etildi, aniq sabab ko'rsatildi ("juda qisqa, juda umumiy, faqat raqamli") ✓, kuchli parol bilan yaratish ishladi ✓, oddiy login throttling'dan zarar ko'rmadi ✓.

> **Xodimlar va Profil (2026-07-17):** Ikkita bo'shliq to'ldirildi: (1) markaz admini o'qituvchi akkaunt yarata olmasdi (faqat Django admin) — `frontend/src/pages/Xodimlar.jsx` (nav: faqat admin) + backend `accounts.XodimlarView` (`GET/POST /api/xodimlar/`, o'z markaziga teacher yaratadi/parol tiklaydi). (2) hech kim (owner ham) o'z parolini frontend'dan o'zgartira olmasdi — `frontend/src/pages/Profil.jsx` (nav: barcha rollar) + backend `accounts.ParolOzgartirishView` (`POST /api/profil/parol/`, Google orqali kirgan/parolsiz foydalanuvchi uchun eski parol talab qilinmaydi — birinchi marta qo'yish). **Brauzerda jonli tekshirildi:** markaz admini "Xodimlar"da yangi o'qituvchi yaratdi, o'sha login/parol bilan real login qildi ✓, Profil'da ism/login/rol/markaz to'g'ri ko'rsatildi ✓, parolni eski parol orqali yangisiga almashtirdi, eski chiqib yangi parol bilan qayta kirish ishladi ✓, konsolda xato yo'q ✓.

> **Owner paneli — Markazlar (2026-07-17):** Owner uchun frontend'da alohida sahifa qo'shildi — `frontend/src/pages/Markazlar.jsx` (nav: faqat `is_owner` bo'lsa "Markazlar" ko'rinadi). Yangi markaz yaratish (nomi+AI provayder) va har bir markaz kartasida to'g'ridan-to'g'ri **admin tayinlash** formasi (ism+login+parol — mavjud user bo'lsa yangilaydi, bo'lmasa yaratadi). Backend: `accounts/views.py` — `MarkazlarView` (GET/POST) va `MarkazAdminTayinlashView` (POST `/api/markazlar/<id>/admin-tayinlash/`), ikkalasi ham `owner_mi()` bilan himoyalangan. `ProfilView` javobiga `is_owner` maydoni qo'shildi (frontend shundan nav'ni boshqaradi). **Brauzerda jonli tekshirildi:** owner sifatida yangi markaz yaratildi ✓, unga yangi admin tayinlandi (admin_soni 0→1) ✓, keyin o'sha admin login qilib faqat o'z (yangi) markazini ko'rdi, Everest Education guruhlarini ko'rmadi ✓, owner bo'lmagan admin'da "Markazlar" nav yo'qligi tasdiqlandi ✓. Test ma'lumotlar tozalandi.

> **Platforma egasi — Owner (2026-07-17):** `shukhrat0594@gmail.com` — Django superuser (`/admin/` to'liq huquq) + LMS role=admin, markazga biriktirilmagan. `accounts/permissions.py`dagi `owner_mi(user)` (= `user.is_superuser`) — markazga bog'liq (markaz_id bo'yicha filtrlaydigan) har qanday view'da ENG BOSHIDA tekshirilishi kerak bo'lgan konvensiya: shunda **yangi markaz qo'shilganda ham owner avtomatik ko'radi**, alohida sozlash shart emas. Hozircha `academics/views.py` (Guruhlar/Davomat) shu konvensiyaga o'tkazilgan va tekshirilgan (owner ikkita turli markazning guruhlarini ham bir vaqtda ko'rdi). Kelajakda markazga bog'liq yangi view yozilganda ham shu `owner_mi()` bypass qo'llanishi kerak.

> **Platforma nomi va bitta markazga qulflash (2026-07-18):** Foydalanuvchi qaror qildi — platforma **"Utmost o'quv markazi"** deb nomlanadi va hozircha **faqat bitta markaz** bilan ishlaydi (ko'p-markazli infratuzilma kodda saqlanib qoladi, lekin yopiq — kelajakda kerak bo'lsa qayta ochiladi, bu tanlov xavfsiz/qaytariladigan yondashuv sifatida tavsiya qilingan edi). Amalga oshirildi: (1) ikkita mavjud markaz (test paytida boshqa sessiyada tasodifan yaratilgan) **birlashtirildi** — asosiy ma'lumotlar (talaba tarixi, guruh) saqlangan holda bitta markazga (`Utmost o'quv markazi`) ko'chirildi. (2) Backend — `MarkazlarView.post` va `MarkazSorovView.post` endi **agar biror markaz mavjud bo'lsa yangisini yaratishni rad etadi** (400). (3) Frontend — `Profil.jsx`dan "Yangi markaz so'rash" bo'limi butunlay olib tashlandi; `Markazlar.jsx` soddalashtirildi — endi faqat mavjud (bitta) markazni va unga admin tayinlash formasini ko'rsatadi, "Yangi markaz yaratish" va "Kutilayotgan so'rovlar" yo'q. (4) Standart brenddagi nom ("EduCenter") barcha joyda "Utmost o'quv markazi"ga almashtirildi (`Layout.jsx` fallback, `index.html` title). **Tekshirildi:** tab sarlavhasi "Utmost o'quv markazi" ✓, Markazlar sahifasida faqat 1 markaz va yaratish tugmasi yo'qligi ✓, Profil'da so'rov formasi yo'qligi ✓, konsolda xato yo'q ✓. **Kelajak rejasi (9-faza, "Keyingi fazalar"ga yozildi):** mashqlarni admin kiritayotganda "hammaga ochiq" yoki "faqat Utmost talabalari uchun" deb belgilash + bir martada bir nechta mashq kiritish formasi — **hali qurilmagan**, foydalanuvchi signal berganda boshlanadi.

> **Birlashtirilgan Tarix sahifasi (2026-07-18):** Foydalanuvchi so'radi — "bajargan mashqlar tarixi, audio yuklab Speaking tekshirgan bo'lsa ular ham". Yangi `GET /api/tarix/` (`assessment.TarixView`) — Writing va Speaking tekshiruvlarini **bitta ro'yxatga birlashtirib**, sana bo'yicha tartiblab qaytaradi; Speaking yozuvida audio fayl bo'lsa (kelajakdagi Tezkor tahlil rejimi uchun tayyorlangan, hozircha har doim bo'sh) `audio_url` bilan birga. Frontend: `Tarix.jsx` (nav: "Tarix" 🕐, barcha talabalar) — ro'yxat (turi+sarlavha+sana+band), bosilganda tafsilot (xatolar/kuchli tomonlar/AI tahlili, umumiy `xatoUtils.js` orqali) ochiladi, audio bo'lsa pleyer ko'rsatiladi. **Eslatma kodda qoldirildi:** audio real ishga tushganda B3.2 qoidasiga ko'ra xom `/media/` havola emas, authenticated stream endpoint kerak bo'ladi. **Tekshirildi:** Writing va Speaking yozuvlari bitta xronologik ro'yxatda to'g'ri aralashib chiqishi ✓, bosilganda to'liq tafsilot (7 xato, kuchli tomonlar, tahlil) ochilishi ✓, konsolda xato yo'q ✓.

> **Yana 2 o'yin: Tezkor viktorina + Harflarni tartiblash (2026-07-18):** StudyCards'da bo'lgan (lekin kodi saqlanmagan, faqat nomlari topilgan) 4 o'yindan 2 tasi qayta qurildi — mavjud so'z ma'lumotidan (`/api/oyinlar/sozlar/`) foydalanib, **yangi backend shart bo'lmadi**. **Tezkor viktorina** (Speed Quiz) — inglizcha so'zga 4 variantdan to'g'ri tarjimani 10 soniya ichida tanlash, ball to'planadi, vaqt tugasa xato hisoblanadi. **Harflarni tartiblash** (Unscramble) — aralashtirilgan harflardan so'zni yig'ish (bosib tanlash, tozalash, ko'rsatma tugmasi bilan tarjimani ko'rish), server orqali emas, klient tomonida solishtiriladi (past-stakes mashq). "Word Battle" (4-o'yin) — foydalanuvchi bilan kelishilgan holda hozircha qurilmadi (mexanikasi noaniq edi). **Brauzerda tekshirildi:** Tezkor viktorinada to'g'ri javob tanlanganda yashil belgilanib ball oshishi ✓; Harflarni tartiblashda so'z to'g'ri yig'ilganda ball oshishi (bir nechta so'z bilan, jumladan qisqa "now" so'zi bilan aniq) ✓, "Ko'rsatma" tarjimani ko'rsatishi ✓, konsolda xato yo'q ✓.

> **Mashqlar strukturasi + Grammatika o'yini + CSS tuzatishlar (2026-07-18):** (1) **Mashqlar qayta qurildi** — `Mashqlar.jsx` (nav: "Mashqlar", talabalar) endi IELTS/CEFR tab'lari bilan: **IELTS faol** (Writing/Speaking/Reading/Listening sub-tab'lari — Writing va Speaking mavjud komponentlarni ichiga oladi, Reading/Listening "tez orada"), **CEFR "tez orada"** (kontent/backend hali yo'q, 6-faza). Alohida "Writing AI"/"Speaking AI" nav bandlari olib tashlandi. (2) **Yana bir o'yin ko'chirildi** — StudyCards'dan grammatika savollari (90 ta, 9 mavzu: present-simple, past-simple, articles va h.k.) `GrammatikaSavoli` modeliga import qilindi (`grammatika_import` buyrug'i). Yangi "Grammatika testi" o'yini (`GET/POST /api/oyinlar/grammatika*`) — mavzu tanlanadi, ko'p variantli savol, javob serverda tekshiriladi (B3.2 — to'g'ri javob frontend'ga oldindan yuborilmaydi), natija (to'g'ri/N) ko'rsatiladi. (3) **CSS tuzatishlar**: Kartochka (Flashcard) endi haqiqiy 3D-aylanish animatsiyasi bilan (`perspective`+`preserve-3d`+`backface-visibility`), oldingi/orqa tomon bir vaqtda DOM'da, `rotateY` orqali almashadi. Juftini top kartalari sezilarli kichraytirildi (aspect-ratio kvadrat, kichik shrift, `max-width:420px`) — telefonda barcha 12 karta bitta ekrandan chiqmaydi. **Tekshirildi:** Mashqlar'da IELTS ichida Writing/Speaking/Reading/Listening tab almashinuvi, CEFR "tez orada" ekanligi ✓; Grammatika testida 9 mavzu to'g'ri chiqishi, javob tekshirilib to'g'ri/noto'g'ri rangda ko'rsatilishi (server orqali) ✓; Flashcard klik bilan "aylangan" klassini olishi (CSS qoidasi mavjud, standart flip-card texnikasi) — **vizual skrinshot orqali tasdiqlab bo'lmadi, chunki bu sessiyada brauzer skrinshot/computed-style vositasi ishlamay qoldi** (hatto qo'lda majburiy `!important transform` ham `getComputedStyle`da aks etmadi — bu vosita nosozligi, CSS/klass mantig'i to'g'ri ekanligi kod darajasida tasdiqlangan). Foydalanuvchi o'z tarafida vizual tekshirishi tavsiya etiladi.

> **O'yinlar bo'limi (2026-07-17, yangi):** Yangi Django ilova `games` — `Soz` modeli (en/uz/daraja/turkum/misol). `word-app-backup` (eski StudyCards)dagi 6 ta lug'at JSON faylidan (`a1–c1.json`, `idioms.json`) **5,454 so'z** `sozlar_import` management buyrug'i orqali import qilindi. API: `GET /api/oyinlar/sozlar/?daraja=A1&soni=N` (tasodifiy so'zlar), `GET /api/oyinlar/darajalar/`. Frontend: `Oyinlar.jsx` (nav: "O'yinlar" 🎮, barcha talabalar uchun) — ikkita o'yin: **Juftini top** (memory/matching — inglizcha va o'zbekcha kartalarni moslashtirish, harakat sonini hisoblaydi) va **Kartochkalar** (flashcard — so'z, bosilganda tarjima+turkum+misol ochiladi, Oldingi/Keyingi navigatsiya). CEFR darajasi (A1–C1, idiom) tanlanadi. **Brauzerda tekshirildi:** Juftini top'da noto'g'ri juftlik avtomatik yopilishi ✓, to'g'ri juftlik doimiy ochiq qolishi ("topilgan" holat) ✓, Kartochkalar aylanib tarjima+misol to'g'ri ko'rsatilishi ✓, konsolda xato yo'q ✓. **Eslatma:** Writing/Speaking'ni "Mashqlar" ichiga ko'chirish va IELTS/CEFR struktura qurish so'ralgan edi, lekin foydalanuvchi aniqlashtiruvchi savollarni bekor qildi — bu ish **kutilmoqda**, hali amalga oshirilmagan.

> **Narx ko'rsatkichlari UI'dan olib tashlandi (2026-07-17):** To'lov tizimi hali yo'qligi sababli (merchant hisob yo'q), Writing/Speaking "Tekshirish" tugmalaridagi "— 600 so'm"/"— 1000 so'm" ko'rsatkichlari olib tashlandi (`Writing.jsx`, `Speaking.jsx` — `/api/narxlar/` chaqiruvi va narx ko'rsatish kodi o'chirildi). Backend (`config/narxlar.py`, `/api/narxlar/`) o'zgarishsiz qoldi — kelajakda to'lov tizimi ulanganda qayta ishlatiladi. **Tekshirildi:** brauzerda ikkala sahifada ham tugma endi faqat "Tekshirish" deb ko'rsatilishi, narx umuman ko'rinmasligi tasdiqlandi ✓.

> **Biznes model o'zgardi — API kalit doim owner'niki (2026-07-17):** Markazlar endi o'z API kalitini kirita olmaydi — bu funksiya **butunlay olib tashlandi** (`Markaz.api_key` maydoni migratsiya bilan o'chirildi — `accounts/migrations/0004_...`). Endi barcha Writing/Speaking AI so'rovlari **har doim platforma (owner) kaliti** orqali ishlaydi (`config/settings.py`dagi `GEMINI_API_KEY`/yangi qo'shilgan `ANTHROPIC_API_KEY`). Markaz faqat AI **provayderni** (Gemini/Claude) tanlashda qoladi, lekin xarajat doim owner'ga tushadi. `assessment/providers.provider_tanla()` shunga mos soddalashtirildi. Hozircha (foydalanuvchi bilan kelishilgan) **haqiqiy to'lov/hisob-kitob yo'q** — bu "2-faza" (to'lov integratsiyasi) bosqichida, hozir faqat AI xarajati platformaga tushishi arxitektura darajasida ta'minlandi. Frontend'dagi barcha "API kalit" kiritish maydonlari (Profil so'rov formasi, Markazlar owner formasi) va "kalit bor/yo'q" ko'rsatkichlari olib tashlandi. **Tekshirildi:** API kalitsiz markaz so'rovi muvaffaqiyatli yuborildi ✓, `Markaz` modelida `api_key` maydoni umuman yo'qligi tasdiqlandi ✓, shu markazga tegishli talaba Writing tekshiruvini yubordi va **platforma Gemini kaliti orqali** to'liq javob oldi (band 4, tahlil bilan) ✓, konsolda xato yo'q ✓. Test ma'lumotlar tozalandi.

> **Markaz so'rovi — to'liq forma (2026-07-17):** Foydalanuvchi so'ragan kelishtirilgan ro'yxat: markaz nomi (majburiy), logo, brend rangi, AI provayder (Gemini/Claude), API kalit — hammasi endi **bitta so'rov formasida** birga yuboriladi (avval faqat nomi so'ralib, qolgani keyin qo'lda to'ldirilar edi, API kalit uchun esa frontend'da umuman joy yo'q edi — faqat Django admin). Backend: `MarkazSorovView`/`MarkazlarView` endi `MultiPartParser` bilan logo fayl + `ai_provider` + `api_key` (shifrlanib saqlanadi) qabul qiladi. Frontend: `Profil.jsx`dagi "Markaz so'rash" va `Markazlar.jsx`dagi owner "Yangi markaz" formalari — ikkalasi ham logo yuklash, AI provayder tanlash, API kalit kiritish maydonlarini oldi (`apiForm` orqali FormData). Owner "Kutilayotgan so'rovlar"da endi so'ragan odam nomi bilan birga AI provayder/kalit holatini ham ko'radi — qaror qabul qilish uchun kifoya ma'lumot. **Brauzerda tekshirildi:** talaba to'liq forma (nom+AI provayder=claude+API kalit) bilan so'rov yubordi ✓, bazada `ai_provider=claude`, `api_key` shifrlangan holda to'g'ri saqlangani tasdiqlandi ✓, owner "Kutilayotgan so'rovlar"da shu ma'lumotlarni (claude · API kalit kiritilgan) to'liq ko'rdi ✓. Test ma'lumotlar tozalandi.

> **Login matni umumlashtirildi + profil holati bag'i tuzatildi (2026-07-17):** (1) "Xodim sifatida kirish" → **"Login va parol bilan kirish"** (i18n: `xodim_kirish`/`xodim_izoh`/`yoki_xodim`) — endi xodimlarga xos emas, parol o'rnatgan **istalgan** foydalanuvchi (talaba, o'qituvchi, admin, owner) shu orqali kiradi. (2) **Bag** — Profil'da parol qo'yilgandan keyin ham Layout'dagi "sizda parol yo'q" banner yo'qolmasdi, chunki `Layout.jsx` va `Profil.jsx` profilni **mustaqil, bir martalik** `useState`larda saqlar edi (ikkisi sinxron emas edi). Tuzatish: `frontend/src/profilContext.jsx` — butun ilova bo'ylab yagona `ProfilProvider` (React Context), `useProfil()` hook orqali `{profil, yangila}` beradi. `Layout`, `Profil`, `BoshSahifa`, `Leaderboard` endi shu umumiy holatni o'qiydi; `Login.jsx` login muvaffaqiyatli bo'lgach `yangila()`ni chaqiradi (aks holda ProfilProvider ilk yuklanishda — tokensiz — bo'sh qolib ketardi). **Brauzerda tekshirildi:** parolsiz foydalanuvchida banner ko'rindi ✓, Profil'da parol qo'yilgach **sahifани yangilamasdan** SPA ichida Bosh sahifaga o'tilganda banner butunlay yo'qolgani tasdiqlandi ✓, yangi login matni ("Login va parol bilan kirish" / izoh: "talaba, o'qituvchi, markaz admini yoki owner") to'g'ri chiqdi ✓.

> **Davomat hisoboti + dinamik brend (2026-07-17):** (1) Markaz admini uchun yangi "Davomat hisoboti" bo'limi (`DavomatHisoboti.jsx`, nav ikon 📊) — backend `academics.DavomatHisobotView` (`GET /api/davomat-hisoboti/`) har bir guruh va talaba bo'yicha jami Keldi/Kelmadi sonini va foizini qaytaradi (o'qituvchi kunlik belgilagan davomatning yig'ma ko'rinishi). (2) Brauzer tab sarlavhasi va favicon endi **markaz nomiga/logotipiga qarab dinamik** — `Layout.jsx`dagi `useEffect` `document.title`ni va `<link rel="icon">` hrefini profildagi markaz ma'lumotidan yangilaydi (logo bo'lmasa standart favicon qoladi). **Brauzerda tekshirildi:** markaz admin hisobotda guruh+talaba bo'yicha to'g'ri son/foiz (Keldi:2, Kelmadi:1, 67%) ko'rdi ✓, boshqa markaz admin hisobotida "Utmost o'quv markazi" nomi tab sarlavhasida to'g'ri chiqdi ✓, logo bor markazda (`Everest Education`) favicon markaz logotipiga almashgani DOM orqali tasdiqlandi ✓. Test ma'lumotlar tozalandi.

> **Markaz so'rovi + brending + umumiy parol boshqaruvi (2026-07-17):** Katta panel to'plami qo'shildi: (1) **Har qanday parol** — owner uchun `Foydalanuvchilar.jsx` (nav: faqat owner) + backend `FoydalanuvchilarView`/`FoydalanuvchiParolTiklashView` — istalgan rol/markazdagi foydalanuvchiga parol o'rnatadi (ro'yxatdan qidirish bilan). (2) **Google orqali kirganlarga ogohlantirish** — `Layout.jsx`da global banner (`profil.parol_bormi === false` bo'lsa) — Profil'ga parol qo'yishga taklif qiladi. (3) **Markaz so'rash (self-service)** — `accounts.Markaz`ga `tasdiqlangan`/`soruvchi` maydonlari qo'shildi (migratsiya `0003`). Istalgan foydalanuvchi Profil'da (`MarkazSorovView`) markaz nomi kiritib so'rov yuboradi (`tasdiqlangan=False`); owner `Markazlar.jsx`da "Kutilayotgan so'rovlar" bo'limida ko'rib, **Tasdiqlash** (so'ragan foydalanuvchi avtomatik shu markazning admini bo'ladi — qo'shimcha parol/login kerak emas) yoki **Rad etish** qiladi. (4) **Markaz brendingi** — tasdiqlangach markaz admini uchun yangi "Markaz" bo'limi (`MarkazSozlash.jsx`, faqat admin, owner uchun emas) — logo yuklash va brend rangini (`brend_rang` hex) tanlash; `Layout.jsx` shu rangni `--sariq` CSS o'zgaruvchisiga qo'yadi — **butun interfeys** (nav, tugmalar) shu markaz rangida ko'rinadi. **Brauzerda to'liq zanjir tekshirildi:** talaba Profil'dan markaz so'radi ("Kutilmoqda") ✓ → owner Markazlar'da ko'rib tasdiqladi ✓ → so'ragan foydalanuvchi avtomatik admin bo'lgani DB'da tasdiqlandi (`role=admin`, `markaz=<yangi>`) ✓ → o'sha admin "Markaz" bo'limida rang tanlab saqladi ✓ → sahifa CSS o'zgaruvchisi (`--sariq`) haqiqatan ham yangi rangga o'zgargani `getComputedStyle` orqali tasdiqlandi ✓ → owner "Foydalanuvchilar"da istalgan foydalanuvchiga (masalan talabaga) parol o'rnatib, o'sha parol bilan login ishlashi tekshirildi ✓. Test ma'lumotlar tozalandi.

> **Narxlar — yagona manba (2026-07-17):** barcha AI tekshiruv/paket narxlari `config/narxlar.py`da belgilanadi (`WRITING_TEZKOR`, `SPEAKING_MATN`, `SPEAKING_TEZKOR`, `PAKET_CHEGIRMA`). `packages/models.py`dagi `PAKETLAR` narxi shu yerdan formula bilan hisoblanadi (qattiq yozilmagan). Frontend `GET /api/narxlar/` orqali o'qiydi (`accounts.NarxlarView`) — Writing/Speaking/Paketlar sahifalarida narx hech qayerda hardcode qilinmaydi. Narx o'zgarsa — faqat `config/narxlar.py` tahrirlanadi.

VPS'ga deploy — B1 tugagach yoki server tayyor bo'lganda amalga oshiriladi.

> **Git repo (2026-07-15):** LMS uchun `https://github.com/shukhrat0594/word-app` qayta ishlatiladi (StudyCards jonli emas, foydalanuvchisiz). B1'da: repo tarkibi tozalanadi, Django skeleti push qilinadi. Eski materiallar (5,454 so'z, Grammar/Reading/Listening/Writing/Speaking mashqlari, 12 audio fayl) va butun StudyCards kodi `D:\shuk\Проекты\claude ai\word-app-backup`ga to'liq (git tarixi bilan) zaxiralab qo'yilgan. Bu materiallar keyinchalik LMS'ning mini-o'yinlar/lug'at moduliga import qilinadi.

> **B3.1 haqida eslatma:** Bu — to'liq multi-tenant SaaS (3-faza, alohida domen/branding) emas, balki **bitta platforma ichida** markazlar orasida kontent almashish tizimi. Bu hoziroq (B bosqichida) amalga oshiriladi, chunki `markaz_id` asosidagi ma'lumot ajratish allaqachon reja qilingan edi.

> **B3.2 amalga oshirilishi boshlandi (2026-07-16):** Audio endi to'g'ridan-to'g'ri media URL bilan berilmaydi — faqat `/api/mashqlar/<id>/audio/` autentifikatsiyalangan stream (tokensiz 401, ochiq /media/ havola 404). Video — YouTube embed (yuklab olish tugmasi yo'q). Screenshot'ga texnik qarshilik qilinmaydi (foydalanuvchi qarori). **Deploy eslatmasi:** production'da nginx `media/mashqlar/audio/` va `media/speaking/audio/` papkalarini statik servis qilmasligi shart.

> **B3.2 haqida eslatma (2026-07-15 kelishilgan):** Maqsad — mashqlar, AI feedback, video, audio saytdan/ilova/botdan tashqariga **ommaviy tarzda chiqib ketmasligi va tarqalmasligi**. Muhim: 100% himoya texnik jihatdan imkonsiz (agar kontent ekranda ko'rinsa/eshitilsa, screenshot/screen recording bilan baribir olinishi mumkin — "analog hole"), shuning uchun maqsad **ommaviy/skript orqali yuklab olish va oson tarqatishni qiyinlashtirish + tarqalsa manbasini aniqlash** (watermark, access log). Bu B3/B4/B5/B8/B9 bosqichlarining barchasiga tarqaladigan (cross-cutting) talab, alohida bosqich emas — har birida amalga oshiriladi. Talabaning **o'z natijalari tarixiga**, shuningdek bog'langan **ota-onaning farzandi natijalariga** (B6.1) kirishi hech qanday holatda cheklanmaydi — lekin ota-ona faqat o'z farzandi(lari)ni ko'radi, boshqa talabalarni emas.

## 2-bosqich: Frontend — dizayn va kod (taxminan 5-6 hafta)

| # | Bosqich | Nima qilinadi |
|---|---|---|
| F1 ✅ | UI/UX dizayn | Figma o'rniga **HTML/CSS mockup** (amaliyroq — React'ning asosi bo'ladi): `design/f1_dizayn.html`, Artifact: claude.ai/code/artifact/eddf9f1b-... **Tasdiqlandi (2026-07-16, "zo'r"):** sariq-qora brend (#FFD400 + #2B2A28, EduCenter "U" logo), 5 ekran (Login/Dashboard/Writing/Mashqlar/Paketlar), UZ/RU/EN i18n lug'at bilan jonli almashadi, yorug'+qorong'u tema (CSS token'lar), radar/chiziq diagrammalar canvas'da. O'qituvchi/admin/ota-ona ekranlari shu dizayn tizimida F2/F5.1 paytida qilinadi. Markaz logotipi joyi — keyingi iteratsiyada |
| F2 ✅ | Asosiy sahifalar | `frontend/` — **Vite + React + react-router**. Login (Google OAuth tugmasi — GIS, xodim uchun JWT forma), **Dashboard real API'larga ulangan** (`/api/statistika/`, `/api/gamifikatsiya/`, `/api/leaderboard/`): stat kartalar, radar/dinamika (canvas), reyting, badge'lar. i18n UZ/RU/EN (Context), yorug'/qorong'u tema (localStorage), F1 dizayn tokenlari. JWT: localStorage + avto-refresh, 401→login. Dev: vite proxy → Django 8000. **Brauzerda tekshirildi:** login → dashboard haqiqiy ma'lumotlar bilan (XP 40, Speaking 5.3, badge, reyting), RU tili jonli almashdi, skrinshot mockup'ga mos. **+ Markaz brendingi (2026-07-16):** `/api/profil/` — sidebar/topbar'da markaz nomi va logosi ko'rsatiladi (admin panelda Markaz'ga yuklanadi), markaz bo'lmasa standart "EduCenter"; logo `/media/markaz_logos/` ochiq (brending), audio yopiqligicha. **+ Login UX:** talabaga parol yo'q izohi, xodim formasi yashirin toggle |
| F2.1 ✅ | Guruh va Davomat UI | **Backend API yangi qo'shildi** (`academics/views.py`+`urls.py` — avval faqat Django admin orqali ishlagan): `GET/POST /api/guruhlar/`, `GET/PATCH /api/guruhlar/<id>/`, `GET /api/markaz-azolari/` (admin uchun o'qituvchi/talaba ro'yxati), `GET/POST /api/davomat/`. Ruxsat: admin — o'z markazidagi barcha guruh, o'qituvchi — faqat o'ziniki. **Frontend:** `Guruhlar.jsx` (faqat admin nav'da) — ro'yxat, yangi guruh yaratish (nomi+o'qituvchi+talabalar checkbox), mavjudini tahrirlash. `Davomat.jsx` (admin+o'qituvchi nav'da) — guruh+sana tanlash, har talaba uchun Keldi/Kelmadi tugmalari, saqlash. `Layout.jsx` nav endi profil roliga qarab farqlanadi (talaba/o'qituvchi/admin uchun alohida ro'yxat) | **Brauzerda jonli tekshirildi:** admin bilan guruh yaratildi (nomi+o'qituvchi+1 talaba) ✓, admin davomat belgiladi (Keldi) va saqladi, DB'da to'g'ri yozuv tasdiqlandi ✓, o'qituvchi hisobi bilan kirib faqat "Davomat" nav ko'rinishi (Guruhlar yo'q) va faqat o'z guruhi + oldindan saqlangan holat to'g'ri yuklanishi tasdiqlandi ✓, konsolda xato yo'q ✓ |
| F3 ✅ | Writing AI interfeysi | `frontend/src/pages/Writing.jsx` — insho kiritish formasi (so'z sanog'i jonli), "Tekshirish — 600 so'm" tugmasi (`POST /api/writing/tekshirish/`), natija: Overall Band + task turi, 4 mezon ball, xatolar "noto'g'ri → to'g'ri (sabab)" formatida (F1 dizayniga mos), kuchli tomonlar, AI tahlili. Tarix ro'yxati (`GET /api/writing/tarix/`) — bosilsa o'sha natija qayta ko'rsatiladi, "Yangi tekshiruv" bilan formaga qaytiladi. i18n UZ/RU/EN to'liq | **Brauzerda jonli tekshirildi:** login (test talaba) → insho yuborildi → band 5, 7 xato to'g'ri formatda ko'rsatildi (masalan "technology have → technology has (Subject-verb agreement)") ✓, tarix ro'yxati ✓, eski tekshiruvni bosib ochish ✓, XP/paket yechish backend orqali avtomatik ishladi ✓, konsolda xato yo'q ✓ |
| F4 ✅ | Speaking AI interfeysi | `frontend/src/pages/Speaking.jsx` — tarif tanlash tab'lari (Matn rejimi aktiv/ishlaydi, Tezkor tahlil (audio) hozircha o'chirilgan, "tez orada" izohi bilan — Azure hali ulanmagan, B8/4-bosqich). Matn rejimi: javob kiritish, so'z sanog'i, "Tekshirish" tugmasi (`POST /api/speaking/matn/`, narx `/api/narxlar/`dan), natija: Overall Band + Part turi, 3 mezon (Fluency&Coherence/Lexical/Grammar, Pronunciation'siz), xatolar Writing bilan bir xil "noto'g'ri → to'g'ri (sabab)" formatida (umumiy `xatoUtils.js`ga chiqarildi). Tarix (`GET /api/speaking/tarix/`), i18n UZ/RU/EN | **Brauzerda jonli tekshirildi:** login → Matn rejimida javob yuborildi → Part 1 to'g'ri aniqlandi, band 5.5, 7 xato to'g'ri formatda ✓, tarix yangilandi ✓, Tezkor tahlil tugmasi disabled va bosilmaydi ✓, narx (600 so'm) backend'dan dinamik keldi ✓, konsolda xato yo'q ✓ |
| F5 ✅ | Gamifikatsiya UI | `frontend/src/pages/Leaderboard.jsx` (nav: talaba uchun "Reyting") — Jami XP + o'rin kartalari, tab guruhi (Umumiy + har bir guruh alohida, `GET /api/leaderboard/`dagi `guruhlar` massividan avtomatik chiqadi), to'liq reyting ro'yxati (o'zini "siz" bilan ajratib), **barcha 6 badge** (olingan/qulflangan holatda, nom+tavsif i18n katalogida), so'nggi XP hodisalari (sabab+miqdor, i18n label bilan) | **Brauzerda jonli tekshirildi:** login → Reyting sahifasida jami XP/o'rin/umumiy reyting/6 badge (ba'zilari qulflangan)/so'nggi hodisalar to'g'ri ko'rsatildi ✓, talabani vaqtincha guruhga qo'shib guruh-tab paydo bo'lishi va unga bosilganda faqat guruh a'zolari ko'rsatilishi tasdiqlandi ✓, konsolda xato yo'q ✓ |
| F5.1 ✅ | Ota-ona dashboard UI | Backend o'zgarmadi (B6.1'da tayyor edi). `frontend/src/pages/OtaOna.jsx` — farzand tanlash (bir nechtadan bo'lsa tab, bitta bo'lsa avtomatik), band/foiz kartalar (Writing/Speaking/Listening/Reading), ko'nikmalar radar + Writing dinamikasi, Dars faolligi (boshlangan/tugatilgan) va Davomat (keldi/kelmadi) kartalar — hammasi faqat o'qish rejimida. `BoshSahifa.jsx` — bosh sahifa (`/`) endi profil roliga qarab Dashboard (talaba/o'qituvchi/admin) yoki OtaOna (ota-ona) ko'rsatadi. Radar/Dinamika grafiklari `components/Grafiklar.jsx`ga chiqarilib, Dashboard va OtaOna ikkalasi qayta ishlatadi (dublikat yo'q) | **Brauzerda jonli tekshirildi:** ota-ona hisobi bilan kirib bitta farzand avtomatik tanlanishi, band/foiz/radar/dars faolligi/davomat to'g'ri ko'rsatilishi ✓, nav'da faqat "Bosh sahifa" borligi ✓, keyin talaba hisobi bilan kirib Dashboard hamon avvalgidek ishlashi (regressiya yo'q) ✓, konsolda xato yo'q ✓ |
| F6 | ~~"AI Tarifi" paket UI~~ | **2026-07-17: hozircha voz kechildi** — MVP'dan olib tashlandi, 8-fazada ("Keyingi fazalar") moslashuvchan (konstruktor) paket tizimi sifatida qayta quriladi |

## 3-bosqich: QA va yakunlash (1 hafta)

- To'liq tizim testdan o'tkaziladi
- MVP mijozga/foydalanuvchilarga taqdim etiladi

## 4-bosqich: Azure — Speaking "Tezkor tahlil" (audio) (2026-07-16: eng oxirgi bosqichga ko'chirildi)

QA testidan KEYIN, MVP'ning eng oxirgi qadami sifatida:
- Shuxrat Azure hisobini ochadi (portal.azure.com, Speech xizmati — bepul tier: 5 soat audio/oy)
- Audio yuklash endpointi → Azure Speech-to-Text (transkripsiya) + Pronunciation Assessment (prosody)
- Transkripsiya matni mavjud Gemini Speaking tahliliga (3 mezon) beriladi, natijalar birlashtiriladi
- `SpeakingTekshiruv` modeli tayyor (rejim="tezkor", `pronunciation` JSON maydoni kutmoqda)
- Audio yetkazish B3.2 talablariga mos (signed URL)

---

## Keyingi fazalar (MVP'dan keyin, hozir emas)

**Ustuvorlik (2026-07-19 foydalanuvchi belgiladi):** quyidagi 3 ta faza (6, 10, 9) navbatning eng boshiga chiqarildi — boshqalaridan oldin shular bilan boshlanadi.

| Faza | Nima | Qachon |
|---|---|---|
| 6-faza | **CEFR / O'zbekiston Multilevel'ga tayyorlash** (2026-07-16 kelishilgan) — milliy sertifikat imtihoni (A2–C1). Arxitektura tayyor: `Mashq`ga `imtihon_turi` (ielts/multilevel) + `daraja` (A2/B1/B2/C1) maydonlari, Writing/Speaking uchun alohida **CEFR-daraja promptlari** (band o'rniga daraja baholash), kontent — yangi Kurslar sifatida, statistikada daraja dinamikasi (A2→B1), IELTS↔CEFR mos kelish jadvali (masalan band 5.5–6.5 ≈ B2) talabaga ikkala o'lchovda ko'rsatiladi. Provider tizimi/Azure o'zgarmaydi | **Ustuvor — navbatning boshida (2026-07-19)** |
| 10-faza | **Reading/Listening/Writing/Speaking mashqlarini `word-app-backup`dan ko'chirish** (2026-07-19 aniqlangan) — `word-app-backup/content/word-app/data/` ichida tayyor IELTS kontenti bor: **Reading** 5 ta matn (`reading/passages.json`, bo'lim+savollar bilan), **Listening** 12 ta audio fayl + transkript+savollar (`listening/audios.json` + `public/audio/*.mp3`), **Writing** IELTS Task 1/2 topshiriqlari bosqichma-bosqich yo'riqnoma bilan (`writing/materials.json`), **Speaking** IELTS Part 1/2/3 savollari namuna javoblar bilan (`speaking/materials.json`). Hozircha `exercises.Mashq` modeli faqat Listening/Reading uchun bor (bo'sh, 0 qator), Writing/Speaking uchun model umuman yo'q (chunki bular hozir faqat AI-tekshiruv, tayyor mashq banki emas). Kerak bo'ladigan ish: (1) Writing/Speaking uchun yangi mashq-bank modeli, (2) kontent formatini loyihaga moslashtirish, (3) `games/management/commands/sozlar_import.py`ga o'xshash import buyruqlari, (4) Mashqlar UI'da bu kontentni ko'rsatish (hozir "tez orada" placeholder). 9-faza (ochiq/yopiq belgilash + bulk-entry forma) bilan bog'liq — birga qilingani ma'qul | **Ustuvor — navbatning boshida (2026-07-19)** |
| 9-faza | **Mashqlarni ochiq/yopiq belgilash + ko'p mashq kiritish formasi** (2026-07-18 kelishilgan) — Mashqlar va O'yinlar bo'limlari **Utmost talabasi bo'lmagan foydalanuvchilar uchun ham ochiq** bo'lishi kerak (hozir O'yinlar allaqachon shunday — markazga bog'liq emas; Mashqlar/Reading/Listening hali qurilmagan, lekin qurilganda shu qoidaga bo'ysunadi). Har bir mashqni **admin kiritayotganda o'zi belgilaydi**: "hammaga ochiq" yoki "faqat Utmost talabalari uchun" (`exercises.Mashq`ga yangi maydon, masalan `hammaga_ochiq` bool). Buning uchun **bir martada bir nechta mashqni kiritish imkonini beruvchi forma** (bulk-entry) kerak bo'ladi — hozircha faqat rejaga yozib qo'yildi, **hali qurilmagan** | **Ustuvor — navbatning boshida (2026-07-19)**, 10-faza bilan birga qilingani ma'qul |
| — | **Telegram bot bildirishnoma** | Vaqt qisqarsa, MVP'dan keyin qo'shiladi (B bosqichlaridan olib tashlandi) |
| — | **"Chuqurroq tahlil" (Claude Sonnet 5)** — Writing va Speaking'ning ikkalasida ham | MVP'dan keyin qo'shiladi (2026-07-15: soddalik/xarajatsiz ishga tushish uchun MVP'dan chiqarildi — B5/B8/B9/F3/F4/F6'dan olib tashlandi) |
| 2-faza | To'lov integratsiyasi (Payme/Click) | MVP'dan keyin |
| 3-faza | Multi-tenant SaaS (o'z domeni, to'liq branding) | Biznes talab qilganda |
| 4-faza | Native mobil ilova (agar PWA yetmasa) | Kerak bo'lsa |
| 5-faza | Cloudflare R2'ga o'tish (katta hajm uchun) | Foydalanuvchi ko'paysa |
| 7-faza | **Jonli suhbat orqali Speaking mashqi** (Gemini 2.5 Flash Native Audio Dialog / Live API) — talaba rasmiy (ballanadigan) Speaking testidan oldin AI bilan real-vaqtli ovozli suhbatda erkin mashq qiladi, AI imtihonchidek savol berib, jonli javob qaytaradi. Baholashdan mustaqil — faqat amaliyot rejimi, Azure Pronunciation Assessment/B8 asosiy oqimiga ta'sir qilmaydi | Eng oxirgi bosqich, barcha boshqa fazalardan keyin |
| 8-faza | **Moslashuvchan (konstruktor) paketlar** (2026-07-17 kelishilgan) — hozirgi qattiq kodlangan "AI Tarifi" (B9, `packages.PAKETLAR` — faqat 5x5/10x10 W+S) o'rniga: admin/owner Django admin (yoki alohida UI) orqali **o'zi paket yaratadi** — qaysi mashq turlari (Writing/Speaking, kelajakda Reading/Listening ham) va necha donadan kirishini tanlaydi, **bitta umumiy narxni qo'lda belgilaydi** (standalone yig'indidan avtomatik hisoblanmaydi). Talabaga ko'rsatilganda: standalone narx bilan solishtirib **chegirma foizi avtomatik hisoblab ko'rsatiladi**, **muddati (necha kun amal qiladi)** ham ko'rinadi. Hozircha (MVP) paketlar butunlay **ishlatilmaydi/ko'rsatilmaydi** — F6 qurilmaydi, B9 backend kodi tegilmagan holda qoladi (keyin shu fazada butunlay almashtiriladi yoki o'chiriladi — qaror shu faza boshlanganda beriladi) | MVP, Azure va boshqa fazalardan keyin, biznes talab qilganda |
