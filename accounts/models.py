from django.contrib.auth.models import AbstractUser
from django.db import models

from .fields import EncryptedTextField


class Markaz(models.Model):
    """O'quv markazi. Har bir foydalanuvchi (talaba/o'qituvchi/admin) shu modelga biriktiriladi."""

    class AIProvider(models.TextChoices):
        CLAUDE = "claude", "Claude"
        GEMINI = "gemini", "Gemini"

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="markaz_logos/", blank=True, null=True)

    ai_provider = models.CharField(
        max_length=10, choices=AIProvider.choices, default=AIProvider.GEMINI
    )
    api_key = EncryptedTextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        TEACHER = "teacher", "O'qituvchi"
        STUDENT = "student", "Talaba"
        PARENT = "parent", "Ota-ona"

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
