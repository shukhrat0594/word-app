from django.contrib import admin

from .models import GrammatikaSavoli, Soz


@admin.register(Soz)
class SozAdmin(admin.ModelAdmin):
    list_display = ("en", "uz", "daraja", "turkum")
    list_filter = ("daraja",)
    search_fields = ("en", "uz")


@admin.register(GrammatikaSavoli)
class GrammatikaSavoliAdmin(admin.ModelAdmin):
    list_display = ("mavzu", "savol", "togri")
    list_filter = ("mavzu",)
    search_fields = ("savol",)
