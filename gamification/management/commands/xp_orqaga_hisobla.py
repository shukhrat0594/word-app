"""Eski natijalar uchun XP'ni ORQAGA hisoblaydi (2026-10-05, yangi reyting qoidalari).

IELTS Reading/Listening testlari (`exercises.TestYechim`) va Kurslar mashqlari
(`courses.KursMashqYechim`) oldin XP bermagan. Bu buyruq har talaba+test va talaba+mashq uchun
BIRINCHI urinishni topib, yangi qoida bo'yicha XP yozadi. Yozuv ASL SANA bilan saqlanadi —
"Shu oy" reytingi to'g'ri chiqadi.

Takror ishga tushirsa ham XP ikki marta berilmaydi (`xp_takror_bermaslik` cheklovi).
Ishlatilishi:
    python manage.py xp_orqaga_hisobla --quruq     # faqat nechta yozuv bo'lishini ko'rsatadi
    python manage.py xp_orqaga_hisobla
"""

from django.core.management.base import BaseCommand

from courses.models import KursMashqYechim
from exercises.models import TestYechim
from gamification.models import XP_TURLARI, XPYozuv
from gamification.signals import kurs_xp_miqdorlari, test_xp_miqdori


class Command(BaseCommand):
    help = "Eski R/L testlari va Kurslar mashqlari uchun XP'ni orqaga hisoblaydi (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument("--quruq", action="store_true", help="Hech narsa yozmaydi, faqat sonini ko'rsatadi")

    def handle(self, *args, **opts):
        quruq = opts["quruq"]
        yangi = []  # (talaba_id, sabab, manba_id, miqdor, asl_sana)

        # 1) IELTS Reading/Listening testlari: har talaba+test uchun eng birinchi urinish
        korilgan = set()
        for y in TestYechim.objects.filter(test__bolim__in=["reading", "listening"]).select_related("test") \
                .order_by("created_at", "id"):
            kalit = (y.talaba_id, y.test_id)
            if kalit in korilgan:
                continue
            korilgan.add(kalit)
            yangi.append((y.talaba_id, "test_yechildi", y.test_id, test_xp_miqdori(y.band), y.created_at))

        # 2) Kurslar mashqlari: har talaba+mashq uchun birinchi urinish
        korilgan = set()
        for y in KursMashqYechim.objects.order_by("created_at", "id"):
            kalit = (y.talaba_id, y.mashq_id)
            if kalit in korilgan:
                continue
            korilgan.add(kalit)
            asosiy, bonus = kurs_xp_miqdorlari(y.ball, y.jami)
            yangi.append((y.talaba_id, "kurs_mashq", y.mashq_id, asosiy, y.created_at))
            if bonus:
                yangi.append((y.talaba_id, "kurs_mukammal", y.mashq_id, bonus, y.created_at))

        yozildi = 0
        for talaba_id, sabab, manba_id, miqdor, sana in yangi:
            if XPYozuv.objects.filter(talaba_id=talaba_id, sabab=sabab, manba_id=manba_id).exists():
                continue
            if not quruq:
                yozuv = XPYozuv.objects.create(
                    talaba_id=talaba_id, miqdor=miqdor, sabab=sabab, manba_id=manba_id,
                    tur=XP_TURLARI.get(sabab, "ielts"),
                )
                # created_at `auto_now_add` — yaratilgach asl sanaga qaytariladi
                XPYozuv.objects.filter(pk=yozuv.pk).update(created_at=sana)
            yozildi += 1
        self.stdout.write(
            f"{'Yoziladi (quruq rejim)' if quruq else 'Yozildi'}: {yozildi} ta XP yozuvi "
            f"({len(yangi) - yozildi} tasi allaqachon bor edi)"
        )
