from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Bolim(models.TextChoices):
    LISTENING = "listening", "Listening"
    READING = "reading", "Reading"
    WRITING = "writing", "Writing"
    SPEAKING = "speaking", "Speaking"


class Tur(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    FILL_BLANKS = "fill_blanks", "Fill in the Blanks"
    MATCHING = "matching", "Matching"
    MAP_LABELLING = "map_labelling", "Plan/Map/Diagram Labelling"
    SHORT_ANSWER = "short_answer", "Short Answer"
    MATCHING_HEADINGS = "matching_headings", "Matching Headings"
    TFNG = "tfng", "True/False/Not Given"
    TASK1 = "task1", "Writing Task 1"
    TASK2 = "task2", "Writing Task 2"
    PART1 = "part1", "Speaking Part 1"
    PART2 = "part2", "Speaking Part 2"
    PART3 = "part3", "Speaking Part 3"


# Har bo'limda qaysi turlar bor (real IELTS formati, 2026-07-16).
# Kunlik limit (B4.1) shu ro'yxat uzunligidan hisoblanadi — tur qo'shilsa
# limit avtomatik moslashadi (qattiq kodlangan "5" yo'q). Writing/Speaking —
# auto-baholanmaydigan kontent banki (mavzu/namuna), shuning uchun limitga
# kirmaydi (ular MashqYechim orqali emas, faqat o'qish uchun).
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
    Bolim.WRITING: [Tur.TASK1, Tur.TASK2],
    Bolim.SPEAKING: [Tur.PART1, Tur.PART2, Tur.PART3],
}

# Auto-baholanadigan (savollar/to'g'ri javob talab qiladigan) bo'limlar.
AVTO_BAHOLANADIGAN_BOLIMLAR = (Bolim.LISTENING, Bolim.READING)


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
    matn = models.TextField(
        blank=True, help_text="Reading passage / Writing topshirig'i / Speaking savoli"
    )
    audio_fayl = models.FileField(upload_to="mashqlar/audio/", blank=True)
    rasm = models.ImageField(
        upload_to="mashqlar/rasm/", blank=True,
        help_text="Plan/Map/Diagram Labelling yoki Writing Task 1 grafigi uchun",
    )
    namuna_javob = models.TextField(
        blank=True, help_text="Writing/Speaking uchun namuna javob (ixtiyoriy)"
    )

    savollar = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Ro\'yxat: [{"savol": "...", "variantlar": ["A", "B"], '
            '"togri": "A"}] — "togri" ro\'yxat ham bo\'lishi mumkin. '
            "Writing/Speaking uchun bo'sh qoldirilishi mumkin."
        ),
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
        if self.bolim in (Bolim.READING, Bolim.WRITING, Bolim.SPEAKING) and not self.matn:
            xatolar["matn"] = "Matn (passage/topshiriq/savol) majburiy."
        if self.tur == Tur.MAP_LABELLING and not self.rasm:
            xatolar["rasm"] = "Labelling turi uchun rasm majburiy."

        if self.bolim in AVTO_BAHOLANADIGAN_BOLIMLAR:
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
    """Foydalanuvchiga ko'rinadigan mashqlar (B3.1 qoidasi bilan bir xil).

    Markazga biriktirilmagan foydalanuvchi (masalan "oddiy foydalanuvchi")
    ham "hammaga ochiq" (`korinish="public"`) mashqlarni ko'radi — 9-faza
    qoidasi: Mashqlar Utmost talabasi bo'lmaganlar uchun ham ochiq.
    """
    from content.models import public_kontent_ochiqmi

    if user.markaz_id is None:
        return Mashq.objects.filter(korinish="public")
    ozimniki = models.Q(markaz_id=user.markaz_id)
    if public_kontent_ochiqmi(user.markaz):
        return Mashq.objects.filter(ozimniki | models.Q(korinish="public"))
    return Mashq.objects.filter(ozimniki)


class ImtihonTest(models.Model):
    """To'liq IELTS testi (masalan Cambridge uslubidagi Reading/Listening Test)
    — bir nechta TestQismi'dan iborat, uzluksiz raqamlangan yagona imtihon.

    Mavjud Mashq bankidan (bitta passage/audio = alohida kichik mashq)
    mustaqil — kunlik limit tizimiga bog'lanmaydi (10/11-faza, 2026-07-19).
    """

    name = models.CharField(max_length=200)
    bolim = models.CharField(max_length=10, choices=Bolim.choices)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="imtihon_testlari"
    )
    korinish = models.CharField(
        max_length=10,
        choices=[("private", "Shaxsiy"), ("public", "Umumiy")],
        default="private",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Imtihon testlari"

    def __str__(self):
        return f"{self.name} [{self.get_bolim_display()}]"


class TestQismi(models.Model):
    """Bitta testning bir qismi (Reading passage / Listening audio bo'lagi)."""

    test = models.ForeignKey(ImtihonTest, on_delete=models.CASCADE, related_name="qismlar")
    tartib = models.PositiveSmallIntegerField()
    sarlavha = models.CharField(max_length=200, blank=True, help_text="masalan 'Passage 1'")
    yoriqnoma = models.CharField(
        max_length=300, blank=True,
        help_text="masalan 'You should spend about 20 minutes on Questions 1-13.'",
    )
    matn = models.TextField(
        blank=True, help_text="Reading passage matni / Writing-Speaking uchun savol-topshiriq matni"
    )
    tur = models.CharField(
        max_length=20, choices=Tur.choices, blank=True,
        help_text="Faqat Writing/Speaking uchun: task1/task2/part1/part2/part3. Reading/Listening'da savol turlari 'savollar' ichida, bu yerda bo'sh qoladi.",
    )
    audio_fayl = models.FileField(upload_to="imtihon/audio/", blank=True)
    rasm = models.ImageField(
        upload_to="imtihon/rasm/", blank=True,
        help_text="Plan/Map/Diagram Labelling yoki Writing Task 1 grafigi uchun",
    )
    savollar = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Reading/Listening uchun ro\'yxat: [{"savol": "...", "tur": "multiple_choice", '
            '"variantlar": ["A", "B"], "togri": "A", "guruh_boshi": "Questions 1-7" (ixtiyoriy)}]. '
            "Writing/Speaking'da bo'sh qoladi — javob AI orqali baholanadi."
        ),
    )

    class Meta:
        ordering = ["tartib"]
        unique_together = [("test", "tartib")]
        verbose_name_plural = "Test qismlari"

    def __str__(self):
        return f"{self.test.name} — {self.sarlavha or self.tur or self.tartib}"


class TestYechim(models.Model):
    """Talabaning to'liq testga bergan javoblari va natijasi (flat, uzluksiz)."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="imtihon_yechimlari",
        limit_choices_to={"role": "student"},
    )
    test = models.ForeignKey(ImtihonTest, on_delete=models.CASCADE, related_name="yechimlar")
    javoblar = models.JSONField()
    ball = models.PositiveIntegerField()
    jami = models.PositiveIntegerField()
    natijalar = models.JSONField()
    band = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Imtihon yechimlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — {self.test} — {self.ball}/{self.jami} (Band {self.band})"


# Ommaviy IELTS tayyorgarlik manbalaridan olingan TAXMINIY xom ball -> band
# jadvali (Academic, 40 savol asosida). Rasmiy Cambridge/IDP konvertatsiya
# jadvali bilan ozgina farq qilishi mumkin — aniq rasmiy manba emas.
_READING_BAND_JADVALI = [
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0), (27, 6.5),
    (23, 6.0), (19, 5.5), (15, 5.0), (13, 4.5), (10, 4.0), (8, 3.5),
    (6, 3.0), (4, 2.5),
]
_LISTENING_BAND_JADVALI = [
    (39, 9.0), (37, 8.5), (35, 8.0), (32, 7.5), (30, 7.0), (26, 6.5),
    (23, 6.0), (18, 5.5), (16, 5.0), (13, 4.5), (11, 4.0), (8, 3.5),
    (6, 3.0), (4, 2.5),
]


def band_hisobla(ball, jami, bolim):
    """Xom ballni (ball/jami) taxminiy IELTS bandiga aylantiradi.

    jami 40'dan farq qilsa, 40 savolga proporsional moslashtiriladi.
    """
    if jami <= 0:
        return None
    ball40 = round(ball / jami * 40)
    jadval = _READING_BAND_JADVALI if bolim == Bolim.READING else _LISTENING_BAND_JADVALI
    for chegara, band in jadval:
        if ball40 >= chegara:
            return band
    return 2.0


def korinadigan_testlar(user):
    """Foydalanuvchiga ko'rinadigan to'liq testlar.

    Platforma bitta markaz rejimida ishlaydi (REJA.md) — shuning uchun
    markaz/korinish bo'yicha filtrlash foyda bermaydi, faqat guruhga hali
    qo'shilmagan (`markaz=None`, masalan Google orqali endigina ro'yxatdan
    o'tgan) talabani noto'g'ri barcha testlardan mahrum qilardi. Endi
    "oddiy foydalanuvchi" (Utmost talabasi emas) dan boshqa barcha
    autentifikatsiyalangan foydalanuvchi (talaba/o'qituvchi/admin/owner)
    barcha testlarni ko'radi (2026-07-21).
    """
    if user.role == "oddiy":
        return ImtihonTest.objects.none()
    return ImtihonTest.objects.all()
