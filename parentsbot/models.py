"""Ota-ona boti modellari.

Maxfiylik: bu yerda bola ma'lumoti NUSXALANMAYDI — faqat `Talaba` (User) ga havola.
Xabar matnlari yuborish paytida o'qiladi.
"""

from datetime import time

from django.conf import settings
from django.db import models
from django.utils import timezone


def _hamma_kunlar():
    return [0, 1, 2, 3, 4, 5, 6]


def _dushanba():
    return [0]


class ParentsBotSozlama(models.Model):
    """Xabarlar QACHON va NIMA yuborilishi (CRM -> Sozlamalar -> "Ota-ona boti").

    Bitta yozuv (pk=1) — butun markaz uchun. Kunlar: 0=dushanba ... 6=yakshanba.
    """

    davomat_yoqilgan = models.BooleanField(default=True)
    davomat_kelmadi = models.BooleanField(default=True)
    davomat_kechikdi = models.BooleanField(default=True)
    davomat_sababli = models.BooleanField(default=False)

    tolov_yoqilgan = models.BooleanField(default=True)

    qarz_yoqilgan = models.BooleanField(default=True)
    qarz_kunlari = models.JSONField(default=_dushanba)
    qarz_soati = models.TimeField(default=time(10, 0))

    natija_yoqilgan = models.BooleanField(default=True)
    natija_kunlari = models.JSONField(default=_hamma_kunlar)
    natija_soati = models.TimeField(default=time(19, 0))

    # Tinch soatlar: shu vaqtda tushgan xabarlar kutadi va tugagach yuboriladi.
    tinch_boshi = models.TimeField(default=time(22, 0))
    tinch_oxiri = models.TimeField(default=time(8, 0))

    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ota-ona boti sozlamasi"

    @classmethod
    def ol(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ParentsBotKuzatuv(models.Model):
    """Bot jarayonining ichki holati (bitta yozuv, pk=1): oxirgi ko'rilgan Telegram
    yangilanishi — qayta ishga tushganda xabarlar takrorlanmasin."""

    oxirgi_update_id = models.BigIntegerField(default=0)
    # Davomat xabarlari shu paytdan KEYIN yaratilgan yozuvlar uchun yuboriladi (eski davomatlar
    # birinchi ishga tushganda ota-onalarga bir yo'la yog'ilib ketmasin).
    davomat_boshlandi = models.DateTimeField(null=True, blank=True)
    # To'lov xabarlari ham xuddi shunday: faqat shu paytdan keyin kiritilgan to'lovlar.
    tolov_boshlandi = models.DateTimeField(null=True, blank=True)
    # Qarz/natija shu sana uchun allaqachon skanerlangan — kun oxirigacha har 30 soniyada
    # og'ir hisob-kitob qaytarilmasin.
    qarz_skanlandi = models.DateField(null=True, blank=True)
    natija_skanlandi = models.DateField(null=True, blank=True)

    @classmethod
    def ol(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Abonent(models.Model):
    """Botga kirgan Telegram foydalanuvchisi (ota-ona)."""

    class Holat(models.TextChoices):
        TIL = "til", "Til tanlash"
        TELEFON = "telefon", "Telefon kutilmoqda"
        FARZAND_ISM = "farzand_ism", "Farzand ismi kutilmoqda"
        FARZAND_SANA = "farzand_sana", "Tug'ilgan sana kutilmoqda"
        TAYYOR = "tayyor", "Tayyor"

    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True)
    ism = models.CharField(max_length=200, blank=True)  # Telegramdagi ism (adminga ko'rsatiladi)
    telefon = models.CharField(max_length=20, blank=True)  # faqat O'Z kontakti bilan ulashilgan
    til = models.CharField(max_length=2, default="uz")
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.TIL)
    kontekst = models.JSONField(default=dict, blank=True)  # suhbatning vaqtinchalik ma'lumoti
    faol = models.BooleanField(default=True)  # /stop -> False: xabar yuborilmaydi
    toifa_ochirilgan = models.JSONField(default=list, blank=True)  # ota-ona o'zi o'chirgan toifalar
    urinishlar = models.JSONField(default=list, blank=True)  # ism bilan urinish vaqtlari (ISO)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ota-ona (Telegram)"

    def __str__(self):
        return f"{self.ism or self.telegram_id}"


class Boglanish(models.Model):
    """Ota-ona <-> farzand. Xabarlar FAQAT faol bog'lanishlar bo'yicha yuboriladi."""

    class Usul(models.TextChoices):
        TELEFON = "telefon", "Telefon raqami"
        ISM_SANA = "ism_sana", "Ism va tug'ilgan sana"
        ADMIN = "admin", "Admin ulagan"

    abonent = models.ForeignKey(Abonent, on_delete=models.CASCADE, related_name="boglanishlar")
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ota_bot_boglanishlar",
        limit_choices_to={"role": "student"},
    )
    usul = models.CharField(max_length=10, choices=Usul.choices)
    kim = models.ForeignKey(  # admin ulagan bo'lsa — kim
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    faol = models.BooleanField(default=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    # Oxirgi marta ulangan (qayta ulanganda yangilanadi): davomat/to'lov xabarlari faqat shundan
    # KEYINGI voqealar uchun — yangi ulangan ota-onaga eski tarix yog'ilib ketmasin.
    faollashgan = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["abonent", "talaba"], name="parentsbot_boglanish_unikal")]


class Sorov(models.Model):
    """Avtomatik ulanmagan ota-ona so'rovi — adminlar ko'rib chiqadi."""

    class Holat(models.TextChoices):
        KUTILMOQDA = "kutilmoqda", "Kutilmoqda"
        ULANDI = "ulandi", "Ulandi"
        RAD = "rad", "Rad etildi"

    abonent = models.ForeignKey(Abonent, on_delete=models.CASCADE, related_name="sorovlar")
    farzand_ismi = models.CharField(max_length=200)
    tugilgan_sana = models.CharField(max_length=30, blank=True)  # ota-ona yozgan matn
    nomzodlar = models.JSONField(default=list, blank=True)  # taxminiy mos talaba ID'lari
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA, db_index=True)
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    hal_qilgan = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    hal_vaqti = models.DateTimeField(null=True, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-yaratilgan"]


class Xabar(models.Model):
    """Ota-onaga yuboriladigan xabar navbati (davomat, to'lov, qarz, natija).

    Nega navbat: tinch soatlarda xabar kutadi, kechiktirilgan xabar yuborishdan oldin qayta
    tekshiriladi (davomat tuzatilgan bo'lsa bekor), va bir voqea uchun ikki marta yuborilmaydi
    (`abonent + kalit` yagona).
    """

    class Holat(models.TextChoices):
        KUTILMOQDA = "kutilmoqda", "Kutilmoqda"
        YUBORILDI = "yuborildi", "Yuborildi"
        BEKOR = "bekor", "Bekor qilindi"
        XATO = "xato", "Xato"

    abonent = models.ForeignKey(Abonent, on_delete=models.CASCADE, related_name="xabarlar")
    talaba = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    turi = models.CharField(max_length=20)  # "davomat" | "tolov" | "qarz" | "natija"
    kalit = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    yuborilsin = models.DateTimeField(db_index=True)  # shundan oldin yuborilmaydi
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA, db_index=True)
    urinish = models.PositiveSmallIntegerField(default=0)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yuborildi = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["abonent", "kalit"], name="parentsbot_xabar_unikal")]
        ordering = ["id"]
