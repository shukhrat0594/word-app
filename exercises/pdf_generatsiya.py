"""IELTS Reading/Listening testini PDF'dan to'g'ridan-to'g'ri chiqarish
(2026-07-31).

=== NEGA KERAK ===

Avval yagona yo'l ZIP edi: admin darslikni tashqi AI'ga qo'lda beradi,
u JSON qaytaradi, admin uni ZIP'ga solib yuklaydi. Amalda shu bosqichda
xato chiqardi — foydalanuvchi xabar berdi (2026-07-31): Reading ZIP'da
"passage 2 ning matni passage 3 ga o'tib ketardi". Sabab: tashqi AI'ga
matn NUSXALAB berilganda sahifa chegaralari yo'qoladi va model
passage'lar qayerda tugashini faqat chamalaydi.

PDF'da esa bunday emas: Claude PDF'ni `document` bloki orqali O'ZI
o'qiydi — sahifa tuzilishini ham, matnni ham ko'radi, ya'ni "Reading
Passage 2" sarlavhasi qayerda boshlanib qayerda tugashini chamalamaydi.
Shu sababli bu yerdagi prompt sahifa chegarasi qoidasini ALOHIDA
ta'kidlaydi (`PASSAGE_QOIDASI`).

=== PRINSIP ===

Kurslar bo'limidagi "rasmdan mashq qo'shish" bilan bir xil (foydalanuvchi
talabi): bitta fayl tanlanadi -> bitta sinxron AI chaqiruvi -> natija
darhol bazaga yoziladi. Ko'p-bosqichli jarayon (ZIP'dagi kabi) yo'q.
"""

from assessment.providers import ProviderXatosi

# To'liq IELTS Reading testi (3 passage matni + 40 savol) 4096 tokenga
# sig'maydi — o'lchov bo'yicha ~8-12K token chiqadi.
MAKS_TOKEN = 16000

# Gunicorn 300s'da worker'ni o'ldiradi — 240s zaxira bilan past (xuddi
# `courses.blok_generatsiya.SAHIFA_TIMEOUT_MS` kabi).
PDF_TIMEOUT_MS = 240_000

# Claude PDF hujjat blokining chegarasi (Anthropic API): 100 sahifa,
# 32 MB. Undan kattasi so'rov yuborilmasdan, tushunarli xato bilan
# qaytariladi — aks holda API'dan tushunarsiz 400 kelardi.
MAKS_SAHIFA = 100
MAKS_HAJM_MB = 32

PASSAGE_QOIDASI = (
    "PASSAGE/PART CHEGARASI — ENG MUHIM QOIDA, DIQQAT BILAN BAJARING:\n"
    "Sizga PDF'ning O'ZI berilyapti, ya'ni sahifalarni va sarlavhalarni "
    "o'z ko'zingiz bilan ko'rasiz. Har bir passage (Reading) yoki part "
    "(Listening) matni FAQAT o'sha passage'ga tegishli bo'lishi shart:\n"
    "- Passage 2 ning matni Passage 3 ga O'TIB KETMASIN va aksincha. Bu "
    "eng ko'p uchraydigan xato.\n"
    "- Passage qayerda tugashini SARLAVHADAN aniqlang: keyingi passage "
    "\"READING PASSAGE 3\" (yoki \"Part 3\", \"SECTION 3\") sarlavhasidan "
    "boshlanadi — o'sha sarlavhadan OLDINGI matn oldingi passage'niki, "
    "KEYINGI matn yangisiniki.\n"
    "- Savollar bloki (\"Questions 14-26\") passage MATNIGA KIRMAYDI — u "
    "faqat \"savollar\" massiviga tushadi. \"matn\" maydonida faqat "
    "o'qish matni (passage) bo'lsin.\n"
    "- Passage matnini QISQARTIRMANG va O'Z SO'ZINGIZ BILAN QAYTA "
    "YOZMANG — PDF'dagi matnni AYNAN, to'liq ko'chiring (abzatslar "
    "orasida \\n\\n). Agar passage'da A, B, C... deb belgilangan "
    "abzatslar bo'lsa, o'sha harflarni ham saqlang.\n"
)

PDF_PROMPT = (
    "Siz IELTS test materialini strukturali JSON'ga o'giruvchi "
    "yordamchisiz. Sizga IELTS Reading yoki Listening testining PDF "
    "fayli beriladi (Cambridge IELTS kitobidan yoki shunga o'xshash).\n\n"

    "FAQAT valid JSON obyekt qaytaring — hech qanday izoh, sarlavha yoki "
    "markdown belgisi (```json) qo'shmang.\n\n"

    "Format:\n"
    "{\n"
    '  "name": "Testning to\'liq nomi (masalan \'Cambridge IELTS 21 '
    "Academic Reading Test 4'). PDF'da nom ko'rinmasa, mazmuniga qarab "
    'mos nom o\'ylab toping",\n'
    '  "bolim": "reading" | "listening",\n'
    '  "korinish": "private",\n'
    '  "qismlar": [\n'
    "    {\n"
    '      "tartib": 1,\n'
    '      "sarlavha": "Passage 1" (reading) yoki "Part 1" (listening),\n'
    '      "yoriqnoma": "You should spend about 20 minutes on Questions '
    '1-13, which are based on Reading Passage 1 below.",\n'
    '      "matn": "Reading uchun passage matni TO\'LIQ shu yerga. '
    'Listening uchun bo\'sh qoldiring ("") — audio alohida yuklanadi.",\n'
    '      "savollar": [\n'
    "        {\n"
    '          "savol": "Savol yoki band matni",\n'
    '          "tur": "quyidagi ro\'yxatdan",\n'
    '          "variantlar": ["variant1", "variant2"],\n'
    '          "togri": "To\'g\'ri javob (bir nechta qabul qilinadigan '
    'javob bo\'lsa — massiv, masalan ["20%", "twenty percent"])",\n'
    '          "guruh_boshi": "Questions 1-7" (ixtiyoriy — faqat '
    "guruhning BIRINCHI savolida yozing, qolganida bo'sh qoldiring)\n"
    "        }\n"
    "      ],\n"
    '      "maxsus_format": {...} (ixtiyoriy — pastdagi qoidaga qarang)\n'
    "    }\n"
    "  ]\n"
    "}\n\n"

    + PASSAGE_QOIDASI +

    "\nQolgan qoidalar:\n"
    '- "bolim"="reading" bo\'lsa "tur": multiple_choice, tfng, '
    "matching_headings, matching, fill_blanks, short_answer\n"
    '- "bolim"="listening" bo\'lsa "tur": multiple_choice, fill_blanks, '
    "matching, map_labelling, short_answer\n"
    '- True/False/Not Given savollarida "variantlar": ["True", "False", '
    '"Not Given"]. Yes/No/Not Given bo\'lsa mos ravishda ["Yes", "No", '
    '"Not Given"]\n'
    '- Ochiq javobli (fill_blanks/short_answer) savollarda "variantlar"ni '
    "bo'sh massiv [] qoldiring\n"
    "- **So'z banki bilan bo'sh joy to'ldirish** (Summary/Note Completion "
    "with a word list): har bir bo'sh joy uchun ALOHIDA savol "
    '(tur="fill_blanks"), "savol"ga o\'sha bo\'sh joygacha bo\'lgan matn '
    'parchasi, HAMMASIGA BIR XIL "variantlar" (butun so\'z banki) — '
    "frontend bularni avtomatik bitta oqim+bank qilib birlashtiradi\n"
    '- Savollarni RAQAMLAMANG ("1. ..." deb yozmang) — raqamlash '
    "frontend'da avtomatik, barcha qismlar bo'yicha uzluksiz qo'yiladi\n"
    '- "tartib" — qismning testdagi raqami (1,2,3...)\n'
    "- Har qismdagi savollar soni real testdagidek bo'lsin (Reading har "
    "passage ~13-14 ta, Listening har part ~10 ta)\n"
    "- **Table/Note/Summary/Flow-chart Completion** (asl kitobdagi "
    'jadval/blok-sxema ko\'rinishida) — qismga "maxsus_format" qo\'shing:\n'
    '  - Jadval: {"tur":"jadval","sarlavha":"...","ustunlar":[...],'
    '"qatorlar":[["katak {{5}} bilan","ikkinchi katak"],...]}\n'
    '  - Flow-chart: {"tur":"oqim","sarlavha":"...","qadamlar":["1-qadam '
    '{{26}} bilan",...]}\n'
    '  - Oddiy matn (jadval/sxema emas, bank ham yo\'q): {"tur":"matn",'
    '"sarlavha":"...","matn":"to\'liq matn, bo\'sh joylar {{31}} kabi"}\n'
    "  - {{n}} — o'sha bo'sh joyning BUTUN TEST bo'yicha uzluksiz savol "
    'raqami; u "savollar" massividagi mos savolning tartibiga AYNAN mos '
    "kelishi SHART\n"
    '  - Bu holatda ham "savollar"ni ODATDAGIDEK har bir bo\'sh joy uchun '
    'alohida yozing — "maxsus_format" faqat KO\'RINISH uchun, javob '
    'tekshirish baribir "savollar"dan olinadi\n'
    "- PDF'da javoblar kaliti (Answer key) bo'lsa — undan foydalanib "
    '"togri" maydonlarini to\'ldiring. Kalit bo\'lmasa va javobni aniq '
    'bilmasangiz, "togri"ni bo\'sh qoldiring (admin keyin to\'ldiradi) — '
    "javobni O'YLAB TOPMANG.\n"
    "- PDF'da bir nechta test bo'lsa (masalan Test 1 va Test 2) — FAQAT "
    "BIRINCHISINI oling.\n"
    "- Rasm (Map/Diagram Labelling) PDF'da bo'lsa ham uni chiqara "
    'olmaysiz — bunday savollarni oddiy savol sifatida yozing, "rasm" '
    "maydonini umuman yozmang (admin rasmni keyin qo'lda biriktiradi)."
)


def pdf_provider_olish():
    """PDF'ni o'qish uchun Claude (Gemini yo'lida `document` bloki
    ishlatilmaydi). Model — `claude-sonnet-5`: bu yerda ANIQLIK narxdan
    muhimroq, chunki butun passage matni aynan ko'chirilishi kerak
    (haiku qisqartirib yuborish/chalkashtirishga moyil)."""
    from django.conf import settings

    from assessment.providers import ClaudeProvider

    kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
    return ClaudeProvider(kalit, model="claude-sonnet-5", timeout_ms=PDF_TIMEOUT_MS)


def pdf_sahifalar_soni(pdf_bytes):
    """PDF sahifalari soni — kutubxonasiz, xom "/Type /Page" belgilari
    bo'yicha taxminiy hisob. Aniq son shart emas: bu faqat Anthropic'ning
    100-sahifa chegarasidan oshib ketmaslikni oldindan aytish uchun."""
    import re

    try:
        return len(re.findall(rb"/Type\s*/Page[^s]", pdf_bytes))
    except Exception:  # noqa: BLE001 — hisob taxminiy, xatosi jarayonni to'xtatmasin
        return 0


def pdfdan_test_chiqar(pdf_bytes, bolim=""):
    """PDF -> IELTS test JSON'i (`_test_yarat` kutadigan format).

    Qaytaradi: (data, xato_matni) — biri doim None."""
    if len(pdf_bytes) > MAKS_HAJM_MB * 1024 * 1024:
        return None, f"PDF juda katta (chegara {MAKS_HAJM_MB} MB)"
    sahifalar = pdf_sahifalar_soni(pdf_bytes)
    if sahifalar > MAKS_SAHIFA:
        return None, (
            f"PDF juda uzun (~{sahifalar} sahifa, chegara {MAKS_SAHIFA}) — "
            "faqat kerakli sahifalarni ajratib yuklang"
        )

    topshiriq = "Shu PDF'dagi IELTS testini yuqoridagi JSON formatiga o'giring."
    if bolim in ("reading", "listening"):
        topshiriq += f' Bu {bolim} bo\'limi — "bolim" maydoniga "{bolim}" yozing.'

    try:
        provider = pdf_provider_olish()
        javob = provider.generate_json_pdf(PDF_PROMPT, topshiriq, pdf_bytes, MAKS_TOKEN)
    except ProviderXatosi as e:
        return None, str(e)
    except Exception as e:  # noqa: BLE001 — SDK/tarmoqning kutilmagan xatosi
        return None, f"{type(e).__name__}: {e}"

    data = javob.get("natija")
    if not isinstance(data, dict):
        return None, "AI yaroqli JSON qaytarmadi"
    return data, None
