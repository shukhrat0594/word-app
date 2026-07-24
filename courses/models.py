from django.conf import settings
from django.db import models


class KursTugun(models.Model):
    """Kurslar bo'limining bitta tuguni — o'z-o'ziga bog'langan daraxt
    (Kurslar > Fan > Daraja > Bo'lim > Mashq turi, PDF texnik topshiriqdagi
    sxema bo'yicha). Farzandi bo'lmagan tugun — "oxirgi qatlam", unga
    to'g'ridan-to'g'ri fayl biriktiriladi.

    Tuzilma hozircha qattiq (management buyrug'i orqali bir martalik
    urug'lantiriladi) — admin faqat oxirgi qatlamga fayl biriktiradi,
    daraxtning o'zini frontenddan qura olmaydi (2026-07-21 kelishuvi).
    """

    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="kurs_tugunlari"
    )
    nomi = models.CharField(max_length=200)
    ikonka = models.CharField(
        max_length=10, blank=True, help_text="Emoji ikonka (masalan 🇬🇧, 📖)"
    )
    tartib = models.PositiveSmallIntegerField(default=0)
    tez_kunda = models.BooleanField(
        default=False,
        help_text="Hali kontent tayyor emas (masalan Rus tili/Matematika) — bo'sh, 'tez kunda' deb ko'rsatiladi",
    )
    unit_darsi = models.BooleanField(
        default=False,
        help_text=(
            "Ketma-ket o'tiladigan dars (masalan darslik Unit'i). Shu belgi "
            "qo'yilgan tugunlar bir xil ota-tugun ostida tartib bo'yicha "
            "ketma-ket ochiladi — talaba uchun keyingisi oldingisining "
            "BARCHA bo'limlaridagi mashqlardan jami 60%+ ball olmaguncha "
            "qulflangan bo'ladi."
        ),
    )
    fayl = models.FileField(
        upload_to="kurslar/fayllar/", blank=True,
        help_text="Faqat oxirgi qatlam (farzandsiz) tugunlarda ishlatiladi",
    )

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs tugunlari"

    def __str__(self):
        return self.nomi


class KursProgress(models.Model):
    """Talabaning bitta (oxirgi qatlam) tugunni tugatgani haqida belgisi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kurs_progresslari"
    )
    tugun = models.ForeignKey(KursTugun, on_delete=models.CASCADE, related_name="progresslar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Kurs progresslari"
        constraints = [
            models.UniqueConstraint(fields=["talaba", "tugun"], name="kurs_progress_unikal")
        ]


class KursMashq(models.Model):
    """Oxirgi qatlam tuguniga tegishli interaktiv, tekshiriladigan mashq
    (masalan darslikdan chiqarilgan savol-javob). `exercises.Mashq`dan
    mustaqil — Kurslar bo'limi o'z tarkibiga ega (2026-07-21).

    `savollar` — xuddi `exercises.Mashq.savollar` formati:
    [{"savol": "...", "variantlar": [...] (ixtiyoriy), "togri": "..."}]
    """

    tugun = models.ForeignKey(KursTugun, on_delete=models.CASCADE, related_name="mashqlar")
    tartib = models.PositiveSmallIntegerField(default=0)
    matn = models.TextField(blank=True, help_text="Topshiriq/passage matni (ixtiyoriy)")
    rasm = models.ImageField(
        upload_to="kurslar/mashq_rasm/", blank=True,
        help_text="Masalan darslikdagi rasmli savol (nechta narsa bor va h.k.)",
    )
    audio = models.FileField(
        upload_to="kurslar/mashq_audio/", blank=True,
        help_text="Darslikdagi audio (masalan Listening bo'limi uchun)",
    )
    savollar = models.JSONField(
        default=list,
        help_text='[{"savol": "...", "variantlar": [...] (ixtiyoriy), "togri": "..."}]',
    )

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs mashqlari"

    def __str__(self):
        return f"{self.tugun.nomi} — mashq #{self.tartib}"


class KursMashqYechim(models.Model):
    """Talabaning bitta KursMashq'ga bergan javoblari va natijasi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kurs_mashq_yechimlari"
    )
    mashq = models.ForeignKey(KursMashq, on_delete=models.CASCADE, related_name="yechimlar")
    javoblar = models.JSONField()
    ball = models.PositiveIntegerField()
    jami = models.PositiveIntegerField()
    natijalar = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Kurs mashq yechimlari"
        ordering = ["-created_at"]
