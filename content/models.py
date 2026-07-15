from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Kurs(models.Model):
    """O'quv kursi (masalan "IELTS tayyorlov B1") — Markazga tegishli."""

    name = models.CharField(max_length=200)
    tavsif = models.TextField(blank=True)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="kurslar"
    )
    yaratgan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="yaratgan_kurslar",
    )
    tartib = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurslar"

    def __str__(self):
        return f"{self.name} ({self.markaz.name})"


class Dars(models.Model):
    """Kurs ichidagi bitta dars (masalan "1-dars: Introduction")."""

    name = models.CharField(max_length=200)
    kurs = models.ForeignKey(Kurs, on_delete=models.CASCADE, related_name="darslar")
    tavsif = models.TextField(blank=True)
    tartib = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Darslar"

    def __str__(self):
        return f"{self.kurs.name} / {self.name}"


class Material(models.Model):
    """Kontent birligi — matn, video (YouTube unlisted) yoki audio.

    Darsga bog'langan bo'lishi mumkin (video dars, uning matni) yoki
    mustaqil (lug'at, lug'at o'yinlari — dars=None).
    """

    class Turi(models.TextChoices):
        MATN = "matn", "Matn"
        VIDEO = "video", "Video (YouTube)"
        AUDIO = "audio", "Audio"

    class Korinish(models.TextChoices):
        PRIVATE = "private", "Shaxsiy (faqat o'z markazi)"
        PUBLIC = "public", "Umumiy (almashish tizimi)"

    name = models.CharField(max_length=200)
    turi = models.CharField(max_length=10, choices=Turi.choices)
    korinish = models.CharField(
        max_length=10, choices=Korinish.choices, default=Korinish.PRIVATE
    )
    dars = models.ForeignKey(
        Dars, on_delete=models.CASCADE, null=True, blank=True,
        related_name="materiallar",
    )
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="materiallar"
    )

    # Kontent maydonlari — turiga qarab bittasi to'ldiriladi
    matn = models.TextField(blank=True)
    youtube_id = models.CharField(
        max_length=20, blank=True,
        help_text="Faqat video ID (masalan dQw4w9WgXcQ), to'liq URL emas",
    )
    audio_fayl = models.FileField(upload_to="materiallar/audio/", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Materiallar"

    def clean(self):
        if self.dars_id and self.markaz_id:
            if self.dars.kurs.markaz_id != self.markaz_id:
                raise ValidationError(
                    "Material markazi dars kursining markazi bilan mos emas."
                )
        talab = {
            self.Turi.MATN: ("matn", self.matn),
            self.Turi.VIDEO: ("youtube_id", self.youtube_id),
            self.Turi.AUDIO: ("audio_fayl", self.audio_fayl),
        }
        if self.turi in talab:
            maydon, qiymat = talab[self.turi]
            if not qiymat:
                raise ValidationError(
                    {maydon: f"'{self.get_turi_display()}' turi uchun bu maydon majburiy."}
                )

    def __str__(self):
        return f"{self.name} [{self.get_turi_display()}]"


class DarsFaollik(models.Model):
    """Talabaning materialga kirishi — progress va B6.1 (ota-ona) uchun asos.

    Kirish logi vazifasini ham bajaradi (B3.2 — kim qachon nimani ochdi).
    """

    class Holat(models.TextChoices):
        BOSHLADI = "boshladi", "Boshladi"
        TUGATDI = "tugatdi", "Tugatdi"

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dars_faolliklari",
        limit_choices_to={"role": "student"},
    )
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE, related_name="faolliklar"
    )
    holat = models.CharField(
        max_length=10, choices=Holat.choices, default=Holat.BOSHLADI
    )
    boshlagan_vaqt = models.DateTimeField(auto_now_add=True)
    tugatgan_vaqt = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["talaba", "material"], name="faollik_unikal"
            )
        ]
        verbose_name_plural = "Dars faolliklari"

    def __str__(self):
        return f"{self.talaba} — {self.material} — {self.get_holat_display()}"


def public_kontent_ochiqmi(markaz) -> bool:
    """B3.1: markaz boshqa markazlarning Public kontentini ko'ra oladimi.

    Shart: o'zi kamida PUBLIC_UNLOCK_LIMIT ta Public material kiritgan
    bo'lishi kerak. Chegara sozlanadigan (settings), qattiq kodlanmagan.
    """
    limit = getattr(settings, "PUBLIC_UNLOCK_LIMIT", 5)
    return (
        Material.objects.filter(
            markaz=markaz, korinish=Material.Korinish.PUBLIC
        ).count()
        >= limit
    )


def korinadigan_materiallar(user):
    """Foydalanuvchiga ko'rinadigan materiallar to'plami (B3.1 qoidasi).

    - O'z markazining barcha materiallari (Private + Public).
    - Markaz ochilish shartini bajargan bo'lsa — boshqa markazlarning
      Public materiallari ham.
    """
    if user.markaz_id is None:
        return Material.objects.none()
    ozimniki = models.Q(markaz_id=user.markaz_id)
    if public_kontent_ochiqmi(user.markaz):
        return Material.objects.filter(
            ozimniki | models.Q(korinish=Material.Korinish.PUBLIC)
        )
    return Material.objects.filter(ozimniki)
