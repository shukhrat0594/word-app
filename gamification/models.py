from django.conf import settings
from django.db import models
from django.db.models import Sum


# XP miqdorlari — bir joyda, o'zgartirish oson
XP_QOIDALARI = {
    "mashq_yechildi": 10,
    "mashq_mukammal": 5,   # 100% natijaga bonus
    "writing_tekshiruv": 20,
    "speaking_tekshiruv": 20,
    "davomat_keldi": 2,
    # IELTS Reading/Listening TESTI (2026-10-05): 10 XP + band x 4; shu testni qayta yechish XP bermaydi.
    "test_yechildi": 10,
    # Kurslar (Beginner, Elementary...): mashqning birinchi urinishi — 1 to'g'ri javob = 1 XP (miqdor
    # chaqiruvchidan keladi) + 100% bo'lsa bonus.
    "kurs_mashq": 0,
    "kurs_mukammal": 5,
}

# XP qaysi reytingga tegishli: "ielts" (platforma: mashq, Writing, Speaking, R/L testlar), "kurs"
# (Kurslar mashqlari), "umumiy" (davomat — ikkala reytingga ham hisoblanadi).
TEST_BAND_KOEFFITSIENT = 4
XP_TURLARI = {
    "kurs_mashq": "kurs",
    "kurs_mukammal": "kurs",
    "davomat_keldi": "umumiy",
}

# Badge katalogi: kod -> (nom, tavsif)
BADGES = {
    "birinchi_mashq": ("Birinchi qadam", "Birinchi mashq yechildi"),
    "birinchi_writing": ("Yozuvchi", "Birinchi Writing tekshiruvi"),
    "mukammal_natija": ("Mukammal", "Birinchi 100% natija"),
    "xp_100": ("Yulduz", "100 XP to'plandi"),
    "xp_500": ("Chempion", "500 XP to'plandi"),
    "davomat_5": ("Intizomli", "5 kun darsga keldi"),
}


class XPYozuv(models.Model):
    """Bitta XP hodisasi. Jami XP = yozuvlar yig'indisi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_yozuvlar",
    )
    miqdor = models.PositiveIntegerField()
    sabab = models.CharField(max_length=30)
    # Qaysi reytingga hisoblanadi: "ielts" | "kurs" | "umumiy" (ikkalasiga ham).
    tur = models.CharField(max_length=10, default="ielts", db_index=True)
    manba_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Hodisa manbai (yechim/tekshiruv/faollik id) — takror bermaslik uchun",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "XP yozuvlari"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["talaba", "sabab", "manba_id"],
                name="xp_takror_bermaslik",
                condition=models.Q(manba_id__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.talaba} +{self.miqdor} ({self.sabab})"


class TalabaBadge(models.Model):
    """Talabaga berilgan badge."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="badges",
    )
    kod = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Talaba badgelari"
        constraints = [
            models.UniqueConstraint(fields=["talaba", "kod"], name="badge_unikal")
        ]

    def __str__(self):
        nom = BADGES.get(self.kod, (self.kod, ""))[0]
        return f"{self.talaba} — {nom}"


def jami_xp(talaba):
    return talaba.xp_yozuvlar.aggregate(s=Sum("miqdor"))["s"] or 0


def xp_ber(talaba, sabab, manba_id=None, miqdor=None):
    """XP beradi (takror hodisaga bermaydi), keyin badge'larni tekshiradi.

    `miqdor` berilmasa — `XP_QOIDALARI`dagi qat'iy qiymat. Qaytaradi: XP haqiqatan berildimi."""
    if miqdor is None:
        miqdor = XP_QOIDALARI[sabab]
    tur = XP_TURLARI.get(sabab, "ielts")
    if manba_id is not None:
        _, yaratildi = XPYozuv.objects.get_or_create(
            talaba=talaba, sabab=sabab, manba_id=manba_id,
            defaults={"miqdor": miqdor, "tur": tur},
        )
        if not yaratildi:
            return False
    else:
        XPYozuv.objects.create(talaba=talaba, miqdor=miqdor, sabab=sabab, tur=tur)
    badgelarni_tekshir(talaba)
    return True


def badgelarni_tekshir(talaba):
    """Shartlari bajarilgan badge'larni beradi (bor bo'lsa o'tkazib yuboradi)."""
    from academics.models import Davomat
    from assessment.models import WritingTekshiruv
    from exercises.models import MashqYechim

    mavjud = set(talaba.badges.values_list("kod", flat=True))
    yangi = []

    def bor(kod, shart):
        if kod not in mavjud and shart():
            yangi.append(kod)

    bor("birinchi_mashq",
        lambda: MashqYechim.objects.filter(talaba=talaba).exists())
    bor("birinchi_writing",
        lambda: WritingTekshiruv.objects.filter(talaba=talaba).exists())
    bor("mukammal_natija",
        lambda: MashqYechim.objects.filter(
            talaba=talaba, jami__gt=0, ball=models.F("jami")
        ).exists())
    bor("xp_100", lambda: jami_xp(talaba) >= 100)
    bor("xp_500", lambda: jami_xp(talaba) >= 500)
    bor("davomat_5",
        lambda: Davomat.objects.filter(talaba=talaba, holat="keldi").count() >= 5)

    for kod in yangi:
        TalabaBadge.objects.get_or_create(talaba=talaba, kod=kod)
