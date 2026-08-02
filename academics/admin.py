from django.contrib import admin

from .models import Davomat, Guruh, GuruhAzoligi


class GuruhAzoligiInline(admin.TabularInline):
    model = GuruhAzoligi
    extra = 0
    autocomplete_fields = ("talaba",)


@admin.register(Guruh)
class GuruhAdmin(admin.ModelAdmin):
    list_display = ("name", "markaz", "oqituvchi", "fan", "daraja", "talaba_soni", "created_at")
    list_filter = ("markaz", "fan", "daraja")
    search_fields = ("name",)
    # 2026-08-02: `talabalar` endi `through=GuruhAzoligi` (boshlanish_unit
    # saqlash uchun) — `filter_horizontal` through-modelli M2M'ni
    # qo'llab-quvvatlamaydi, shuning uchun inline orqali boshqariladi.
    inlines = [GuruhAzoligiInline]

    def talaba_soni(self, obj):
        return obj.talabalar.count()

    talaba_soni.short_description = "Talabalar soni"


@admin.register(Davomat)
class DavomatAdmin(admin.ModelAdmin):
    list_display = ("sana", "guruh", "talaba", "holat", "belgilagan")
    list_filter = ("holat", "guruh", "sana")
    date_hierarchy = "sana"

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        if not change:
            obj.belgilagan = request.user
        super().save_model(request, obj, form, change)
