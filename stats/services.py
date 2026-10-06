"""Talaba statistikasi (B6) — B6.1'da ota-ona ham xuddi shu funksiyadan
foydalanadi (faqat o'z farzandi uchun)."""

from django.db.models import Avg, Count, Q

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from exercises.models import BOLIM_TURLARI, Bolim, MashqYechim, band_hisobla


def _bolim_statistikasi(talaba, bolim):
    """L yoki R bo'limi: jami yechilgan, o'rtacha foiz, har tur bo'yicha.

    2026-08-15: avval har tur uchun queryset qayta baholanardi (sum() x2
    + .count() — bitta DB so'rovi o'rniga 3 tadan) — endi hammasi BITTA
    so'rovda (`.values()`) xotiraga olinadi, qolgani Python ichida."""
    yechimlar = list(
        MashqYechim.objects.filter(talaba=talaba, mashq__bolim=bolim)
        .order_by("created_at")
        .values("mashq__tur", "ball", "jami", "created_at")
    )
    jami_ball = 0
    jami_savol = 0
    tur_boyicha = {}
    for tur in BOLIM_TURLARI[bolim]:
        tur_yechimlar = [y for y in yechimlar if y["mashq__tur"] == tur]
        ball = sum(y["ball"] for y in tur_yechimlar)
        savol = sum(y["jami"] for y in tur_yechimlar)
        jami_ball += ball
        jami_savol += savol
        tur_boyicha[str(tur)] = {
            "yechildi": len(tur_yechimlar),
            "foiz": round(ball / savol * 100) if savol else None,
        }
    # Har bir bajarilgan mashq bo'yicha % natija — Dinamika (line) grafigi uchun.
    dinamika = [
        {
            "sana": y["created_at"].date(),
            "foiz": round(y["ball"] / y["jami"] * 100) if y["jami"] else None,
        }
        for y in yechimlar
    ]
    return {
        "jami_yechildi": len(yechimlar),
        "ortacha_foiz": round(jami_ball / jami_savol * 100) if jami_savol else None,
        # Ko'nikmalar diagrammasi uchun: foiz emas, IELTS band jadvali
        # bo'yicha taxminiy band (Writing/Speaking bilan bir xil 0-9
        # shkalada solishtirish mumkin bo'lsin).
        "ortacha_band": band_hisobla(jami_ball, jami_savol, bolim) if jami_savol else None,
        "tur_boyicha": tur_boyicha,
        "dinamika": dinamika,
    }


def talaba_statistikasi(talaba):
    """To'liq statistika: Writing dinamikasi, L/R, dars faolligi, davomat."""

    writing = WritingTekshiruv.objects.filter(talaba=talaba)
    writing_dinamika = [
        {"sana": t.created_at.date(), "band": t.overall_band, "task_type": t.task_type}
        for t in writing.order_by("created_at")
    ]
    # 2026-08-15: avval `.count()` + `.aggregate()` alohida, va
    # `.aggregate()` yana "konikmalar" uchun QAYTA chaqirilardi (3 ta
    # so'rov) — endi bitta `.aggregate()`da ikkalasi, natija qayta
    # ishlatiladi.
    writing_agg = writing.aggregate(soni=Count("id"), ortacha_band=Avg("overall_band"))

    davomat = Davomat.objects.filter(talaba=talaba).aggregate(
        keldi=Count("id", filter=Q(holat="keldi")),
        kelmadi=Count("id", filter=Q(holat="kelmadi")),
    )

    listening = _bolim_statistikasi(talaba, Bolim.LISTENING)
    reading = _bolim_statistikasi(talaba, Bolim.READING)

    speaking = SpeakingTekshiruv.objects.filter(talaba=talaba)
    speaking_dinamika = [
        {"sana": t.created_at.date(), "band": t.overall_band,
         "rejim": t.rejim, "part_type": t.part_type}
        for t in speaking.order_by("created_at")
    ]
    speaking_agg = speaking.aggregate(soni=Count("id"), ortacha_band=Avg("overall_band"))

    return {
        "writing": {
            "soni": writing_agg["soni"],
            "ortacha_band": writing_agg["ortacha_band"],
            "oxirgi_band": writing_dinamika[-1]["band"] if writing_dinamika else None,
            "dinamika": writing_dinamika,
        },
        "speaking": {
            "soni": speaking_agg["soni"],
            "ortacha_band": speaking_agg["ortacha_band"],
            "oxirgi_band": speaking_dinamika[-1]["band"] if speaking_dinamika else None,
            "dinamika": speaking_dinamika,
        },
        "listening": listening,
        "reading": reading,
        # Ko'nikmalar diagrammasi (radar) uchun tayyor qiymatlar
        "konikmalar": {
            "writing_band": writing_agg["ortacha_band"],
            "listening_band": listening["ortacha_band"],
            "reading_band": reading["ortacha_band"],
            "speaking_band": speaking_agg["ortacha_band"],
        },
        "davomat": davomat,
    }
