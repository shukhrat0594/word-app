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

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    markaz = models.ForeignKey(
        Markaz, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
