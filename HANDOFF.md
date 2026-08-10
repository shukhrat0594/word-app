# LMS loyihasi — davom ettirish (2026-08-09)

> Bu faylni yangi Claude Code sessiyasiga to'liq nusxa ko'chiring, yoki
> shunchaki "HANDOFF.md faylini o'qi va davom ettir" deng.

Loyiha: `D:\shuk\Проекты\claude ai\LMS` (Django + React, "Utmost o'quv markazi").
Til: o'zbekcha. Menga **Shuhrat** deb murojaat qil.

## 0. Boshlash

Working tree TOZA — yarim qolgan ish yo'q, hammasi push qilingan
(oxirgi commit `07258ad`). Avval shularni o'qi:

- **Reja fayli**: `C:\Users\Shuk\.claude\plans\pure-riding-parnas.md`
  — eng tepasida HOLAT XULOSASI jadvali bor (qaysi bo'lim bajarilgan,
  qaysi biri yo'q). Bu asosiy manba, quyida faqat qisqacha takror.
- `git log --oneline -10` va `CHANGELOG.md`.

## 1. Qolgan ishlar (rejadan)

13 bo'limdan 10 tasi bajarilgan. Qolgani:

1. **Owner uchun Backup tugmasi** — hali aniqlashtirilmagan. Boshlashdan
   oldin so'rash kerak: faqat bazami yoki media fayllar hammi? qayerga
   saqlanadi (brauzerga yuklab olishmi, R2'gami)? avtomatik jadval
   kerakmi yoki qo'lda tugmami?
2. **Render pullik tarifga o'tish** — billing qarori, kod emas. Hozir
   Hobby (bepul): 750 soat/oy, 512MB RAM. 3 ta xizmat: `Utmost_LC`
   (backend), `utmost-frontend` (static), `mulohaza-bot` (bu loyihaga
   aloqasi yo'q — Shuhrat o'chirmoqchi edi, o'chirilsa 750 soat faqat
   LMS'ga qoladi va muammo yo'qoladi).
3. **Kurslar blok-mashq — 2 ta band**: "+ Rasm qo'shish" tugmasi va
   bloklarni ▲▼ bilan qayta tartiblash (`BlokTasdiqlash.jsx`).
   **OCHIQ SAVOL**: bular BLOK rejimiga tegishli. Agar asosiy rejim
   RASM-FON bo'lsa, bu ikkisi ma'nosini yo'qotadi. Shuhratdan so'rash
   kerak: blok rejimi hali kerakmi? (Blok rejimida matn tanlanadi,
   tarjima qilinadi, mobilda o'qiladi — rasm-fonda bular yo'q.)

## 2. Ma'lum, ochiq sifat muammolari (alohida ish)

Commit izohlarida halol yozilgan, hali tuzatilmagan:

- **Writing baholashda bir tekis +0.5 og'ish** (5.5→6.0, 7.0→7.5).
  Tartib to'g'ri va barqaror, shuning uchun jiddiy emas deb baholangan.
  Tuzatish yo'li sifatida "promtga haqiqiy band-7/band-9 namuna
  inshalari (anchor) qo'shish" taklif qilingan.
- **AI Listening Part 4** (akademik ma'ruza) transkripti talab
  qilingan uzunlikka yetmaydi — 3 urinishdan keyin ham 608/640 so'z.
  Promt alohida kuchaytirilishi kerak.
- **`bosh_joy_aniqlash`** faqat chiziqcha turidagi bo'sh joyni topadi,
  QUTI turini yo'q (chegarasi och kulrang) — admin qo'lda qo'shadi.
  Hudud aniqlash grafik zich sahifada zaif.
- **`matching_headings`** promt tuzatishi mavjud testlarga ta'sir
  qilmaydi — ular qayta generatsiya qilinishi kerak.

## 3. Loyiha konvensiyalari (BUZMA)

- **CHANGELOG.md** — har reliz uchun bo'lim yoziladi va u owner'ga
  ilova ichida BILDIRISHNOMA bo'lib boradi (`accounts/relizlar.py`).
  Matn **odam tilida** bo'lsin, commit sarlavhasi emas. Format
  faylning o'zida yozilgan (parser shunga tayanadi). Yangi ish
  qilganda shu yerga ham yozish kerak.
- **Rasm ko'rsatish**: R2 bucket YOPIQ. Oddiy `<img src=...>`
  ISHLAMAYDI (Authorization sarlavhasi yuborilmaydi → 401). Media
  uchun `apiBlobUrl`, profil rasmi uchun tayyor
  `frontend/src/components/Avatar.jsx`. `mediaManzil` faqat markaz
  logosi uchun (u lokal diskda, ochiq).
- **Ota-ona ↔ farzand**: `farzandlar` M2M YO'Q. Bolaning o'zida
  `ota_ona` FK (bitta bola = bitta ota-ona, DB darajasida).
  `related_name="farzandlar"` ataylab eski nom bilan —
  `parent.farzandlar.all()` ishlaydi.

## 4. Ish uslubi (qat'iy)

- **Har safar REAL AI chaqiruvi bilan sinash**, mock emas.
- Sinov materiali: Headway Beginner PDF — `C:\Users\Shuk\Downloads\`,
  sahifa JPEG'lari `C:\Users\Shuk\Downloads\photos\`.
- venv: `source venv/Scripts/activate` (Bash), keyin `python manage.py ...`.
- Tekshiruv: backend — `python -m py_compile <fayl> && python manage.py check`;
  frontend — `cd frontend && npx oxlint <fayl>` va `npm run build`.
- Brauzer sinovi uchun: `preview_start` bilan `django` va `frontend`.
- Sinov foydalanuvchilari: `real_ai_sinov` (owner), `migr_sinov_talaba`
  (talaba), `Teacher1`. Parolni vaqtincha qo'yib, **sinovdan keyin
  albatta `set_unusable_password()` bilan qaytar**. Yaratilgan sinov
  yozuvlarini o'chir.
- Gemini TTS bepul limiti: 10/kun, 3/daqiqa — Listening sinovida tez tugaydi.
- Commit erkin, lekin **har push oldidan alohida ruxsat so'ra**.
- "Tayyor" deyishdan oldin nimani tekshirganingni ro'yxat qilib ayt.
- Ishonchsiz bo'lsang — to'qima, ayt. Noto'g'ri deb hisoblasang — bahslash.

## Birinchi qadam

Reja faylidagi holat jadvalini o'qi, keyin Shuhratdan so'ra: yuqoridagi
3 ta qolgan ishdan qaysi biridan boshlaymiz, yoki yangi vazifa bormi?
