"""O'chirilgan foydalanuvchilar "savati" — 7 kun ichida tiklash
(2026-09-25, Shuhrat talabi). Model izohi: `OchirilganFoydalanuvchi`.

Uch amal:

- `ochir_va_saqla(user, kim)` — nusxa oladi va foydalanuvchini o'chiradi
  (bitta tranzaksiyada: nusxa yozilmasa, foydalanuvchi ham o'chmaydi).
- `tikla(yozuv, kim)` — nusxadan qayta yozadi va SET_NULL bilan uzilgan
  bog'lanishlarni qayta ulaydi. Oradagi vaqtda o'chib ketgan narsaga
  (masalan, guruh o'chirilgan) bog'liq yozuv tiklanmaydi — nima
  tiklanmagani javobda aytiladi, qolgani tiklanadi.
- `muddati_otganlarni_tozala()` — 7 kundan eski nusxalarni o'chiradi
  (so'rov paytida "turtki", `accounts/middleware.py`, zaxira kabi).
"""

import logging
import threading
import time
from datetime import timedelta

from django.apps import apps
from django.core import serializers
from django.db import connection, router, transaction
from django.db.models.deletion import Collector
from django.utils import timezone

from .models import OchirilganFoydalanuvchi, User

logger = logging.getLogger(__name__)

SAQLASH_KUNI = 7

# Tiklanmaydigan bog'lanishlar: eski JWT tokenlar qayta ulanmaydi —
# tiklangan foydalanuvchi qaytadan kiradi.
_QAYTA_ULANMAYDI = {"token_blacklist.OutstandingToken"}


def _m2m_egasi_nusxada(model, modellar):
    """Avtomatik M2M oraliq jadvali (masalan `User_groups`). Uni e'lon
    qilgan model nusxada bo'lsa, qatorlar o'sha modelning M2M qiymati
    sifatida serializatsiya qilinadi — ikkinchi marta olinmaydi."""
    return bool(model._meta.auto_created) and model._meta.auto_created in modellar


def nusxa_ol(user):
    """O'chirilganda yo'qoladigan hamma narsa: `(obyektlar, bogliqlar)`."""
    collector = Collector(using=router.db_for_write(User), origin=user)
    collector.collect([user])
    modellar = set(collector.data)

    obyektlar = []
    for model, yozuvlar in collector.data.items():
        if not _m2m_egasi_nusxada(model, modellar):
            obyektlar.extend(yozuvlar)
    for qs in collector.fast_deletes:
        if not _m2m_egasi_nusxada(qs.model, modellar):
            obyektlar.extend(qs)

    bogliqlar = []
    for (maydon, qiymat), toplamlar in collector.field_updates.items():
        belgi = maydon.model._meta.label
        if qiymat is not None or belgi in _QAYTA_ULANMAYDI:
            continue
        pklar = []
        for t in toplamlar:
            pklar.extend(t.values_list("pk", flat=True) if hasattr(t, "values_list") else [o.pk for o in t])
        if pklar:
            bogliqlar.append({"model": belgi, "maydon": maydon.name, "pklar": sorted(set(pklar))})
    return obyektlar, bogliqlar


def ochir_va_saqla(user, kim):
    """Nusxa + o'chirish, bitta tranzaksiyada."""
    with transaction.atomic():
        obyektlar, bogliqlar = nusxa_ol(user)
        yozuv = OchirilganFoydalanuvchi.objects.create(
            foydalanuvchi_id=user.pk,
            username=user.username,
            ism=(user.get_full_name() or "")[:300],
            rol=user.role,
            ochirgan=kim,
            obyektlar=serializers.serialize("json", obyektlar),
            bogliqlar=bogliqlar,
            soni=len(obyektlar),
        )
        user.delete()
    return yozuv


def tugash_vaqti(yozuv):
    return yozuv.ochirilgan_vaqt + timedelta(days=SAQLASH_KUNI)


def _fk_maydonlari(model):
    return [f for f in model._meta.concrete_fields if f.is_relation and (f.many_to_one or f.one_to_one)]


def _nomi(obj):
    """Tiklanmagan yozuv nomi. `str(obj)` EMAS — u yo'qolgan bog'liq
    obyektga murojaat qilib, o'zi xato berishi mumkin."""
    return f"{obj._meta.verbose_name} #{obj.pk}"


def tikla(yozuv, kim=None):
    """Nusxadan tiklaydi. Qaytaradi: `(user, tiklanmaganlar)`.

    `ValueError` — umuman tiklab bo'lmasa (login band, muddat o'tgan).
    """
    if timezone.now() > tugash_vaqti(yozuv):
        raise ValueError("Tiklash muddati o'tgan")
    if User.objects.filter(username=yozuv.username).exists():
        raise ValueError(f"«{yozuv.username}» logini boshqa foydalanuvchiga berilgan — tiklab bo'lmaydi")
    if User.objects.filter(pk=yozuv.foydalanuvchi_id).exists():
        raise ValueError("Bu foydalanuvchi allaqachon mavjud")

    obyektlar = list(serializers.deserialize("json", yozuv.obyektlar, ignorenonexistent=True))
    nusxada = {(type(d.object), d.object.pk) for d in obyektlar}

    # Oradagi vaqtda bazada o'chib ketgan narsaga ishora qiluvchi yozuvlar:
    # ixtiyoriy bog'lanish bo'sh qoldiriladi, majburiysi bo'lsa yozuv
    # tiklanmaydi. Tashlab ketilgan yozuvga bog'liqlar ham — shuning
    # uchun o'zgarish qolmaguncha takrorlanadi.
    bor_kesh = {}

    def bormi(model, pk):
        if (model, pk) in nusxada:
            return True
        kalit = (model, pk)
        if kalit not in bor_kesh:
            bor_kesh[kalit] = model._base_manager.filter(pk=pk).exists()
        return bor_kesh[kalit]

    tiklanmaganlar = []
    ozgardi = True
    while ozgardi:
        ozgardi = False
        for d in list(obyektlar):
            obj = d.object
            for f in _fk_maydonlari(type(obj)):
                qiymat = getattr(obj, f.attname)
                if qiymat is None or bormi(f.related_model, qiymat):
                    continue
                if f.null:
                    setattr(obj, f.attname, None)
                    continue
                obyektlar.remove(d)
                nusxada.discard((type(obj), obj.pk))
                tiklanmaganlar.append(_nomi(obj))
                ozgardi = True
                break

    # Asl PK band bo'lsa (juda kam holat) — o'sha yozuv USTIDAN YOZILMAYDI.
    for d in list(obyektlar):
        obj = d.object
        if type(obj)._base_manager.filter(pk=obj.pk).exists():
            obyektlar.remove(d)
            tiklanmaganlar.append(_nomi(obj))

    # M2M qiymatlari (masalan `groups`) — oradagi vaqtda o'chganlari tashlanadi.
    for d in obyektlar:
        for nomi, pklar in list((d.m2m_data or {}).items()):
            boglangan = type(d.object)._meta.get_field(nomi).related_model
            d.m2m_data[nomi] = list(boglangan._base_manager.filter(pk__in=pklar).values_list("pk", flat=True))

    jadvallar = {type(d.object)._meta.db_table for d in obyektlar}
    with transaction.atomic():
        # `loaddata` naqshi: tartibdan qat'i nazar yoziladi, bog'lanishlar
        # oxirida tekshiriladi.
        with connection.constraint_checks_disabled():
            for d in obyektlar:
                d.save()
        connection.check_constraints(table_names=list(jadvallar))
        for b in yozuv.bogliqlar:
            try:
                model = apps.get_model(b["model"])
            except LookupError:
                continue
            maydon = b["maydon"]
            # Faqat hali ham BO'SH turganlari — oradagi vaqtda boshqa
            # talabaga bog'langan yozuvga tegilmaydi.
            model._base_manager.filter(pk__in=b["pklar"], **{f"{maydon}__isnull": True}).update(
                **{maydon: yozuv.foydalanuvchi_id}
            )
        yozuv.delete()
    user = User.objects.get(pk=yozuv.foydalanuvchi_id)
    return user, tiklanmaganlar


# ── Saytdan o'chirilmaydigan foydalanuvchilar ────────────────────────
#
# CRM o'quvchisi saytdagi "O'chirish" bilan O'CHIRILMAYDI — faqat saytga
# kirishi yopiladi (Shuhrat, 2026-09-25): sayt hisobi va CRM talabasi
# BITTA yozuv, o'chirilsa CRM'dagi guruhlar va moliya ham ketardi.
#
# Qaysi foydalanuvchi "CRM o'quvchisi" ekanini accounts BILMAYDI (u crm'dan
# import qilmaydi — `crm.tests.IzolyatsiyaTest`). CRM o'z tekshiruvini
# shu ro'yxatga qo'shadi (`crm/apps.py`); CRM olib tashlansa ro'yxat bo'sh
# qoladi va hamma avvalgidek o'chiriladi.
#
# Tekshiruv: `fn(user_idlar) -> set(id)` — o'chirilmaydiganlar.
SAYTDAN_OCHIRILMAYDIGANLAR = []


def ochirilmaydiganlar(user_idlar):
    idlar = list(user_idlar)
    natija = set()
    if not idlar:
        return natija
    for tekshiruv in SAYTDAN_OCHIRILMAYDIGANLAR:
        natija |= set(tekshiruv(idlar))
    return natija


def sayt_kirishini_yop(user):
    """O'chirish o'rniga: parol olib tashlanadi va barcha seanslar
    yopiladi. Hamma ma'lumot (guruh, moliya, natijalar) joyida qoladi;
    "Parol o'rnatish" bilan kirish qayta ochiladi."""
    from .seans_views import kalitlarni_bekor_qil

    user.set_unusable_password()
    user.save(update_fields=["password"])
    return kalitlarni_bekor_qil(user.pk)


def muddati_otganlarni_tozala():
    """Saqlash muddati o'tgan nusxalarni butunlay o'chiradi. Qaytaradi: soni."""
    chegara = timezone.now() - timedelta(days=SAQLASH_KUNI)
    eskilar = OchirilganFoydalanuvchi.objects.filter(ochirilgan_vaqt__lt=chegara)
    # Avval faqat O'QISH: odatda o'chiradigan narsa yo'q, fon oqimi esa
    # keraksiz yozish bilan jadvalni qulflamasin (SQLite'da boshqa
    # so'rovga "database table is locked" berardi).
    if not eskilar.exists():
        return 0
    soni, _ = eskilar.delete()
    return soni


# So'rov paytidagi "turtki" — `assessment.audio_tozalash` naqshi.
_TEKSHIRUV_ORALIGI_SEK = 60 * 60
_oxirgi_tekshiruv = 0.0
_qulf = threading.Lock()


def fonda_tekshir():
    global _oxirgi_tekshiruv

    hozir = time.monotonic()
    with _qulf:
        if _oxirgi_tekshiruv and hozir - _oxirgi_tekshiruv < _TEKSHIRUV_ORALIGI_SEK:
            return
        _oxirgi_tekshiruv = hozir

    def ishla():
        try:
            soni = muddati_otganlarni_tozala()
            if soni:
                logger.info("Savat: %s ta muddati o'tgan foydalanuvchi nusxasi o'chirildi", soni)
        except Exception:  # noqa: BLE001
            logger.exception("Savatni tozalash muvaffaqiyatsiz")
        finally:
            connection.close()

    threading.Thread(target=ishla, name="savat-tozalash", daemon=True).start()
