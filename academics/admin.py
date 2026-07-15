from django.contrib import admin

from .models import Guruh


@admin.register(Guruh)
class GuruhAdmin(admin.ModelAdmin):
    list_display = ("name", "markaz", "oqituvchi", "talaba_soni", "created_at")
    list_filter = ("markaz",)
    search_fields = ("name",)
    filter_horizontal = ("talabalar",)

    def talaba_soni(self, obj):
        return obj.talabalar.count()

    talaba_soni.short_description = "Talabalar soni"
