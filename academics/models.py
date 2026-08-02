from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


class Guruh(models.Model):
    """O'quv guruhi — bitta o'qituvchi va bir nechta talabani birlashtiradi."""

    name = models.CharField(max_length=200)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="guruhlar"
    )
    oqituvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oqituvchi_guruhlari",
        limit_choices_to={"role": "teacher"},
    )
    # `through="GuruhAzoligi"` (2026-08-02) — avval oddiy M2M edi, endi har
    # talaba uchun `boshlanish_unit` (qaysi Unit'dan boshlaydi) saqlanadi.
    talabalar = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="talaba_guruhlari",
        blank=True,
        limit_choices_to={"role": "student"},
        through="GuruhAzoligi",
    )
    # Fan/daraja (2026-08-02, foydalanuvchi talabi) — Kurslar bo'limidagi
    # daraxtdan olinadi (qattiq ro'yxat emas): `fan` — "Kurslar" ildizining
    # bevosita bolasi (masalan "Ingliz tili"), `daraja` — o'sha fanning
    # bolasi (masalan "Beginner", "IELTS", "CEFR"). Ikkisi ham ixtiyoriy —
    # eski guruhlar fan/darajasiz qolishi mumkin, keyin admin to'ldiradi.
    fan = models.ForeignKey(
        "courses.KursTugun", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="guruhlar_fan", help_text="Kurslar bo'limidagi fan (masalan Ingliz tili)",
    )
    daraja = models.ForeignKey(
        "courses.KursTugun", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="guruhlar_daraja", help_text="Tanlangan fan ichidagi daraja (masalan Beginner, IELTS)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.markaz.name})"


class GuruhAzoligi(models.Model):
    """Guruh-talaba bog'lanishi (2026-08-02) — `Guruh.talabalar`ning
    `through` modeli. Oddiy M2M'dan farqi: `boshlanish_unit` — talaba
    guruhga (demak, guruhning `daraja`siga) qo'shilganda, Kurslar
    bo'limida QAYSI Unit'dan boshlashi kerakligini belgilaydi.

    Foydalanuvchi talabi: boshlanish_unit'dan OLDINGI barcha Unit'lar
    talaba uchun QULFSIZ bo'ladi (lekin "tugallangan" deb belgilanmaydi —
    faqat qulf yo'q, statistikaga ta'sir qilmaydi). boshlanish_unit va
    undan keyingilari ODATDAGI tartibda (oldingi Unit'ning 60%+ natijasi
    bilan) ochiladi. Qo'shilganda standart qiymat — o'sha darajaning
    BIRINCHI Unit'i (ya'ni cheklovsiz, oddiy tartib) — admin keyin
    o'zgartirishi mumkin (`courses.views._unit_qulflanganmi` shu
    maydonni hisobga oladi)."""

    guruh = models.ForeignKey(Guruh, on_delete=models.CASCADE)
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={"role": "student"},
    )
    boshlanish_unit = models.ForeignKey(
        "courses.KursTugun", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Guruhning darajasi ichidagi Unit — talaba shundan boshlaydi, oldingilar qulfsiz",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("guruh", "talaba")
        verbose_name_plural = "Guruh a'zoliklari"


class Davomat(models.Model):
    """Kunlik yo'qlama — o'qituvchi guruh bo'yicha kim kelganini belgilaydi.

    Dars jadvali/kalendar yo'q (soddalashtirilgan): bitta yozuv = bitta
    talaba, bitta guruh, bitta sana, holat (Keldi/Kelmadi).
    """

    class Holat(models.TextChoices):
        KELDI = "keldi", "Keldi"
        KELMADI = "kelmadi", "Kelmadi"

    sana = models.DateField()
    guruh = models.ForeignKey(
        Guruh, on_delete=models.CASCADE, related_name="davomatlar"
    )
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="davomatlar",
        limit_choices_to={"role": "student"},
    )
    holat = models.CharField(max_length=10, choices=Holat.choices)
    belgilagan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="belgilagan_davomatlar",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sana", "guruh", "talaba"], name="davomat_unikal"
            )
        ]
        ordering = ["-sana"]

    def clean(self):
        if self.guruh_id and self.talaba_id:
            if not self.guruh.talabalar.filter(pk=self.talaba_id).exists():
                raise ValidationError(
                    f"{self.talaba} bu guruhga ({self.guruh}) a'zo emas."
                )

    def __str__(self):
        return f"{self.sana} — {self.talaba} — {self.get_holat_display()}"


@receiver(m2m_changed, sender=Guruh.talabalar.through)
def guruhga_qoshilganda_markaz_biriktir(sender, instance, action, pk_set, **kwargs):
    """Talaba guruhga qo'shilganda uning markazini guruh markaziga moslashtiradi.

    Talaba markazsiz bo'lsa (Google OAuth orqali o'z-o'zidan ro'yxatdan
    o'tgan) — guruh markazi biriktiriladi. Talaba boshqa markazga
    biriktirilgan bo'lsa — xato beriladi (bitta talaba bir vaqtda faqat
    bitta markazga tegishli bo'lishi kerak).
    """
    if action != "pre_add" or pk_set is None:
        return

    User = instance.talabalar.model
    for talaba in User.objects.filter(pk__in=pk_set):
        if talaba.markaz_id is None:
            talaba.markaz = instance.markaz
            talaba.save(update_fields=["markaz"])
        elif talaba.markaz_id != instance.markaz_id:
            raise ValidationError(
                f"{talaba} allaqachon boshqa markazga ({talaba.markaz}) "
                f"biriktirilgan, {instance.markaz} guruhiga qo'sha olmaysiz."
            )
