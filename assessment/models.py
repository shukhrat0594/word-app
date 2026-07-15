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
