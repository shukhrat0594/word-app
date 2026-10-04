"""Ota-onaga xabar yuborish: davomat (2-bosqich). To'lov/qarz/natija shu mexanizm ustiga quriladi.

Signal ISHLATILMAYDI (CRM qoidasi) — davriy tekshiruv:

1. `skanerla_davomat`: yangi davomat yozuvlarini topib, ulangan ota-onalar uchun `Xabar` yaratadi.
   "Kelmadi" xabari DARHOL emas, `KECHIKISH` dan keyin yuboriladi: admin belgini adashib qo'yib
   tuzatsa, ota-onaga xato xabar ketmasin.
2. `yubor_navbat`: vaqti kelgan xabarlarni yuboradi. Yuborishdan oldin qayta tekshiradi
   (davomat o'zgargan/o'chirilgan, ota-ona to'xtatgan, sozlama o'chirilgan — bekor qilinadi).
   Tinch soatlarda hech narsa yuborilmaydi — xabar kutadi.

Eski davomatlar yog'ilib ketmasin: faqat birinchi tekshiruvdan KEYIN yaratilgan yozuvlar va
faqat kecha/bugungi sanalar uchun.
"""

import logging
import time
from datetime import timedelta

from django.utils import timezone

from academics.models import Davomat

from . import matnlar
from .models import Boglanish, ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from .moslash import talaba_ismi
from .telegram import TgXato

log = logging.getLogger("parentsbot")

KECHIKISH = timedelta(minutes=5)
URINISH_CHEGARASI = 5
YOSH_KUNLAR = 1  # shuncha kun oldingi sanagacha bo'lgan davomatlar xabar beradi (kecha va bugun)


def tinch_mi(vaqt, boshi, oxiri):
    """Tinch soatlarmi? Yarim tundan oshadigan oraliq (22:00-08:00) ham to'g'ri ishlaydi."""
    if boshi == oxiri:
        return False
    if boshi < oxiri:
        return boshi <= vaqt < oxiri
    return vaqt >= boshi or vaqt < oxiri


def davomat_kodi(d):
    """Davomat yozuvi -> 'kelmadi' | 'sababli' | 'kechikdi' | None (xabar kerak emas)."""
    izoh = getattr(d, "crm_izoh", None)  # CRM belgilari (bo'lmasa — None)
    if d.holat == Davomat.Holat.KELMADI:
        return "sababli" if izoh is not None and izoh.sababli else "kelmadi"
    if izoh is not None and izoh.kechikdi:
        return "kechikdi"
    return None


def _kod_yoqilgan(sozlama, kod):
    if not sozlama.davomat_yoqilgan:
        return False
    return {"kelmadi": sozlama.davomat_kelmadi, "kechikdi": sozlama.davomat_kechikdi,
            "sababli": sozlama.davomat_sababli}.get(kod, False)


def skanerla_davomat(hozir=None):
    """Yangi xabarlar sonini qaytaradi. Birinchi chaqiruv faqat boshlanish vaqtini belgilaydi."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.davomat_boshlandi is None:
        kuzatuv.davomat_boshlandi = hozir
        kuzatuv.save(update_fields=["davomat_boshlandi"])
        return 0
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.davomat_yoqilgan:
        return 0
    bugun = timezone.localdate(hozir)
    yangi = 0
    yozuvlar = Davomat.objects.filter(
        sana__gte=bugun - timedelta(days=YOSH_KUNLAR), created_at__gte=kuzatuv.davomat_boshlandi,
    ).select_related("guruh", "crm_izoh")
    for d in yozuvlar:
        kod = davomat_kodi(d)
        if not kod or not _kod_yoqilgan(sozlama, kod):
            continue
        for b in Boglanish.objects.filter(talaba_id=d.talaba_id, faol=True, abonent__faol=True).select_related("abonent"):
            _, yaratildi = Xabar.objects.get_or_create(
                abonent=b.abonent, kalit=f"davomat:{d.id}:{kod}",
                defaults={
                    "talaba_id": d.talaba_id, "turi": "davomat", "yuborilsin": hozir + KECHIKISH,
                    "payload": {"davomat_id": d.id, "kod": kod, "sana": d.sana.isoformat(), "guruh": d.guruh.name},
                },
            )
            yangi += yaratildi
    return yangi


def _hali_yaroqli(x, sozlama):
    """Yuborishdan oldingi tekshiruv: bekor qilish kerakmi?"""
    ab = x.abonent
    if not ab.faol or x.turi in (ab.toifa_ochirilgan or []):
        return False
    if not Boglanish.objects.filter(abonent=ab, talaba_id=x.talaba_id, faol=True).exists():
        return False
    if x.turi == "davomat":
        d = Davomat.objects.filter(pk=x.payload.get("davomat_id")).select_related("crm_izoh").first()
        kod = x.payload.get("kod")
        return d is not None and davomat_kodi(d) == kod and _kod_yoqilgan(sozlama, kod)
    return True


def _matn(x, bugun):
    from datetime import date

    ab = x.abonent
    sana = date.fromisoformat(x.payload["sana"])
    return matnlar.t(
        ab.til, f"davomat_{x.payload['kod']}",
        ism=talaba_ismi(x.talaba), kun=matnlar.kun_matni(ab.til, sana, bugun), guruh=x.payload.get("guruh", ""),
    )


def yubor_navbat(tg, hozir=None, pauza=0.05):
    """Vaqti kelgan xabarlarni yuboradi. Qaytaradi: yuborilganlar soni."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if tinch_mi(timezone.localtime(hozir).time(), sozlama.tinch_boshi, sozlama.tinch_oxiri):
        return 0  # tinch soatlar: xabarlar kutadi
    bugun = timezone.localdate(hozir)
    yuborildi = 0
    navbat = Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA, yuborilsin__lte=hozir) \
        .select_related("abonent", "talaba")[:100]
    for x in navbat:
        if not _hali_yaroqli(x, sozlama):
            x.holat = Xabar.Holat.BEKOR
            x.save(update_fields=["holat"])
            continue
        try:
            tg.yubor(x.abonent.telegram_id, _matn(x, bugun))
        except TgXato as xato:
            if "403" in str(xato):  # ota-ona botni bloklagan — boshqa urinmaymiz
                x.abonent.faol = False
                x.abonent.save(update_fields=["faol"])
                x.holat = Xabar.Holat.XATO
                x.save(update_fields=["holat"])
                log.info("Ota-ona botni bloklagan: xabarlar to'xtatildi")
                continue
            x.urinish += 1
            if x.urinish >= URINISH_CHEGARASI:
                x.holat = Xabar.Holat.XATO
            x.save(update_fields=["urinish", "holat"])
            log.warning("Xabar yuborilmadi (urinish %s): %s", x.urinish, type(xato).__name__)
            continue
        x.holat, x.yuborildi = Xabar.Holat.YUBORILDI, hozir
        x.save(update_fields=["holat", "yuborildi"])
        yuborildi += 1
        if pauza:
            time.sleep(pauza)  # Telegram: sekundiga ~30 xabar
    return yuborildi
