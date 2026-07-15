from django.contrib import admin

from .models import Davomat, Guruh


@admin.register(Guruh)
class GuruhAdmin(admin.ModelAdmin):
    list_display = ("name", "markaz", "oqituvchi", "talaba_soni", "created_at")
    list_filter = ("markaz",)
    search_fields = ("name",)
    filter_horizontal = ("talabalar",)

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
