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
    kalit = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text=(
            "Barqaror identifikator (masalan 'mashqlar', 'vocabulary', "
            "'students_book'). 2026-07-28 da qo'shildi: avval tugunni NOMI "
            "bo'yicha topardik (backendda `bolalar[\"Mashqlar\"]`, frontendda "
            "`nomi === \"Vocabulary\"`), lekin nomlar 3 tilda ko'rsatiladigan "
            "bo'lgach bu yo'l sinadi. Endi kod HAR DOIM shu kalitga tayanadi, "
            "`nomi` esa faqat zaxira ko'rinish (kaliti yo'q tugunlar uchun). "
            "Kalit GLOBAL unikal EMAS — 'vocabulary' bir necha joyda uchraydi, "
            "muhimi bitta ota-tugun ichida takrorlanmasligi."
        ),
    )
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
    matn = models.TextField(
        blank=True,
        help_text=(
            "Sof matnli tugunlar uchun (masalan 'Vocabulary' — shu Unit "
            "bo'yicha qisqa grammatika xulosasi, so'zlar ro'yxati bilan "
            "BIR sahifada keladi). Fayl emas, chunki AI buni to'g'ridan-"
            "to'g'ri matn sifatida generatsiya qiladi (2026-07-27, Unit'ni "
            "bitta so'rovda yuklash imkoniyati)."
        ),
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


class KursMashqRasmGuruhi(models.Model):
    """Bir nechta `KursMashq` BITTA rasmni ulashishi uchun (2026-08-09,
    foydalanuvchi talabi: "bitta rasm turadi, uning yonida ikkita mashq").

    Alohida model — shu tufayli rasmni BIR MARTA saqlaymiz va o'zgartirsak
    (yoki o'chirsak) unga bog'langan BARCHA mashqlarda bir vaqtda
    o'zgaradi. `KursMashq.rasm_guruhi` to'ldirilgan bo'lsa, o'z alohida
    `KursMashq.rasm` maydoni o'rniga shu yerdagi rasm ishlatiladi."""

    class Tomon(models.TextChoices):
        TEPA = "tepa", "Matn tepasida"
        PAST = "past", "Matn ostida"
        CHAP = "chap", "Matnning chapida"
        ONG = "ong", "Matnning o'ngida"

    tugun = models.ForeignKey(KursTugun, on_delete=models.CASCADE, related_name="rasm_guruhlari")
    rasm = models.ImageField(upload_to="kurslar/mashq_rasm_guruhi/")
    tomon = models.CharField(
        max_length=10, choices=Tomon.choices, default=Tomon.CHAP,
        help_text="Ulashilgan rasm mashqlarga nisbatan qayerda turadi (admin tanlaydi)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tugun.nomi} — rasm guruhi #{self.id}"


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
    rasm_guruhi = models.ForeignKey(
        KursMashqRasmGuruhi, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mashqlar",
        help_text=(
            "To'ldirilgan bo'lsa, rasm shu YERDAN olinadi (o'z `rasm` maydoni "
            "e'tiborga olinmaydi) — bir nechta mashq bitta rasmni ulashishi uchun."
        ),
    )
    audio = models.FileField(
        upload_to="kurslar/mashq_audio/", blank=True,
        help_text="Darslikdagi audio (masalan Listening bo'limi uchun)",
    )
    audio_kerak = models.BooleanField(
        default=False,
        help_text=(
            "Blok-mashq tasdiqlashda belgilanadi (2026-08-05) — PDF'da audio "
            "ikonkasi bor, lekin audio faylining o'zi PDF'dan chiqmaydi, admin "
            "alohida yuklashi kerak. Faqat ogohlantirish uchun, hech narsani "
            "bloklamaydi."
        ),
    )
    savollar = models.JSONField(
        default=list,
        help_text='[{"savol": "...", "variantlar": [...] (ixtiyoriy), "togri": "..."}]',
    )
    bloklar = models.JSONField(
        default=list, blank=True,
        help_text=(
            "Darslik sahifasining STRUKTURALI ko'rinishi (2026-07-28). Bo'sh "
            "bo'lsa — eski ko'rinish ishlaydi (sahifa rasmi + ustida foizli "
            "pozitsiyadagi input'lar). To'ldirilgan bo'lsa — sahifa qaytadan "
            "quriladi: matn haqiqiy HTML matni (o'tkir, tanlanadi, "
            "tarjima qilinadi), suratlar `KursMashqRasmi` sifatida alohida "
            "kesib olinadi.\n\n"
            "MUHIM: bo'sh joylar (input'lar) BU YERDA SAQLANMAYDI — ular "
            "`savollar` massiviga yassilanadi, blok esa faqat `savol_idx` "
            "orqali ishora qiladi. Shu tufayli javob tekshirish, ball, 60% "
            "qoidasi va Unit qulfi mexanizmiga UMUMAN TEGILMAYDI."
        ),
    )

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs mashqlari"

    def __str__(self):
        return f"{self.tugun.nomi} — mashq #{self.tartib}"

    @property
    def effektiv_rasm(self):
        """Ko'rsatiladigan rasm — `rasm_guruhi` to'ldirilgan bo'lsa
        o'shandan, aks holda o'z `rasm` maydonidan."""
        if self.rasm_guruhi_id:
            return self.rasm_guruhi.rasm
        return self.rasm


class KursMashqAudio(models.Model):
    """Bitta mashqqa tegishli BIR NECHTA audio (2026-07-27, foydalanuvchi
    talabi). Sabab: bitta sahifa (=bitta mashq) darslikda bir nechta
    Listening bandi/tracki bo'lishi mumkin (masalan 4 ta savol, har biri
    o'z audiosi bilan) — talaba mashq ichida barcha tegishli audiolarni
    yon panelda ko'rib, keraklisini navbat bilan play qiladi.

    `KursMashq.audio` (yakka, eski maydon) FLAT (Unit'siz) bo'limlar uchun
    saqlanib qolgan — u yerda odatda bitta mashqga bitta audio kifoya."""

    mashq = models.ForeignKey(KursMashq, on_delete=models.CASCADE, related_name="audiolar")
    audio = models.FileField(upload_to="kurslar/mashq_audio_royxat/")
    raqam = models.CharField(
        max_length=20, blank=True,
        help_text="Darslikdagi track raqami (masalan '1.01') — faqat ma'lumot uchun",
    )
    tartib = models.PositiveSmallIntegerField(default=0)
    fayl_xesh = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text=(
            "Audio faylning SHA-256 yig'indisi (2026-08-08, foydalanuvchi "
            "talabi: \"bir xil audio ikki marta yuklanmasin\"). Bir xil "
            "xeshli yozuv topilsa yangi fayl YOZILMAYDI — mavjud faylning "
            "o'zi ko'rsatiladi. Shu sababli BIR fayliga bir nechta yozuv "
            "ishora qilishi mumkin; faylni o'chirishdan oldin boshqa "
            "yozuvlar foydalanmayotganini tekshirish SHART "
            "(`courses.views._audio_faylini_xavfsiz_ochir`)."
        ),
    )

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs mashq audiolari"

    def __str__(self):
        return f"{self.mashq} — audio {self.raqam or self.tartib}"


class KursMashqRasmi(models.Model):
    """Blok formatidagi sahifadan KESIB OLINGAN surat (2026-07-28).

    Nega alohida model: blok formatida sahifa qaytadan quriladi, ya'ni
    butun sahifa rasmi emas, undagi har bir MAZMUNLI surat (odamlar,
    mashq rasmlari) alohida fayl bo'lib saqlanadi. Blok JSON ichida
    faqat shu yozuvning `tartib` raqami turadi.

    Kesish AI ISHI EMAS: AI faqat suratning sahifadagi o'rnini foizda
    aytadi, kesishni Pillow bajaradi — ya'ni piksellar asl skandan
    olinadi, qayta chizilmaydi."""

    mashq = models.ForeignKey(KursMashq, on_delete=models.CASCADE, related_name="rasmlar")
    tartib = models.PositiveSmallIntegerField(default=0)
    rasm = models.ImageField(upload_to="kurslar/blok_rasm/")
    izoh = models.CharField(
        max_length=200, blank=True,
        help_text="Nima tasvirlangani (alt matni) — AI beradi",
    )

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs mashq rasmlari"

    def __str__(self):
        return f"{self.mashq} — rasm {self.tartib}"


class KursZipJarayoni(models.Model):
    """Blok formatida ZIP yuklashning UZOQ jarayoni (2026-07-28).

    Nega kerak: bitta Unit ZIP'i 7-10 sahifa, har sahifa AI'da ~125
    sekund => 15-20 daqiqa. `gunicorn.conf.py` da `timeout = 300`, ya'ni
    bitta so'rovda sig'maydi. Shuning uchun ZIP BIR MARTA yuklanadi va
    shu yerda saqlanadi, keyin sahifalar BITTALAB (har biri alohida
    so'rov) qayta ishlanadi — frontend progress ko'rsatadi.

    Celery/worker ATAYLAB ishlatilmadi: Render'da bu qo'shimcha servis va
    xarajat, holbuki jarayonni frontend boshqarsa yetarli."""

    class Holat(models.TextChoices):
        YANGI = "yangi", "Yangi"
        ISHLANMOQDA = "ishlanmoqda", "Ishlanmoqda"
        TASDIQ_KUTILMOQDA = "tasdiq_kutilmoqda", "Tasdiqlash kutilmoqda"
        TUGADI = "tugadi", "Tugadi"
        XATO = "xato", "Xato"

    class ManbaTuri(models.TextChoices):
        ZIP = "zip", "ZIP (rasmlar)"

    class Rejim(models.TextChoices):
        """2026-08-09: "rasm-fon" (PDF, sahifa fon) rejimi butunlay olib
        tashlandi — AI hudud-aniqlash xatolari (koordinata tizimli
        surilishi) tuzatilishidan oldin foydalanuvchi qarori bilan bekor
        qilindi. Faqat BLOK qoladi — sahifa HTML sifatida QAYTA QURILADI
        (matn o'tkir, mobilda o'qiladi, tarjima qilinadi), admin oxirida
        TASDIQLASH oynasida tuzatadi."""

        BLOK = "blok", "Blok formati (sahifa qayta quriladi)"

    tugun = models.ForeignKey(
        KursTugun, on_delete=models.CASCADE, related_name="zip_jarayonlari",
        help_text="KITOB tuguni (Student's Book / Workbook)",
    )
    # Nomi tarixiy (`zip_fayl`) — 2026-08-03dan buyon PDF ham qabul
    # qilinadi (`manba_turi` shuni belgilaydi), lekin maydon nomini
    # o'zgartirish ko'plab joyni tegishni talab qilardi, shuning uchun
    # saqlab qolindi.
    zip_fayl = models.FileField(upload_to="kurslar/zip_jarayon/")
    manba_turi = models.CharField(max_length=10, choices=ManbaTuri.choices, default=ManbaTuri.ZIP)
    rejim = models.CharField(max_length=10, choices=Rejim.choices, default=Rejim.BLOK)
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.YANGI)
    jami_sahifa = models.PositiveSmallIntegerField(default=0)
    ishlangan_sahifa = models.PositiveSmallIntegerField(default=0)
    natijalar = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "Oraliq natijalar: sahifa tahlillari, javob kaliti bandlari, "
            "xatolar. Javob kaliti odatda MASHQ sahifalaridan KEYIN keladi, "
            "shuning uchun bazaga yozish oxirida bir yo'la bajariladi."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Kurs ZIP jarayonlari"

    def __str__(self):
        return f"{self.tugun.nomi} — {self.ishlangan_sahifa}/{self.jami_sahifa} ({self.holat})"


class KursSoz(models.Model):
    """Bitta Unit'ning "Wordlist" bo'limiga tegishli so'z (2026-07-27,
    foydalanuvchi talabi). `games.Soz`dan MUSTAQIL — u umumiy CEFR
    hovuzi (A1-C1/idiom), bu esa faqat BITTA Unit'ga tegishli so'zlar.
    O'yinlar (Juftini top/Kartochkalar/Tezkor viktorina/Harflarni
    tartiblash) shu Unit doirasida ishlashi uchun kerak — Wordlist
    bo'limida "O'yinlar"dagi bilan bir xil 4 o'yin ko'rsatiladi, lekin
    faqat shu ro'yxatdagi so'zlar bilan (Grammatika testi bu yerga
    kirmaydi — u gap-asosidagi savollarga ishlaydi, so'zga bog'liq emas).
    """

    tugun = models.ForeignKey(KursTugun, on_delete=models.CASCADE, related_name="sozlar")
    tartib = models.PositiveSmallIntegerField(default=0)
    en = models.CharField(max_length=200)
    uz = models.CharField(max_length=300)
    turkum = models.CharField(max_length=50, blank=True, help_text="So'z turkumi (ixtiyoriy)")
    misol = models.TextField(blank=True, help_text="Namuna gap (ixtiyoriy)")

    class Meta:
        ordering = ["tartib", "id"]
        verbose_name_plural = "Kurs so'zlari"

    def __str__(self):
        return f"{self.tugun.nomi} — {self.en}"


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
