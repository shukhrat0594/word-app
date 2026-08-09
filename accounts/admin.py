from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Markaz, User


@admin.register(Markaz)
class MarkazAdmin(admin.ModelAdmin):
    list_display = ("name", "ai_provider", "created_at")
    list_filter = ("ai_provider",)
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "markaz", "is_staff")
    list_filter = ("role", "markaz", "is_staff", "is_superuser")
    # 2026-08-09: `farzandlar` M2M o'rniga bolaning o'zidagi `ota_ona` FK
    # (bitta bola = bitta ota-ona). Shuning uchun bu yerda ota-onani
    # TALABA sahifasida tanlanadi, `filter_horizontal` esa kerak emas.
    fieldsets = BaseUserAdmin.fieldsets + (
        ("LMS", {"fields": ("role", "markaz", "ota_ona", "rasm")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("LMS", {"fields": ("role", "markaz")}),
    )
