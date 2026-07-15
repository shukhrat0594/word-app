from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


class Guruh(models.Model):
    """O'quv guruhi — bitta o'qituvchi va bir nechta talabani birlashtiradi."""

    name = models.CharField(max_length=200)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="guruhlar"
    )
    oqituvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oqituvchi_guruhlari",
        limit_choices_to={"role": "teacher"},
    )
    talabalar = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="talaba_guruhlari",
        blank=True,
        limit_choices_to={"role": "student"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.markaz.name})"


@receiver(m2m_changed, sender=Guruh.talabalar.through)
def guruhga_qoshilganda_markaz_biriktir(sender, instance, action, pk_set, **kwargs):
    """Talaba guruhga qo'shilganda uning markazini guruh markaziga moslashtiradi.

    Talaba markazsiz bo'lsa (Google OAuth orqali o'z-o'zidan ro'yxatdan
    o'tgan) — guruh markazi biriktiriladi. Talaba boshqa markazga
    biriktirilgan bo'lsa — xato beriladi (bitta talaba bir vaqtda faqat
    bitta markazga tegishli bo'lishi kerak).
    """
    if action != "pre_add" or pk_set is None:
        return

    User = instance.talabalar.model
    for talaba in User.objects.filter(pk__in=pk_set):
        if talaba.markaz_id is None:
            talaba.markaz = instance.markaz
            talaba.save(update_fields=["markaz"])
        elif talaba.markaz_id != instance.markaz_id:
            raise ValidationError(
                f"{talaba} allaqachon boshqa markazga ({talaba.markaz}) "
                f"biriktirilgan, {instance.markaz} guruhiga qo'sha olmaysiz."
            )
