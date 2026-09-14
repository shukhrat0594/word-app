"""CRM / Moliya modellari (2026-09-14).

MUHIM ARXITEKTURA QOIDASI (TZ 3.0): bog'lanish FAQAT bir tomonga —
`crm` -> LMS. LMS modellarida (`accounts`, `academics`, `courses`) `crm`ga
bitta ham ishora yo'q va yangi maydon qo'shilmaydi. Shu tufayli CRM
istalgan paytda o'chirilsa, LMS hech nima sezmaydi.

Guruh va a'zolikka kerak bo'lgan moliyaviy maydonlar ularning O'ZIGA
qo'shilmaydi — buning o'rniga OneToOne kengaytma jadvallari
(`GuruhMoliya`, `AzolikMoliya`) ishlatiladi. `academics.Guruh` LMS'ning
markaziy modeli (davomat, Kurslar qulfi, statistika unga tayanadi), unga
migratsiya qilish "tegilmaydi" shartini buzardi.
"""

from django.conf import settings
from django.db import models


class Filial(models.Model):
    """Markazning jismoniy filiali (Utmost Gor-Park va h.k.).

    `accounts.Markaz` bilan aralashtirmaslik kerak: Markaz — butun o'quv
    markazi (bitta), Filial — uning binolari (uchta). Markaz LMS modeli,
    Filial esa butunlay CRM ichida.
    """

    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="crm_filiallar"
    )
    nomi = models.CharField(max_length=200)
    manzil = models.CharField(max_length=300, blank=True)
    telefon = models.CharField(max_length=30, blank=True)
    faol = models.BooleanField(
        default=True, help_text="False bo'lsa — arxivlangan, ro'yxatlarda ko'rinmaydi"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nomi"]
        verbose_name_plural = "Filiallar"

    def __str__(self):
        return self.nomi


class KursNarxi(models.Model):
    """Kurs (daraja) darajasidagi oylik narx — narxning ASOSIY manbasi.

    Foydalanuvchi talabi (2026-09-14): "Kurs uchun bir xil summa bo'ladi,
    masalan IELTS - 660 000, Beginner - 400 000, guruh turiga qarab shu
    kurs narxi qo'shiladi."

    `academics.Guruh.daraja` allaqachon `courses.KursTugun`ga ishora
    qiladi, shuning uchun narx bir marta kiritiladi va o'sha darajaning
    BARCHA guruhlari uni avtomatik oladi — 20 ta IELTS guruhiga 20 marta
    narx kiritish shart emas.

    Guruh yoki alohida talaba uchun boshqacha narx kerak bo'lsa —
    `GuruhMoliya.narx` / `AzolikMoliya.narx` bilan bekor qilinadi
    (`crm.mantiq.amaldagi_narx`).
    """

    daraja = models.OneToOneField(
        "courses.KursTugun",
        on_delete=models.CASCADE,
        related_name="crm_narxi",
        help_text="Kurslar daraxtidagi daraja tuguni (Beginner, IELTS, CEFR...)",
    )
    narx = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Oylik narx, so'm"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Kurs narxlari"

    def __str__(self):
        return f"{self.daraja.nomi} — {self.narx}"


class GuruhMoliya(models.Model):
    """`academics.Guruh`ning CRM kengaytmasi — guruhga tegishli moliyaviy
    sozlamalar.

    Yozuv guruh yaratilganda AVTOMATIK yaratilmaydi (signal yo'q —
    `apps.py` izohiga qara): CRM'da admin guruhni sozlaganda
    `get_or_create` bilan paydo bo'ladi. Yozuvi yo'q guruh = CRM'da hali
    sozlanmagan guruh; unga hisob ochilmaydi va ogohlantirishlar
    ro'yxatida ko'rsatiladi.
    """

    guruh = models.OneToOneField(
        "academics.Guruh", on_delete=models.CASCADE, related_name="moliya"
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="guruhlar"
    )
    # Odatda BO'SH qoladi — kurs (daraja) narxi ishlatiladi. Faqat shu
    # guruh uchun boshqacha narx kerak bo'lsagina to'ldiriladi.
    narx = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Ixtiyoriy — kurs narxini bekor qiladi. Bo'sh bo'lsa daraja narxi olinadi",
    )
    boshlanish_sana = models.DateField(
        null=True, blank=True,
        help_text="Guruh ochilgan sana — birinchi oy shunga qarab proporsional bo'ladi",
    )
    tugash_sana = models.DateField(null=True, blank=True, help_text="Guruh tugaydigan sana")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Guruh moliyasi"

    def __str__(self):
        return f"{self.guruh.name} — moliya"


class DarsJadvali(models.Model):
    """Guruhning haftalik dars kunlari.

    1-bosqichda AYNAN moliya uchun kerak: proporsional hisob oyda nechta
    dars borligini bilishi shart (`crm.mantiq.oylik_dars_kunlari`).
    Haftalik setka UI, xona va konflikt tekshiruvi — 2-bosqichda; o'shanda
    shu modelga `xona` FK qo'shiladi.
    """

    class HaftaKuni(models.IntegerChoices):
        DUSHANBA = 0, "Dushanba"
        SESHANBA = 1, "Seshanba"
        CHORSHANBA = 2, "Chorshanba"
        PAYSHANBA = 3, "Payshanba"
        JUMA = 4, "Juma"
        SHANBA = 5, "Shanba"
        YAKSHANBA = 6, "Yakshanba"

    guruh = models.ForeignKey(
        "academics.Guruh", on_delete=models.CASCADE, related_name="crm_jadval"
    )
    hafta_kuni = models.PositiveSmallIntegerField(choices=HaftaKuni.choices)
    boshlanish_vaqti = models.TimeField()
    tugash_vaqti = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["hafta_kuni", "boshlanish_vaqti"]
        constraints = [
            models.UniqueConstraint(
                fields=["guruh", "hafta_kuni", "boshlanish_vaqti"],
                name="crm_jadval_takrorlanmasin",
            )
        ]
        verbose_name_plural = "Dars jadvallari"

    def __str__(self):
        return f"{self.guruh.name} — {self.get_hafta_kuni_display()} {self.boshlanish_vaqti}"


class AzolikMoliya(models.Model):
    """`academics.GuruhAzoligi`ning CRM kengaytmasi — talabaning SHU
    guruhdagi moliyaviy holati.

    Uch sababga ko'ra kerak (TZ 3.4):

    1. `GuruhAzoligi.created_at` yaramaydi — u `auto_now_add=True`, ya'ni
       tahrirlab bo'lmaydi. Talaba 3-sentabrda kelgan, admin uni
       10-sentabrda kiritsa, proporsional summa xato chiqadi va tuzatib
       bo'lmaydi. Shuning uchun `boshlanish_sana` shu yerda, qo'lda
       tahrirlanadigan qilib saqlanadi.

    2. Talaba holati (sinov/muzlatilgan). Ularga hisob ochilmasligi kerak
       — aks holda admin har oy qo'lda chegirma bosadi va hisobotdagi
       "chegirma" ustuni soxta raqamlar bilan to'lib ketadi.

    3. `oxirgi_hisob_oy` — generatsiya watermark'i. U ATAYLAB har
       a'zolikda alohida, umumiy "oxirgi oy" emas: umumiy watermark bilan
       oy o'rtasida qo'shilgan talabaga o'sha oy uchun hisob umuman
       ochilmay qolardi (ya'ni pul yo'qolardi) — `crm/mantiq.py` izohiga
       qara.
    """

    class Holat(models.TextChoices):
        SINOV = "sinov", "Sinov"
        FAOL = "faol", "Faol"
        MUZLATILGAN = "muzlatilgan", "Muzlatilgan"
        ARXIV = "arxiv", "Arxiv"

    azolik = models.OneToOneField(
        "academics.GuruhAzoligi", on_delete=models.CASCADE, related_name="moliya"
    )
    holat = models.CharField(
        max_length=15, choices=Holat.choices, default=Holat.FAOL, db_index=True,
        help_text="Faqat 'faol' holatdagi a'zolikka hisob ochiladi",
    )
    boshlanish_sana = models.DateField(
        help_text=(
            "Talaba shu guruhda boshlagan sana (standart — a'zolik yaratilgan "
            "kun, lekin tahrirlanadi)"
        )
    )
    tugash_sana = models.DateField(
        null=True, blank=True,
        help_text="Guruhdan chiqqan sana — o'sha oy proporsional qayta hisoblanadi",
    )
    # Muzlatishdan keyin qayta boshlagan sana. Soddalashtirish (bilib
    # turib, TZ 4.6): bir oy ichida bir necha marta muzlatilsa, faqat
    # OXIRGI sana hisobga olinadi — oraliqdagi kunlar hisoblanmaydi. Bu
    # talabaning foydasiga bo'lgan mayda xato; amalda muzlatish oy
    # hisobida bo'ladi.
    qayta_faol_sana = models.DateField(null=True, blank=True)
    narx = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Ixtiyoriy — guruh va kurs narxini bekor qiladi (aka-uka chegirmasi va h.k.)",
    )
    oxirgi_hisob_oy = models.DateField(
        null=True, blank=True, db_index=True,
        help_text=(
            "Hisob generatsiyasi shu a'zolik uchun qaysi oygacha yetgani "
            "(doim oyning 1-sanasi)"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "A'zolik moliyasi"

    def __str__(self):
        return f"{self.azolik} — {self.get_holat_display()}"


class Hisob(models.Model):
    """Bir talabaning bir guruhdagi BIR OYLIK hisob-fakturasi.

    Har oy avtomatik ochiladi (`crm.mantiq.hisoblarni_generatsiya_qil`),
    yoki admin qo'lda yaratadi (boshlang'ich qarzlar — `qolda=True`).

    `summa` generatsiya paytida QOTIB QOLADI: keyin kurs narxi o'zgarsa,
    o'tgan oylar hisobi o'zgarmaydi (SoffCRM'da ham shunday — avgust
    600 000, sentabr 660 000).
    """

    class Holat(models.TextChoices):
        QARZDOR = "qarzdor", "Qarzdor"
        QISMAN = "qisman", "Qisman to'langan"
        TOLANDI = "tolandi", "To'langan"

    # ── NEGA SET_NULL, CASCADE EMAS ─────────────────────────────────
    # Loyihada ikkita BUTUNLAY O'CHIRISH amali bor:
    # `accounts.FoydalanuvchiOchirishView` (user.delete()) va
    # `academics.GuruhDetailView.delete` (guruh.delete()). CASCADE bo'lsa,
    # admin o'qishni tugatgan talabani o'chirganda uning bir yillik to'lov
    # tarixi JIMGINA yo'qolardi va o'tgan oylar hisoboti o'zgarib ketardi
    # — buni hech kim sezmaydi.
    #
    # PROTECT ham EMAS: u LMS'dagi o'chirish tugmasini ishdan chiqarardi,
    # ya'ni CRM LMS xatti-harakatini o'zgartirgan bo'lardi — aynan biz
    # qochayotgan narsa.
    #
    # Shuning uchun SET_NULL + nom NUSXASI. Bu usul loyihada allaqachon
    # ishlatilgan: `audit.FaoliyatYozuvi` da `foydalanuvchi` -> SET_NULL,
    # yoniga `obyekt_nomi` ("obyekt o'chirilgandan keyin ham qolishi
    # uchun").
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="crm_hisoblari",
    )
    talaba_ism = models.CharField(
        max_length=200, help_text="Nom nusxasi — talaba o'chirilsa ham qoladi"
    )
    guruh = models.ForeignKey(
        "academics.Guruh", on_delete=models.SET_NULL, null=True,
        related_name="crm_hisoblari",
    )
    guruh_nomi = models.CharField(
        max_length=200, help_text="Nom nusxasi — guruh o'chirilsa ham qoladi"
    )
    # Filial SNAPSHOT: guruh boshqa filialga ko'chsa, O'TGAN oylar
    # hisoboti orqaga qarab o'zgarmasligi uchun.
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="hisoblar",
    )

    oy = models.DateField(help_text="Doim oyning 1-sanasi (2026-09-01)")
    summa = models.DecimalField(max_digits=12, decimal_places=2)
    proporsional = models.BooleanField(
        default=False,
        help_text="To'liq oy emas — guruh yoki talaba oy o'rtasida boshlagan/tugatgan",
    )
    darslar_jami = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Oydagi BARCHA dars kunlari (diagnostika uchun)"
    )
    darslar_talaba = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Shundan talabaga tegishlisi (diagnostika uchun)"
    )
    holat = models.CharField(
        max_length=10, choices=Holat.choices, default=Holat.QARZDOR, db_index=True,
        help_text=(
            "FAQAT `crm.mantiq.hisobni_yangila()` yozadi — boshqa hech qayerda "
            "qo'lda o'zgartirilmaydi"
        ),
    )
    qolda = models.BooleanField(
        default=False,
        help_text="Admin qo'lda kiritgan (boshlang'ich qarz), avtomatik generatsiya emas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-oy", "guruh_nomi", "talaba_ism"]
        constraints = [
            # Bir talabaga bir guruhda bir oyda BITTA hisob. Bu cheklov
            # generatsiyani idempotent qiladi: `get_or_create` bir necha
            # marta chaqirilsa ham dublikat bo'lmaydi.
            #
            # DIQQAT: `talaba`/`guruh` SET_NULL bilan NULL bo'lib qolsa,
            # SQL'da NULL'lar o'zaro teng emas — ya'ni o'chirilgan
            # talabaning yozuvlarida bu cheklov amalda ishlamay qoladi.
            # Bu MUAMMO EMAS: o'chirilgan talabaga yangi hisob
            # ochilmaydi, eski yozuvlar esa faqat tarix uchun qoladi.
            models.UniqueConstraint(
                fields=["talaba", "guruh", "oy"], name="crm_hisob_unikal"
            )
        ]
        verbose_name_plural = "Hisoblar"

    def __str__(self):
        return f"{self.talaba_ism} — {self.guruh_nomi} — {self.oy:%Y-%m} — {self.summa}"


class Tolov(models.Model):
    """Kassa yozuvi — to'lov, chegirma, bonus yoki pul qaytarish.

    | Turi      | Kassaga pul | Oy qarzini yopadi | Balansga |
    |-----------|-------------|-------------------|----------|
    | tolov     | Ha          | Ha                | +        |
    | chegirma  | YO'Q        | Ha                | +        |
    | bonus     | YO'Q        | Ha                | +        |
    | qaytarish | Chiqdi      | YO'Q              | -        |

    MUHIM: `chegirma` va `bonus` qarzni yopadi, lekin kassaga pul
    tushmaydi. Hisobotda "olingan pul" FAQAT `tolov` bo'yicha sanaladi,
    chegirma esa alohida ustunda — aks holda hisobot markaz olmagan pulni
    ko'rsatardi.

    `qaytarish` oy holatini O'ZGARTIRMAYDI (foydalanuvchi qarori,
    2026-09-14): pul qaytarish odatda bitta oyga bog'liq emas —
    ketayotgan odamga umumiy hisob-kitob qilib beriladi, ya'ni "qaysi
    oyni qayta ochamiz?" degan savol javobsiz qolardi. Qaytarilgan pul
    faqat BALANSDA ko'rinadi.
    """

    class Turi(models.TextChoices):
        TOLOV = "tolov", "To'lov"
        CHEGIRMA = "chegirma", "Chegirma"
        BONUS = "bonus", "Bonus"
        QAYTARISH = "qaytarish", "Pul qaytarish"

    # SET_NULL + nom nusxasi — sabab `Hisob` izohida.
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="crm_tolovlari",
    )
    talaba_ism = models.CharField(max_length=200)
    guruh = models.ForeignKey(
        "academics.Guruh", on_delete=models.SET_NULL, null=True,
        related_name="crm_tolovlari",
    )
    guruh_nomi = models.CharField(max_length=200)
    hisob = models.ForeignKey(
        Hisob, on_delete=models.SET_NULL, null=True, blank=True, related_name="tolovlar",
        help_text="Qaysi oy uchun. `qaytarish` uchun odatda bo'sh — u oyga bog'lanmaydi",
    )

    sana = models.DateField(help_text="Pul haqiqatda kelgan/chiqqan sana")
    summa = models.DecimalField(max_digits=12, decimal_places=2)
    turi = models.CharField(
        max_length=10, choices=Turi.choices, default=Turi.TOLOV, db_index=True
    )
    izoh = models.CharField(max_length=300, blank=True)
    kim_kiritdi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crm_kiritgan_tolovlari",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Qarzni yopadigan turlar — `hisobni_yangila()` shu ro'yxatga tayanadi.
    # Bitta joyda turadi, chunki ikki nusxa vaqt o'tib bir-biridan
    # uzoqlashadi (birida bonus qo'shilsa, ikkinchisida unutilardi).
    YOPUVCHI_TURLAR = (Turi.TOLOV, Turi.CHEGIRMA, Turi.BONUS)

    class Meta:
        ordering = ["-sana", "-id"]
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.sana} — {self.talaba_ism} — {self.get_turi_display()} {self.summa}"


class Sozlama(models.Model):
    """Bitta qatorli xizmat jadvali.

    ATAYLAB `accounts.Markaz`ga qo'shilmadi — u LMS modeli, unga maydon
    qo'shish "LMS'ga tegilmaydi" shartini buzardi (TZ 3.0, 1-qoida).
    """

    boshlangich_oy = models.DateField(
        help_text="Tizim yoqilgan oy — undan OLDINGI oylarga avtomatik hisob ochilmaydi",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Sozlamalar"

    def __str__(self):
        return f"CRM sozlamasi (boshlang'ich oy: {self.boshlangich_oy:%Y-%m})"
