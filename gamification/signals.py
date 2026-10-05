"""XP hodisalari — mavjud modellarga signal orqali ulanadi (B7).

Boshqa applar gamification haqida bilmaydi — bog'liqlik bir tomonlama.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from courses.models import KursMashqYechim
from exercises.models import MashqYechim, TestYechim

from .models import TEST_BAND_KOEFFITSIENT, XP_QOIDALARI, xp_ber


def test_xp_miqdori(band):
    """IELTS Reading/Listening testi XP'si: asos + band x 4 (band yo'q bo'lsa — faqat asos)."""
    return XP_QOIDALARI["test_yechildi"] + (round(float(band) * TEST_BAND_KOEFFITSIENT) if band is not None else 0)


def kurs_xp_miqdorlari(ball, jami):
    """Kurslar mashqi (birinchi urinish): (asosiy XP, bonus XP). Asosiy = to'g'ri javoblar soni."""
    bonus = XP_QOIDALARI["kurs_mukammal"] if jami and ball == jami else 0
    return ball, bonus


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


@receiver(post_save, sender=TestYechim)
def test_uchun_xp(sender, instance, created, raw=False, **kwargs):
    """Faqat Reading/Listening testlari (Writing/Speaking o'z tekshiruvi orqali XP oladi).
    Manba = test id: bir talaba bir testdan FAQAT BIR MARTA XP oladi (qayta yechish XP bermaydi)."""
    if raw or not created or instance.test.bolim not in ("reading", "listening"):
        return
    xp_ber(instance.talaba, "test_yechildi", manba_id=instance.test_id, miqdor=test_xp_miqdori(instance.band))


@receiver(post_save, sender=KursMashqYechim)
def kurs_mashq_uchun_xp(sender, instance, created, raw=False, **kwargs):
    """Kurslar reytingi: mashqning BIRINCHI urinishi (manba = mashq id) — to'g'ri javoblar soni XP,
    100% bo'lsa bonus. Keyingi urinishlar XP bermaydi."""
    if raw or not created:
        return
    asosiy, bonus = kurs_xp_miqdorlari(instance.ball, instance.jami)
    if xp_ber(instance.talaba, "kurs_mashq", manba_id=instance.mashq_id, miqdor=asosiy) and bonus:
        xp_ber(instance.talaba, "kurs_mukammal", manba_id=instance.mashq_id, miqdor=bonus)


@receiver(post_save, sender=Davomat)
def davomat_uchun_xp(sender, instance, created, raw=False, **kwargs):
    if not raw and created and instance.holat == "keldi":
        xp_ber(instance.talaba, "davomat_keldi", manba_id=instance.id)
