from django.contrib import admin

from .models import FaoliyatYozuvi


@admin.register(FaoliyatYozuvi)
class FaoliyatYozuviAdmin(admin.ModelAdmin):
    list_display = ("vaqt", "foydalanuvchi", "harakat", "obyekt_turi", "obyekt_nomi")
    list_filter = ("harakat", "obyekt_turi", "markaz")
    search_fields = ("obyekt_nomi", "foydalanuvchi__username")
    readonly_fields = [f.name for f in FaoliyatYozuvi._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
