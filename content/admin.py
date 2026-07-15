from django.contrib import admin

from .models import Dars, DarsFaollik, Kurs, Material


class DarsInline(admin.TabularInline):
    model = Dars
    extra = 0
    fields = ("tartib", "name", "tavsif")


@admin.register(Kurs)
class KursAdmin(admin.ModelAdmin):
    list_display = ("name", "markaz", "yaratgan", "tartib", "created_at")
    list_filter = ("markaz",)
    search_fields = ("name",)
    inlines = [DarsInline]

    def save_model(self, request, obj, form, change):
        if not change and obj.yaratgan is None:
            obj.yaratgan = request.user
        super().save_model(request, obj, form, change)


class MaterialInline(admin.TabularInline):
    model = Material
    extra = 0
    fields = ("name", "turi", "korinish")
    show_change_link = True


@admin.register(Dars)
class DarsAdmin(admin.ModelAdmin):
    list_display = ("name", "kurs", "tartib")
    list_filter = ("kurs__markaz", "kurs")
    search_fields = ("name",)
    inlines = [MaterialInline]


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "turi", "korinish", "markaz", "dars", "created_at")
    list_filter = ("turi", "korinish", "markaz")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(DarsFaollik)
class DarsFaollikAdmin(admin.ModelAdmin):
    list_display = ("talaba", "material", "holat", "boshlagan_vaqt", "tugatgan_vaqt")
    list_filter = ("holat", "material__markaz")
    date_hierarchy = "boshlagan_vaqt"
