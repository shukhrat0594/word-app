from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Markaz(models.Model):
    """O'quv markazi. Har bir foydalanuvchi (talaba/o'qituvchi/admin) shu modelga biriktiriladi.

    Ikki xil yaratilish yo'li bor: (1) owner to'g'ridan-to'g'ri yaratadi —
    `tasdiqlangan=True`, `soruvchi=None`; (2) istalgan ro'yxatdan o'tgan
    foydalanuvchi o'zi so'rov yuboradi — `tasdiqlangan=False`,
    `soruvchi=<user>`, owner tasdiqlagach `soruvchi` shu markazning admini
    bo'ladi (`MarkazTasdiqlashView`).
    """

    class AIProvider(models.TextChoices):
        CLAUDE = "claude", "Claude"
        GEMINI = "gemini", "Gemini"

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="markaz_logos/", blank=True, null=True)
    brend_rang = models.CharField(
        max_length=7, default="#FFD400",
        help_text="Markaz brendining asosiy rangi (hex, masalan #FFD400)",
    )

    ai_provider = models.CharField(
        max_length=10, choices=AIProvider.choices, default=AIProvider.GEMINI,
        help_text="Qaysi AI ishlatilsa ham, xarajat doim platforma (owner) kaliti orqali to'lanadi",
    )

    # Ijtimoiy tarmoqlar (2026-07-27) — saytning pastki panelida ko'rsatiladi.
    # Bo'sh qoldirilgani ko'rsatilmaydi, ya'ni markaz faqat o'zida bor
    # tarmoqlarni chiqaradi. Kodga qattiq yozilmagan — admin panelidan
    # boshqariladi (logo/brend rangi bilan bir xil yondashuv).
    telegram = models.URLField(blank=True, help_text="Telegram kanal/guruh havolasi")
    instagram = models.URLField(blank=True, help_text="Instagram profil havolasi")
    youtube = models.URLField(blank=True, help_text="YouTube kanal havolasi")
    facebook = models.URLField(blank=True, help_text="Facebook sahifa havolasi")

    # Pastki panelda ko'rsatish tartibi va yorlig'i — bitta joyda saqlanadi,
    # backend ham, frontend ham shu ro'yxatga tayanadi.
    IJTIMOIY_MAYDONLAR = [
        ("telegram", "Telegram"),
        ("instagram", "Instagram"),
        ("youtube", "YouTube"),
        ("facebook", "Facebook"),
    ]

    def ijtimoiy_havolalar(self):
        """Faqat TO'LDIRILGAN ijtimoiy tarmoqlar — {kalit: havola}."""
        return {k: getattr(self, k) for k, _ in self.IJTIMOIY_MAYDONLAR if getattr(self, k)}

    tasdiqlangan = models.BooleanField(
        default=True,
        help_text="False bo'lsa — owner tasdig'ini kutayotgan so'rov",
    )
    soruvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sorolgan_markazlar",
        help_text="Markazni o'zi so'rab yuborgan foydalanuvchi (tasdiqlangach admin bo'ladi)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        TEACHER = "teacher", "O'qituvchi"
        STUDENT = "student", "Talaba"
        PARENT = "parent", "Ota-ona"
        ODDIY = "oddiy", "Oddiy foydalanuvchi"

    class KorishRejimi(models.TextChoices):
        """Faqat OWNER (superuser) uchun (2026-07-29) — profil sahifasida
        tanlab, saytni boshqa rol nazari bilan ko'rish ("View As"). Owner
        har safar chiqib, boshqa test-foydalanuvchidan qayta kirmasligi
        uchun.

        MUHIM: bu TO'LIQ simulyatsiya — `accounts.authentication`dagi
        maxsus autentifikatsiya klassi shu qiymat "owner"dan farqli bo'lsa,
        SO'ROV DAVOMIDA `request.user.role`/`is_superuser`ni VAQTINCHALIK
        (faqat xotirada, bazaga yozilmasdan) shu qiymatga almashtiradi —
        butun ilova (backend ham, frontend ham) owner'ni HAQIQATAN shu rol
        deb ko'radi. Batafsil izoh: accounts/authentication.py."""

        OWNER = "owner", "Owner (asl holat)"
        ADMIN = "admin", "Administrator"
        # 2026-08-09 talabi. Ota-ona rejimidagi kabi cheklov bor: o'qituvchi
        # ko'radigan Guruhlar/Talabalar `oqituvchi=<o'zi>` bo'yicha
        # filtrlanadi, owner esa hech bir guruhning o'qituvchisi emas — shu
        # rejimda ro'yxatlar BO'SH chiqadi.
        TEACHER = "teacher", "O'qituvchi"
        STUDENT = "student", "Talaba"
        # 2026-08-09 talabi. DIQQAT: ota-onaning bosh sahifasi FARZANDLAR
        # ro'yxati, owner'da esa biriktirilgan farzand yo'q — shu rejimda
        # ro'yxat BO'SH ko'rinadi. Bu simulyatsiyaning tabiati (Talaba
        # rejimida ham owner o'z natijalarini, ya'ni bo'sh ro'yxatni
        # ko'radi): rejim panel/qulf/ruxsatlarni sinash uchun, boshqa
        # odamning ma'lumotini ko'rish uchun emas.
        PARENT = "parent", "Ota-ona"
        ODDIY = "oddiy", "Mehmon (oddiy foydalanuvchi)"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    korish_rejimi = models.CharField(
        max_length=10, choices=KorishRejimi.choices, default=KorishRejimi.OWNER, blank=True,
        help_text="Faqat owner uchun — 'Ko'rish rejimi' (View As) joriy tanlovi",
    )
    markaz = models.ForeignKey(
        Markaz, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    korinadigan_panellar = models.JSONField(
        null=True, blank=True, default=None,
        help_text=(
            "Owner (istalgan foydalanuvchiga) yoki admin (faqat talabalarga) "
            "belgilaydigan QO'SHIMCHA cheklov (2026-08-05) — rolga asoslangan "
            "standart navigatsiya ustiga qo'yiladi, faqat TORAYTIRADI, "
            "KENGAYTIRMAYDI. null/bo'sh = cheklovsiz (rol bo'yicha standart). "
            "Ro'yxat elementlari nav yo'llari (masalan '/kurslar')."
        ),
    )
    # 2026-08-09: avval bu ko'p-ko'pga (`farzandlar` M2M) edi, ya'ni bitta
    # bolani bir nechta ota-onaga biriktirish mumkin bo'lardi.
    # Foydalanuvchi qarori: bitta ota-onada bir NECHTA farzand bo'lishi
    # mumkin, lekin bitta bola FAQAT BITTA ota-onaga biriktiriladi —
    # shuning uchun bog'lanish bolaning O'ZIDA turadigan FK'ga
    # o'tkazildi. Cheklov endi DB darajasida: bitta ustunga ikkita
    # qiymat sig'maydi, ya'ni qoidani buzib bo'lmaydi (endpoint ham,
    # admin panel ham).
    #
    # `related_name="farzandlar"` ATAYLAB eski nom bilan: `parent
    # .farzandlar.all()` avvalgidek ishlaydi, shuning uchun mavjud kod
    # (`stats/views.py`) tegilmadi.
    ota_ona = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="farzandlar",
        limit_choices_to={"role": "parent"},
        help_text="Faqat 'Talaba' roli uchun — kuzatuvchi ota-ona (bitta)",
    )
    rasm = models.ImageField(
        upload_to="foydalanuvchi_rasm/", blank=True,
        help_text=(
            "Profil rasmi (2026-08-09). R2 bucket YOPIQ, shuning uchun "
            "to'g'ridan-to'g'ri URL bilan emas, autentifikatsiyalangan "
            "endpoint orqali uzatiladi — `FoydalanuvchiRasmView`."
        ),
    )
    qurilmalar = models.JSONField(
        default=list, blank=True,
        help_text=(
            "Hisobni boshqalar bilan bo'lishmaslik uchun (2026-08-12, "
            "2026-08-13'da ko'p-qurilmali qilib kengaytirildi) — "
            "OWNER'dan boshqa har bir foydalanuvchi FAQAT shu ro'yxatdagi "
            "qurilmalardan (frontend localStorage'dagi tasodifiy ID'lar) "
            "kira oladi. Yangi qurilma `qurilma_limiti`ga yetmagunча "
            "AVTOMATIK qo'shiladi (keyingi login), limit to'lgach rad "
            "etiladi. Bo'sh ro'yxat = hali hech qaysi qurilmaga "
            "bog'lanmagan. Faqat owner/admin 'Qurilmani tiklash' orqali "
            "TO'LIQ tozalay oladi (limitga tegmasdan) — "
            "`XodimLoginView`/`QurilmaTiklashView`ga qarang."
        ),
    )
    qurilma_limiti = models.PositiveSmallIntegerField(
        default=1,
        help_text=(
            "2026-08-13 — nechta qurilmadan bir vaqtda kirish mumkinligi "
            "(standart 1). Hozircha FAQAT owner o'zgartira oladi "
            "(`QurilmaLimitiView`) — kelajakda adminga ham berilishi "
            "mumkin (foydalanuvchi qarori)."
        ),
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Bildirishnoma(models.Model):
    """Ilova ichidagi bildirishnoma (2026-08-08, foydalanuvchi talabi:
    "har gal nimadir yangi narsa push qilinganda ownerga xabar
    keladigan qila olamizmi? nimalar qo'shilganini?").

    Manbalari:
      * RELIZ — `CHANGELOG.md` (qarang `accounts.relizlar`), FAQAT owner'ga.
      * OGOHLANTIRISH — owner/admin foydalanuvchining profil rasmini
        o'chirganda, sababi bilan (2026-08-09). Rasm shaxsiy narsa, uni
        boshqa odam olib tashlaganda egasi buni BILISHI va NEGA ekanini
        ko'rishi kerak — aks holda rasm jimgina yo'qolgandek tuyuladi.

    Telegram orqali dublikat yuborish REJADA; u qo'shilganda shu model
    o'zgarmaydi, faqat yuborish bosqichi qo'shiladi.

    `kalit` — takrorlanishni to'sish uchun barqaror identifikator
    (masalan "reliz:2026-08-08:Sarlavha"). Bir foydalanuvchiga bir xil
    kalitli bildirishnoma IKKI MARTA yaratilmaydi, shuning uchun manbani
    (CHANGELOG'ni) xohlagancha qayta o'qish xavfsiz. Ogohlantirishda
    kalitga aniq vaqt qo'shiladi — u TAKRORLANADIGAN voqea (rasm bir
    necha marta o'chirilishi mumkin), har biri alohida xabar bo'lishi
    kerak."""

    class Turi(models.TextChoices):
        RELIZ = "reliz", "Yangilanish"
        OGOHLANTIRISH = "ogohlantirish", "Ogohlantirish"

    foydalanuvchi = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bildirishnomalar"
    )
    turi = models.CharField(max_length=20, choices=Turi.choices, default=Turi.RELIZ)
    kalit = models.CharField(max_length=200)
    sarlavha = models.CharField(max_length=300)
    matn = models.TextField(blank=True)
    oqilgan = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["foydalanuvchi", "kalit"], name="bildirishnoma_kalit_takrorlanmasin"
            )
        ]
        verbose_name_plural = "Bildirishnomalar"

    def __str__(self):
        return f"{self.foydalanuvchi.username} — {self.sarlavha}"
