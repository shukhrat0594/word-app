# Loyihani boshqa kompyuterga ko'chirish

Sana: 2026-09-05. Ikkala kompyuter ham Windows.

## Qisqacha

```
  ESKI kompyuter                    YANGI kompyuter
  ─────────────                     ───────────────
  .\kochirish_tayyorla.ps1  ──►  tashqi disk  ──►  .\ornatish.ps1
        -Manzil E:\LMS                                (o'zi hammasini
                                                       o'rnatadi)
```

## Nega oddiy `git clone` yetarli emas

Loyihaning eng muhim qismi git'da **yo'q** — `.gitignore` ataylab
chiqarib tashlagan:

| Nima | Hajmi | Nega git'da yo'q |
|---|---|---|
| `db.sqlite3` | 8,9 MB | Baza — har mashinada o'ziniki |
| `media/` | 4,0 GB | Yuklangan rasm/audio — git uchun juda katta |
| `.env` | — | **API kalitlar va SECRET_KEY** — sirlar git'ga tushmasligi kerak |
| `courses/management/commands/headway_*unit*.py` | 124 fayl | Darslik kontenti — 2026-08-17 da ataylab chiqarilgan |
| `courses/fixtures/headway/` | — | Shu sabab |

Ya'ni GitHub'dan klon qilsangiz **kod keladi, ma'lumot kelmaydi**.

## 1-qadam — eski kompyuterda

Tashqi diskni ulang va loyiha papkasida:

```powershell
.\kochirish_tayyorla.ps1 -Manzil E:\LMS-kochirish
```

Kitoblarsiz (14 GB tejaladi, faqat ishlash uchun kerakli qismi):

```powershell
.\kochirish_tayyorla.ps1 -Manzil E:\LMS-kochirish -KitoblarSiz
```

Skript butun papkani nusxalaydi, lekin `venv` (324 MB) va
`node_modules` (94 MB) ni **tashlab ketadi** — ular platformaga bog'liq,
yangi mashinada qaytadan quriladi. Oxirida eng muhim fayllar joyidami,
tekshirib ko'rsatadi.

Taxminiy hajm: **hammasi bilan ~18 GB**, `-KitoblarSiz` bilan **~4 GB**.

> **Diqqat:** `.env` ichida API kalitlar va `SECRET_KEY` bor. Tashqi
> diskni boshqa odamga bermang, ish tugagach diskdan o'chiring.

## 2-qadam — yangi kompyuterda

Papkani diskdan qattiq diskka nusxalang (masalan `D:\LMS`), PowerShell'da
o'sha papkaga kiring va:

```powershell
.\ornatish.ps1
```

Skript ketma-ket:

1. **Git, Python 3.14, Node.js** bor-yo'qligini tekshiradi, yo'q bo'lsa
   `winget` orqali o'rnatadi
2. `venv` yaratib, `requirements.txt` (52 paket) ni o'rnatadi
3. `requirements-kontent.txt` (PDF/DOCX/OCR asboblari) ni o'rnatadi
4. `npm install` bilan frontend paketlarini o'rnatadi
5. `.env`, `db.sqlite3`, `media/` joyidami tekshiradi
6. `manage.py migrate` yuritadi

**Muhim:** agar skript Python yoki Node'ni yangi o'rnatgan bo'lsa, u
to'xtaydi va PowerShell'ni qayta ochishni so'raydi (PATH yangilanishi
uchun). Qayta ochib, skriptni **yana bir marta** yuriting.

Faqat holatni ko'rish (hech narsa o'rnatmaydi):

```powershell
.\ornatish.ps1 -OrnatmasdanTekshir
```

## 3-qadam — ishga tushirish

Ikkita alohida PowerShell oynasida:

```powershell
.\venv\Scripts\python.exe manage.py runserver 8000
```

```powershell
npm run dev --prefix frontend
```

Brauzerda: **http://localhost:3000**

## Keyin git bilan ishlash

Papka `.git` bilan birga ko'chgani uchun tarix va remote saqlanadi.
Tekshirish:

```powershell
git remote -v
git status
```

Agar `git push` autentifikatsiya so'rasa — GitHub hisobiga qayta kirish
kerak bo'ladi (eski kompyuterdagi kalit ko'chmaydi).

## Nozik joylar

- **`pytesseract` uchun alohida dastur kerak.** Python paketi o'zi
  yetarli emas:
  `winget install --id UB-Mannheim.TesseractOCR`
- **Node versiyasi 20+ bo'lishi shart** (`frontend/package.json`
  `engines`). winget eng yangisini o'rnatadi, muammo bo'lmasligi kerak.
- **`requirements.txt` ga tegmang.** Prod (Railway) faqat shuni
  o'rnatadi. Kontent asboblari alohida `requirements-kontent.txt` da —
  ataylab shunday.
- **Eski `venv` ni ko'chirmang.** Ko'chirilsa ham ishlamaydi: ichida
  absolyut yo'llar va platformaga bog'langan `.pyd` fayllar bor.
- **Ikkala kompyuterda bir vaqtda ishlamang.** `db.sqlite3` va `media/`
  alohida-alohida o'zgaradi va keyin ularni birlashtirib bo'lmaydi.
  Ishni bittasida davom ettiring.
