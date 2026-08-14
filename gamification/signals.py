"""XP hodisalari — mavjud modellarga signal orqali ulanadi (B7).

Boshqa applar gamification haqida bilmaydi — bog'liqlik bir tomonlama.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from exercises.models import MashqYechim

from .models import xp_ber


@receiver(post_save, sender=MashqYechim)
def mashq_uchun_xp(sender, instance, created, raw=False, **kwargs):
    # 2026-08-15: `raw=True` — `loaddata` (fixture/backup tiklash) orqali
    # saqlanayotganda Django shu bayroqni beradi. Bunda signalni ishga
    # tushirmaymiz — aks holda dump'dagi ASL XPYozuv yozuvi bilan
    # to'qnashib, `UniqueConstraint` xatosi beradi (backup tiklashda
    # aniqlangan haqiqiy bug, 2026-08-15).
    if raw or not created:
        return
    xp_ber(instance.talaba, "mashq_yechildi", manba_id=instance.id)
    if instance.jami and instance.ball == instance.jami:
        xp_ber(instance.talaba, "mashq_mukammal", manba_id=instance.id)


@receiver(post_save, sender=WritingTekshiruv)
def writing_uchun_xp(sender, instance, created, raw=False, **kwargs):
    if not raw and created:
        xp_ber(instance.talaba, "writing_tekshiruv", manba_id=instance.id)


@receiver(post_save, sender=SpeakingTekshiruv)
def speaking_uchun_xp(sender, instance, created, raw=False, **kwargs):
    if not raw and created:
        xp_ber(instance.talaba, "speaking_tekshiruv", manba_id=instance.id)


@receiver(post_save, sender=Davomat)
def davomat_uchun_xp(sender, instance, created, raw=False, **kwargs):
    if not raw and created and instance.holat == "keldi":
        xp_ber(instance.talaba, "davomat_keldi", manba_id=instance.id)
