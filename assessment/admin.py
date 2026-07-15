from django.contrib import admin

from .models import WritingTekshiruv


@admin.register(WritingTekshiruv)
class WritingTekshiruvAdmin(admin.ModelAdmin):
    list_display = (
        "talaba", "task_type", "overall_band", "provider", "model",
        "input_tokens", "output_tokens", "created_at",
    )
    list_filter = ("provider", "task_type")
    date_hierarchy = "created_at"
    readonly_fields = (
        "talaba", "matn", "natija", "task_type", "overall_band",
        "provider", "model", "input_tokens", "output_tokens",
    )
