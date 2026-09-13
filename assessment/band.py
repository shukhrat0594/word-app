"""IELTS band ballarini 0.5 qadamga yaxlitlash (2026-09-14, Shuhrat
talabi: "hozirda 7.3 7.2 kabi baholar ham bor, baholash 0.5 baldan
o'zgarishi kerak — yoki butun bo'ladi yoki 0.5 ballga ko'p").

NEGA KERAK: band ballarni AI (Gemini/Claude) JSON ichida qaytaradi va
promtda "0.5 qadam" sharti YO'Q — model 7.3, 6.8 kabi oraliq qiymatlar
berib yuboradi. Rasmiy IELTS'da esa band faqat butun yoki .5 bo'ladi,
ya'ni bunday ball talabani chalg'itadi.

NEGA PROMT EMAS, KOD: promtga "faqat 0.5 qadam" deb yozish ham mumkin
edi, lekin bu ISHONCHSIZ — model baribir 7.3 qaytarishi mumkin va buni
hech kim sezmaydi. Kod darajasidagi yaxlitlash esa kafolat beradi.
Promt o'zgartirilsa ham bu qatlam zarar qilmaydi (7.5 -> 7.5).

QAYERGA QO'LLANADI: Speaking ham, Writing ham (2026-09-14 da Shuhrat
ikkalasini ham so'radi) — `assessment/views.py` (3 ta oqim) va
`exercises/views.py` (IELTS testlari oqimi).

MUHIM: faqat SAQLASHDAN oldin yaxlitlanadi. AI'ning xom javobi
o'zgartirilmaydi degan qoida yo'q — aksincha, `natija` JSON'i ham
yaxlitlangan holda saqlanadi, chunki talaba aynan o'sha JSON'dagi mezon
ballarini (Fluency 7.3 kabi) ko'radi.
"""

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Har bir mezon ball maydonining kaliti. Writing va Speaking'da mezonlar
# turlicha (`assessment/providers.py` dagi JSON sxemalariga qara), shuning
# uchun ikkalasining kalitlari birlashtirilgan — yo'q kalit tinch
# o'tkazib yuboriladi.
MEZON_KALITLARI = (
    # Writing
    "task_achievement",
    "coherence_cohesion",
    # Speaking
    "fluency_coherence",
    # Ikkalasida ham
    "lexical_resource",
    "grammatical_range",
    "pronunciation",
)

# Yakuniy ball maydonlari. Speaking'da Pronunciation'siz variant
# ishlatiladi (`overall_band_no_pronunciation`), Writing'da oddiy
# `overall_band`.
UMUMIY_KALITLAR = ("overall_band", "overall_band_no_pronunciation")


def yaxlitla(qiymat):
    """Bitta ballni eng yaqin 0.5 ga yaxlitlaydi.

    7.3 -> 7.5, 7.2 -> 7.0, 6.74 -> 6.5, 8.0 -> 8.0, 6.25 -> 6.5.

    `None`, bo'sh satr yoki songa aylanmaydigan qiymat — o'zgarishsiz
    `None` qaytadi (AI maydonni umuman qaytarmasligi mumkin).

    NEGA `round()` EMAS, `Decimal(ROUND_HALF_UP): Python'ning o'rnatilgan
    `round()` "bankir yaxlitlashi" ishlatadi — juft tomonga yaxlitlaydi:
    `round(6.25 * 2) / 2` -> 6.0, lekin `round(6.75 * 2) / 2` -> 7.0.
    Ya'ni aynan YARIM qiymatlar bir xil qoidaga bo'ysunmaydi. Rasmiy
    IELTS'da esa yarmi har doim YUQORIGA yaxlitlanadi (6.25 -> 6.5,
    6.75 -> 7.0). Sinovda 6.25 -> 6.0 chiqqani uchun shu yo'l tanlandi.

    `float`'ni to'g'ridan-to'g'ri `Decimal`ga bermaymiz (0.1 kabi sonlar
    ikkilik kasrda aniq emas) — avval `str()` orqali o'tkaziladi.
    """
    if qiymat is None or isinstance(qiymat, bool):
        return None
    try:
        xom = float(qiymat)
    except (TypeError, ValueError):
        return None
    # nan/inf — JSON'da uchramaydi, lekin `float("nan")` quantize'dan
    # jimgina o'tib ketardi va bazaga NaN band yozilardi.
    if not math.isfinite(xom):
        return None
    try:
        son = Decimal(str(xom))
    except InvalidOperation:
        return None
    # 0.5 qadam = ikkiga ko'paytirib butungacha yaxlitlab, ikkiga bo'lish.
    return float((son * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2)


def natijani_yaxlitla(natija):
    """AI qaytargan `natija` lug'atidagi BARCHA ball maydonlarini joyida
    yaxlitlaydi va o'sha lug'atni qaytaradi.

    Tegadigan joylari: har mezonning `{"score": N}` qiymati va yakuniy
    `overall_band` / `overall_band_no_pronunciation`. Izohlar, xatolar
    ro'yxati, `word_count` va boshqa maydonlarga TEGILMAYDI.

    Lug'at bo'lmasa (AI kutilmagan narsa qaytargan) — hech narsa
    qilmaydi, kelgan qiymatni qaytaradi.
    """
    if not isinstance(natija, dict):
        return natija

    for kalit in MEZON_KALITLARI:
        mezon = natija.get(kalit)
        if isinstance(mezon, dict) and "score" in mezon:
            yangi = yaxlitla(mezon.get("score"))
            if yangi is not None:
                mezon["score"] = yangi

    for kalit in UMUMIY_KALITLAR:
        if kalit in natija:
            yangi = yaxlitla(natija.get(kalit))
            if yangi is not None:
                natija[kalit] = yangi

    return natija
