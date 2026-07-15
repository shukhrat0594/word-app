from django.contrib import admin

from .models import Mashq, MashqYechim


@admin.register(Mashq)
class MashqAdmin(admin.ModelAdmin):
    list_display = ("name", "bolim", "tur", "korinish", "markaz", "created_at")
    list_filter = ("bolim", "tur", "korinish", "markaz")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(MashqYechim)
class MashqYechimAdmin(admin.ModelAdmin):
    list_display = ("talaba", "mashq", "ball", "jami", "created_at")
    list_filter = ("mashq__bolim", "mashq__tur")
    date_hierarchy = "created_at"
    readonly_fields = ("talaba", "mashq", "javoblar", "ball", "jami", "natijalar")
