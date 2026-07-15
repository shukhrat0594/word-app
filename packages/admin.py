from django.contrib import admin

from .models import PaketXarid


@admin.register(PaketXarid)
class PaketXaridAdmin(admin.ModelAdmin):
    list_display = (
        "talaba", "paket_turi", "narx", "muddat_kun", "boshlanish",
        "w_ishlatilgan", "w_jami", "s_ishlatilgan", "s_jami",
    )
    list_filter = ("paket_turi", "muddat_kun")
    date_hierarchy = "created_at"
