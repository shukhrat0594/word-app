from django.conf import settings
from django.db import models


class FaoliyatYozuvi(models.Model):
    """Admin/owner boshqaruv harakati — nima qo'shildi/o'chirildi/o'zgartirildi.

    Talaba/oddiy foydalanuvchining bajargan mashqlari bu yerda YOZILMAYDI —
    ular allaqachon `gamification.XPYozuv`da bor (mashq_yechildi/
    writing_tekshiruv/speaking_tekshiruv/material_tugatildi/davomat_keldi),
    Owner hisoboti (`audit.views.AuditHisobotView`) ikkalasini birlashtirib
    o'qiydi.
    """

    class Harakat(models.TextChoices):
        YARATISH = "yaratish", "Yaratish"
        OZGARTIRISH = "ozgartirish", "O'zgartirish"
        OCHIRISH = "ochirish", "O'chirish"

    foydalanuvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="faoliyat_yozuvlari",
        help_text="Harakatni bajargan admin/owner",
    )
    harakat = models.CharField(max_length=15, choices=Harakat.choices)
    obyekt_turi = models.CharField(
        max_length=40,
        help_text="masalan 'Mashq', 'ImtihonTest', 'Foydalanuvchi', 'Guruh', 'Markaz'",
    )
    obyekt_id = models.PositiveIntegerField(null=True, blank=True)
    obyekt_nomi = models.CharField(
        max_length=200,
        help_text="O'qiladigan nom (snapshot) — obyekt o'chirilgandan keyin ham qolishi uchun",
    )
    ozgarishlar = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "yaratish/o'chirish: to'liq snapshot; "
            "o'zgartirish: {maydon: {eski, yangi}} — faqat o'zgargan maydonlar"
        ),
    )
    markaz = models.ForeignKey(
        "accounts.Markaz",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faoliyat_yozuvlari",
    )
    vaqt = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Faoliyat yozuvlari"
        ordering = ["-vaqt"]

    def __str__(self):
        return f"{self.foydalanuvchi} — {self.harakat} {self.obyekt_turi} #{self.obyekt_id}"
