from django.db import models


class Soz(models.Model):
    """Lug'at so'zi — o'yinlar (Juftini top, Flashcard) uchun.

    Eski StudyCards loyihasidan import qilingan (~5,454 ta, CEFR darajalari
    bo'yicha) — `games/management/commands/sozlar_import.py`.
    """

    class Daraja(models.TextChoices):
        A1 = "A1", "A1"
        A2 = "A2", "A2"
        B1 = "B1", "B1"
        B2 = "B2", "B2"
        C1 = "C1", "C1"
        IDIOM = "idiom", "Idioma"

    en = models.CharField(max_length=200)
    uz = models.CharField(max_length=300)
    daraja = models.CharField(max_length=10, choices=Daraja.choices)
    turkum = models.CharField(max_length=50, blank=True)
    misol = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "So'zlar"
        indexes = [models.Index(fields=["daraja"])]

    def __str__(self):
        return f"{self.en} — {self.uz} ({self.daraja})"


class GrammatikaSavoli(models.Model):
    """Grammatika testi savoli (ko'p variantli) — o'yin sifatida.

    Eski StudyCards loyihasidan import qilingan (~90 ta, 9 mavzu bo'yicha) —
    `games/management/commands/grammatika_import.py`.
    """

    mavzu = models.CharField(max_length=50)
    savol = models.CharField(max_length=300)
    variantlar = models.JSONField()
    togri = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Grammatika savollari"
        indexes = [models.Index(fields=["mavzu"])]

    def __str__(self):
        return f"[{self.mavzu}] {self.savol}"
