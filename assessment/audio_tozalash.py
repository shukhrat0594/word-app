"""Speaking audiolarini muddat bo'yicha tozalash (2026-09-11,
foydalanuvchi talabi: "shu audiolarni 7 kundan keyin o'chib ketadigan
qil, push qilganingizda darhol tekshirsin, muddati o'tganlarini o'chirib
tashlasin").

2026-09-14, Shuhrat talabi bilan O'ZGARTIRILDI: "har kuni tungi 00:00 da
yozilganiga 24 soatdan oshgan speaking javoblari audiolarini o'chirish
kerak". Ikkita o'zgarish:
  1) muddat 7 kun -> 24 soat (`SAQLASH_SOATI`);
  2) tekshiruv soatiga bir marta emas, KUNIGA bir marta — mahalliy
     (Asia/Tashkent) sana almashgach, ya'ni tungi 00:00 dan keyingi
     birinchi so'rovda.

BUNING OQIBATI (Shuhratga aytilgan va u shu variantni tanlagan):
tekshiruv faqat yarim tunda bo'lgani uchun audio 24 soatdan ko'proq
yashashi mumkin. Ertalab 10:00 da yozilgan audio keyingi tunda hali 14
soatlik — o'chmaydi; undan keyingi tunda 38 soatlik bo'lib o'chadi.
Ya'ni amaldagi umr 24-48 soat. "Aynan 24 soat" kerak bo'lsa —
`_kunlik_tekshiruv` o'rniga soatlik oraliqqa qaytish kifoya.

NEGA CRON/CELERY EMAS: loyihada tashqi rejalashtiruvchi ATAYLAB
ishlatilmaydi — sabab `accounts/zaxira.py` va `accounts/relizlar.py`
izohlarida asoslangan. Shu naqsh davom ettirildi: "vaqt keldimi?"
savoli SO'ROV paytida beriladi (`accounts/middleware.py`), ish esa fon
oqimida bajariladi, ya'ni foydalanuvchi so'rovi kutib turmaydi.

"PUSH QILGANDA DARHOL": deploydan keyin jarayon yangidan ko'tariladi va
`_oxirgi_kun` `None` ga qaytadi — ya'ni saytga kelgan BIRINCHI
so'rovdayoq tekshiruv o'tadi, ertangi kunni kutmaydi.

FAQAT AUDIO o'chadi, `SpeakingTekshiruv` yozuvining o'zi (matn, band,
natija) QOLADI — talabaning tarixi buzilmasligi kerak. Frontend audio
yo'qligini allaqachon hisobga oladi (`NatijalarRoyxati.jsx`:
`{y.audio_url && ...}`), serializer esa audio bo'lmasa `audio_url`ni
`None` qaytaradi (`assessment/views.py: _audio_url`).

2026-09-14 dan boshlab IELTS testlari bo'limidagi speaking ham SHU
qoidaga bo'ysunadi: avval u oqimda audio umuman saqlanmasdi, endi
javob audiosi `SpeakingTekshiruv.audio_fayl`ga yoziladi
(`exercises/views.py: ImtihonYozGapTekshirishView`) va shu tozalash
uni ham qamrab oladi — model bitta bo'lgani uchun qo'shimcha kod
kerak emas.
"""

import datetime
import logging
import threading

from django.utils import timezone

from .models import SpeakingTekshiruv

logger = logging.getLogger(__name__)

# Audio necha soat saqlanadi (2026-09-14 talabi: 24 soat).
SAQLASH_SOATI = 24

# Tozalash oxirgi marta QAYSI mahalliy kunda bajarilgani. Sana almashsa
# (ya'ni tungi 00:00 o'tsa) — keyingi so'rovda qayta bajariladi.
# Jarayon qayta ishga tushsa (deploy) `None` ga qaytadi va birinchi
# so'rovdayoq tekshiradi — "push qilganda darhol" sharti shundan.
_oxirgi_kun = None
_qulf = threading.Lock()


def eskilarni_ochir(soat=SAQLASH_SOATI):
    """Muddati o'tgan audiolarni saqlagichdan (R2 yoki lokal disk)
    o'chirib, yozuvdagi maydonni bo'shatadi.

    Fayl o'chmasa (masalan R2 javob bermasa) maydon ATAYLAB bo'sh
    qolmaydi — aks holda fayl saqlagichda "yetim" bo'lib abadiy qolib
    ketardi. Bunday yozuv keyingi tekshiruvda qayta uriniladi.

    Qaytaradi: o'chirilgan audiolar soni."""
    chegara = timezone.now() - datetime.timedelta(hours=soat)
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
    gunicorn `gthread` worker'ida (`gunicorn.conf.py`) bu xavfsiz.

    KUNIGA BIR MARTA: `timezone.localdate()` — TIME_ZONE (Asia/Tashkent)
    bo'yicha sana. U o'zgargan bo'lsa, demak tungi 00:00 o'tgan va
    tozalash vaqti kelgan (2026-09-14 talabi)."""
    global _oxirgi_kun

    bugun = timezone.localdate()
    with _qulf:
        # `_oxirgi_kun is None` — jarayon endi ko'tarilgan, darhol
        # tekshiramiz (deploydan keyingi birinchi so'rov).
        if _oxirgi_kun == bugun:
            return
        _oxirgi_kun = bugun

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
