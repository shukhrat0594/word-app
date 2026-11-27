from django.conf import settings
from django.db import models


class WritingTekshiruv(models.Model):
    """Bitta Writing AI tekshiruvi — matn, AI natijasi va token sarfi.

    MVP'da bitta tarif: Tezkor tahlil (600 so'm). Chuqurroq tahlil (Sonnet)
    keyingi fazada qo'shiladi. To'lov 2-fazada — hozircha yozuvlar to'lovsiz.

    2026-08-15: `holat` maydoni qo'shildi — talabaning matni AI chaqirilishidan
    OLDIN, "kutilmoqda" holatida saqlanadi (AI xato bersa ham matn yo'qolmaydi).
    Standart qiymat TAYYOR — bu maydon qo'shilishidan oldin yaratilgan barcha
    yozuvlar muvaffaqiyatli tugatilgan edi, ular orqaga moslik uchun TAYYOR
    hisoblanadi.
    """

    class Holat(models.TextChoices):
        KUTILMOQDA = "kutilmoqda", "Kutilmoqda"
        TAYYOR = "tayyor", "Tayyor"
        XATO = "xato", "Xato"

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="writing_tekshiruvlar",
    )
    matn = models.TextField()
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.TAYYOR)
    natija = models.JSONField(null=True, blank=True)
    task_type = models.CharField(max_length=10, blank=True)
    overall_band = models.FloatField(null=True, blank=True)
    provider = models.CharField(max_length=10, blank=True)
    model = models.CharField(max_length=50, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Writing tekshiruvlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — band {self.overall_band} — {self.created_at:%Y-%m-%d %H:%M}"


class SpeakingTekshiruv(models.Model):
    """Bitta Speaking AI tekshiruvi.

    Matn rejimi (600 so'm): talaba matn kiritadi, faqat 3 mezon (Pronunciation
    yo'q). Tezkor tahlil (1000 so'm, B8-audio): audio -> Azure transkripsiya +
    Pronunciation + shu 3 mezon — Azure hisobi ochilganda qo'shiladi.
    """

    class Rejim(models.TextChoices):
        MATN = "matn", "Matn rejimi"
        TEZKOR = "tezkor", "Tezkor tahlil (audio)"

    class Holat(models.TextChoices):
        KUTILMOQDA = "kutilmoqda", "Kutilmoqda"
        TAYYOR = "tayyor", "Tayyor"
        XATO = "xato", "Xato"

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speaking_tekshiruvlar",
    )
    rejim = models.CharField(max_length=10, choices=Rejim.choices)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.TAYYOR)
    matn = models.TextField(help_text="Kiritilgan matn yoki Azure transkripsiyasi", blank=True)
    audio_fayl = models.FileField(upload_to="speaking/audio/", blank=True)
    natija = models.JSONField(null=True, blank=True)
    pronunciation = models.JSONField(
        null=True, blank=True, help_text="Azure Pronunciation natijasi (Tezkor rejimda)"
    )
    part_type = models.CharField(max_length=10, blank=True)
    overall_band = models.FloatField(
        null=True, blank=True,
        help_text="Matn rejimida — Pronunciation'siz 3 mezon o'rtachasi",
    )
    provider = models.CharField(max_length=10, blank=True)
    model = models.CharField(max_length=50, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Speaking tekshiruvlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — {self.get_rejim_display()} — band {self.overall_band}"


class AiTrenajyorYozuvi(models.Model):
    """AI Speaking Trainer va AI Grammar Coach mashg'ulotlari tarixi
    (Matn-TZ 779: Head Teacher talaba profilida shu mashqlar va natijalar
    tarixini ko'rishi kerak). Ikkala trenajyor holatni serverda
    saqlamaydi — bu yozuv faqat kuzatuv uchun:

    * Speaking Trainer — bitta suhbat = bitta yozuv (`sessiya` — frontend
      har so'rovda yuboradigan sessiya urug'i); har javobda `xabar_soni`
      va AI'ning so'nggi javobi (ball/izoh shu matnda) yangilanadi.
    * Grammar Coach — bitta mavzu = bitta yozuv; qo'shimcha savollar
      (follow-up) shu yozuvning `xabar_soni`ni oshiradi.
    """

    class Tur(models.TextChoices):
        SPEAKING_TRAINER = "speaking_trainer", "AI Speaking Trainer"
        GRAMMAR_COACH = "grammar_coach", "AI Grammar Coach"

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_trenajyor_yozuvlari"
    )
    tur = models.CharField(max_length=20, choices=Tur.choices)
    sessiya = models.CharField(max_length=20, blank=True)
    mavzu = models.CharField(max_length=200, blank=True, help_text="Daraja (Trainer) yoki mavzu (Coach)")
    xabar_soni = models.PositiveIntegerField(default=1)
    oxirgi_javob = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name_plural = "AI trenajyor yozuvlari"
        indexes = [models.Index(fields=["talaba", "tur", "sessiya"])]

    def __str__(self):
        return f"{self.talaba} — {self.get_tur_display()} — {self.mavzu}"
