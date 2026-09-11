"""Speaking AI audiolarini muddat bo'yicha tozalash (2026-09-11,
foydalanuvchi talabi: "shu audiolarni 7 kundan keyin o'chib ketadigan
qil, push qilganingizda darhol tekshirsin, muddati o'tganlarini o'chirib
tashlasin").

NEGA CRON/CELERY EMAS: loyihada tashqi rejalashtiruvchi ATAYLAB
ishlatilmaydi — sabab `accounts/zaxira.py` va `accounts/relizlar.py`
izohlarida asoslangan. Shu naqsh davom ettirildi: "vaqt keldimi?"
savoli SO'ROV paytida beriladi (`accounts/middleware.py`), ish esa fon
oqimida bajariladi, ya'ni foydalanuvchi so'rovi kutib turmaydi.

"PUSH QILGANDA DARHOL": deploydan keyin jarayon yangidan ko'tariladi va
`_oxirgi_tekshiruv` nolga qaytadi — ya'ni saytga kelgan BIRINCHI
so'rovdayoq tekshiruv o'tadi, oraliqni kutmaydi.

FAQAT AUDIO o'chadi, `SpeakingTekshiruv` yozuvining o'zi (matn, band,
natija) QOLADI — talabaning tarixi buzilmasligi kerak. Frontend audio
yo'qligini allaqachon hisobga oladi (`NatijalarRoyxati.jsx`:
`{y.audio_url && ...}`), serializer esa audio bo'lmasa `audio_url`ni
`None` qaytaradi (`assessment/views.py: _audio_url`).

IELTS testlari bo'limidagi speaking bu yerga UMUMAN tegishli emas — u
oqimda audio hech qachon saqlanmaydi (`SpeakingTranskripsiyaView`:
audio faqat transkripsiya uchun o'qiladi va tashlab yuboriladi).
"""

import datetime
import logging
import threading
import time

from django.utils import timezone

from .models import SpeakingTekshiruv

logger = logging.getLogger(__name__)

# Audio necha kun saqlanadi (2026-09-11 talabi: 7 kun).
SAQLASH_KUNI = 7

# Ayni jarayonda tekshiruv shu tez-tezlikdan ko'p bajarilmaydi — har bir
# HTTP so'rovda bazaga qarash shart emas. Jarayon qayta ishga tushsa
# (deploy) qiymat nolga qaytadi va birinchi so'rov darhol tekshiradi.
_TEKSHIRUV_ORALIGI_SEK = 60 * 60
_oxirgi_tekshiruv = 0.0
_qulf = threading.Lock()


def eskilarni_ochir(kun=SAQLASH_KUNI):
    """Muddati o'tgan audiolarni saqlagichdan (R2 yoki lokal disk)
    o'chirib, yozuvdagi maydonni bo'shatadi.

    Fayl o'chmasa (masalan R2 javob bermasa) maydon ATAYLAB bo'sh
    qolmaydi — aks holda fayl saqlagichda "yetim" bo'lib abadiy qolib
    ketardi. Bunday yozuv keyingi tekshiruvda qayta uriniladi.

    Qaytaradi: o'chirilgan audiolar soni."""
    chegara = timezone.now() - datetime.timedelta(days=kun)
    qs = SpeakingTekshiruv.objects.filter(created_at__lt=chegara).exclude(audio_fayl="")

    sanoq = 0
    for tekshiruv in qs.iterator():
        nom = tekshiruv.audio_fayl.name
        try:
            # `FieldFile.delete` faylni saqlagichdan o'chiradi va maydonni
            # bo'shatadi; `save=False` — yozuvni o'zimiz saqlaymiz.
            tekshiruv.audio_fayl.delete(save=False)
        except Exception:  # noqa: BLE001 — bitta fayl butun tozalashni to'xtatmasin
            logger.warning("Speaking audiosi o'chmadi: %s", nom)
            continue
        tekshiruv.save(update_fields=["audio_fayl"])
        sanoq += 1
    return sanoq


def fonda_tekshir():
    """So'rov paytidan chaqiriladi (`accounts/middleware.py`). Ishni
    ASOSIY so'rovni ushlab turmasdan, alohida oqimda bajaradi —
    gunicorn `gthread` worker'ida (`gunicorn.conf.py`) bu xavfsiz."""
    global _oxirgi_tekshiruv

    hozir = time.monotonic()
    with _qulf:
        # `_oxirgi_tekshiruv == 0` — jarayon endi ko'tarilgan, darhol
        # tekshiramiz (deploydan keyingi birinchi so'rov).
        if _oxirgi_tekshiruv and hozir - _oxirgi_tekshiruv < _TEKSHIRUV_ORALIGI_SEK:
            return
        _oxirgi_tekshiruv = hozir

    def ishla():
        from django.db import connection

        try:
            sanoq = eskilarni_ochir()
            if sanoq:
                logger.info("Speaking: %s ta muddati o'tgan audio o'chirildi", sanoq)
        except Exception:  # noqa: BLE001
            logger.exception("Speaking audiolarini tozalash muvaffaqiyatsiz")
        finally:
            # Oqim o'z ulanishini yopmasa, ulanish hovuzida "bo'sh"
            # ulanish qolib ketadi.
            connection.close()

    threading.Thread(target=ishla, name="speaking-audio-tozalash", daemon=True).start()
