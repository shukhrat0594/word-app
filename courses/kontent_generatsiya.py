"""Beginner Unit kontentini ZIP+AI orqali avtomatlashtirish (2026-07-27).

Admin bitta Unit uchun ZIP yuklaydi (sahifa rasmlari + audio fayllar) —
har sahifa rasmi ALOHIDA AI'ga yuboriladi ("sahifa = mashq" qoidasi:
bitta sahifadagi barcha savollar BITTA `KursMashq`ga, har biri o'z
`pozitsiya`si bilan). Unit ichida UCHTA sahifa turi bo'ladi:

- "mashq" — oddiy topshiriq sahifasi.
- "vocabulary" — Grammar reference + Wordlist BIR sahifada (darslikda
  shunday joylashgan) — grammatika qisqa xulosasi + tarjima yozish uchun
  so'zlar ro'yxati.
- "javob_kaliti" — darslik oxiridagi "Answer key" sahifasi, mashq
  raqami+band raqami bo'yicha guruhlangan to'g'ri javoblar — bularni
  tegishli mashqning "togri" maydoniga OVERRIDE qilish uchun ishlatiladi
  (AI o'zi taxmin qilgan javobdan ko'ra ANIQROQ manba).

2026-07-27 (2-marta): javob kaliti rasmlari ZIP ichida ALOHIDA papkada
("answers" — nomida "answer" so'zi bo'lgan har qanday papka) keladi.
Bu rasmlar UMUMIY 3-tur klassifikatorga EMAS, maxsus (faqat javob_kaliti
kutuvchi) promtga yuboriladi — aks holda AI ularni "mashq" sahifasi deb
tushunib qolishi xavfi bor edi (foydalanuvchi ogohlantirdi). Papka
yo'lidan ANIQ ma'lum bo'lgani uchun klassifikatsiya qilish shart emas.

2026-07-28: provider GEMINI'DAN CLAUDE'GA o'tkazildi — real ZIP bilan
sinovda Gemini haqiqiy (zich matnli) sahifalarda `pozitsiya`ni DEYARLI
HECH QACHON bermadi (promt qanchalik kuchaytirilsa ham), Claude esa
xuddi shu sahifalarda barcha savollarga mantiqiy pozitsiya berdi (sinovda
tasdiqlangan: 8 savolli sahifada 8tasi ham real x/y bilan qaytdi).

Bu modul faqat AI bilan ishlash va fayl nomlaridan tartib/raqam ajratish
mantiqini o'z ichiga oladi — bazaga yozish (`courses/views.py:
KursZipYuklashView`) alohida.
"""

import os
import re

from assessment.providers import ClaudeProvider, ProviderXatosi

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}

SAHIFA_TURLARI = ("mashq", "vocabulary", "javob_kaliti")

# Shape mos kelmasa (masalan "turi" yo'q/noto'g'ri) qayta urinish soni —
# ClaudeProvider._generate o'zi buzuq JSON uchun ICHKARIDA qayta uradi
# (URINISHLAR=2), bu esa BIZNING shakl talabimiz mos kelmasa qo'shimcha
# qatlam (foydalanuvchi talabi: "xato json qaytarsa yana bir marta
# so'rov yuborilsin").
SAHIFA_URINISHLAR = 2

SAHIFA_SYSTEM_PROMPT = (
    "Siz ingliz tili o'quv darsligi (masalan Headway) sahifasini JSON'ga "
    "o'giruvchi yordamchisiz. Sizga BITTA sahifaning rasmi beriladi. "
    "Avval sahifa TURINI aniqlang, keyin shu turga mos JSON qaytaring. "
    "FAQAT JSON qaytaring, boshqa matn/izoh yozmang.\n\n"

    "TUR 1 — MASHQ sahifasi (savol-javob, gap to'ldirish, rasmli topshiriq "
    "va h.k.): sahifada NECHTA kichik topshiriq/savol bo'lsa HAMMASINI "
    "BITTA mashqning savollar ro'yxatiga joylang (alohida-alohida mashq "
    "QILMANG — bitta sahifa har doim bitta mashq, sahifada bir necha "
    "\"Exercise N\" bloki bo'lsa ham):\n"
    "{\n"
    '  "turi": "mashq",\n'
    '  "matn": "sahifadagi umumiy topshiriq/sarlavha (ixtiyoriy)",\n'
    '  "audio_raqamlar": ["1.01", "1.02"] (sahifada ko\'ringan BARCHA audio/track '
    'raqamlari, masalan \\"1.01\\" — ko\'rinmasa umuman yozmang),\n'
    '  "savollar": [\n'
    "    {\n"
    '      "savol": "savol yoki band nomi",\n'
    '      "mashq_raqami": "shu bandning tegishli Exercise raqami, masalan \\"3\\" '
    "(sahifada bir nechta Exercise bloki bo'lsa muhim — javob kaliti bilan "
    'moslashtirish uchun; sahifada faqat bitta Exercise bo\'lsa ham yozing)",\n'
    '      "band_raqami": "shu Exercise ICHIDAGI band/savol raqami, masalan '
    '\\"1\\" (Exercise ichida qaytadan 1dan boshlanadi)",\n'
    '      "variantlar": ["variant1", "variant2"] (ixtiyoriy — ochiq javobli bo\'lsa bo\'sh massiv []),\n'
    '      "togri": "sizning taxminingizcha to\'g\'ri javob (agar aniq bo\'lmasa ham eng yaqin javobni yozing — bu keyin javob kaliti bilan tekshiriladi)",\n'
    '      "pozitsiya": {"x": 0-100, "y": 0-100} — MAJBURIY, deyarli HAR '
    "DOIM yozing (sahifaning BUTUN rasmi mashqga fon sifatida biriktiriladi, "
    "savollar ANIQ shu rasm ustida ko'rsatiladi — shuning uchun HAR bir "
    "savol o'zi tegishli matn/bo'sh joy sahifada QAYERDA joylashganini "
    "ko'rsatishi kerak, faqat rasmli-band uchun emas, ODDIY matn savollari "
    "uchun HAM). Savol matni yoki bo'sh joy (___) sahifaning qaysi qismida "
    "(qaysi qatorda, tepadan pastga, chapdan o'ngga) joylashganini "
    "baholang. MUHIM: \"x\" va \"y\" PIKSEL EMAS, FOIZ (0 dan 100 gacha) — "
    "rasmning HAQIQIY o'lchamidan (piksel) MUSTAQIL nisbiy qiymat. Masalan "
    "savol matni rasmning aynan o'rtasida (gorizontal) va yuqori qismida "
    "bo'lsa — rasm 600px yoki 6000px kenglikda bo'lishidan qat'iy nazar, "
    "\"x\": 50, \"y\": 10 deb yozing (piksel sonini emas, foizni hisoblang: "
    "piksel_x / rasm_kengligi * 100). Bu maydonni FAQAT sahifada bu "
    "savolga tegishli matn UMUMAN topilmasa (masalan sahifadan tashqi "
    "kontekstdan chiqargan savol bo'lsa) tashlab ketasiz — aks holda "
    "har doim taxminiy pozitsiya bering, aniq bo'lmasa ham.\n"
    "    }\n"
    "  ]\n"
    "}\n\n"

    "MUHIM — qaysi bandlarni \"savollar\"ga QO'SHMASLIK kerak (Headway "
    "seriyasida tez-tez uchraydi):\n"
    "- Faqat MUHOKAMA/og'zaki-fikr savollari (\"What do you think?\", "
    "\"Discuss in small groups\", \"Talk to a partner\", rolli o'yin/roleplay "
    "kabi) — bularda \"to'g'ri javob\" umuman yo'q, shuning uchun bunday "
    "bandni ro'yxatga UMUMAN QO'SHMANG (\"togri\" maydoniga o'zingiz "
    "o'ylab chiqargan javob yozmang).\n"
    "- O'z-o'zini baholash/shaxsiyat viktorinasi (masalan savol javoblariga "
    "ball beriladi, keyin ball oralig'iga qarab matn tavsifi o'qiladi, "
    "\"Your scores\" kabi jadval bilan) — bunda ham to'g'ri/noto'g'ri "
    "tushunchasi yo'q, shuning uchun bunday sahifadagi savollarni QO'SHMANG.\n"
    "- Agar band matni boshqa sahifaga havola qilsa (masalan \"Turn to "
    "p154\", \"See Extra material p22\") va o'sha sahifaning rasmi SIZGA "
    "berilgan sahifalar orasida YO'Q bo'lsa, bu bandni QO'SHMANG — "
    "yo'q ma'lumotni taxmin qilib to'ldirmang.\n"
    "- Xato topish/tuzatish mashqlarida (\"There is one mistake in each "
    "sentence, correct it and say what kind of mistake it is\") \"togri\" "
    "maydoniga TUZATILGAN gapni yozing, xato turini qavs ichida qo'shing, "
    "masalan: \"autumn (spelling)\".\n"
    "- Jadval/chart to'ldirish mashqlarida (masalan intervyu jadvali: "
    "\"Where/from?\", \"What/do?\" kabi qator sarlavhalari, ustunlarda "
    "turli odamlar) HAR bir bo'sh katakni ALOHIDA savol sifatida yozing, "
    "\"savol\" maydoniga qator sarlavhasi + kimga tegishli ekanini qo'shing "
    "(masalan \"Kim va Ethan: Where/from?\").\n\n"

    "TUR 2 — VOCABULARY sahifasi (darslikda Grammar reference VA Wordlist "
    "BIR sahifada birga keladi): grammatika qisqa xulosasi (bo'lsa) + "
    "so'zlar ro'yxati (tarjimasi bilan):\n"
    "{\n"
    '  "turi": "vocabulary",\n'
    '  "grammar_matn": "sahifadagi grammatika qoidasining qisqa xulosasi '
    "(bo'lmasa bu maydonni umuman yozmang)\",\n"
    '  "wordlist": [\n'
    '    {"en": "so\'z", "uz": "tarjimasi", "turkum": "so\'z turkumi (ixtiyoriy)", "misol": "namuna gap (ixtiyoriy)"}\n'
    "  ]\n"
    "}\n\n"

    "TUR 3 — JAVOB KALITI sahifasi (darslik oxiridagi \"Answer key\" — "
    "har Exercise uchun ALOHIDA raqamlangan to'g'ri javoblar ro'yxati, "
    "masalan \"Exercise 3: 1. is  2. are  3. am\"):\n"
    "{\n"
    '  "turi": "javob_kaliti",\n'
    '  "javoblar": [\n'
    '    {"mashq_raqami": "3", "band_raqami": "1", "javob": "is"},\n'
    '    {"mashq_raqami": "3", "band_raqami": "2", "javob": "are"}\n'
    "  ]\n"
    "}\n\n"

    "Qoidalar:\n"
    "- \"rasm\" va \"audio\" maydonlarini HECH QACHON JSON'ga qo'shmang — "
    "ular fayl sifatida alohida biriktiriladi, siz haqiqiy fayl yarata olmaysiz.\n"
    "- Sahifa qaysi turga tegishli ekanini ANIQ hal qiling — agar sahifada "
    "ham mashq, ham boshqa narsa bo'lsa, ASOSIY mazmunga qarab bittasini "
    "tanlang.\n"
    "- Faqat yuqoridagi 3 tur JSON obyektidan birini qaytaring, boshqa "
    "shaklda javob bermang."
)

# 2026-07-27 (2-marta): "answers" papkasidagi rasmlar uchun ALOHIDA, faqat
# javob_kaliti kutuvchi promt — bu rasmlar ANIQ shu turga tegishli ekani
# papka yo'lidan ma'lum, klassifikatsiya qilish (va xato qilish xavfi)
# shart emas.
JAVOB_KALITI_SAHIFA_PROMPT = (
    "Siz ingliz tili o'quv darsligi (masalan Headway) darsligining "
    '"Answer key" (javoblar) sahifasini JSON\'ga o\'giruvchi yordamchisiz. '
    "Sizga BITTA javob kaliti sahifasining rasmi beriladi — unda odatda "
    "har Exercise uchun ALOHIDA raqamlangan to'g'ri javoblar ro'yxati bor "
    "(masalan \"Exercise 3: 1. is  2. are  3. am\"). FAQAT quyidagi JSON "
    "qaytaring, boshqa matn/izoh yozmang:\n"
    "{\n"
    '  "turi": "javob_kaliti",\n'
    '  "javoblar": [\n'
    '    {"mashq_raqami": "3", "band_raqami": "1", "javob": "is"},\n'
    '    {"mashq_raqami": "3", "band_raqami": "2", "javob": "are"}\n'
    "  ]\n"
    "}\n"
    "\"mashq_raqami\" — Exercise raqami, \"band_raqami\" — shu Exercise "
    "ICHIDAGI band/savol raqami (har Exercise'da qaytadan 1dan boshlanadi). "
    "Sahifadagi BARCHA Exercise'lar va bandlarni to'liq kiriting, "
    "bittasini ham tashlab ketmang."
)


def tabiiy_tartib_kaliti(fayl_nomi):
    """Fayl nomidagi raqamlarni SONNI hisobga olib tartiblash uchun kalit
    ("1.jpg" < "2.jpg" < "10.jpg" — oddiy alfavit bo'lganda "10" < "2"
    bo'lib qolardi)."""
    return [
        int(qism) if qism.isdigit() else qism
        for qism in re.split(r"(\d+)", fayl_nomi)
    ]


def audio_raqamini_ajrat(fayl_nomi):
    """Audio fayl nomining OXIRIDAGI raqamli segmentni ajratib oladi —
    masalan "Headway_5e_Beg_SB_1.01.mp3" -> "1.01". Avval "N.NN" ko'rinishini
    (Headway audio-CD konventsiyasi — Unit.Track), topilmasa oddiy so'nggi
    raqamni qaytaradi."""
    nom, _ = os.path.splitext(fayl_nomi)
    mos = re.search(r"(\d+\.\d+)$", nom)
    if mos:
        return mos.group(1)
    mos = re.search(r"(\d+)$", nom)
    return mos.group(1) if mos else None


def raqam_kaliti(raqam):
    """Audio/track raqamini SOLISHTIRISH uchun kanonik shaklga o'giradi —
    Gemini "1.1" deb qaytarishi mumkin, fayl nomi esa "1.01" (nolli)
    bo'ladi (2026-07-28, haqiqiy ZIP bilan sinovda topilgan haqiqiy xato:
    12 audiodan atigi 3tasi — 1.10/1.11/1.12 — mos kelib, qolgan 9tasi
    "1.1"≠"1.01" kabi satr solishtirishda mos kelmagan edi). Har nuqta
    bilan ajratilgan segmentni SONGA aylantirib solishtiramiz — "1.1" va
    "1.01" ikkisi ham (1, 1) bo'ladi."""
    if not raqam:
        return None
    try:
        return tuple(int(qism) for qism in str(raqam).split("."))
    except ValueError:
        return str(raqam).strip().lower()


def kengaytma_turi(fayl_nomi):
    """Fayl kengaytmasidan turini aniqlaydi — papka NOMIGA emas, aynan
    kengaytmaga qarab (foydalanuvchi talabi: "nomiga qaramay")."""
    _, ext = os.path.splitext(fayl_nomi.lower())
    if ext in IMAGE_EXTS:
        return "rasm"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def sahifa_provider_olish():
    """2026-07-28: Claude ishlatiladi (Gemini emas) — real ZIP bilan
    sinovda Gemini zich matnli sahifalarda `pozitsiya` bermadi, Claude
    esa berdi (yuqoridagi modul docstringiga qarang)."""
    from django.conf import settings

    kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
    return ClaudeProvider(kalit)


def _pozitsiya_tozala(savollar):
    """Gemini ba'zan "pozitsiya"ni FOIZ (0-100) o'rniga PIKSEL sifatida
    qaytaradi (real testda kuzatilgan: 600px rasmda x=165) — bu frontendda
    inputni butunlay noto'g'ri joyga chiqarib qo'yardi. Diapazondan (0-100)
    tashqari qiymatlar OLIB TASHLANADI (keyin `_pozitsiya_toldir` avtomatik
    o'rnini bosadi) — noto'g'ri joyga chiqarishdan ko'ra avtomatik-taxminiy
    pozitsiya xavfsizroq."""
    for s in savollar:
        poz = s.get("pozitsiya")
        if not isinstance(poz, dict):
            continue
        x, y = poz.get("x"), poz.get("y")
        agar_notogri = (
            not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not (0 <= x <= 100)
            or not (0 <= y <= 100)
        )
        if agar_notogri:
            s.pop("pozitsiya", None)
    return savollar


def _ai_json_urin(provider, prompt, rasm_bytes, rasm_mime, tekshir):
    """Umumiy retry-tsikl: `tekshir(natija)` shakl xatosi bo'lsa xato matnini
    (str) qaytaradi, to'g'ri bo'lsa None. Provider (Claude) o'zi bo'sh/buzuq
    JSON uchun ICHKARIDA qayta uradi — bu tashqi tsikl esa BIZNING shakl
    talabimiz mos kelmasa qayta so'rov yuboradi (foydalanuvchi talabi:
    "xato json qaytarsa yana bir marta so'rov yuborilsin").

    Matn qismi bo'sh emas ("Sahifani tahlil qiling.") — Claude API bo'sh
    matn blokini rad etadi (Gemini bo'sh matnga chidamli edi, lekin bu
    matn ikkalasi uchun ham zararsiz)."""
    oxirgi_xato = None
    for _ in range(SAHIFA_URINISHLAR):
        try:
            javob = provider.generate_json(prompt, "Sahifani tahlil qiling.", rasm_bytes, rasm_mime)
        except ProviderXatosi as e:
            oxirgi_xato = str(e)
            continue
        natija = javob["natija"]
        shakl_xatosi = tekshir(natija)
        if shakl_xatosi:
            oxirgi_xato = shakl_xatosi
            continue
        return natija, None

    return None, oxirgi_xato or "AI yaroqli javob bermadi"


def _sahifa_shaklini_tekshir(natija):
    turi = natija.get("turi")
    if turi not in SAHIFA_TURLARI:
        return f"'turi' maydoni noto'g'ri yoki yo'q (kelgan: {turi!r})"
    if turi == "mashq" and not isinstance(natija.get("savollar"), list):
        return "'mashq' turida 'savollar' massiv emas"
    if turi == "vocabulary" and not isinstance(natija.get("wordlist"), list):
        return "'vocabulary' turida 'wordlist' massiv emas"
    if turi == "javob_kaliti" and not isinstance(natija.get("javoblar"), list):
        return "'javob_kaliti' turida 'javoblar' massiv emas"
    return None


def sahifani_tahlil_qil(provider, rasm_bytes, rasm_mime):
    """Bitta ODDIY (rasm/audio papkasidagi) sahifani AI'ga yuborib,
    tahlil natijasini qaytaradi — turi mashq/vocabulary/javob_kaliti
    bo'lishi mumkin (AI o'zi klassifikatsiya qiladi).

    Qaytaradi: (natija_dict, xato_matni). Muvaffaqiyatli bo'lsa
    xato_matni None, aks holda natija_dict None."""
    natija, xato = _ai_json_urin(
        provider, SAHIFA_SYSTEM_PROMPT, rasm_bytes, rasm_mime, _sahifa_shaklini_tekshir
    )
    if natija and natija.get("turi") == "mashq":
        natija["savollar"] = _pozitsiya_tozala(natija["savollar"])
    return natija, xato


def javob_kaliti_sahifasini_tahlil_qil(provider, rasm_bytes, rasm_mime):
    """"answers" (yoki nomida "answer" bo'lgan) papkadagi rasm — ANIQ javob
    kaliti sahifasi ekani papka yo'lidan ma'lum, shuning uchun umumiy
    3-tur klassifikatorga emas, MAXSUS (faqat javob_kaliti kutuvchi)
    promtga yuboriladi (2026-07-27, foydalanuvchi ogohlantirdi — aks
    holda AI bunday sahifani "mashq" deb tushunib qolishi mumkin edi)."""

    def tekshir(natija):
        if natija.get("turi") != "javob_kaliti" or not isinstance(natija.get("javoblar"), list):
            return f"Javob kaliti shakliga mos kelmadi (kelgan: {natija!r})"
        return None

    return _ai_json_urin(
        provider, JAVOB_KALITI_SAHIFA_PROMPT, rasm_bytes, rasm_mime, tekshir
    )


def _mashq_band_kaliti(mashq_raqami, band_raqami):
    """Mashq/band raqamini SOLISHTIRISH uchun kanonik shaklga o'giradi —
    AI ikki xil sahifada (mashq va javob kaliti) bir xil Exercise'ni
    turlicha yozishi mumkin ("GRAMMAR SPOT" vs "Grammar Spot", ortiqcha
    bo'sh joy) — katta-kichik harf va bo'sh joyga sezmas solishtiramiz."""
    return (str(mashq_raqami or "").strip().lower(), str(band_raqami or "").strip().lower())


def javob_kaliti_indeksla(sahifa_natijalari):
    """Barcha "javob_kaliti" turidagi sahifalardan (mashq_raqami, band_raqami)
    -> javob lug'atini quradi."""
    indeks = {}
    for natija in sahifa_natijalari:
        if natija.get("turi") != "javob_kaliti":
            continue
        for band in natija.get("javoblar", []):
            kalit = _mashq_band_kaliti(band.get("mashq_raqami"), band.get("band_raqami"))
            if kalit != ("", "") and band.get("javob"):
                indeks[kalit] = band["javob"]
    return indeks


def savollarga_javob_kaliti_qoll(savollar, javob_kaliti_indeksi):
    """Har savolga, agar mashq_raqami+band_raqami javob kalitida topilsa,
    ANIQ javobni "togri" maydoniga yozadi (Gemini taxminidan ustun —
    darslikning haqiqiy javob kaliti manbasi)."""
    for s in savollar:
        kalit = _mashq_band_kaliti(s.get("mashq_raqami"), s.get("band_raqami"))
        if kalit in javob_kaliti_indeksi:
            s["togri"] = javob_kaliti_indeksi[kalit]
    return savollar
