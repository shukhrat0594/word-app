from django.conf import settings
from django.db import models


class WritingTekshiruv(models.Model):
    """Bitta Writing AI tekshiruvi — matn, AI natijasi va token sarfi.

    MVP'da bitta tarif: Tezkor tahlil (600 so'm). Chuqurroq tahlil (Sonnet)
    keyingi fazada qo'shiladi. To'lov 2-fazada — hozircha yozuvlar to'lovsiz.
    """

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="writing_tekshiruvlar",
    )
    matn = models.TextField()
    natija = models.JSONField()
    task_type = models.CharField(max_length=10, blank=True)
    overall_band = models.FloatField(null=True, blank=True)
    provider = models.CharField(max_length=10)
    model = models.CharField(max_length=50)
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

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speaking_tekshiruvlar",
    )
    rejim = models.CharField(max_length=10, choices=Rejim.choices)
    matn = models.TextField(help_text="Kiritilgan matn yoki Azure transkripsiyasi")
    audio_fayl = models.FileField(upload_to="speaking/audio/", blank=True)
    natija = models.JSONField()
    pronunciation = models.JSONField(
        null=True, blank=True, help_text="Azure Pronunciation natijasi (Tezkor rejimda)"
    )
    part_type = models.CharField(max_length=10, blank=True)
    overall_band = models.FloatField(
        null=True, blank=True,
        help_text="Matn rejimida — Pronunciation'siz 3 mezon o'rtachasi",
    )
    provider = models.CharField(max_length=10)
    model = models.CharField(max_length=50)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Speaking tekshiruvlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — {self.get_rejim_display()} — band {self.overall_band}"
