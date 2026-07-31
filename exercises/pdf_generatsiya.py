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

# 1-bosqich (reja) chiqishi juda kichik — nom + qismlar ro'yxati.
REJA_MAKS_TOKEN = 2000

# 2-bosqich: bitta passage matni (~900 so'z) + ~14 savol => ~4-5K token.
# 8000 zaxira bilan yetarli; kattaroq qilish faqat kutishni uzaytiradi.
QISM_MAKS_TOKEN = 8000

# BITTA AI chaqiruvi uchun timeout. Endi har chaqiruv qisqa (bitta
# passage), shuning uchun 240s emas, 120s — muammo bo'lsa tez bilinadi.
PDF_TIMEOUT_MS = 120_000

# BUTUN so'rov uchun vaqt budjeti. Gunicorn 300s'da worker'ni o'ldiradi;
# 200s'da to'xtab, qolgan qismlarni "chiqarilmadi" deb aytganimiz —
# proxy uzib qo'yib, foydalanuvchiga tushunarsiz xato ko'rsatganidan
# yaxshiroq (2026-07-31 da aynan shu holat bo'lgan edi).
JAMI_BUDJET_SONIYA = 200

# Claude PDF hujjat blokining chegarasi (Anthropic API): 100 sahifa,
# 32 MB. Undan kattasi so'rov yuborilmasdan, tushunarli xato bilan
# qaytariladi — aks holda API'dan tushunarsiz 400 kelardi.
MAKS_SAHIFA = 100
MAKS_HAJM_MB = 32

# Bo'lak PDF'ga oxiridan qo'shiladigan ZAXIRA sahifa (2026-07-31).
# Sabab: foydalanuvchi 40 o'rniga 38 savol oldi. Reja bosqichi
# "tugash_sahifa"ni bir varaq kalta bergan bo'lsa, savollar blokining
# dumi bo'lak PDF'ga UMUMAN tushmaydi — model uni ko'rmaydi ham, ya'ni
# prompt bilan tuzatib bo'lmaydi. Bir sahifa zaxira shu holatni yopadi;
# qo'shni passage matni kirib ketmasligi uchun promptda ALOHIDA
# ogohlantiriladi.
ZAXIRA_SAHIFA = 1

PASSAGE_QOIDASI = (
    "PASSAGE/PART CHEGARASI — ENG MUHIM QOIDA:\n"
    "Sizga PDF'ning O'ZI berilyapti, ya'ni sahifalarni va sarlavhalarni "
    "o'z ko'zingiz bilan ko'rasiz. Passage qayerda tugashini SARLAVHADAN "
    "aniqlang: keyingi passage \"READING PASSAGE 3\" (yoki \"Part 3\", "
    "\"SECTION 3\") sarlavhasidan boshlanadi — o'sha sarlavhadan OLDINGI "
    "matn oldingi passage'niki, KEYINGI matn yangisiniki.\n"
)

# ======================================================================
# 1-BOSQICH: REJA
# ======================================================================
# Butun PDF bo'yicha FAQAT tuzilma so'raladi (nomi, nechta passage,
# qaysi sahifalarda) — matn va savollar EMAS. Chiqish juda kichik
# (~500 token), shuning uchun tez va xatosiz.

REJA_PROMPT = (
    "Siz IELTS test materialini tahlil qiluvchi yordamchisiz. Sizga IELTS "
    "Reading yoki Listening testining PDF fayli beriladi.\n\n"

    "Vazifa: FAQAT TUZILMANI aniqlang — testning nomi va unda nechta "
    "passage/part bor, har biri PDF'ning qaysi sahifalarida joylashgan. "
    "Passage MATNINI va SAVOLLARNI bu bosqichda YOZMANG — ular keyin "
    "alohida so'raladi.\n\n"

    + PASSAGE_QOIDASI +

    "\nQoidalar:\n"
    "- \"name\": testning to'liq nomi (masalan \"Cambridge IELTS 21 "
    "Academic Reading Test 4\"). PDF'da nom ko'rinmasa mazmuniga qarab "
    "mos nom o'ylab toping.\n"
    "- \"bolim\": \"reading\" yoki \"listening\".\n"
    "- Har qism uchun \"boshlanish_sahifa\" va \"tugash_sahifa\" — "
    "PDF varag'ining tartib raqami (1 dan boshlab sanaladi, kitobda chop "
    "etilgan sahifa raqami EMAS). Oraliq SHU passage'ning matnini HAM, "
    "unga tegishli savollarni HAM qamrab olsin.\n"
    "- Oraliqlar bir-birining ustiga tushmasin.\n"
    "- \"yoriqnoma\": kitobdagi ko'rsatma (masalan \"You should spend "
    "about 20 minutes on Questions 1-13...\"). Bo'lmasa bo'sh qoldiring.\n"
    "- \"birinchi_savol\" va \"oxirgi_savol\" — SHU qismning savol "
    "raqamlari oralig'i (masalan Passage 2 uchun 14 va 26). Kitobda "
    "\"Questions 14-26\" deb yozilgan bo'ladi; ko'rinmasa savollarni "
    "sanab chiqing. BU MUHIM: shu raqamlar bo'yicha keyin har qism "
    "TO'LIQ chiqqanini tekshiramiz.\n"
    "- PDF'da bir nechta test bo'lsa — FAQAT BIRINCHISINI oling.\n"
    "- Javoblar kaliti (Answer key) sahifalarini qismlarga QO'SHMANG."
)

REJA_SXEMASI = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "bolim": {"type": "string", "enum": ["reading", "listening"]},
        "qismlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tartib": {"type": "integer"},
                    "sarlavha": {"type": "string"},
                    "yoriqnoma": {"type": "string"},
                    "boshlanish_sahifa": {"type": "integer"},
                    "tugash_sahifa": {"type": "integer"},
                    "birinchi_savol": {"type": "integer"},
                    "oxirgi_savol": {"type": "integer"},
                },
                "required": [
                    "tartib", "sarlavha", "yoriqnoma",
                    "boshlanish_sahifa", "tugash_sahifa",
                    "birinchi_savol", "oxirgi_savol",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["name", "bolim", "qismlar"],
    "additionalProperties": False,
}

# ======================================================================
# 2-BOSQICH: BITTA QISM
# ======================================================================
# Har passage uchun PDF'ning FAQAT o'sha sahifalari yuboriladi
# (`pdf_bolagini_ol`). Ikki foydasi bor: (1) kirish tokenlari keskin
# kamayadi, ya'ni chaqiruv tez tugaydi; (2) model faqat bitta passage'ni
# ko'radi, ya'ni "matn qo'shni passage'ga o'tib ketishi" fizik jihatdan
# imkonsiz bo'ladi — foydalanuvchining ASOSIY shikoyati shu edi.

QISM_PROMPT = (
    "Siz IELTS test materialini strukturali JSON'ga o'giruvchi "
    "yordamchisiz. Sizga IELTS testining BITTA passage/part'iga tegishli "
    "sahifalar beriladi.\n\n"

    "Vazifa: shu passage'ning MATNINI va unga tegishli SAVOLLARNI "
    "chiqaring.\n\n"

    "DIQQAT — CHEGARA: berilgan varaqlarning oxirida QO'SHNI qismning "
    "boshi ham ko'rinib qolishi mumkin (biz ataylab bir varaq zaxira "
    "qo'shamiz, savollar dumi kesilib qolmasin deb). Sizga topshiriqda "
    "AYNAN qaysi qism kerakligi va uning savol raqamlari aytiladi — "
    "FAQAT o'shani oling. Keyingi passage sarlavhasidan (\"READING "
    "PASSAGE ...\", \"Part ...\", \"SECTION ...\") keyingi matnni va "
    "unga tegishli savollarni QO'SHMANG.\n\n"

    "MATN QOIDASI:\n"
    "- \"matn\" — FAQAT o'qish matni (passage). Savollar bloki "
    "(\"Questions 14-26\") va yo'riqnomalar unga KIRMAYDI.\n"
    "- Matnni QISQARTIRMANG va O'Z SO'ZINGIZ BILAN QAYTA YOZMANG — "
    "PDF'dagi matnni AYNAN, to'liq ko'chiring (abzatslar orasida \\n\\n).\n"
    "- Passage'da A, B, C... deb belgilangan abzatslar bo'lsa, o'sha "
    "harflarni ham saqlang.\n"
    "- Listening bo'lsa \"matn\"ni bo'sh qoldiring (audio alohida "
    "yuklanadi), faqat savollarni chiqaring.\n\n"

    "SAVOLLAR QOIDASI:\n"
    "- Savollarni RAQAMLAMANG (\"1. ...\" deb yozmang) — raqamlash "
    "frontend'da avtomatik qo'yiladi.\n"
    "- \"tur\": reading uchun multiple_choice, tfng, matching_headings, "
    "matching, fill_blanks, short_answer; listening uchun "
    "multiple_choice, fill_blanks, matching, map_labelling, "
    "short_answer.\n"
    "- True/False/Not Given savollarida \"variantlar\": [\"True\", "
    "\"False\", \"Not Given\"]. Yes/No/Not Given bo'lsa mos ravishda.\n"
    "- Ochiq javobli (fill_blanks/short_answer) savollarda "
    "\"variantlar\" bo'sh massiv [].\n"
    "- \"guruh_boshi\": guruh sarlavhasi (masalan \"Questions 1-7\") — "
    "FAQAT guruhning BIRINCHI savolida yozing, qolganida bo'sh.\n"
    "- **So'z banki bilan bo'sh joy to'ldirish**: har bo'sh joy uchun "
    "ALOHIDA savol (tur=\"fill_blanks\"), \"savol\"ga o'sha bo'sh "
    "joygacha bo'lgan matn parchasi, HAMMASIGA BIR XIL \"variantlar\" "
    "(butun so'z banki).\n"
    "- PDF'da javoblar kaliti bo'lsa \"togri\"ni undan to'ldiring. "
    "Kalit bo'lmasa va javobni aniq bilmasangiz \"togri\"ni bo'sh "
    "qoldiring — javobni O'YLAB TOPMANG.\n\n"

    "JADVAL / BLOK-SXEMA QOIDASI:\n"
    "Agar savol bloki kitobda JADVAL (ustun-qatorli to'r), BLOK-SXEMA "
    "(o'qlar bilan bog'langan qutilar) yoki QAYD/XULOSA ko'rinishida "
    "bo'lsa — uni oddiy savollar ro'yxatiga AYLANTIRIB YUBORMANG, "
    "\"maxsus_format\" to'ldiring:\n"
    "- Jadval: {\"tur\":\"jadval\",\"sarlavha\":\"...\","
    "\"ustunlar\":[...],\"qatorlar\":[[\"katak {{5}} bilan\",\"ikkinchi "
    "katak\"]]} — ustunlar soni har qatorda bir xil bo'lsin.\n"
    "- Blok-sxema: {\"tur\":\"oqim\",\"sarlavha\":\"...\","
    "\"qadamlar\":[\"1-qadam {{26}} bilan\"]}\n"
    "- Oddiy matn (jadval/sxema emas, so'z banki ham yo'q): "
    "{\"tur\":\"matn\",\"sarlavha\":\"...\",\"matn\":\"to'liq matn, "
    "bo'sh joylar {{31}} kabi\"}\n"
    "- {{n}} — BUTUN TEST bo'yicha uzluksiz savol raqami. Sizga shu "
    "qismning birinchi savoli qaysi raqamdan boshlanishi aytiladi.\n"
    "- \"maxsus_format\" faqat KO'RINISH uchun — javob tekshirish "
    "baribir \"savollar\"dan olinadi, ikkalasi bir xil SON va TARTIBDA "
    "bo'lishi shart.\n"
    "- Jadval/sxema yo'q bo'lsa \"maxsus_format\"ni null qoldiring.\n\n"

    "RASM QOIDASI:\n"
    "Agar qismda RASM bo'lsa — xarita (Map Labelling), diagramma, "
    "chizma yoki grafik — uni matn bilan tasvirlashga urinmang. Faqat "
    "\"rasm_sahifasi\"ga u turgan PDF varag'ining raqamini yozing "
    "(sizga qaysi varaqlar berilganini aytamiz). Rasm bo'lmasa null."
)

QISM_SXEMASI = {
    "type": "object",
    "properties": {
        "matn": {"type": "string"},
        # `anyOf` — hujjatda ANIQ qo'llab-quvvatlanadi deb yozilgan;
        # {"type": ["integer","null"]} massiv shakli esa yozilmagan.
        "rasm_sahifasi": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "savollar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "savol": {"type": "string"},
                    "tur": {"type": "string"},
                    "variantlar": {"type": "array", "items": {"type": "string"}},
                    # Ba'zi savollarda bir nechta javob qabul qilinadi
                    # (masalan "20%" va "twenty percent") — shuning uchun
                    # string HAM, massiv HAM ruxsat.
                    "togri": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "guruh_boshi": {"type": "string"},
                },
                "required": ["savol", "tur", "variantlar", "togri", "guruh_boshi"],
                "additionalProperties": False,
            },
        },
        "maxsus_format": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "tur": {"type": "string", "enum": ["jadval"]},
                        "sarlavha": {"type": "string"},
                        "ustunlar": {"type": "array", "items": {"type": "string"}},
                        "qatorlar": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "required": ["tur", "sarlavha", "ustunlar", "qatorlar"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "tur": {"type": "string", "enum": ["oqim"]},
                        "sarlavha": {"type": "string"},
                        "qadamlar": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["tur", "sarlavha", "qadamlar"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "tur": {"type": "string", "enum": ["matn"]},
                        "sarlavha": {"type": "string"},
                        "matn": {"type": "string"},
                    },
                    "required": ["tur", "sarlavha", "matn"],
                    "additionalProperties": False,
                },
            ]
        },
    },
    "required": ["matn", "rasm_sahifasi", "savollar", "maxsus_format"],
    "additionalProperties": False,
}


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



def pdf_bolagini_ol(pdf_bytes, boshlanish, tugash):
    """PDF'dan FAQAT [boshlanish..tugash] sahifalarini yangi PDF qilib
    ajratadi (1 dan boshlab, ikkala chegara ham kiradi).

    Nega kerak: har passage uchun butun PDF'ni qayta yuborish kirish
    tokenlarini bir necha barobar oshiradi va chaqiruvni sekinlashtiradi.
    Bundan tashqari model faqat bitta passage'ni ko'rsa, matn qo'shni
    passage'ga o'tib keta olmaydi.

    Chegaralar noto'g'ri bo'lsa None qaytadi — chaqiruvchi butun PDF'ga
    qaytadi (xavfsiz zaxira)."""
    import pypdfium2 as pdfium

    manba = pdfium.PdfDocument(pdf_bytes)
    try:
        jami = len(manba)
        b = max(1, min(int(boshlanish), jami))
        t = max(b, min(int(tugash), jami))
        if b > jami:
            return None
        bolak = pdfium.PdfDocument.new()
        try:
            bolak.import_pages(manba, list(range(b - 1, t)))
            bufer = io.BytesIO()
            bolak.save(bufer)
            return bufer.getvalue()
        finally:
            bolak.close()
    except Exception:  # noqa: BLE001 — zaxira yo'l bor, jarayon to'xtamasin
        return None
    finally:
        manba.close()


def _kutilgan_savol_soni(qism_rejasi):
    """Reja aytgan savol raqamlari oralig'idan savol sonini hisoblaydi.
    Reja bermasa yoki qiymatlar bema'ni bo'lsa None."""
    try:
        b = int(qism_rejasi["birinchi_savol"])
        o = int(qism_rejasi["oxirgi_savol"])
    except (KeyError, TypeError, ValueError):
        return None
    return o - b + 1 if 0 < b <= o else None


def _qismni_chiqar(provider, pdf_bytes, qism_rejasi, bolim, boshlangich_raqam,
                   kamchilik=None):
    """Bitta passage/part uchun matn + savollar. (natija, xato) qaytaradi.

    `kamchilik` — (chiqqan_soni, kutilgan_soni). Berilsa bu QAYTA so'rov:
    modelga nechta savol tashlab ketgani aniq aytiladi."""
    b = qism_rejasi.get("boshlanish_sahifa") or 1
    t = qism_rejasi.get("tugash_sahifa") or b
    # Oxiriga ZAXIRA sahifa — savollar bloki keyingi varaqqa o'tib ketgan
    # bo'lsa ham modelga ko'rinsin (tafsilot: `ZAXIRA_SAHIFA` izohi).
    bolak = pdf_bolagini_ol(pdf_bytes, b, t + ZAXIRA_SAHIFA) or pdf_bytes

    kutilgan = _kutilgan_savol_soni(qism_rejasi)
    topshiriq = (
        f"Bu {bolim} bo'limining \"{qism_rejasi.get('sarlavha') or ''}\" qismi.\n"
        f"Berilgan varaqlar PDF'ning {b}-{t + ZAXIRA_SAHIFA} sahifalari "
        f"(oxirgi varaq — zaxira, unda keyingi qismning boshi bo'lishi "
        f"mumkin). \"rasm_sahifasi\"ni shu oraliqdagi raqam bilan yozing.\n"
        f"Bu qismning birinchi savoli butun test bo'yicha "
        f"{boshlangich_raqam}-savol — {{{{n}}}} raqamlarini shundan boshlab "
        "sanang."
    )
    if kutilgan:
        topshiriq += (
            f"\nBu qismda AYNAN {kutilgan} ta savol bo'lishi kerak "
            f"({boshlangich_raqam}-{boshlangich_raqam + kutilgan - 1}). "
            "Hammasini chiqaring — bittasini ham tashlab ketmang. Agar "
            "savol jadval yoki blok-sxema ichidagi bo'sh joy bo'lsa, u ham "
            "alohida savol sifatida sanaladi."
        )
    if kamchilik:
        chiqqan, kerak = kamchilik
        topshiriq += (
            f"\n\nDIQQAT — QAYTA SO'ROV: oldingi urinishda siz {chiqqan} ta "
            f"savol qaytardingiz, lekin {kerak} ta bo'lishi kerak. "
            "Sahifalarni QAYTADAN, boshidan oxirigacha ko'zdan kechiring: "
            "jadval kataklaridagi bo'sh joylar, blok-sxema qutilari, "
            "so'z banki bilan to'ldiriladigan har bir bo'sh joy — "
            "bularning HAR BIRI alohida savol. Keyingi varaqqa o'tib "
            "ketgan savollarni ham qo'shing."
        )
    try:
        javob = provider.generate_json_pdf(
            QISM_PROMPT, topshiriq, bolak,
            max_tokens=QISM_MAKS_TOKEN, javob_sxemasi=QISM_SXEMASI,
        )
    except ProviderXatosi as e:
        return None, str(e)
    except Exception as e:  # noqa: BLE001 — SDK/tarmoqning kutilmagan xatosi
        return None, f"{type(e).__name__}: {e}"

    natija = javob.get("natija")
    if not isinstance(natija, dict):
        return None, "AI yaroqli JSON qaytarmadi"
    return natija, None


def pdfdan_test_chiqar(pdf_bytes, bolim="", nom="", oraliqlar=None):
    """PDF -> IELTS test JSON'i (`_test_yarat` kutadigan format).

    IKKI BOSQICHLI (2026-07-31 da qayta yozildi). Avval BITTA katta
    chaqiruv bor edi — u ikki sabab bilan ishlamadi (foydalanuvchi
    production'da uchradi):
      1) 10K+ belgilik JSON'ni model qo'lda yozganda passage matnidagi
         qo'shtirnoqni qochirmay yuborardi -> "Expecting ',' delimiter".
         Endi Structured Outputs (`javob_sxemasi`) yaroqli JSON'ni
         KAFOLATLAYDI.
      2) Bitta so'rov juda uzoq cho'zilib timeout'ga tushardi (yoki
         chala test yaratardi). Endi har passage alohida, QISQA
         chaqiruv — va unga PDF'ning faqat o'z sahifalari yuboriladi.

    Umumiy VAQT BUDJETI bor: budjet tugasa qolgan qismlar tashlanadi va
    `xatolar`da aniq aytiladi — gunicorn uzib qo'yishidan ko'ra
    "nima yetishmadi" deb aytgan yaxshiroq.

    `nom` va `oraliqlar` — ADMIN yuklash oynasida bergan ma'lumot
    (2026-07-31 talabi). `oraliqlar` = [{"boshi": 1, "oxiri": 14}, ...].
    Nega admin beradi: AI savol oraliqlarini o'zi taxmin qilganda 40
    o'rniga 38 savol chiqargan edi, test nomini ham noto'g'ri olgandi.
    Admin bergan oraliq — HAQIQAT MANBASI: har qismdan aynan shuncha
    savol kutiladi, kam chiqsa QAYTA so'raladi, baribir kam bo'lsa
    `xatolar`da aniq aytiladi (jim 38 bo'lib qolmaydi).

    Qaytaradi: (data, xato_matni, xatolar_royxati)."""
    import time

    if len(pdf_bytes) > MAKS_HAJM_MB * 1024 * 1024:
        return None, f"PDF juda katta (chegara {MAKS_HAJM_MB} MB)", []
    sahifalar = pdf_sahifalar_soni(pdf_bytes)
    if sahifalar > MAKS_SAHIFA:
        return None, (
            f"PDF juda uzun (~{sahifalar} sahifa, chegara {MAKS_SAHIFA}) — "
            "faqat kerakli sahifalarni ajratib yuklang"
        ), []

    boshlandi = time.monotonic()
    try:
        provider = pdf_provider_olish()
    except ProviderXatosi as e:
        return None, str(e), []

    # --- 1-bosqich: reja ---
    topshiriq = "Shu PDF'dagi IELTS testining tuzilmasini aniqlang."
    if bolim in ("reading", "listening"):
        topshiriq += f' Bu {bolim} bo\'limi — "bolim" maydoniga "{bolim}" yozing.'
    try:
        javob = provider.generate_json_pdf(
            REJA_PROMPT, topshiriq, pdf_bytes,
            max_tokens=REJA_MAKS_TOKEN, javob_sxemasi=REJA_SXEMASI,
        )
    except ProviderXatosi as e:
        return None, str(e), []
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", []

    reja = javob.get("natija")
    if not isinstance(reja, dict):
        return None, "AI yaroqli JSON qaytarmadi", []
    reja_qismlar = reja.get("qismlar") or []
    if not reja_qismlar:
        return None, "PDF'da passage/part topilmadi", []
    reja_qismlar.sort(key=lambda q: q.get("tartib") or 0)

    # Admin oraliq bergan bo'lsa — u HAQIQAT MANBASI. Rejaning o'z
    # taxminini almashtiramiz (sahifa oraliqlari esa rejadan qoladi —
    # admin qaysi varaqda ekanini bilmaydi).
    oraliqlar = oraliqlar or []
    if oraliqlar and len(oraliqlar) != len(reja_qismlar):
        xatolar_boshlangich = [
            f"Siz {len(oraliqlar)} ta qism kiritdingiz, PDF'da "
            f"{len(reja_qismlar)} ta topildi — oraliqlar tartib bo'yicha "
            "moslashtirildi"
        ]
    else:
        xatolar_boshlangich = []
    for i, rq in enumerate(reja_qismlar):
        if i < len(oraliqlar):
            rq["birinchi_savol"] = oraliqlar[i].get("boshi")
            rq["oxirgi_savol"] = oraliqlar[i].get("oxiri")

    # --- 2-bosqich: har qism alohida ---
    qismlar, xatolar = [], list(xatolar_boshlangich)
    keyingi_savol_raqami = 1
    test_bolimi = reja.get("bolim") or bolim or "reading"
    for i, rq in enumerate(reja_qismlar, start=1):
        qism_nomi = rq.get("sarlavha") or f"{i}-qism"
        if time.monotonic() - boshlandi > JAMI_BUDJET_SONIYA:
            xatolar.append(f"{qism_nomi}: vaqt budjeti tugadi, chiqarilmadi")
            continue

        kutilgan = _kutilgan_savol_soni(rq)
        boshi = rq.get("birinchi_savol") or keyingi_savol_raqami
        natija, xato = _qismni_chiqar(
            provider, pdf_bytes, rq, test_bolimi, boshi,
        )
        if xato:
            xatolar.append(f"{qism_nomi}: {xato}")
            continue
        savollar = natija.get("savollar") or []

        # Savol soni kutilganidan KAM bo'lsa BIR marta qayta so'raymiz —
        # aynan shu holat "40 o'rniga 38" bo'lib chiqqan edi. Budjet
        # yetmasa qayta so'ramaymiz, faqat ogohlantiramiz.
        if (kutilgan and len(savollar) != kutilgan
                and time.monotonic() - boshlandi <= JAMI_BUDJET_SONIYA):
            qayta, qayta_xato = _qismni_chiqar(
                provider, pdf_bytes, rq, test_bolimi, boshi,
                kamchilik=(len(savollar), kutilgan),
            )
            if not qayta_xato:
                qayta_savollar = qayta.get("savollar") or []
                # Faqat YAXSHIROQ bo'lsa almashtiramiz.
                if abs(len(qayta_savollar) - kutilgan) < abs(len(savollar) - kutilgan):
                    natija, savollar = qayta, qayta_savollar
        if kutilgan and len(savollar) != kutilgan:
            xatolar.append(
                f"{qism_nomi}: {kutilgan} ta savol kutilgandi, "
                f"{len(savollar)} ta chiqdi — javoblarni tekshiring"
            )

        qismlar.append({
            "tartib": rq.get("tartib") or i,
            "sarlavha": qism_nomi,
            "yoriqnoma": rq.get("yoriqnoma") or "",
            "matn": natija.get("matn") or "",
            "savollar": savollar,
            "maxsus_format": natija.get("maxsus_format") or None,
            "rasm_sahifasi": natija.get("rasm_sahifasi"),
        })
        keyingi_savol_raqami = boshi + len(savollar)

    if not qismlar:
        return None, "; ".join(xatolar) or "Hech qanday qism chiqarilmadi", xatolar

    return {
        # Admin nom bergan bo'lsa — o'shaniki (AI nomni noto'g'ri
        # olayotgani uchun, 2026-07-31 foydalanuvchi xabari).
        "name": (nom or "").strip() or reja.get("name") or "IELTS test",
        "bolim": test_bolimi,
        "korinish": "private",
        "qismlar": qismlar,
    }, None, xatolar
