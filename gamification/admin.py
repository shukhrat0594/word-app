from django.contrib import admin

from .models import TalabaBadge, XPYozuv


@admin.register(XPYozuv)
class XPYozuvAdmin(admin.ModelAdmin):
    list_display = ("talaba", "miqdor", "sabab", "manba_id", "created_at")
    list_filter = ("sabab",)
    date_hierarchy = "created_at"


@admin.register(TalabaBadge)
class TalabaBadgeAdmin(admin.ModelAdmin):
    list_display = ("talaba", "kod", "created_at")
    list_filter = ("kod",)
