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

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    markaz = models.ForeignKey(
        Markaz, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    # B6.1: Ota-ona <-> Talaba (ko'p-ko'pga). Bog'lashni faqat Markaz
    # (Admin/O'qituvchi) admin panelda amalga oshiradi.
    farzandlar = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="ota_onalar",
        limit_choices_to={"role": "student"},
        help_text="Faqat 'Ota-ona' roli uchun — kuzatiladigan talabalar",
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
