"""Avtomatik kunlik baza zaxirasi (2026-09-03, foydalanuvchi talabi:
"har kuni beckup olishni qo'shamiz, vaqt belgilab qo'yamiz, R2 ga har
kuni shu vaqtda beckup olib qo'yadi").

NEGA CRON/CELERY EMAS: loyihada tashqi rejalashtiruvchi ATAYLAB
ishlatilmaydi — `accounts/relizlar.py` va `courses/blok_views.py`
izohlarida shu qaror asoslangan (qo'shimcha servis, sozlash va to'lov
talab qiladi). Shu naqsh davom ettirildi: zaxira SO'ROV PAYTIDA
tekshiriladi va kerak bo'lsa FON OQIMIDA bajariladi.

Kamchiligi oshkora: belgilangan vaqtdan keyin saytga hech kim kirmasa,
zaxira birinchi kirishda olinadi (03:00 emas, masalan 08:15 da).
Talabalar har kuni kirgani uchun amalda kechikish kichik. Aniq vaqt
kerak bo'lsa Railway Cron `zaxira_yarat` buyrug'ini chaqirishi kifoya —
bu yerdagi mantiq o'zgarmaydi.

TAKRORLANMASLIK: `Zaxira` modelida `unique_together (markaz, sana,
turi)` bor. Bir vaqtda kelgan ikki so'rov ham "bugungisi yo'q" deb
topsa, ikkinchisi bazada to'qnashadi va jimgina tashlab ketiladi —
alohida qulf mexanizmi kerak emas.
"""

import datetime
import logging
import threading
import time

from django.core.files.base import File
from django.db import IntegrityError, transaction
from django.utils import timezone

from .backup_views import baza_zip_yasa
from .models import Markaz, Zaxira

logger = logging.getLogger(__name__)

# Ayni jarayonda tekshiruv shu tez-tezlikdan ko'p bajarilmaydi — har bir
# HTTP so'rovda bazaga qarash shart emas. Jarayon qayta ishga tushsa
# qiymat nolga qaytadi, bu muammo emas: takrorlanish baribir bazadagi
# `unique_together` bilan to'siladi.
_TEKSHIRUV_ORALIGI_SEK = 60
_oxirgi_tekshiruv = 0.0
_qulf = threading.Lock()


def _markaz():
    """Platforma bitta markaz rejimida ishlaydi (REJA.md) — boshqa
    joylardagi (`Markaz.objects.first()`) yondashuv bilan bir xil."""
    return Markaz.objects.first()


def kerakmi(markaz=None):
    """Bugungi avtomatik zaxira olinishi kerakmi: sozlama yoqilgan,
    mahalliy vaqt belgilangan vaqtdan o'tgan va bugun uchun yozuv
    hali yo'q."""
    markaz = markaz or _markaz()
    if not markaz or not markaz.zaxira_avtomatik:
        return False
    hozir = timezone.localtime()
    if hozir.time() < markaz.zaxira_vaqti:
        return False
    return not Zaxira.objects.filter(
        markaz=markaz, sana=hozir.date(), turi=Zaxira.Turi.AVTOMATIK
    ).exists()


def zaxira_yarat(markaz=None, turi=Zaxira.Turi.AVTOMATIK):
    """Baza zaxirasini yasab, `Zaxira.fayl`ga (ya'ni R2'ga) saqlaydi va
    muddati o'tganlarini o'chiradi. Yozuvni qaytaradi, allaqachon bor
    bo'lsa `None`.

    Format `BackupYuklabOlishView` bilan AYNAN bir xil (`baza_zip_yasa`
    umumiy) — shuning uchun bu fayl `BackupdanTiklashView` orqali
    tiklanadi.

    YOZUV ISHDAN KEYIN YARATILADI (2026-09-03 (2), kod-ревьюда topilgan
    haqiqiy xato): avval yozuv OLDIN yaratilardi — "bir vaqtda ketgan
    ikkinchi urinish og'ir dumpni takrorlamasin" degan niyatda. Lekin
    fon oqimi `daemon` bo'lgani uchun deploy yoki OOM paytida jarayon
    bilan DARHOL o'lardi va `except` ham bajarilmasdi. Natijada yozuv
    `fayl=""`, `xato=""` holatida qolib ketardi va:
      * `kerakmi()` "bugungisi bor" deb kun oxirigacha qayta urinmasdi;
      * ro'yxatda 0.00 MB sababsiz turardi;
      * tasma ham chiqmasdi (`exclude(fayl="")`).
    Ya'ni zaxira olinmagani JIMGINA yashirilardi. Endi jarayon o'lsa
    bazada hech narsa qolmaydi va keyingi so'rov qaytadan urinadi.
    Bunga to'lov — juda kam holatda ikki oqim dumpni parallel bajarishi
    (ortiqcha CPU), lekin natija baribir to'g'ri: biri bazada
    to'qnashadi va o'z faylini o'chirib chiqib ketadi."""
    markaz = markaz or _markaz()
    if not markaz:
        return None
    sana = timezone.localdate()

    # Avtomatik zaxira kunda BITTA (qo'lda esa cheksiz — foydalanuvchi
    # talabi). Bu faqat "ortiqcha ish qilmaslik" tekshiruvi; haqiqiy
    # kafolat bazadagi shartli UniqueConstraint'da.
    if turi == Zaxira.Turi.AVTOMATIK and Zaxira.objects.filter(
        markaz=markaz, sana=sana, turi=turi
    ).exists():
        return None

    bufer = fayl_nomi = None
    xato = ""
    try:
        bufer, fayl_nomi = baza_zip_yasa()
    except Exception as exc:  # noqa: BLE001 — sababni yozuvda saqlaymiz
        logger.exception("Zaxira olinmadi")
        xato = f"{type(exc).__name__}: {exc}"[:2000]

    yozuv = Zaxira(markaz=markaz, sana=sana, turi=turi, xato=xato)
    try:
        if bufer is not None:
            bufer.seek(0, 2)
            yozuv.hajm = bufer.tell()
            bufer.seek(0)
            yozuv.fayl.save(fayl_nomi, File(bufer), save=False)
        with transaction.atomic():
            yozuv.save()
    except IntegrityError:
        # Parallel avtomatik urinish g'olib bo'ldi — o'zimizning
        # yuklangan faylni qoldirib ketmaymiz (R2'da yetim fayl).
        if yozuv.fayl:
            try:
                yozuv.fayl.delete(save=False)
            except Exception:  # noqa: BLE001
                logger.warning("Yetim zaxira fayli o'chmadi: %s", yozuv.fayl.name)
        return None
    finally:
        if bufer is not None:
            bufer.close()

    if not xato:
        eskilarini_ochir(markaz)
    return yozuv


def eskilarini_ochir(markaz=None):
    """Saqlash muddati o'tgan zaxiralarni R2'dan va bazadan o'chiradi.

    ENG OXIRGI (muvaffaqiyatli) zaxira HAR DOIM qoladi — foydalanuvchi
    qarori (2026-09-03): sayt bir oy ishlatilmasa R2'da hech narsa
    qolmasligi xavfli. Shu sababli chegara sanasidan eski bo'lsa ham
    eng yangi nusxa tegilmaydi.

    Qaytaradi: o'chirilgan yozuvlar soni."""
    markaz = markaz or _markaz()
    if not markaz:
        return 0
    kun = markaz.zaxira_saqlash_kuni or 0
    if kun <= 0:
        return 0
    chegara = timezone.localdate() - datetime.timedelta(days=kun)

    eng_yangi = (
        Zaxira.objects.filter(markaz=markaz, xato="")
        .exclude(fayl="")
        .order_by("-sana", "-id")
        .first()
    )
    qs = Zaxira.objects.filter(markaz=markaz, sana__lt=chegara)
    if eng_yangi:
        qs = qs.exclude(pk=eng_yangi.pk)

    sanoq = 0
    for z in qs:
        if z.fayl:
            try:
                z.fayl.delete(save=False)
            except Exception:  # noqa: BLE001 — fayl yo'q bo'lsa ham yozuv ketadi
                logger.warning("Zaxira fayli o'chmadi: %s", z.fayl.name)
        z.delete()
        sanoq += 1
    return sanoq


def fonda_tekshir():
    """So'rov paytidan chaqiriladi (`accounts/middleware.py`). Ishni
    ASOSIY so'rovni ushlab turmasdan, alohida oqimda bajaradi —
    gunicorn `gthread` worker'ida (`gunicorn.conf.py`) bu xavfsiz.

    Bazaga har so'rovda qaramaslik uchun jarayon ichida oralik bor."""
    global _oxirgi_tekshiruv

    hozir = time.monotonic()
    with _qulf:
        if hozir - _oxirgi_tekshiruv < _TEKSHIRUV_ORALIGI_SEK:
            return
        _oxirgi_tekshiruv = hozir

    try:
        if not kerakmi():
            return
    except Exception:  # noqa: BLE001 — tekshiruv hech qachon so'rovni buzmasin
        logger.exception("Zaxira tekshiruvi muvaffaqiyatsiz")
        return

    def ishla():
        from django.db import connection

        try:
            zaxira_yarat()
        except Exception:  # noqa: BLE001
            logger.exception("Fon zaxirasi muvaffaqiyatsiz")
        finally:
            # Oqim o'z ulanishini yopmasa, ulanish hovuzida "bo'sh"
            # ulanish qolib ketadi.
            connection.close()

    threading.Thread(target=ishla, name="zaxira", daemon=True).start()
