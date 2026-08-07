"""Provider-agnostic AI baholash qatlami (B5).

Claude va Gemini bir xil interfeys ortida: har provider `writing_baholash(matn)`
metodini beradi va bir xil tuzilmadagi dict qaytaradi. Markaz faqat provayderni
(Markaz.ai_provider) tanlaydi — API kalit har doim platforma (owner) kaliti,
markaz o'z kalitini kirita olmaydi (2026-07-17).
"""

import json

from django.conf import settings


class ProviderXatosi(Exception):
    """AI provider bilan ishlashdagi xato (kalit yo'q, javob buzuq va h.k.)."""


# v5 prompt (2026-07-20): B8.1'da talaba Task turini tanlamasligi uchun
# AI mavzuni MATNDAN TAXMIN qilar edi — bu, savol/mavzu matni AI'ga UMUMAN
# yuborilmagani sababli, mavzudan butunlay chetga chiqqan javoblarni ham
# yuqori ball bilan baholab yuborish bug'iga olib kelgan (2026-07-20
# aniqlangan: sinov — real Task 2 mavzusiga umuman aloqasi yo'q insho
# "Mavzu to'liq yoritilgan" deb 7.0 band olgan). v5'da: talabaga berilgan
# ASL SAVOL matni va turi (task1/task2) endi ANIQ, kontent ichida beriladi
# — AI endi mavzuni taxmin qilmaydi, TASdiqlaydi va mavzuga moslikni
# tekshiradi.
# 2026-07-28: Task 1 va Task 2 endi ALOHIDA promt bilan baholanadi (sinov
# tariqasida, foydalanuvchi talabi). Sabab: ikki task butunlay boshqa
# janr — Task 1 berilgan grafik/jadval/xatni TAVSIFLASH (o'z fikri
# qo'shilmaydi), Task 2 esa dalilli INSHO (o'z pozitsiyasi shart). Bitta
# umumiy promt ikkalasini bir xil o'lchov bilan baholardi.
#
# Rol qismi (ingliz tilida) — foydalanuvchi bergan matn, aynan saqlangan.
# Qolgan qoidalar (mavzuga moslik, so'z soni, JSON sxemasi) OLDINGIDEK —
# ular real buglar tuzatilgandan keyin qo'shilgan, olib tashlanmaydi
# (pastdagi `_WRITING_UMUMIY_QOIDALAR` izohlariga qarang).
WRITING_TASK1_ROLI = (
    "I want you to be an experienced IELTS examiner, check my Task 1 essays, "
    "give your assessment according to IELTS band score criteria with "
    "explanation of my weaknesses and give exact suggestions how to improve "
    "it to raise my score.\n\n"
)

WRITING_TASK2_ROLI = (
    "I want you to be an experienced IELTS examiner, check my Task 2 essays, "
    "give your assessment according to IELTS band score criteria with "
    "explanation of my weaknesses and give exact suggestions how to improve "
    "it to raise my score.\n\n"
)

_WRITING_UMUMIY_QOIDALAR = (
    "Sizga (1) talabaga berilgan aniq Writing SAVOL/MAVZU matni va uning "
    "turi, (2) talabaning shu savolga yozgan javobi beriladi. Quyidagi "
    "tartibda baholang:\n\n"

    "1) MAVZUGA MOSLIK (ENG MUHIM TEKSHIRUV): talabaning javobi BERILGAN "
    "SAVOLGA haqiqatda javob berayotganini albatta tekshiring. Agar talaba "
    "butunlay boshqa mavzuda yozgan bo'lsa, savolni chetlab o'tgan bo'lsa "
    "yoki savolning barcha qismlariga javob bermagan bo'lsa (masalan savol "
    "ikki qismli bo'lsa-yu, faqat bittasiga javob bergan bo'lsa) — Task "
    "Achievement balini KESKIN pasaytiring (bunday holatda 2-4 balldan "
    "oshmasin) va buni izohda ANIQ ayting (masalan: \"talaba berilgan "
    "savolga javob bermadi, butunlay boshqa mavzuda yozdi\"). Til sifati "
    "qanchalik yaxshi bo'lishidan qat'iy nazar, javob mavzuga mos kelmasa "
    "yuqori ball berilmasin.\n\n"

    "2) SO'Z SONI: O'ZINGIZ SANAMANG. So'z soni va uning minimumga yetgan-"
    "yetmagani sizga kontent ichida ANIQ berilgan — uni dastur sanaydi, "
    "sizning hisobingiz emas (2026-07-26: sinovda modellar izchil 3-6% kam "
    "sanab, minimumdan sal yuqoridagi javoblarni NOHAQ jazolagani aniqlandi). "
    "Faqat berilgan ma'lumotga tayaning: minimumga yetgan bo'lsa so'z soni "
    "uchun ball PASAYTIRMANG; kam bo'lsa Task Achievement balini pasaytiring "
    "va buni izohda ayting.\n\n"

    "3) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 2-3 gaplik ATROFLICHA xulosa yozing — nima yaxshi, nima "
    "kamchilik, aniq misollar bilan (bir gaplik yuzaki xulosa YETARLI "
    "EMAS) — shu asosda ball bering.\n"
    "Band yo'riqnomasi: 4-5=ko'p tizimli xato/rivojlanmagan fikr; "
    "6=tushunarli lekin sezilarli xato; 7=xato kam, fikr dalillangan; "
    "8-9=deyarli xatosiz, murakkab til.\n\n"

    "4) XATOLAR: matnni qatorma-qator o'qib, BARCHA xatolarni toping "
    "(ega-kesim, birlik/ko'plik, artikl, egalik, imlo), TOPGANLARINGIZNI "
    "TO'LIQ sanab o'ting (sun'iy ravishda cheklab qo'ymang). Bir xil xato "
    "matnda necha marta uchrasa, HAR BIRINI ALOHIDA, aniq qaysi so'z "
    "birikmasida ekanini ko'rsatib yozing.\n\n"

    "5) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "6) KUCHLI TOMONLAR: 2-3 ta ijobiy narsani, aniq misol bilan "
    "ko'rsating (talaba nimani to'g'ri qilgan — shu joyni ANIQ "
    "ko'rsating, umumiy gap yozmang).\n\n"

    "7) YAXSHILASH TAVSIYALARI: har mezon izohida ('comment') faqat "
    "kamchilikni aytib qo'ya qolmang — ballni ko'tarish uchun talaba ANIQ "
    "nima qilishi kerakligini ko'rsating (umumiy maslahat emas, shu "
    "javobdagi aniq joyga bog'langan).\n\n"

    "8) UCH TILDA YOZISH — MAJBURIY: JSON ichidagi BARCHA izoh/tahlil "
    "matnlari (pastda ko'rsatilgan) BITTA satr EMAS, quyidagicha UCHTA "
    "tilda BIR XIL MA'NODA yoziladigan OBYEKT bo'lsin: "
    '{"en": "...", "uz": "...", "ru": "..."} — \'en\' asosiy (talaba shuni '
    "birinchi ko'radi), \"uz\" va \"ru\" xuddi shu mazmunni o'zbek/rus "
    "tilida tabiiy tarjima qilib beradi (so'zma-so'z emas, tabiiy "
    "tushunarli tilda). Talabaning matnidan iqtibos olingan xato/tuzatish "
    "so'zlarini (\"xato\"/\"tuzatish\" maydonlarini) TARJIMA QILMANG — ular "
    "har doim inglizcha (talaba yozgan/tuzatilgan asl so'zlar), FAQAT "
    "sabab izohi (\"izoh\") uch tilda bo'lsin.\n\n"

    "Faqat quyidagi JSON qaytaring, boshqa matn yozmang. 'task_type' "
    "maydoniga sizga berilgan turni ('task1' yoki 'task2') aynan shu "
    "ko'rinishda yozing (o'zingiz taxmin qilmang, sizga aniq berilgan). "
    "'word_count' maydoniga ham sizga berilgan so'z sonini AYNAN "
    "ko'chiring — o'zingiz sanagan raqamni yozmang:\n"
    "{\n"
    '  "task_type": "task1 yoki task2",\n'
    '  "word_count": 0,\n'
    '  "analysis": {\n'
    '    "task_achievement": {"en": "", "uz": "", "ru": ""},\n'
    '    "coherence_cohesion": {"en": "", "uz": "", "ru": ""},\n'
    '    "lexical_resource": {"en": "", "uz": "", "ru": ""},\n'
    '    "grammatical_range": {"en": "", "uz": "", "ru": ""}\n'
    "  },\n"
    '  "task_achievement": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "coherence_cohesion": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "lexical_resource": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "grammatical_range": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "overall_band": 0,\n'
    '  "errors": [\n'
    '    {"xato": "talaba yozgan noto\'g\'ri qism (inglizcha, tarjima qilinmaydi)", '
    '"tuzatish": "to\'g\'ri shakl (inglizcha, tarjima qilinmaydi)", '
    '"izoh": {"en": "", "uz": "", "ru": ""}}\n'
    "  ],\n"
    '  "strengths": [{"en": "", "uz": "", "ru": ""}]\n'
    "}"
)

WRITING_TASK1_SYSTEM_PROMPT = WRITING_TASK1_ROLI + _WRITING_UMUMIY_QOIDALAR
WRITING_TASK2_SYSTEM_PROMPT = WRITING_TASK2_ROLI + _WRITING_UMUMIY_QOIDALAR


def writing_promt_ol(tur):
    """Task turiga mos system promt (2026-07-28) — `_writing_kontent_tuz`
    bilan bir xil qoida: "task1" dan boshqa hamma narsa Task 2 hisoblanadi."""
    return WRITING_TASK1_SYSTEM_PROMPT if tur == "task1" else WRITING_TASK2_SYSTEM_PROMPT


def soz_sonini_sana(matn):
    """So'zlarni sanaydi — bo'sh joy bo'yicha ajratilgan tokenlar (IELTS
    qoidasiga yaqin: qo'shma so'z ham, son ham bitta so'z hisoblanadi).

    Nega dastur sanaydi, AI emas (2026-07-26): sinovda ikkala Gemini modeli
    ham so'zni izchil KAM sanadi (285 so'zli inshoni 272-278, 185 so'zlini
    178-182). Natijada 250 so'z minimumidan sal yuqoridagi javob "minimumdan
    kam" deb NOHAQ jazolanardi — 257 so'zli javobga gemini-3.1-flash-lite
    5/5 urinishda Task Achievement'ni pasaytirgan (TA 6.0, sanash to'g'ri
    berilganda esa 8.0). LLM aniq sanashni bilmaydi va bu prompt bilan
    tuzatilmaydi, shuning uchun son AI'ga tayyor holda beriladi."""
    return len(matn.split())


def _soz_soni_qismi(matn, minimum):
    """Kontentga qo'shiladigan so'z soni bloki — AI qayta sanamasligi va
    minimumga yetgan javobni jazolamasligi uchun ANIQ ko'rsatma bilan."""
    soni = soz_sonini_sana(matn)
    if soni >= minimum:
        holat = "MINIMUMGA YETADI — so'z soni uchun ball PASAYTIRMANG"
    else:
        holat = (
            f"MINIMUMDAN {minimum - soni} SO'Z KAM — Task Achievement balini "
            f"pasaytiring va buni izohda ALBATTA ayting"
        )
    return (
        f"TALABA JAVOBIDAGI SO'Z SONI: {soni} — bu son dastur tomonidan ANIQ "
        f"sanalgan. O'ZINGIZ QAYTA SANAMANG va boshqa raqam aytmang; "
        f"'word_count' maydoniga aynan {soni} yozing.\n"
        f"SO'Z SONI HOLATI: {holat}.\n\n"
    )


def _writing_kontent_tuz(savol_matni, tur, matn):
    """AI'ga yuboriladigan kontentni tuzadi — talaba javobi bilan birga
    ASL SAVOL matni, turi (task1/task2) va ANIQ so'z soni beriladi, AI
    bularning hech birini taxmin qilmaydi."""
    tur_nomi = "Task 1" if tur == "task1" else "Task 2"
    minimum = 150 if tur == "task1" else 250
    savol_qismi = (
        f"BERILGAN SAVOL/MAVZU MATNI:\n{savol_matni}\n\n" if savol_matni else ""
    )
    return (
        f"BU — WRITING {tur_nomi.upper()} (minimal {minimum} so'z talab qilinadi).\n\n"
        f"{_soz_soni_qismi(matn, minimum)}"
        f"{savol_qismi}"
        f"TALABANING JAVOBI (shu savolga nisbatan baholang):\n{matn}"
    )


# Speaking matn-mazmun tahlili — v5 (2026-07-20): Writing bilan bir xil
# sabab bilan, AI'ga endi ASL SAVOL/MAVZU matni va turi (part1/part2) ANIQ
# beriladi, taxmin qilinmaydi. "part2" turi — bu tizimda Part 2 (cue card
# monolog) VA Part 3 (chuqurroq munozara) BIRLASHTIRILGAN holda saqlanadi.
# Pronunciation BAHOLANMAYDI — u Azure vazifasi (Tezkor tahlil rejimida).
SPEAKING_SYSTEM_PROMPT = (
    "Siz professional IELTS Speaking imtihonchisiz. Sizga (1) talabaga "
    "berilgan aniq savol/mavzu (cue card) matni va uning turi (Part 1, yoki "
    "Part 2/3 — bu tizimda ular birlashtirilgan holda beriladi), (2) "
    "talabaning OG'ZAKI javobining matni (transkripsiya yoki yozma "
    "kiritilgan) beriladi. FAQAT quyidagi 3 mezon bo'yicha baholang. "
    "PRONUNCIATION (talaffuz)ni BAHOLAMANG — u alohida audio tizim orqali "
    "baholanadi.\n\n"

    "1) MAVZUGA MOSLIK (ENG MUHIM TEKSHIRUV): talabaning javobi BERILGAN "
    "SAVOL/MAVZUGA haqiqatda javob berayotganini albatta tekshiring. Agar "
    "talaba butunlay boshqa mavzuda gapirgan bo'lsa yoki savolni chetlab "
    "o'tgan bo'lsa — bu mezonlarning barchasiga (ayniqsa fluency_coherence) "
    "salbiy ta'sir qilsin va buni izohda ANIQ ayting.\n\n"

    "2) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 2-3 gaplik ATROFLICHA xulosa yozing — nima yaxshi, nima "
    "kamchilik, aniq misollar bilan (bir gaplik yuzaki xulosa YETARLI "
    "EMAS).\n"
    "Band yo'riqnomasi: 4-5=ko'p pauza/takrorlash, oddiy bog'lovchilar, "
    "tez-tez xato; 6=tushunarli oqim lekin ba'zan ikkilanish, xato bor-yu "
    "tushunishga xalaqit bermaydi; 7=nisbatan erkin, moslashuvchan lug'at, "
    "xato kam; 8-9=deyarli erkin va tabiiy, murakkab til.\n\n"

    "3) MEZONLAR: fluency_coherence (nutq oqimi, discourse markerlar, "
    "izchillik), lexical_resource (so'z boyligi, idiomalar), "
    "grammatical_range (gap tuzilishi xilma-xilligi, og'zaki nutqda kichik "
    "xato kechiriladi, tizimli xato pasaytiradi).\n\n"

    "4) XATOLAR: faqat GRAMMATIK va LEKSIK xatolar, TOPGANLARINGIZNI "
    "TO'LIQ sanab o'ting (kam bo'lsa kamini, ko'p bo'lsa hammasini — "
    "sun'iy ravishda 1-2 taga cheklab qo'ymang). Har biri uchun aniq "
    "noto'g'ri va to'g'ri shaklni ko'rsating.\n\n"

    "5) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "6) KUCHLI TOMONLAR: 2-3 ta ijobiy narsani, aniq misol bilan "
    "ko'rsating (talaba nimani to'g'ri qilgan — shu joyni ANIQ ko'rsating, "
    "\"yaxshi gapirdi\" kabi umumiy gap yozmang).\n\n"

    "7) UCH TILDA YOZISH — MAJBURIY: JSON ichidagi BARCHA izoh/tahlil "
    "matnlari (pastda ko'rsatilgan) BITTA satr EMAS, quyidagicha UCHTA "
    "tilda BIR XIL MA'NODA yoziladigan OBYEKT bo'lsin: "
    '{"en": "...", "uz": "...", "ru": "..."} — \'en\' asosiy (talaba shuni '
    "birinchi ko'radi), \"uz\" va \"ru\" xuddi shu mazmunni o'zbek/rus "
    "tilida tabiiy tarjima qilib beradi (so'zma-so'z emas, tabiiy "
    "tushunarli tilda). Talabaning gapidan iqtibos olingan xato/tuzatish "
    "so'zlarini (\"xato\"/\"tuzatish\" maydonlarini) TARJIMA QILMANG — ular "
    "har doim inglizcha (talaba gapirgan/tuzatilgan asl so'zlar), FAQAT "
    "sabab izohi (\"izoh\") uch tilda bo'lsin.\n\n"

    "Faqat quyidagi JSON qaytaring ('overall_band_no_pronunciation' — "
    "Pronunciation'siz 3 mezon o'rtachasi, yakuniy IELTS ball EMAS). "
    "'part_type' maydoniga sizga berilgan turni aynan shu ko'rinishda "
    "yozing (o'zingiz taxmin qilmang):\n"
    "{\n"
    '  "part_type": "part1 yoki part2",\n'
    '  "word_count": 0,\n'
    '  "analysis": {\n'
    '    "fluency_coherence": {"en": "", "uz": "", "ru": ""},\n'
    '    "lexical_resource": {"en": "", "uz": "", "ru": ""},\n'
    '    "grammatical_range": {"en": "", "uz": "", "ru": ""}\n'
    "  },\n"
    '  "fluency_coherence": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "lexical_resource": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "grammatical_range": {"score": 0, "comment": {"en": "", "uz": "", "ru": ""}},\n'
    '  "overall_band_no_pronunciation": 0,\n'
    '  "errors": [\n'
    '    {"xato": "talaba aytgan noto\'g\'ri qism (inglizcha, tarjima qilinmaydi)", '
    '"tuzatish": "to\'g\'ri shakl (inglizcha, tarjima qilinmaydi)", '
    '"izoh": {"en": "", "uz": "", "ru": ""}}\n'
    "  ],\n"
    '  "strengths": [{"en": "", "uz": "", "ru": ""}]\n'
    "}"
)


def _speaking_kontent_tuz(savol_matni, tur, matn):
    """Speaking uchun ham xuddi shu naqsh — asl savol/cue card matni va
    turi (part1/part2) ANIQ beriladi. So'z soni ham dastur tomonidan
    beriladi (Speaking'da minimum yo'q, lekin `word_count` maydoni
    to'g'ri chiqishi uchun — qarang: `soz_sonini_sana`)."""
    tur_nomi = "Part 1" if tur == "part1" else "Part 2/3"
    savol_qismi = (
        f"BERILGAN SAVOL/MAVZU (CUE CARD) MATNI:\n{savol_matni}\n\n" if savol_matni else ""
    )
    return (
        f"BU — SPEAKING {tur_nomi.upper()}.\n\n"
        f"TALABA JAVOBIDAGI SO'Z SONI: {soz_sonini_sana(matn)} — dastur ANIQ "
        f"sanagan. O'ZINGIZ QAYTA SANAMANG; 'word_count' maydoniga aynan shu "
        f"sonni yozing. Speaking'da minimal so'z talabi YO'Q — so'z soni "
        f"uchun ball pasaytirmang.\n\n"
        f"{savol_qismi}"
        f"TALABANING OG'ZAKI JAVOBI MATNI (shu savol/mavzuga nisbatan "
        f"baholang):\n{matn}"
    )


def javobni_parse_qil(raw_text):
    """AI javobidan JSON ajratadi (```json ... ``` o'ramini olib tashlab).

    `raw_decode` ishlatiladi, `json.loads` emas (2026-07-26): model ba'zan
    to'g'ri JSON'dan keyin ortiqcha matn yoki IKKINCHI JSON obyektini ham
    qo'shib yuboradi ("Extra data: line 38 ..."). Bunday javob amalda
    yaroqli — birinchi obyekt to'liq va to'g'ri, ortidagi axlat esa keraksiz.
    `raw_decode` birinchi obyektni o'qib, qolganini e'tiborsiz qoldiradi."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        natija, _ = json.JSONDecoder().raw_decode(cleaned)
    except json.JSONDecodeError as e:
        raise ProviderXatosi(f"AI javobi JSON emas: {e}") from e
    if not isinstance(natija, dict):
        raise ProviderXatosi("AI javobi JSON obyekt emas")
    return natija


# 2026-07-26: Gemma 4 26B BUTUNLAY OLIB TASHLANDI. Sabab — ishonchsizligi:
# ba'zan (~1/3 holatda) MAX_TOKENS bilan bo'sh javob qaytarardi, shuning
# uchun har baholash 3 martagacha ketma-ket chaqiruv talab qilardi. Bu
# prod'da gunicorn worker'ini timeout bo'yicha o'ldirishga olib keldi
# (Writing testi = 2 qism x 3 urinish = 6 ketma-ket chaqiruv), talaba esa
# "Xatolik yuz berdi" xabarini ko'rardi.
#
# Yagona model — gemini-3.1-flash-lite. 2026-07-26 sinovi (4 xil darajadagi
# insho + rasmli Task 1, jami 90+ chaqiruv): 3.5-flash-lite bilan sifati
# amalda teng (Task 2'da bir xil, Task 1'da faktik xatolarni `errors`
# ro'yxatiga qo'shgani uchun hatto foydaliroq), lekin ~20% tezroq va
# chiqish tokenlari ~25% kam.
GEMINI_MODEL = "gemini-3.1-flash-lite"
MAX_OUTPUT_TOKENS = 8192

# Bitta AI chaqiruvi uchun timeout (millisekund — google-genai shu birlikda
# oladi). Sinovda odatdagi javob 2-4 sekund, lekin bir marta 45.8 sekund
# ham kuzatilgan — cheksiz kutish worker'ni band qilib turmasligi uchun
# aniq chegara kerak. Chegaradan oshsa, pastdagi qayta urinish ishlaydi.
SOROV_TIMEOUT_MS = 40_000

# Bo'sh yoki buzuq JSON javob uchun umumiy urinishlar soni (1 asosiy +
# 1 qayta). Ko'proq urinish = uzoq kutish = timeout xavfi.
URINISHLAR = 2


def _limit_xatosimi(xato):
    """`courses/blok_generatsiya.py`dagi bilan bir xil tekshiruv (2026-07-29)
    — kunlik/daqiqalik AI so'rov limiti tugaganini aniqlaydi, aks holda
    talaba "kutilmagan xato" degan tushunarsiz xabar ko'rardi."""
    matn = str(xato).lower()
    return "429" in matn or "quota" in matn or "rate" in matn or "resource_exhausted" in matn


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model=GEMINI_MODEL, timeout_ms=SOROV_TIMEOUT_MS):
        """`timeout_ms` — 2026-07-28 da qo'shildi. Sabab: Writing/Speaking
        baholash 40 sekundda ulguradi, lekin darslik sahifasini bloklarga
        ajratish (Gemma 4 31B, `courses.blok_generatsiya`) ~125 sekund
        oladi va qat'iy 40s chegara uni HAR DOIM uzib qo'yardi."""
        if not api_key:
            raise ProviderXatosi("Gemini API kaliti berilmagan")
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms

    def _bitta_sorov(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None,
                     pdf_bytes=None, max_output_tokens=None, javob_sxemasi=None):
        """`pdf_bytes` (2026-08-01) — Gemini PDF'ni O'ZI o'qiydi, xuddi
        rasm kabi `Part.from_bytes` bilan (mime_type="application/pdf").

        `javob_sxemasi` — STRUCTURED OUTPUTS: `response_json_schema`
        bizning (Claude uchun yozilgan) JSON Schema'larni O'ZGARTIRMASDAN
        qabul qiladi (`additionalProperties`, `required`, `anyOf` —
        hammasi qo'llab-quvvatlanadi, SDK hujjatida tasdiqlangan).
        Google Schema (`response_schema`) EMAS — u boshqa, cheklangan
        format."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        contents = matn
        if pdf_bytes:
            contents = [types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), matn]
        elif rasm_bytes:
            contents = [types.Part.from_bytes(data=rasm_bytes, mime_type=rasm_mime), matn]

        qoshimcha = {}
        if javob_sxemasi:
            qoshimcha["response_mime_type"] = "application/json"
            qoshimcha["response_json_schema"] = javob_sxemasi

        return client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_output_tokens or MAX_OUTPUT_TOKENS,
                **qoshimcha,
            ),
        )

    def _generate(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None,
                  pdf_bytes=None, max_output_tokens=None, javob_sxemasi=None):
        """`URINISHLAR` marta uradi: javob bo'sh bo'lsa (MAX_TOKENS va h.k.)
        YOKI JSON buzuq bo'lsa — qayta uriniladi.

        2026-07-26: avval JSON buzuq bo'lsa qayta urinilmasdan darhol xato
        qaytarilardi, holbuki sinovda buzuq JSON 15 urinishdan 1 marta
        uchraydi va oddiy qayta urinish uni hal qiladi. Gemma'ga xos
        "zaxira modelga o'tish" bosqichi olib tashlandi — model bittta."""
        oxirgi_xato = None
        for _ in range(URINISHLAR):
            response = self._bitta_sorov(
                system_prompt, matn, rasm_bytes, rasm_mime,
                pdf_bytes=pdf_bytes, max_output_tokens=max_output_tokens,
                javob_sxemasi=javob_sxemasi,
            )
            if not response.text:
                oxirgi_xato = ProviderXatosi("AI bo'sh javob qaytardi")
                continue
            try:
                natija = javobni_parse_qil(response.text)
            except ProviderXatosi as e:
                oxirgi_xato = e
                continue

            usage = response.usage_metadata
            return {
                "natija": natija,
                "provider": self.name,
                "model": self.model,
                "input_tokens": usage.prompt_token_count or 0,
                "output_tokens": usage.candidates_token_count or 0,
            }

        raise ProviderXatosi(
            f"AI {URINISHLAR} urinishda ham yaroqli javob bermadi ({oxirgi_xato})"
        )

    def audio_transkripsiya_qil(self, audio_bytes, audio_mime="audio/webm"):
        """Ovoz yozuvini MATNGA o'giradi (Speaking mikrofon rejimi,
        2026-07-29). Alohida Speech-to-Text xizmati EMAS — Gemini
        audio-inputni to'g'ridan-to'g'ri qabul qiladi (sinovda tasdiqlandi:
        sun'iy audio bilan aynan bir xil matnni qaytardi). JSON emas, sof
        transkript matni qaytadi. Faqat GeminiProvider'da bor — Claude
        audio-inputni qo'llab-quvvatlamaydi."""
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
                    "Transcribe exactly what is said in this audio recording. "
                    "Return ONLY the raw transcript text, with no extra "
                    "commentary, labels, or formatting.",
                ],
            )
        except Exception as e:
            if _limit_xatosimi(e):
                raise ProviderXatosi(
                    "AI kunlik so'rov limiti tugadi — birozdan so'ng qayta urinib ko'ring"
                ) from e
            raise ProviderXatosi(f"Audio'ni transkripsiya qilishda xato: {e}") from e
        if not response.text or not response.text.strip():
            raise ProviderXatosi("AI audio'dan matn ajrata olmadi (ovoz tushunarsiz yoki bo'sh)")
        return response.text.strip()

    def speaking_audio_baholash(self, audio_bytes, audio_mime, savol_matni="", tur="part1"):
        """Mikrofon rejimi: audio -> transkript -> Matn rejimi bilan BIR
        XIL 3 mezon (Pronunciation'siz) baholash. Natijaga `transkript`
        maydoni qo'shiladi — talaba nima deganini ko'rishi uchun."""
        transkript = self.audio_transkripsiya_qil(audio_bytes, audio_mime)
        if len(transkript.split()) < 20:
            raise ProviderXatosi(
                f'Ovozda tushunarli gap juda kam topildi ("{transkript}") — '
                "kamida 20 so'zlik javob ayting va qayta urinib ko'ring"
            )
        baho = self.speaking_matn_baholash(transkript, savol_matni=savol_matni, tur=tur)
        baho["transkript"] = transkript
        return baho

    def writing_baholash(self, matn, savol_matni="", tur="task2", rasm_bytes=None, rasm_mime=None):
        kontent = _writing_kontent_tuz(savol_matni, tur, matn)
        return self._generate(writing_promt_ol(tur), kontent, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn, savol_matni="", tur="part1"):
        kontent = _speaking_kontent_tuz(savol_matni, tur, matn)
        return self._generate(SPEAKING_SYSTEM_PROMPT, kontent)

    def generate_json(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None,
                       javob_sxemasi=None, max_tokens=None):
        """Boshqa app'lar (masalan `courses`, `exercises.mashq_generatsiya`)
        uchun ochiq interfeys — `_generate` shaxsiy metod, app chegarasidan
        tashqarida chaqirilmasligi kerak.

        `javob_sxemasi`/`max_tokens` (2026-08-02) — AI mashq generatsiyasi
        uchun qo'shildi, avval faqat PDF yo'lida (`generate_json_pdf`) bor
        edi."""
        return self._generate(
            system_prompt, matn, rasm_bytes, rasm_mime,
            max_output_tokens=max_tokens, javob_sxemasi=javob_sxemasi,
        )

    def generate_json_pdf(self, system_prompt, matn, pdf_bytes, max_tokens=16000,
                          javob_sxemasi=None):
        """PDF'dan JSON — `exercises.pdf_generatsiya` uchun. `ClaudeProvider`
        bilan BIR XIL interfeys (2026-08-01, Gemini'ga sinov o'tkazish
        talabi — Claude Haiku savol tarkibida xato ko'p qildi)."""
        return self._generate(
            system_prompt, matn, pdf_bytes=pdf_bytes,
            max_output_tokens=max_tokens, javob_sxemasi=javob_sxemasi,
        )


# 2026-07-26: Gemma olib tashlanganidan keyin bitta tanlov qoldi. Lug'at
# saqlanib turibdi, chunki `_tanlangan_providerlar` va eski frontend
# ("both" tanlovi) shu kalitlar bilan ishlaydi — endi "both" ham amalda
# bitta providerni qaytaradi.
GEMINI_MODEL_TANLOVLARI = {
    "flash_lite": GEMINI_MODEL,
}


def gemini_provider_ol(model_kaliti):
    """Writing/Speaking tekshiruv ekrani yuboradigan model kaliti uchun
    provider qaytaradi.

    2026-07-26: model bitta qolgani uchun notanish kalit (masalan brauzerda
    keshlangan eski JS'dan kelgan "gemma") XATO qaytarmaydi — yagona modelga
    tushib qoladi. Aks holda kesh yangilanmagan talaba "Noto'g'ri model
    tanlovi" xabarini ko'rib, tekshiruvdan butunlay mahrum bo'lardi."""
    model = GEMINI_MODEL_TANLOVLARI.get(model_kaliti, GEMINI_MODEL)
    kalit = getattr(settings, "GEMINI_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
    return GeminiProvider(kalit, model=model)


# 2026-07-29(7), foydalanuvchi tasdiqlagan taqqoslashdan keyin: Writing
# Task 1 va Task 2 ENDI TURLI model bilan tekshiriladi (avval ikkalasi ham
# `GEMINI_MODEL`da edi). Real sinov (bir xil grafik+insho, ikkala model)
# ko'rsatdiki: Gemma 4 31B Task 1'ni (rasm-tavsif) Gemini bilan deyarli BIR
# XIL ishonchlilikda baholaydi (ikkalasi ham yaxshi inshoga 9, zaif inshoga
# 2.5-3 band berdi, xatolarni bir xil topdi) — Gemma allaqachon
# `courses/blok_generatsiya.py`da rasm-input uchun ishlatilgani uchun
# tabiiy tanlov. Task 2 (sof matnli insho) uchun `gemini-3.5-flash`
# sinovda `gemini-3.1-flash-lite`ga deyarli teng natija berdi.
WRITING_TASK1_MODEL = "gemma-4-31b-it"
WRITING_TASK2_MODEL = "gemini-3.5-flash"

# Gemma matnli (rasmsiz) tahlilda ham sekin ishlaydi — WritingTekshirishView
# SINXRON so'rov (blok pipeline'dagi kabi bosqichlab emas), shuning uchun
# oddiy 40s o'rniga ancha kattaroq zaxira beramiz (gunicorn 300s'dan past).
WRITING_TASK1_TIMEOUT_MS = 120_000


def writing_provider_ol(tur):
    """Writing tekshiruvi uchun — TASK TURIGA qarab TO'G'RIDAN-TO'G'RI
    model tanlaydi (frontend "model" tanlovidan mustaqil — u endi Writing
    uchun e'tiborga olinmaydi, chunki tanlov avtomatik)."""
    kalit = getattr(settings, "GEMINI_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
    if tur == "task1":
        return GeminiProvider(kalit, model=WRITING_TASK1_MODEL, timeout_ms=WRITING_TASK1_TIMEOUT_MS)
    return GeminiProvider(kalit, model=WRITING_TASK2_MODEL)


def _matn_blokini_ol(response):
    """Claude javobidan MATN bloklarini oladi.

    2026-07-31 bug (foydalanuvchi PDF yuklashda uchradi): kod
    `response.content[0].text` deb BIRINCHI blokni matn deb hisoblardi.
    Ba'zi modellar (masalan `claude-sonnet-5`) javobni `thinking` bloki
    bilan boshlaydi — u `.text` maydoniga ega emas, natijada
    "AttributeError: 'ThinkingBlock' object has no attribute 'text'".
    Endi bloklar turi bo'yicha tanlanadi (`thinking`/`redacted_thinking`
    va boshqa matnsiz bloklar tashlab yuboriladi)."""
    qismlar = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    if not qismlar:
        # Zaxira: `type` kutilmagan bo'lsa ham `.text` bori ishlatiladi.
        qismlar = [b.text for b in response.content if hasattr(b, "text")]
    if not qismlar:
        raise ProviderXatosi("AI javobida matn bloki yo'q")
    return "\n".join(qismlar)


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key, model="claude-haiku-4-5", timeout_ms=SOROV_TIMEOUT_MS):
        """`timeout_ms` — GeminiProvider'dagi bilan bir xil sabab
        (2026-07-30): `courses.blok_generatsiya` kabi sekin (sahifani
        to'r orqali o'qish) vazifalar uchun standart 40s yetarli emas."""
        if not api_key:
            raise ProviderXatosi("Claude API kaliti berilmagan")
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms

    def _generate(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None,
                  pdf_bytes=None, max_tokens=4096, javob_sxemasi=None):
        """Gemini bilan bir xil naqsh (2026-07-26): aniq timeout va buzuq
        JSON uchun qayta urinish — cheksiz kutish gunicorn worker'ini
        o'ldirmasligi uchun.

        `pdf_bytes` (2026-07-31) — Claude PDF'ni O'ZI o'qiydi (`document`
        bloki): sahifalarni rasmga aylantirish shart emas, model matnni
        ham, sahifa tuzilishini ham ko'radi. `max_tokens` shu sabab
        oshiriladigan qilindi — to'liq IELTS Reading testi (3 passage +
        40 savol) 4096 tokenga sig'maydi."""
        import base64

        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key, timeout=self.timeout_ms / 1000
        )
        content = matn
        if pdf_bytes:
            content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.b64encode(pdf_bytes).decode(),
                    },
                },
                {"type": "text", "text": matn},
            ]
        elif rasm_bytes:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": rasm_mime,
                        "data": base64.b64encode(rasm_bytes).decode(),
                    },
                },
                {"type": "text", "text": matn},
            ]

        # `javob_sxemasi` (2026-07-31) — STRUCTURED OUTPUTS. Berilsa, API
        # generatsiyani sxemaga MAJBURLAYDI va yaroqli JSON kafolatlanadi.
        # Nega kerak: PDF'dan IELTS testi chiqarishda model passage matnini
        # o'zi JSON string ichiga yozadi; matnda qo'shtirnoq bo'lsa (masalan
        # the so-called "green revolution") uni qochirmay yuborardi va
        # "Expecting ',' delimiter" xatosi chiqardi (foydalanuvchi
        # production'da uchradi). Qayta urinish ham foyda bermaydi —
        # bir xil matnda xato takrorlanadi.
        qoshimcha = {}
        if javob_sxemasi:
            qoshimcha["output_config"] = {
                "format": {"type": "json_schema", "schema": javob_sxemasi}
            }

        oxirgi_xato = None
        for _ in range(URINISHLAR):
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
                **qoshimcha,
            )
            # Sxema berilgan bo'lsa ham chegaraga urilsa javob chala qoladi —
            # buni tushunarli xato qilib aytamiz (aks holda "JSON emas" deb
            # chalg'ituvchi xabar chiqardi).
            if response.stop_reason == "max_tokens":
                oxirgi_xato = ProviderXatosi(
                    "AI javobi max_tokens chegarasiga urildi (javob chala qoldi)"
                )
                continue
            try:
                natija = javobni_parse_qil(_matn_blokini_ol(response))
            except ProviderXatosi as e:
                oxirgi_xato = e
                continue
            return {
                "natija": natija,
                "provider": self.name,
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        raise ProviderXatosi(
            f"AI {URINISHLAR} urinishda ham yaroqli javob bermadi ({oxirgi_xato})"
        )

    def writing_baholash(self, matn, savol_matni="", tur="task2", rasm_bytes=None, rasm_mime=None):
        kontent = _writing_kontent_tuz(savol_matni, tur, matn)
        return self._generate(writing_promt_ol(tur), kontent, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn, savol_matni="", tur="part1"):
        kontent = _speaking_kontent_tuz(savol_matni, tur, matn)
        return self._generate(SPEAKING_SYSTEM_PROMPT, kontent)

    def generate_json(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None):
        """Boshqa app'lar (masalan `courses`) uchun ochiq interfeys — `_generate`
        shaxsiy metod, app chegarasidan tashqarida chaqirilmasligi kerak."""
        return self._generate(system_prompt, matn, rasm_bytes, rasm_mime)

    def generate_json_pdf(self, system_prompt, matn, pdf_bytes, max_tokens=16000,
                          javob_sxemasi=None):
        """PDF'dan JSON (2026-07-31, `exercises.pdf_generatsiya` uchun).
        Faqat Claude'da bor — Gemini yo'lida PDF hujjat bloki ishlatilmaydi.

        `javob_sxemasi` berilsa Structured Outputs ishlaydi (qarang:
        `_generate`) — yaroqli JSON kafolatlanadi."""
        return self._generate(
            system_prompt, matn, pdf_bytes=pdf_bytes, max_tokens=max_tokens,
            javob_sxemasi=javob_sxemasi,
        )


def provider_tanla(user):
    """Foydalanuvchi uchun AI provider tanlaydi.

    Markaz faqat AI provayderni (Gemini/Claude) tanlaydi — API kalit har
    doim platforma (owner) kaliti orqali to'lanadi, markazlar o'z kalitini
    kirita olmaydi. Shunday qilib har bir Writing/Speaking tekshiruvi
    xarajati platformaga tushadi (2026-07-17'da shunday qaror qilingan).

    "gemini" provayder tanlansa — model **gemini-3.1-flash-lite**
    (`GEMINI_MODEL`, 2026-07-26'dan; undan oldin Gemma 4 26B edi, u
    ishonchsizligi va timeout muammosi uchun olib tashlandi). Ishonchlilik
    uchun `GeminiProvider._generate` ichida bo'sh/buzuq javob bo'lsa
    avtomatik qayta urinish bor.
    """
    markaz = user.markaz
    provider_nomi = markaz.ai_provider if markaz else "gemini"

    if provider_nomi == "claude":
        kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not kalit:
            raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
        return ClaudeProvider(kalit)

    kalit = getattr(settings, "GEMINI_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
    return GeminiProvider(kalit)
