from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Bolim(models.TextChoices):
    LISTENING = "listening", "Listening"
    READING = "reading", "Reading"


class Tur(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    FILL_BLANKS = "fill_blanks", "Fill in the Blanks"
    MATCHING = "matching", "Matching"
    MAP_LABELLING = "map_labelling", "Plan/Map/Diagram Labelling"
    SHORT_ANSWER = "short_answer", "Short Answer"
    MATCHING_HEADINGS = "matching_headings", "Matching Headings"
    TFNG = "tfng", "True/False/Not Given"


# Har bo'limda qaysi turlar bor (real IELTS formati, 2026-07-16).
# Kunlik limit (B4.1) shu ro'yxat uzunligidan hisoblanadi — tur qo'shilsa
# limit avtomatik moslashadi (qattiq kodlangan "5" yo'q).
BOLIM_TURLARI = {
    Bolim.LISTENING: [
        Tur.MULTIPLE_CHOICE,
        Tur.FILL_BLANKS,
        Tur.MATCHING,
        Tur.MAP_LABELLING,
        Tur.SHORT_ANSWER,
    ],
    Bolim.READING: [
        Tur.MULTIPLE_CHOICE,
        Tur.FILL_BLANKS,
        Tur.MATCHING_HEADINGS,
        Tur.TFNG,
        Tur.SHORT_ANSWER,
    ],
}


def javoblarni_tekshir(savollar, javoblar):
    """Talaba javoblarini tekshiradi (barcha turlar uchun yagona mexanizm).

    savollar: [{"savol": str, "variantlar": [...] (ixtiyoriy),
                "togri": str yoki [str, ...] (qabul qilinadigan variantlar)}]
    javoblar: [str, ...] — savollar tartibida talaba javoblari.

    Qaytaradi: {"ball": int, "jami": int, "natijalar": [bool, ...]}
    Solishtirish registr/bo'shliqqa sezgir emas.
    """

    def norm(s):
        return str(s).strip().lower()

    natijalar = []
    for i, savol in enumerate(savollar):
        togri = savol["togri"]
        qabul = togri if isinstance(togri, list) else [togri]
        javob = javoblar[i] if i < len(javoblar) else ""
        natijalar.append(norm(javob) in [norm(t) for t in qabul])
    return {
        "ball": sum(natijalar),
        "jami": len(savollar),
        "natijalar": natijalar,
    }


class Mashq(models.Model):
    """Bitta Listening yoki Reading mashqi — savollar JSON'da saqlanadi.

    Muhim (B3.2): "savollar" ichida to'g'ri javoblar bor — API orqali
    talabaga yuborishda "togri" maydonlari OLIB TASHLANISHI shart.
    """

    name = models.CharField(max_length=200)
    bolim = models.CharField(max_length=10, choices=Bolim.choices)
    tur = models.CharField(max_length=20, choices=Tur.choices)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="mashqlar"
    )
    korinish = models.CharField(
        max_length=10,
        choices=[("private", "Shaxsiy"), ("public", "Umumiy")],
        default="private",
    )

    # Kontent (turi/bo'limiga qarab)
    matn = models.TextField(blank=True, help_text="Reading passage / ko'rsatma")
    audio_fayl = models.FileField(upload_to="mashqlar/audio/", blank=True)
    rasm = models.ImageField(
        upload_to="mashqlar/rasm/", blank=True,
        help_text="Plan/Map/Diagram Labelling uchun",
    )

    savollar = models.JSONField(
        help_text=(
            'Ro\'yxat: [{"savol": "...", "variantlar": ["A", "B"], '
            '"togri": "A"}] — "togri" ro\'yxat ham bo\'lishi mumkin'
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Mashqlar"

    def clean(self):
        xatolar = {}

        if self.bolim and self.tur:
            ruxsat = BOLIM_TURLARI.get(self.bolim, [])
            if self.tur not in ruxsat:
                xatolar["tur"] = (
                    f"'{self.get_tur_display()}' turi "
                    f"{self.get_bolim_display()} bo'limida yo'q."
                )

        if self.bolim == Bolim.LISTENING and not self.audio_fayl:
            xatolar["audio_fayl"] = "Listening mashqi uchun audio majburiy."
        if self.bolim == Bolim.READING and not self.matn:
            xatolar["matn"] = "Reading mashqi uchun matn (passage) majburiy."
        if self.tur == Tur.MAP_LABELLING and not self.rasm:
            xatolar["rasm"] = "Labelling turi uchun rasm majburiy."

        if not isinstance(self.savollar, list) or not self.savollar:
            xatolar["savollar"] = "Kamida bitta savoldan iborat ro'yxat bo'lishi kerak."
        else:
            for i, s in enumerate(self.savollar):
                if not isinstance(s, dict) or "savol" not in s or "togri" not in s:
                    xatolar["savollar"] = (
                        f"{i + 1}-savolda 'savol' va 'togri' maydonlari majburiy."
                    )
                    break

        if xatolar:
            raise ValidationError(xatolar)

    def __str__(self):
        return f"{self.name} [{self.get_bolim_display()}/{self.get_tur_display()}]"


class MashqYechim(models.Model):
    """Talabaning mashqqa bergan javoblari va avtomatik natijasi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mashq_yechimlari",
        limit_choices_to={"role": "student"},
    )
    mashq = models.ForeignKey(
        Mashq, on_delete=models.CASCADE, related_name="yechimlar"
    )
    javoblar = models.JSONField()
    ball = models.PositiveIntegerField()
    jami = models.PositiveIntegerField()
    natijalar = models.JSONField(help_text="Har savol bo'yicha [true/false]")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Mashq yechimlari"
        ordering = ["-created_at"]

    @classmethod
    def yechish(cls, talaba, mashq, javoblar):
        """Javoblarni tekshirib, natijani saqlaydi."""
        natija = javoblarni_tekshir(mashq.savollar, javoblar)
        return cls.objects.create(
            talaba=talaba,
            mashq=mashq,
            javoblar=javoblar,
            ball=natija["ball"],
            jami=natija["jami"],
            natijalar=natija["natijalar"],
        )

    def __str__(self):
        return f"{self.talaba} — {self.mashq} — {self.ball}/{self.jami}"


class LimitTopUp(models.Model):
    """Kunlik limit to'ldiruvi — 500 so'm = o'sha kunga har turdan +1.

    Hozircha to'lov tizimi yo'q (2-faza, Payme/Click) — yozuvlar test/admin
    orqali yaratiladi. To'lov qo'shilganda shu model to'lovga bog'lanadi.
    """

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="limit_topuplar",
        limit_choices_to={"role": "student"},
    )
    bolim = models.CharField(max_length=10, choices=Bolim.choices)
    sana = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Limit to'ldiruvlari"

    def __str__(self):
        return f"{self.talaba} — {self.get_bolim_display()} — {self.sana} (+har turdan 1)"


def kunlik_limit_holati(talaba, bolim):
    """Talabaning bugungi limiti: har tur bo'yicha ruxsat/ishlatilgan/qolgan.

    Qoida (B4.1): har turdan kuniga 1 ta bepul + har top-up har turga +1.
    Tur ro'yxati BOLIM_TURLARI'dan olinadi — moslashuvchan.
    """
    import datetime

    bugun = datetime.date.today()
    topup = LimitTopUp.objects.filter(
        talaba=talaba, bolim=bolim, sana=bugun
    ).count()
    ruxsat = 1 + topup

    holat = {}
    for tur in BOLIM_TURLARI[bolim]:
        ishlatilgan = MashqYechim.objects.filter(
            talaba=talaba,
            mashq__bolim=bolim,
            mashq__tur=tur,
            created_at__date=bugun,
        ).count()
        holat[str(tur)] = {
            "ruxsat": ruxsat,
            "ishlatilgan": ishlatilgan,
            "qolgan": max(0, ruxsat - ishlatilgan),
        }
    return holat


def korinadigan_mashqlar(user):
    """Foydalanuvchiga ko'rinadigan mashqlar (B3.1 qoidasi bilan bir xil)."""
    from content.models import public_kontent_ochiqmi

    if user.markaz_id is None:
        return Mashq.objects.none()
    ozimniki = models.Q(markaz_id=user.markaz_id)
    if public_kontent_ochiqmi(user.markaz):
        return Mashq.objects.filter(ozimniki | models.Q(korinish="public"))
    return Mashq.objects.filter(ozimniki)
