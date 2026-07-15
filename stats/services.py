"""Talaba statistikasi (B6) — B6.1'da ota-ona ham xuddi shu funksiyadan
foydalanadi (faqat o'z farzandi uchun)."""

from django.db.models import Avg, Count, Q

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from content.models import DarsFaollik
from exercises.models import BOLIM_TURLARI, Bolim, MashqYechim


def _bolim_statistikasi(talaba, bolim):
    """L yoki R bo'limi: jami yechilgan, o'rtacha foiz, har tur bo'yicha."""
    yechimlar = MashqYechim.objects.filter(talaba=talaba, mashq__bolim=bolim)
    jami_ball = 0
    jami_savol = 0
    tur_boyicha = {}
    for tur in BOLIM_TURLARI[bolim]:
        tur_yechimlar = yechimlar.filter(mashq__tur=tur)
        ball = sum(y.ball for y in tur_yechimlar)
        savol = sum(y.jami for y in tur_yechimlar)
        jami_ball += ball
        jami_savol += savol
        tur_boyicha[str(tur)] = {
            "yechildi": tur_yechimlar.count(),
            "foiz": round(ball / savol * 100) if savol else None,
        }
    return {
        "jami_yechildi": yechimlar.count(),
        "ortacha_foiz": round(jami_ball / jami_savol * 100) if jami_savol else None,
        "tur_boyicha": tur_boyicha,
    }


def talaba_statistikasi(talaba):
    """To'liq statistika: Writing dinamikasi, L/R, dars faolligi, davomat."""

    writing = WritingTekshiruv.objects.filter(talaba=talaba)
    writing_dinamika = [
        {"sana": t.created_at.date(), "band": t.overall_band, "task_type": t.task_type}
        for t in writing.order_by("created_at")
    ]

    faollik = DarsFaollik.objects.filter(talaba=talaba).aggregate(
        boshlangan=Count("id"),
        tugatilgan=Count("id", filter=Q(holat="tugatdi")),
    )

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

    return {
        "writing": {
            "soni": writing.count(),
            "ortacha_band": writing.aggregate(a=Avg("overall_band"))["a"],
            "oxirgi_band": writing_dinamika[-1]["band"] if writing_dinamika else None,
            "dinamika": writing_dinamika,
        },
        "speaking": {
            "soni": speaking.count(),
            "ortacha_band": speaking.aggregate(a=Avg("overall_band"))["a"],
            "oxirgi_band": speaking_dinamika[-1]["band"] if speaking_dinamika else None,
            "dinamika": speaking_dinamika,
        },
        "listening": listening,
        "reading": reading,
        # Ko'nikmalar diagrammasi (radar) uchun tayyor qiymatlar
        "konikmalar": {
            "writing_band": writing.aggregate(a=Avg("overall_band"))["a"],
            "listening_foiz": listening["ortacha_foiz"],
            "reading_foiz": reading["ortacha_foiz"],
            "speaking_band": speaking.aggregate(a=Avg("overall_band"))["a"],
        },
        "dars_faollik": faollik,
        "davomat": davomat,
    }
