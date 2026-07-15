"""XP hodisalari — mavjud modellarga signal orqali ulanadi (B7).

Boshqa applar gamification haqida bilmaydi — bog'liqlik bir tomonlama.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from academics.models import Davomat
from assessment.models import WritingTekshiruv
from content.models import DarsFaollik
from exercises.models import MashqYechim

from .models import xp_ber


@receiver(post_save, sender=MashqYechim)
def mashq_uchun_xp(sender, instance, created, **kwargs):
    if not created:
        return
    xp_ber(instance.talaba, "mashq_yechildi", manba_id=instance.id)
    if instance.jami and instance.ball == instance.jami:
        xp_ber(instance.talaba, "mashq_mukammal", manba_id=instance.id)


@receiver(post_save, sender=WritingTekshiruv)
def writing_uchun_xp(sender, instance, created, **kwargs):
    if created:
        xp_ber(instance.talaba, "writing_tekshiruv", manba_id=instance.id)


@receiver(post_save, sender=DarsFaollik)
def material_uchun_xp(sender, instance, **kwargs):
    if instance.holat == "tugatdi":
        xp_ber(instance.talaba, "material_tugatildi", manba_id=instance.id)


@receiver(post_save, sender=Davomat)
def davomat_uchun_xp(sender, instance, created, **kwargs):
    if created and instance.holat == "keldi":
        xp_ber(instance.talaba, "davomat_keldi", manba_id=instance.id)
