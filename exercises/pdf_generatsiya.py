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
talabi): bitta fayl tanlanadi -> natija darhol bazaga yoziladi.

Asosiy chaqiruv BITTA (butun PDF -> test JSON'i). 2026-07-31 dan yana
QO'SHIMCHA chaqiruvlar bo'lishi mumkin: qismda xarita/diagramma bo'lsa,
o'sha SAHIFA alohida qayta ishlanib rasm kesib olinadi
(`qism_rasmini_kes`) — ya'ni rasmli qismlar soni qancha bo'lsa, shuncha
qo'shimcha chaqiruv.
"""

import io

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
    '      "maxsus_format": {...} (pastdagi JADVAL qoidasiga qarang),\n'
    '      "rasm_sahifasi": 7 (pastdagi RASM qoidasiga qarang)\n'
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
    "\nJADVAL / BLOK-SXEMA QOIDASI (MAJBURIY, TASHLAB KETMANG):\n"
    "Siz PDF sahifalarini KO'RIB turibsiz. Agar savol bloki kitobda "
    "JADVAL (ustun-qatorli to'r), BLOK-SXEMA (o'qlar bilan bog'langan "
    "qutilar) yoki QAYD/XULOSA (Note/Summary) ko'rinishida bo'lsa — uni "
    'oddiy savollar ro\'yxatiga AYLANTIRIB YUBORMANG. Qismga albatta '
    '"maxsus_format" qo\'shing, shunda talaba kitobdagidek ko\'radi:\n'
    '  - Jadval: {"tur":"jadval","sarlavha":"...","ustunlar":[...],'
    '"qatorlar":[["katak {{5}} bilan","ikkinchi katak"],...]} — har qator '
    "massiv, har element bitta katak matni; ustunlar soni har qatorda "
    "bir xil bo'lsin\n"
    '  - Blok-sxema: {"tur":"oqim","sarlavha":"...","qadamlar":["1-qadam '
    '{{26}} bilan",...]} — har qadam alohida quti, orasida o\'q chiziladi\n'
    '  - Oddiy matn (jadval/sxema emas, so\'z banki ham yo\'q): '
    '{"tur":"matn","sarlavha":"...","matn":"to\'liq matn, bo\'sh joylar '
    '{{31}} kabi, qatorlar orasida \\n, ro\'yxat uchun matn boshida "- "}\n'
    "  - {{n}} — o'sha bo'sh joyning BUTUN TEST bo'yicha uzluksiz savol "
    'raqami; u "savollar" massividagi mos savolning tartibiga AYNAN mos '
    "kelishi SHART (masalan 26-savol uchun {{26}})\n"
    '  - Bu holatda ham "savollar"ni ODATDAGIDEK har bir bo\'sh joy uchun '
    'alohida yozing — "maxsus_format" faqat KO\'RINISH uchun, javob '
    "tekshirish baribir \"savollar\"dan olinadi (ikkalasi bir xil SON va "
    "TARTIBDA bo'lishi shart)\n"

    "\nRASM / GRAFIK / DIAGRAMMA QOIDASI:\n"
    "Agar qismda RASM bo'lsa — xarita (Map Labelling), diagramma, "
    "chizma, grafik yoki jadval-rasm — uni matn bilan tasvirlashga "
    "urinmang. Faqat u TURGAN SAHIFA raqamini yozing: "
    '"rasm_sahifasi": 7 (PDF\'ning nechanchi sahifasi, 1 dan boshlab '
    "sanaladi — kitobda chop etilgan sahifa raqami emas, PDF varag'ining "
    "tartibi). Biz o'sha sahifani alohida qayta ishlab, rasmni o'zi "
    "kesib olamiz va qismga biriktiramiz.\n"
    "  - Qismda rasm bo'lmasa — bu maydonni UMUMAN yozmang.\n"
    "  - Bitta qismda bir nechta rasm bo'lsa — ENG KATTA/asosiysining "
    "sahifasini yozing.\n"
    "  - Jadval kitobda oddiy to'r (chiziqlar) bilan chizilgan bo'lsa, u "
    'RASM emas — yuqoridagi "maxsus_format" bilan bering.\n'

    "\nQolgan qoidalar:\n"
    "- PDF'da javoblar kaliti (Answer key) bo'lsa — undan foydalanib "
    '"togri" maydonlarini to\'ldiring. Kalit bo\'lmasa va javobni aniq '
    'bilmasangiz, "togri"ni bo\'sh qoldiring (admin keyin to\'ldiradi) — '
    "javobni O'YLAB TOPMANG.\n"
    "- PDF'da bir nechta test bo'lsa (masalan Test 1 va Test 2) — FAQAT "
    "BIRINCHISINI oling."
)

RASM_KESISH_PROMPT = (
    "Sizga IELTS kitobining BITTA sahifasi rasm sifatida beriladi. Rasm "
    "ustiga PRONUMERLANGAN TO'R chizilgan: chiziqlar har 5 foizda, "
    "chetlarida 0 dan 100 gacha raqamlar.\n\n"

    "Vazifa: shu sahifadagi ASOSIY ILLYUSTRATSIYANI toping — xarita, "
    "diagramma, chizma, grafik yoki sxema — va uning chegarasini TO'R "
    "RAQAMLARI bo'yicha ayting.\n\n"

    'FAQAT shu JSON qaytaring: {"topildi":true,"x1":10,"y1":25,'
    '"x2":90,"y2":60}\n'
    "Illyustratsiya umuman bo'lmasa: {\"topildi\":false}\n\n"

    "Qoidalar:\n"
    "- Chamalab yozmang — chegara qaysi chiziqqa to'g'ri kelishini QARAB "
    "o'qing. Bu eng muhim talab.\n"
    "- Quti illyustratsiyani TO'LIQ o'z ichiga olsin (sarlavhasi va "
    "ichidagi yorliqlar/harflar ham kirsin), lekin atrofidagi ODDIY "
    "MATN (savollar, yo'riqnoma, passage) KIRMASIN.\n"
    "- Bir nechta rasm bo'lsa — eng kattasini oling.\n"
    "- Sahifada faqat matn bo'lsa (rasm yo'q) — \"topildi\":false."
)


def pdf_provider_olish():
    """PDF'ni o'qish uchun Claude (Gemini yo'lida `document` bloki
    ishlatilmaydi).

    Model — `claude-haiku-4-5` (2026-07-31, foydalanuvchi tanladi: tez va
    arzon). Dastlab `claude-sonnet-5` qo'yilgandi, chunki butun passage
    matni AYNAN ko'chirilishi kerak; haiku'da matn qisqarib qolishi yoki
    passage chegarasi chalkashishi ehtimoli yuqoriroq — natija yomon
    chiqsa, birinchi navbatda shu qatorni sonnet'ga qaytarib ko'ring."""
    from django.conf import settings

    from assessment.providers import ClaudeProvider

    kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
    return ClaudeProvider(kalit, model="claude-haiku-4-5", timeout_ms=PDF_TIMEOUT_MS)


def pdf_sahifalar_soni(pdf_bytes):
    """PDF sahifalari soni — kutubxonasiz, xom "/Type /Page" belgilari
    bo'yicha taxminiy hisob. Aniq son shart emas: bu faqat Anthropic'ning
    100-sahifa chegarasidan oshib ketmaslikni oldindan aytish uchun."""
    import re

    try:
        return len(re.findall(rb"/Type\s*/Page[^s]", pdf_bytes))
    except Exception:  # noqa: BLE001 — hisob taxminiy, xatosi jarayonni to'xtatmasin
        return 0


def pdf_sahifani_rasmga(pdf_bytes, sahifa_raqami, kenglik=1400):
    """PDF'ning bitta sahifasini JPEG baytlariga aylantiradi.

    `sahifa_raqami` — 1 dan boshlab (AI shunday sanaydi). Chegaradan
    tashqarida bo'lsa None qaytadi.

    `kenglik` 1400 tanlandi: `courses.blok_generatsiya.rasmni_kes`
    kesilgan bo'lakni 900px gacha kichraytiradi, ya'ni undan sezilarli
    kattaroq manba kesim sifatini saqlaydi; bundan ortig'i esa faqat
    xotira va vaqt sarflaydi."""
    import pypdfium2 as pdfium

    hujjat = pdfium.PdfDocument(pdf_bytes)
    try:
        if not 1 <= sahifa_raqami <= len(hujjat):
            return None
        sahifa = hujjat[sahifa_raqami - 1]
        en = sahifa.get_width() or 1
        rasm = sahifa.render(scale=kenglik / en).to_pil().convert("RGB")
        bufer = io.BytesIO()
        rasm.save(bufer, format="JPEG", quality=88)
        return bufer.getvalue()
    finally:
        hujjat.close()


def qism_rasmini_kes(pdf_bytes, sahifa_raqami):
    """PDF sahifasidan ASOSIY illyustratsiyani kesib oladi.

    Kurslar bo'limidagi isbotlangan usul (`courses.blok_generatsiya`)
    shu yerda qayta ishlatiladi — yangidan yozilmaydi:
      1) sahifa rasmga aylantiriladi;
      2) ustiga PRONUMERLANGAN TO'R chiziladi (`tor_chiz`) — busiz model
         koordinatani ko'z bilan chamalab ±3-5% xato beradi va kesilgan
         rasmga begona matn kirib ketadi (2026-07-28 da Kurslar'da
         o'lchov bilan aniqlangan);
      3) AI to'r raqamlari bo'yicha chegarani aytadi;
      4) `rasmni_kes` asl (to'r chizilmagan) renderdan kesadi — ya'ni
         kesilgan rasmda to'r chiziqlari BO'LMAYDI.

    Qaytaradi: JPEG baytlari yoki None (rasm topilmasa/xato bo'lsa —
    bu butun testni yo'qotmasligi kerak, shuning uchun jim None)."""
    from courses.blok_generatsiya import rasmni_kes, tor_chiz

    sahifa_bytes = pdf_sahifani_rasmga(pdf_bytes, sahifa_raqami)
    if not sahifa_bytes:
        return None
    try:
        torli = tor_chiz(sahifa_bytes)
        provider = pdf_provider_olish()
        javob = provider.generate_json(
            RASM_KESISH_PROMPT,
            "To'r raqamlaridan foydalanib, illyustratsiya chegarasini ayting.",
            torli,
            "image/jpeg",
        )
    except Exception:  # noqa: BLE001 — rasm ixtiyoriy, xatosi testni buzmasin
        return None

    natija = javob.get("natija") or {}
    if not natija.get("topildi"):
        return None
    try:
        quti = {k: float(natija[k]) for k in ("x1", "y1", "x2", "y2")}
    except (KeyError, TypeError, ValueError):
        return None
    if not (0 <= quti["x1"] < quti["x2"] <= 100 and 0 <= quti["y1"] < quti["y2"] <= 100):
        return None
    try:
        return rasmni_kes(sahifa_bytes, quti)
    except Exception:  # noqa: BLE001
        return None


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
