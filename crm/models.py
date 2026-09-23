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
    # Video-TZ (13:44-14:05): "baholash tizimi ixtiyoriy, majburiy emas —
    # masalan birdan beshgacha". Bo'sh — guruhda baho qo'yilmaydi.
    baholash_tizimi = models.CharField(
        max_length=5, blank=True,
        choices=[("5", "1-5 ball"), ("10", "1-10 ball"), ("100", "100 ball")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Guruh moliyasi"

    def __str__(self):
        return f"{self.guruh.name} — moliya"


class Xona(models.Model):
    """Filialdagi o'quv xonasi (2026-09-14, 2-bosqichdan oldinga
    ko'chirildi — foydalanuvchi haftalik setkani darhol so'radi).

    Xona FILIALGA tegishli: "2-xona" har filialda boshqa xona, shuning
    uchun nomi global unikal emas, faqat filial ichida.
    """

    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="xonalar")
    nomi = models.CharField(max_length=100, help_text="Masalan '2-xona'")
    sigimi = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Nechta o'quvchi sig'adi (ixtiyoriy)"
    )
    tartib = models.PositiveSmallIntegerField(
        default=0, help_text="Setkada qaysi tartibda turishi"
    )
    faol = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["filial__nomi", "tartib", "nomi"]
        constraints = [
            models.UniqueConstraint(
                fields=["filial", "nomi"], name="crm_xona_filialda_unikal"
            )
        ]
        verbose_name_plural = "Xonalar"

    def __str__(self):
        return f"{self.nomi} ({self.filial.nomi})"


class DarsJadvali(models.Model):
    """Guruhning haftalik dars kunlari.

    1-bosqichda AYNAN moliya uchun kerak: proporsional hisob oyda nechta
    dars borligini bilishi shart (`crm.mantiq.oylik_dars_kunlari`).
    2026-09-14: haftalik setka UI, `xona` va to'qnashuv tekshiruvi ham
    shu yerga qo'shildi (avval 2-bosqichga rejalashtirilgan edi).
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
    # Xona O'CHIRILSA dars yozuvi qolishi kerak (jadval buzilmasin) —
    # shuning uchun SET_NULL. Xonasiz darslar setkada alohida
    # "Xonasiz" qatorida ko'rsatiladi.
    xona = models.ForeignKey(
        Xona, on_delete=models.SET_NULL, null=True, blank=True, related_name="darslar"
    )
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
    # Video (20:30, 22:25): "Qarzdorlikni tahrirlash" oynasida izoh —
    # "Sentabrda 4 ta darsga keladi".
    izoh = models.CharField(max_length=300, blank=True)
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

    class Usul(models.TextChoices):
        """To'lov usuli (video-TZ, 2026-09-23: SoffCRM to'lov oynasidagi
        "Naqd / Click" tanlovi). Hisobotda kassa naqd va o'tkazmaga
        ajratiladi."""

        NAQD = "naqd", "Naqd"
        KARTA = "karta", "Plastik karta"
        CLICK = "click", "Click"
        PAYME = "payme", "Payme"
        OTKAZMA = "otkazma", "Bank o'tkazmasi"
        QR = "qr", "Yagona QR-kod"
        VOUCHER = "voucher", "Voucher"

    sana = models.DateField(help_text="Pul haqiqatda kelgan/chiqqan sana")
    summa = models.DecimalField(max_digits=12, decimal_places=2)
    turi = models.CharField(
        max_length=10, choices=Turi.choices, default=Turi.TOLOV, db_index=True
    )
    usul = models.CharField(
        max_length=10, choices=Usul.choices, default=Usul.NAQD, blank=True,
        help_text="Faqat 'tolov' va 'qaytarish' uchun ma'noli",
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


class Eslatma(models.Model):
    """Guruh yoki talaba haqidagi erkin izoh (2026-09-15).

    SoffCRM'da guruh kartasida "ESLATMALAR" tabi bor va bu — LMS'da ham,
    CRM'da ham BO'LMAGAN yagona narsa edi. Adminning kundalik ishida
    kerak: "onasi 15-sentabrda to'layman dedi", "dars vaqtini
    ko'chirishni so'radi".

    `guruh` va `talaba` ikkalasi ham ixtiyoriy, lekin KAMIDA BITTASI
    bo'lishi shart — eslatma nimagadir tegishli bo'lmasa, uni hech kim
    qayta topa olmaydi.

    `CASCADE` (pul yozuvlaridagi `SET_NULL` emas): eslatma pul emas,
    obyekt o'chirilgach uning izohi ma'nosini yo'qotadi.
    """

    guruh = models.ForeignKey(
        "academics.Guruh", on_delete=models.CASCADE, null=True, blank=True,
        related_name="crm_eslatmalari",
    )
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="crm_eslatmalari",
    )
    # 2026-09-23 (video-TZ): lid kartasidagi "Eslatmalar" tabi ham shu
    # jadvalda — alohida jadval ikki xil "izoh" tushunchasini keltirardi.
    lid = models.ForeignKey(
        "Lid", on_delete=models.CASCADE, null=True, blank=True, related_name="eslatmalar",
    )
    # Ixtiyoriy eslatish vaqti ("23.09 kuni keladi") — lid kartochkasi
    # ustida va bosh sahifada ko'rsatiladi.
    eslatish_vaqti = models.DateTimeField(null=True, blank=True)
    matn = models.TextField(max_length=2000)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crm_yozgan_eslatmalari",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(guruh__isnull=False)
                    | models.Q(talaba__isnull=False)
                    | models.Q(lid__isnull=False)
                ),
                name="crm_eslatma_egasi_bolsin_v2",
            )
        ]
        verbose_name_plural = "Eslatmalar"

    def __str__(self):
        egasi = self.talaba or self.guruh
        return f"{egasi} — {self.matn[:40]}"


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


# ═════════════════════════════════════════════════════════════════════
# 2026-09-23 — VIDEO-TZ ("CRM TZ.mp4"): SoffCRM'dagi hamma bo'limlar.
#
# Shuhrat qarori: CRM endi ASOSIY manba — talaba, guruh, xodim CRM'da
# yaratiladi, saytda faqat mashqlar qoladi. Arxitektura qoidasi
# o'zgarmadi: bog'lanish baribir faqat `crm -> LMS`. CRM LMS jadvallariga
# (User, Guruh, GuruhAzoligi, Davomat) YOZADI, lekin LMS modellariga
# bitta ham maydon qo'shilmaydi — kerakli qo'shimchalar yana OneToOne
# kengaytma jadvallarida (`XodimProfil`, `TalabaProfil`, `DavomatIzoh`).
# ═════════════════════════════════════════════════════════════════════


class LidDoska(models.Model):
    """Lidlar doskasi (SoffCRM'dagi "Bo'lim": "LEADS", "LEADS uzb",
    "Beg"...). Har doskada o'z ustunlari (`LidBolim`) bor — "Bo'lim
    yaratish" doska ochadi, "Qo'shimcha ustun qo'shish" esa ustun."""

    nomi = models.CharField(max_length=100)
    tartib = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tartib", "id"]

    def __str__(self):
        return self.nomi


class LidBolim(models.Model):
    """Lidlar kanbanidagi ustun ("New leads", "Beginner", "Rus tili"...).

    SoffCRM'da ustunlar erkin yaratiladi ("Bo'lim yaratish" / "Qo'shimcha
    ustun qo'shish") — qattiq ro'yxat emas. `tartib` ustunlar ketma-
    ketligi, `filial` bo'sh bo'lsa ustun hamma filialda ko'rinadi.
    """

    nomi = models.CharField(max_length=100)
    tartib = models.PositiveSmallIntegerField(default=0)
    doska = models.ForeignKey(
        LidDoska, on_delete=models.CASCADE, null=True, blank=True, related_name="ustunlar",
    )
    # Ustun guruhga bog'lansa (video 05:40: ustun nomi guruhlardan
    # tanlanadi), "Guruhga qo'shish" shu guruhni taklif qiladi.
    guruh = models.ForeignKey(
        "academics.Guruh", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="lid_bolimlari"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Lid bo'limlari"

    def __str__(self):
        return self.nomi


class Lid(models.Model):
    """Potensial o'quvchi — hali talaba emas (SoffCRM "Lidlar").

    Lid guruhga qo'shilganda (`LidGuruhgaView`) undan LMS talabasi
    (`accounts.User`, role=student) yaratiladi va `talaba` shu yerga
    yoziladi. Lid o'chmaydi — `arxiv=True` bo'ladi, qayerdan kelgani
    (manba) statistikasi uchun kerak.
    """

    class Holat(models.TextChoices):
        YANGI = "yangi", "Yangi"
        BOGLANILDI = "boglanildi", "Bog'lanildi"
        BOGLANA_OLMADI = "boglana_olmadi", "Bog'lana olmadi"
        SINOV = "sinov", "Sinov darsida"
        KELMADI = "kelmadi", "Kelmadi"
        OYLAYAPTI = "oylayapti", "O'ylayapti"
        YOQOTILGAN = "yoqotilgan", "Yo'qotilgan"
        QOSHILDI = "qoshildi", "Guruhga qo'shildi"

    ism = models.CharField(max_length=200)
    telefon = models.CharField(max_length=20)
    qoshimcha_telefon = models.CharField(max_length=20, blank=True)
    qoshimcha_ism = models.CharField(
        max_length=100, blank=True, help_text="Qo'shimcha raqam egasi (masalan 'oyisi Hilola opa')"
    )
    tugilgan_sana = models.DateField(null=True, blank=True)
    manba = models.CharField(max_length=100, blank=True)
    bolim = models.ForeignKey(
        LidBolim, on_delete=models.SET_NULL, null=True, blank=True, related_name="lidlar"
    )
    holat = models.CharField(max_length=16, choices=Holat.choices, default=Holat.YANGI, db_index=True)
    # Lid "harorati" (video 08:15, lid kartasi): qanchalik tayyor.
    harorat = models.CharField(
        max_length=6, blank=True,
        choices=[("issiq", "Issiq"), ("iliq", "Iliq"), ("sovuq", "Sovuq")],
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="lidlar"
    )
    # Lid qaysi kurs/vaqtni xohlaydi — "Qulay vaqt", "O'qituvchi", "Kunlar".
    kurs = models.ForeignKey(
        "courses.KursTugun", on_delete=models.SET_NULL, null=True, blank=True, related_name="crm_lidlari"
    )
    oqituvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crm_lidlari_oqituvchi",
    )
    qulay_vaqt = models.CharField(max_length=50, blank=True)
    kunlar = models.CharField(max_length=20, blank=True, help_text="toq / juft / har_kuni / boshqa")
    izoh = models.CharField(max_length=500, blank=True)
    arxiv = models.BooleanField(default=False, db_index=True)
    qora_royxat = models.BooleanField(default=False, db_index=True)
    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crm_lid_manbasi",
        help_text="Lid talabaga aylangandan keyin — o'sha talaba",
    )
    kim_qoshdi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crm_qoshgan_lidlari",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "Lidlar"

    def __str__(self):
        return f"{self.ism} ({self.telefon})"


class LidTarix(models.Model):
    """Lid kartasidagi "Lead tarixi" — kim, qachon, nimani o'zgartirdi."""

    lid = models.ForeignKey(Lid, on_delete=models.CASCADE, related_name="tarix")
    matn = models.CharField(max_length=300)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class CrmRol(models.Model):
    """Xodimga beriladigan maxsus rol ("Administrator 1", "Marketolog"...).

    SoffCRM'dagi "Yangi rol yaratish" oynasi: rol nomi + ruxsatlar
    daraxti (bo'lim -> kichik bo'limlar). `ruxsatlar` — ruxsat
    kalitlari ro'yxati (`crm.ruxsatlar.RUXSAT_DARAXTI` dagi kalitlar).
    """

    nomi = models.CharField(max_length=100, unique=True)
    faol = models.BooleanField(default=True)
    ruxsatlar = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nomi"]
        verbose_name_plural = "CRM rollari"

    def __str__(self):
        return self.nomi


class XodimProfil(models.Model):
    """`accounts.User` (xodim)ning CRM kengaytmasi — SoffCRM "Xodim
    qo'shish" oynasidagi maydonlar.

    `lavozim` SoffCRM'dagi "Kasbi" tablari. LMS roli lavozimdan kelib
    chiqadi (`crm.ruxsatlar.lms_roli`): o'qituvchi -> teacher,
    administrator -> admin, qolganlari (kassir, marketolog...) -> "oddiy",
    ya'ni saytda hech qanday boshqaruv huquqi yo'q, CRM'ga faqat rol
    ruxsatlari bilan kiradi.
    """

    class Lavozim(models.TextChoices):
        ADMIN = "admin", "Administrator"
        CEO = "ceo", "CEO"
        OQITUVCHI = "oqituvchi", "O'qituvchi"
        SUPPORT = "support", "Support teacher"
        KASSIR = "kassir", "Kassir"
        MARKETOLOG = "marketolog", "Marketolog"
        WATCHER = "watcher", "Kuzatuvchi"
        BOSHQA = "boshqa", "Boshqa"

    class Jins(models.TextChoices):
        ERKAK = "erkak", "Erkak"
        AYOL = "ayol", "Ayol"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_xodim"
    )
    lavozim = models.CharField(max_length=12, choices=Lavozim.choices, default=Lavozim.BOSHQA, db_index=True)
    rol = models.ForeignKey(
        CrmRol, on_delete=models.SET_NULL, null=True, blank=True, related_name="xodimlar",
        help_text="Maxsus rol — bo'lsa, ruxsatlar shundan olinadi",
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="xodimlar"
    )
    jins = models.CharField(max_length=5, choices=Jins.choices, blank=True)
    ishga_olingan_sana = models.DateField(null=True, blank=True)
    oylik = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Doimiy oylik, so'm"
    )
    foiz_ulushi = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Guruh tushumidan ulush, % (o'qituvchi uchun)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Xodim profillari"

    def __str__(self):
        return f"{self.user} — {self.get_lavozim_display()}"


class GuruhOqituvchi(models.Model):
    """Guruhning o'qituvchilari (maksimal 3) va ularning ulushi.

    `academics.Guruh.oqituvchi` bitta — LMS'da davomat va Kurslar shunga
    tayanadi. Asosiy o'qituvchi o'sha maydonga ham yoziladi
    (`GuruhYaratishView`), yordamchilar faqat shu jadvalda.
    """

    class Turi(models.TextChoices):
        ASOSIY = "asosiy", "Asosiy"
        YORDAMCHI = "yordamchi", "Yordamchi"

    guruh = models.ForeignKey("academics.Guruh", on_delete=models.CASCADE, related_name="crm_oqituvchilar")
    oqituvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_guruh_ulushlari"
    )
    class UlushTuri(models.TextChoices):
        """Video (15:21-15:37): o'qituvchiga "foizda, yoki bitta dars uchun
        pul" — o'tilgan darslar soniga qarab."""

        FOIZ = "foiz", "Tushumdan foiz"
        DARS = "dars", "Har dars uchun summa"

    turi = models.CharField(max_length=10, choices=Turi.choices, default=Turi.ASOSIY)
    ulush_turi = models.CharField(max_length=5, choices=UlushTuri.choices, default=UlushTuri.FOIZ)
    foiz = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Shu guruh tushumidan ulush, %. Bo'sh — xodim profilidagi umumiy foiz",
    )
    dars_haqi = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="ulush_turi='dars' bo'lsa — bitta o'tilgan dars uchun, so'm",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["guruh", "oqituvchi"], name="crm_guruh_oqituvchi_unikal")
        ]


class TalabaProfil(models.Model):
    """Talabaning CRM'ga xos maydonlari (LMS `User`ga tegilmaydi)."""

    class Jins(models.TextChoices):
        ERKAK = "erkak", "Erkak"
        AYOL = "ayol", "Ayol"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_talaba"
    )
    jins = models.CharField(max_length=5, choices=Jins.choices, blank=True)
    maktab = models.CharField(max_length=100, blank=True)
    qora_royxat = models.BooleanField(default=False, db_index=True)
    qora_royxat_sabab = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Talaba profillari"


class DavomatIzoh(models.Model):
    """`academics.Davomat` kengaytmasi: "sababli" belgisi va izoh.

    LMS davomatida faqat keldi/kelmadi bor. SoffCRM katagida yana
    "sababli kelmagan" va izoh bor — LMS modeliga choice qo'shmaslik
    uchun shu yerda.
    """

    davomat = models.OneToOneField(
        "academics.Davomat", on_delete=models.CASCADE, related_name="crm_izoh"
    )
    sababli = models.BooleanField(default=False)
    izoh = models.CharField(max_length=300, blank=True)


class DarsOzgarish(models.Model):
    """Jadvaldan tashqari o'zgarish: dars ko'chirildi, qo'shimcha dars
    yoki dars bekor qilindi (SoffCRM "Darsni ko'chirish" /
    "Qo'shimcha dars").

    Faqat shu kunga ta'sir qiladi — haftalik jadval (`DarsJadvali`)
    o'zgarmaydi. MOLIYAGA TA'SIR QILMAYDI (qaror, hisobotga qarang): oylik
    narx oydagi jadval kunlariga qarab hisoblanadi, ko'chirilgan dars
    boshqa kunda baribir o'tiladi.
    """

    class Turi(models.TextChoices):
        KOCHIRISH = "kochirish", "Ko'chirildi"
        QOSHIMCHA = "qoshimcha", "Qo'shimcha dars"
        BEKOR = "bekor", "Bekor qilindi"

    guruh = models.ForeignKey("academics.Guruh", on_delete=models.CASCADE, related_name="crm_dars_ozgarishlari")
    turi = models.CharField(max_length=10, choices=Turi.choices)
    asl_sana = models.DateField(null=True, blank=True, help_text="Ko'chirilgan/bekor qilingan dars sanasi")
    yangi_sana = models.DateField(null=True, blank=True, help_text="Ko'chirilgan/qo'shimcha dars sanasi")
    boshlanish_vaqti = models.TimeField(null=True, blank=True)
    tugash_vaqti = models.TimeField(null=True, blank=True)
    xona = models.ForeignKey(Xona, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    mavzu = models.CharField(max_length=200, blank=True)
    izoh = models.CharField(max_length=300, blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DarsBahosi(models.Model):
    """Darsdagi baho (SoffCRM guruh kartasidagi "BAHO" tabi). Shkala
    guruhning `GuruhMoliya.baholash_tizimi`dan olinadi."""

    guruh = models.ForeignKey("academics.Guruh", on_delete=models.CASCADE, related_name="crm_baholar")
    talaba = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_baholar")
    sana = models.DateField()
    ball = models.DecimalField(max_digits=5, decimal_places=1)
    izoh = models.CharField(max_length=300, blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["guruh", "talaba", "sana"], name="crm_baho_unikal")
        ]


class Chegirma(models.Model):
    """Muddatli chegirma (SoffCRM guruhdagi "Chegirmalar" tabi):
    "3 oy davomida 400 000 so'm", yoki "1 oy tekin".

    `AzolikMoliya.narx` — DOIMIY individual narx; bu esa `boshlanish_oy`
    dan boshlab `oylar_soni` oy amal qiladi, keyin narx o'z-o'zidan
    odatiy holatga qaytadi. Hisob ochilayotgan oy chegirma oynasiga
    tushsa, `mantiq.narx_va_manba` shu narxni oladi.
    """

    azolik = models.ForeignKey(AzolikMoliya, on_delete=models.CASCADE, related_name="chegirmalar")
    narx = models.DecimalField(max_digits=12, decimal_places=2, help_text="Chegirmadagi oylik narx (0 = tekin)")
    boshlanish_oy = models.DateField(help_text="Doim oyning 1-sanasi")
    oylar_soni = models.PositiveSmallIntegerField(default=1)
    izoh = models.CharField(max_length=300, blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-boshlanish_oy", "-id"]
        verbose_name_plural = "Chegirmalar"


class DarsMavzusi(models.Model):
    """Dars mavzusi (SoffCRM davomat jadvalidagi "Mavzular" qatori)."""

    guruh = models.ForeignKey("academics.Guruh", on_delete=models.CASCADE, related_name="crm_mavzular")
    sana = models.DateField()
    mavzu = models.CharField(max_length=200)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["guruh", "sana"], name="crm_mavzu_unikal")]


class XodimDavomat(models.Model):
    """Xodimlar davomati (SoffCRM "Xodimlar davomati" tugmasi va
    hisoboti): kuniga bitta yozuv."""

    class Holat(models.TextChoices):
        KELDI = "keldi", "Keldi"
        KECHIKDI = "kechikdi", "Kechikdi"
        KELMADI = "kelmadi", "Kelmadi"
        SABABLI = "sababli", "Sababli"

    xodim = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_davomat")
    sana = models.DateField()
    holat = models.CharField(max_length=10, choices=Holat.choices)
    izoh = models.CharField(max_length=300, blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["xodim", "sana"], name="crm_xodim_davomat_unikal")]


class GuruhdanChiqish(models.Model):
    """Guruhdan chiqqan o'quvchi yozuvi ("Ketgan o'quvchilar hisoboti" va
    bosh sahifadagi "Ketganlar" soni uchun).

    Kerak, chunki chiqarishda LMS a'zoligi (`GuruhAzoligi`) o'chadi va u
    bilan `AzolikMoliya` ham — ya'ni kim, qachon, nega ketgani boshqa
    hech qayerda qolmaydi. SET_NULL + nom nusxasi — `Hisob` bilan bir xil
    sabab: talaba yoki guruh keyin o'chsa ham yozuv o'qiladi.
    """

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="crm_chiqishlari"
    )
    talaba_ism = models.CharField(max_length=200)
    guruh = models.ForeignKey("academics.Guruh", on_delete=models.SET_NULL, null=True, related_name="+")
    guruh_nomi = models.CharField(max_length=200)
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    boshlagan_sana = models.DateField(null=True, blank=True)
    sana = models.DateField(help_text="Chiqqan sana")
    sabab = models.CharField(max_length=300, blank=True)
    kim = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sana", "-id"]
