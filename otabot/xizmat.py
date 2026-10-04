"""Ulash va so'rovlar bilan ishlash (bot ham, CRM API ham shuni ishlatadi)."""

import logging

from django.db.models import Q
from django.utils import timezone

from accounts.models import Bildirishnoma, User

from . import matnlar, tugmalar
from .models import Abonent, Boglanish, Sorov
from .moslash import talaba_ismi
from .telegram import TgXato

log = logging.getLogger("otabot")


def ulash(abonent, talabalar, usul, kim=None):
    """Ota-onani talabalarga ulaydi (mavjud bo'lsa qayta faollashtiradi). Qaytaradi: yangi/qayta ulanganlar."""
    ulandi = []
    for t in talabalar:
        b, yaratildi = Boglanish.objects.get_or_create(
            abonent=abonent, talaba=t, defaults={"usul": usul, "kim": kim})
        if not yaratildi and not b.faol:
            b.faol, b.usul, b.kim = True, usul, kim
            b.save(update_fields=["faol", "usul", "kim"])
            yaratildi = True
        if yaratildi:
            ulandi.append(t)
    return ulandi


def ismlar_matni(talabalar):
    return ", ".join(talaba_ismi(t) for t in talabalar)


def faol_farzandlar(abonent):
    return [b.talaba for b in abonent.boglanishlar.filter(faol=True, talaba__is_active=True).select_related("talaba")]


def adminlar():
    """So'rovlarni ko'rib chiqa oladigan foydalanuvchilar (owner + `otabot.ulash` ruxsatli xodimlar)."""
    from crm.ruxsatlar import ruxsatlar

    nomzod = User.objects.filter(
        Q(is_superuser=True) | Q(role=User.Role.ADMIN) | Q(crm_xodim__isnull=False), is_active=True,
    ).distinct()
    return [u for u in nomzod if "otabot.ulash" in ruxsatlar(u)]


def adminlarga_bildir(sorov):
    """Yangi so'rov — adminlarga saytdagi 🔔 bildirishnoma (har admin uchun bitta)."""
    for u in adminlar():
        Bildirishnoma.objects.get_or_create(
            foydalanuvchi=u, kalit=f"otabot:sorov:{sorov.id}",
            defaults={
                "turi": Bildirishnoma.Turi.OGOHLANTIRISH,
                "sarlavha": "Ota-ona so'rovi",
                "matn": "Ota-ona farzandiga ulanish uchun so'rov yubordi — CRM → Ota-ona boti bo'limida ko'ring.",
            },
        )


def sorov_yarat(abonent, ism, sana_matni, nomzod_idlar):
    """Bir xil kutilayotgan so'rov takrorlanmaydi: bor bo'lsa — yangilanadi."""
    s = abonent.sorovlar.filter(holat=Sorov.Holat.KUTILMOQDA).first()
    if s:
        s.farzand_ismi, s.tugilgan_sana, s.nomzodlar = ism, sana_matni, nomzod_idlar
        s.save(update_fields=["farzand_ismi", "tugilgan_sana", "nomzodlar"])
        return s
    s = Sorov.objects.create(abonent=abonent, farzand_ismi=ism, tugilgan_sana=sana_matni, nomzodlar=nomzod_idlar)
    adminlarga_bildir(s)
    return s


def _yubor(tg, abonent, kalit, tugmalar_=None, **q):
    try:
        tg.yubor(abonent.telegram_id, matnlar.t(abonent.til, kalit, **q), tugmalar_)
    except TgXato:
        log.warning("Ota-onaga xabar yuborilmadi (so'rov qarori)")


def sorovni_hal_qil(sorov, amal, kim, tg, talaba=None):
    """Admin qarori: "ulash" (talaba bilan) yoki "rad". Ota-onaga Telegram'da xabar boradi.
    ValueError — so'rov allaqachon hal qilingan yoki talaba noto'g'ri."""
    if sorov.holat != Sorov.Holat.KUTILMOQDA:
        raise ValueError("Bu so'rov allaqachon ko'rib chiqilgan")
    if amal == "ulash":
        if talaba is None or talaba.role != User.Role.STUDENT or not talaba.is_active:
            raise ValueError("O'quvchini tanlang")
        ulash(sorov.abonent, [talaba], Boglanish.Usul.ADMIN, kim=kim)
        sorov.holat, sorov.talaba = Sorov.Holat.ULANDI, talaba
    elif amal == "rad":
        sorov.holat = Sorov.Holat.RAD
    else:
        raise ValueError("Noma'lum amal")
    sorov.hal_qilgan, sorov.hal_vaqti = kim, timezone.now()
    sorov.save(update_fields=["holat", "talaba", "hal_qilgan", "hal_vaqti"])
    if tg is not None:
        if amal == "ulash":
            _yubor(tg, sorov.abonent, "admin_ulandi", tugmalar.menyu(sorov.abonent.til), ismlar=talaba_ismi(talaba))
        else:
            _yubor(tg, sorov.abonent, "admin_rad")
    return sorov
