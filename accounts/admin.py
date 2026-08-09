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

    # Rol YARATILGANDAN KEYIN o'zgarmaydi (2026-08-09 qarori) — ilovada
    # ham shunday (`FoydalanuvchiRolView` 409 qaytaradi). Shu qoida BU
    # YERDA HAM amal qiladi: aks holda qoida bir joyda yopiq, boshqa
    # joyda ochiq bo'lib, ma'nosini yo'qotardi.
    #
    # `is_superuser` ham qulflanadi — u aslida "owner" turi, ya'ni rolning
    # bir qismi. Ikkinchi owner ilovadagi YARATISH formasidan ochiladi
    # (`FoydalanuvchiYaratishView` "owner"ni qabul qiladi).
    #
    # Yaratishda esa ikkalasi ham OCHIQ — `obj is None` shu holat.
    QULFLANGAN_MAYDONLAR = ("role", "is_superuser")

    def get_readonly_fields(self, request, obj=None):
        readonly = tuple(super().get_readonly_fields(request, obj))
        if obj is None:
            return readonly
        return readonly + tuple(
            m for m in self.QULFLANGAN_MAYDONLAR if m not in readonly
        )
