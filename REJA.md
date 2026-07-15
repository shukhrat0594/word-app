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
| **B6** | Monitoring va Statistika | Progress, ko'nikmalar diagrammasi ma'lumotlari | Statistika API'ni tekshirish |
| **B6.1** | Ota-ona nazorati | `User.Role`ga **"Ota-ona"** qo'shiladi. Ota-ona ↔ Talaba bog'lanishi — **ko'p-ko'pga** (bir talaba bir nechta ota-onaga, bir ota-ona bir nechta farzandga bog'lanishi mumkin). Bog'lashni faqat **Markaz (Admin/O'qituvchi)** admin panelda amalga oshiradi. Ota-ona faqat o'z farzand(lar)ining **progressini** (XP, band ballari, mashq natijalari, B6 statistikasi), **Dars faolligini** (B3 kontent ko'rish) va **Davomatini** (B2.2 — Keldi/Kelmadi) **faqat o'qish huquqi bilan** ko'radi. Bir nechta farzand bo'lsa — tanlab almashtirish imkoni | Markazda talaba↔ota-ona bog'lab, ota-ona akkountida faqat shu farzand(lar) ma'lumoti (progress+davomat) ko'rinishini, boshqa talabalar ko'rinmasligini tekshirish |
| **B7** | Gamifikatsiya (backend) | XP, Leaderboard (**guruh ichida** va platforma bo'yicha, ikkalasi ham), Badge logikasi | Guruh ichidagi va umumiy reytingning ikkalasi ham to'g'ri hisoblanishini tekshirish |
| **B8** | Speaking AI | Azure hisobi ochiladi (talaffuz — provayderdan mustaqil, har doim Azure), mazmun tahlili (Fluency&Coherence/Lexical/Grammar, matn asosida) **provider-agnostic** (Claude/Gemini) — Writing'dagi bilan bir xil mexanizm, kirish matni Azure transkripsiyasidan keladi. MVP'da ikki tarif: Matn rejimi (600 so'm), Tezkor tahlil (1000 so'm). Chuqurroq tahlil (Azure+Sonnet, 1200 so'm) keyingi fazada qo'shiladi. Audio yetkazish B3.2 talablariga mos (signed URL) | Ikkala tarifni ikkala providerda sinab, narx/xarajatni tekshirish |
| **B8.1** | Writing/Speaking — turini oldindan tanlash shart emas | Talaba faqat **AI tarifini** (Tezkor/Matn) tanlaydi, keyin **istalgan turdagi** (Task 1/Task 2, Part 1/2/3) matn/audio yuboradi — tizim oldindan "qaysi tur" deb so'ramaydi, **nima yuborilsa o'shani tekshiradi** (AI prompt kontekstdan turini aniqlab, mos mezon bilan baholaydi). Bu qoida barcha paketlarga (Arzon, IELTS Boost, AI Tarifi) baravar tegishli | Turli xil (Task1/Task2 aralash) matnlar yuborib, har biri to'g'ri baholanishini tekshirish |
| **B9** | "AI Tarifi" paket | Foydalanuvchi ikkitadan birini tanlaydi — 5W+5S yoki 10W+10S (ikkalasi ham Tezkor tahlil), muddat 3/5/7 kun (narxga ta'sir qilmaydi) | Ikkala tanlovda ham narx to'g'ri hisoblanishini tekshirish |

VPS'ga deploy — B1 tugagach yoki server tayyor bo'lganda amalga oshiriladi.

> **Git repo (2026-07-15):** LMS uchun `https://github.com/shukhrat0594/word-app` qayta ishlatiladi (StudyCards jonli emas, foydalanuvchisiz). B1'da: repo tarkibi tozalanadi, Django skeleti push qilinadi. Eski materiallar (5,454 so'z, Grammar/Reading/Listening/Writing/Speaking mashqlari, 12 audio fayl) va butun StudyCards kodi `D:\shuk\Проекты\claude ai\word-app-backup`ga to'liq (git tarixi bilan) zaxiralab qo'yilgan. Bu materiallar keyinchalik LMS'ning mini-o'yinlar/lug'at moduliga import qilinadi.

> **B3.1 haqida eslatma:** Bu — to'liq multi-tenant SaaS (3-faza, alohida domen/branding) emas, balki **bitta platforma ichida** markazlar orasida kontent almashish tizimi. Bu hoziroq (B bosqichida) amalga oshiriladi, chunki `markaz_id` asosidagi ma'lumot ajratish allaqachon reja qilingan edi.

> **B3.2 haqida eslatma (2026-07-15 kelishilgan):** Maqsad — mashqlar, AI feedback, video, audio saytdan/ilova/botdan tashqariga **ommaviy tarzda chiqib ketmasligi va tarqalmasligi**. Muhim: 100% himoya texnik jihatdan imkonsiz (agar kontent ekranda ko'rinsa/eshitilsa, screenshot/screen recording bilan baribir olinishi mumkin — "analog hole"), shuning uchun maqsad **ommaviy/skript orqali yuklab olish va oson tarqatishni qiyinlashtirish + tarqalsa manbasini aniqlash** (watermark, access log). Bu B3/B4/B5/B8/B9 bosqichlarining barchasiga tarqaladigan (cross-cutting) talab, alohida bosqich emas — har birida amalga oshiriladi. Talabaning **o'z natijalari tarixiga**, shuningdek bog'langan **ota-onaning farzandi natijalariga** (B6.1) kirishi hech qanday holatda cheklanmaydi — lekin ota-ona faqat o'z farzandi(lari)ni ko'radi, boshqa talabalarni emas.

## 2-bosqich: Frontend — dizayn va kod (taxminan 5-6 hafta)

| # | Bosqich | Nima qilinadi |
|---|---|---|
| F1 | UI/UX dizayn (Figma) | Dashboard, monitoring paneli, talaba/o'qituvchi/admin/**ota-ona** interfeyslari. Ranglar/shrift CSS o'zgaruvchilarida. **Markaz logotipini yuklash imkoniyati** (branding uchun alohida joy) |
| F2 | Asosiy sahifalar | Login (talaba uchun **Google OAuth tugmasi**, o'qituvchi/admin uchun oddiy login), dashboard — Backend API'larga ulanadi |
| F2.1 | Guruh va Davomat UI | O'qituvchi/admin — guruh yaratish, talaba/o'qituvchi biriktirish; o'qituvchi — kunlik davomat (Keldi/Kelmadi) belgilash sahifasi |
| F3 | Writing AI interfeysi | Insho kiritish, Tezkor tahlil natija ko'rish sahifasi (Chuqurroq tahlil UI keyingi fazada qo'shiladi) |
| F4 | Speaking AI interfeysi | Audio yozib olish moduli, tarif tanlash (Matn rejimi/Tezkor tahlil), xato so'zlarni qizil/yashil rangda ko'rsatish |
| F5 | Gamifikatsiya UI | Leaderboard (guruh ichida va umumiy), XP, badge ko'rinishi |
| F5.1 | Ota-ona dashboard UI | Farzand tanlash (bir nechtadan bo'lsa), progress (XP/band ballari), Dars faolligi va Davomat ko'rinishi — faqat o'qish rejimi |
| F6 | "AI Tarifi" paket UI | 5W+5S / 10W+10S tanlash, muddat (3/5/7 kun) tanlash, narx ko'rsatish |

## 3-bosqich: QA va yakunlash (1 hafta)

- To'liq tizim testdan o'tkaziladi
- MVP mijozga/foydalanuvchilarga taqdim etiladi

---

## Keyingi fazalar (MVP'dan keyin, hozir emas)

| Faza | Nima | Qachon |
|---|---|---|
| — | **Telegram bot bildirishnoma** | Vaqt qisqarsa, MVP'dan keyin qo'shiladi (B bosqichlaridan olib tashlandi) |
| — | **"Chuqurroq tahlil" (Claude Sonnet 5)** — Writing va Speaking'ning ikkalasida ham | MVP'dan keyin qo'shiladi (2026-07-15: soddalik/xarajatsiz ishga tushish uchun MVP'dan chiqarildi — B5/B8/B9/F3/F4/F6'dan olib tashlandi) |
| 2-faza | To'lov integratsiyasi (Payme/Click) | MVP'dan keyin |
| 3-faza | Multi-tenant SaaS (o'z domeni, to'liq branding) | Biznes talab qilganda |
| 4-faza | Native mobil ilova (agar PWA yetmasa) | Kerak bo'lsa |
| 5-faza | Cloudflare R2'ga o'tish (katta hajm uchun) | Foydalanuvchi ko'paysa |
| 6-faza | **Jonli suhbat orqali Speaking mashqi** (Gemini 2.5 Flash Native Audio Dialog / Live API) — talaba rasmiy (ballanadigan) Speaking testidan oldin AI bilan real-vaqtli ovozli suhbatda erkin mashq qiladi, AI imtihonchidek savol berib, jonli javob qaytaradi. Baholashdan mustaqil — faqat amaliyot rejimi, Azure Pronunciation Assessment/B8 asosiy oqimiga ta'sir qilmaydi | Eng oxirgi bosqich, barcha boshqa fazalardan keyin |
