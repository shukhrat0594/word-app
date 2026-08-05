# Yangi sessiya uchun hendoff prompt — Kurslar blok-mashq generatsiyasi

Quyidagini yangi Claude Code sessiyasiga (shu loyiha papkasida: `D:\shuk\Проекты\claude ai\LMS`) kiriting:

---

## Vazifa va kontekst

LMS (Django+React, "Utmost o'quv markazi") loyihasida **Kurslar** bo'limiga darslik sahifalarini (rasm/ZIP/PDF) yuklab, AI orqali avtomatik mashqqa aylantirish tizimi bor (`courses/blok_generatsiya.py`, `courses/blok_views.py`, frontend `frontend/src/components/BlokMashqi.jsx`, `frontend/src/components/BlokTasdiqlash.jsx`, `frontend/src/pages/Kurslar.jsx`).

Bugungi ish davomida bir necha bosqichda tuzatildi:
1. PDF to'g'ridan-to'g'ri yuklash (ZIP shart emas) — `pypdfium2` orqali.
2. AI natijasi endi bazaga AVTOMATIK yozilmaydi — admin **tasdiqlash oynasi**da (`BlokTasdiqlash.jsx`) ko'rib chiqadi, rasm-quti chegaralarini sudrab tuzatadi, matn/javoblarni tahrirlaydi, keyin "Tasdiqlash va saqlash" bosadi.
3. **Bitta sahifada bir nechta alohida mashq** bo'lishi mumkin (masalan "1 Read and listen", "4 Complete the conversations" — kitobda alohida raqamlangan) — buni ajratish uchun `_mashqlarga_ajrat()` funksiyasi yozildi (`courses/blok_generatsiya.py`).
4. Yangi mashq turi — "so'z banki + raqamlangan rasmlar" (masalan doiradagi 12 ta rasm, har birining javobi so'z bankidan tanlanadi) — `soz_banki`/`rasm_javobli`/`rasm_javobli_grid` tur nomlari bilan.
5. Production OOM va kesh-tozalash buglari tuzatildi.

**Hammasi git'ga push qilingan** (`main` branch, oxirgi commit: `e75079d` — "Sahifani mashq raqami bo'yicha bo'lish, rasm-javob mashqi, tasdiq UI'ni JSON'siz qildi").

## MUAMMO — nega yangi sessiya kerak bo'ldi

`_mashqlarga_ajrat()` (elementlarni sahifadan mashqlarga ajratish) **pozitsiya-asosli o'qish tartibiga** (chap ustun to'liq, keyin o'ng ustun, `_oqish_tartibi_kaliti`) tayanadi. Bu bir necha marta REAL AI sinovida buzilgan holatlar berdi:

- 12 ta rasm (doira shaklida) ikki mashqqa 6+6 bo'lib bo'linib ketdi (ustunlar orasida chetga chiqib ketgani uchun) — `mashq_raqami` maydonini `rasm_javobli` elementiga MAJBURIY qilib biroz tuzatildi.
- 3 ta yonma-yon rasm (Mara/Leo/Nari) — biri boshqa mashqqa ("Stand up and practise") yopishib qoldi. Buni `rasm_qatorlarini_guruhla`/`_rasm_javoblarini_guruhla` chaqiruvini `_mashqlarga_ajrat`dan OLDIN (butun sahifa darajasida) qilib qisman tuzatdim (oxirgi, HALI TEST QILINMAGAN/PUSH QILINMAGAN o'zgarish — commit qilinmagan, ishlab turgan working directory'da bo'lishi mumkin, TEKSHIRING: `git status`).

Bu **pozitsiya-asosli avtomatik guruhlash printsipial jihatdan noishonchli** — har safar yangi sahifa turi (yangi joylashuv) yangi edge-case chiqarishi mumkin.

## YANGI YO'NALISH — foydalanuvchi qarori

Foydalanuvchi avtomatik guruhlashdan voz kechishga qaror qildi. O'rniga:

1. **Rasm-qutilar** — hozirgidek AI taklif qiladi, admin sudrab tasdiqlaydi/tuzatadi (BU QISM O'ZGARMAYDI, allaqachon ishlaydi).
2. **Mashqga biriktirish — DRAG AND DROP**: o'ng tomonda har mashq uchun alohida "quti/karta" bo'ladi (masalan "Mashq 1", "Mashq 2", "+ Yangi mashq"). AI aniqlagan HAR BIR element (rasm ham, matn bloki ham) boshida "erkin" ro'yxatda turadi (yoki AI'ning TAXMINIY guruhlashi bilan boshlanadi — boshidan qurish shart emas). Admin sichqoncha bilan elementni tegishli mashq kartasiga SUDRAB TASHLAYDI.
3. Matn bloklari uchun ham xuddi rasm kabi — mashqga tegishliligi qo'lda tuzatiladi (aynan matn joylashishida ham bug borligi sababli).

**Muhim**: 3-savolga ("matn uchun ham xuddi shu tanlov kerakmi") foydalanuvchi "Something else" dedi, lekin keyin savolni to'liq javoblamasdan sessiyani tugatishga qaror qildi — **bu nuqta ANIQLANMAGAN, yangi sessiyada so'rash kerak**: matn bloklari uchun aynan qanday UI kerak (alohida drag-and-drop, yoki boshqa yechim)?

## Nima qilish kerak (yangi sessiyada)

1. `git status` bilan tekshiring — oxirgi (`rasm_qatorlarini_guruhla`ni oldinga ko'chirish) o'zgarish commit qilinmagan bo'lishi mumkin, uni ko'rib chiqing/push qiling yoki bekor qiling (foydalanuvchi bilan kelishilmagan holda).
2. Foydalanuvchidan matn bloklari uchun drag-and-drop UI qanday bo'lishini SO'RANG (yuqoridagi ANIQLANMAGAN nuqta).
3. Backend: `bloklarni_tayyorla()` endi mashqlarga AVTOMATIK ajratmasin — faqat RAW elementlarni (rasm-idx bilan) qaytarsin, TAXMINIY guruhlashni ("qaysi mashqga tegishli" degan boshlang'ich taxmin) alohida maydon sifatida bering (masalan har elementga `taxminiy_mashq_raqami`), lekin YAKUNIY guruhlash admin tomonidan (frontend orqali) belgilansin.
4. `courses/blok_views.py`: `KursBlokTasdiqlashView`/`_jarayonni_yakunla` — `tahrirlar` payload endi har elementning QAYSI mashqga tegishli ekanini o'z ichiga olishi kerak (masalan har element uchun `mashq_indeksi`).
5. Frontend `BlokTasdiqlash.jsx`: to'liq qayta ko'rib chiqish kerak — drag-and-drop kutubxonasiz (loyihada hech qanday DnD kutubxonasi yo'q, HTML5 drag-and-drop API yoki qo'lda mouse-events bilan qilinishi kerak, xuddi mavjud `QutiTahrirlagich`dagi sudrash mantig'iga o'xshab).

## Foydali fayllar (o'qing, qayta tekshirmasdan ishonmang)

- `courses/blok_generatsiya.py` — AI prompt, `bloklarni_tayyorla`, `_mashqlarga_ajrat`, `_guruh_bloklarini_qur`, `rasm_idxlarni_lokallashtir`.
- `courses/blok_views.py` — `KursBlokSahifaView`, `_jarayonni_yakunla`, `KursBlokTasdiqView`, `KursBlokTasdiqlashView`, `_mashqni_saqla`.
- `frontend/src/components/BlokTasdiqlash.jsx` — hozirgi tasdiqlash oynasi (mashq-kartalar bilan, drag-and-drop YO'Q).
- `frontend/src/components/BlokMashqi.jsx` — talaba/admin ko'radigan yakuniy render (bu O'ZGARMAYDI, faqat ma'lumot manbasi o'zgaradi).

## Sinov uchun material

Foydalanuvchi Headway Beginner darsligining PDF sahifalarini (`C:\Users\Shuk\Downloads\` yoki `C:\Users\Shuk\Desktop\` da qidiring, "Headway" so'zi bilan) real sinov uchun bergan — HAR safar kod o'zgarganda REAL AI chaqiruvi bilan (mock emas) sinab ko'ring, natijani vizual tekshiring (screenshot yoki qayta render qilingan rasm orqali).
