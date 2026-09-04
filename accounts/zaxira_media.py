"""To'liq zaxira — media fayllar ro'yxati va imzolangan havolalari
(2026-09-03, foydalanuvchi talabi: "to'liq beckupni railwayga
bog'lamasdan qilsa bo'ladimi?").

MUAMMO: R2'da ~6.2 GB media (4.4k obyekt). Uni server orqali o'tkazib
yuklab olish MUMKIN EMAS — server avval hammasini o'ziga yig'ishi kerak,
so'ng yuborishi; bu Railway'ning 15 daqiqalik qattiq chegarasidan
oshadi (aynan shu muammo kurslar darajasi importida bo'lgan).

YECHIM: fayllar SERVERDAN O'TMAYDI. Server faqat ro'yxat va har fayl
uchun VAQTINCHALIK IMZOLANGAN HAVOLA (presigned URL) beradi — bu
mahalliy HMAC hisobi, R2'ga so'rov ham ketmaydi. Fayllarni brauzer
R2'dan TO'G'RIDAN-TO'G'RI diskka oqim bilan yozadi:

    Server  ──►  ro'yxat + imzolar (kichik JSON)
    R2      ──────────────────────────────►  brauzer  ──►  disk

Natijada: Railway chegarasi tegishli emas, server xotirasi to'lmaydi,
R2'dan yuklab olish esa Cloudflare'da tekin.

RO'YXAT SAHIFALAB beriladi (foydalanuvchi talabi: "hammasini to'liq
olmasin, bir nechtadan olsin") — bir so'rovda 4400 ta emas, 200 tadan.
Imzolar HAR SAHIFA so'ralganda yangi yasaladi, ya'ni uzun yuklashda
havola muddati tugab qolmaydi.

LOKAL ISHLAB CHIQISH: R2 sozlanmagan bo'lsa (`R2_BUCKET_NAME` bo'sh)
storage lokal diskka tushadi va imzolangan havola tushunchasi yo'q —
bunday holatda ro'yxat MEDIA_ROOT bo'ylab yig'iladi va havola sifatida
shu yerdagi `ZaxiraMediaFaylView` beriladi. Prodda bu yo'l
ISHLATILMAYDI (imzolangan havola bor), u faqat lokal sinov uchun.
"""

import os
from urllib.parse import quote

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import owner_mi

# Bir sahifadagi fayllar soni. 200 — ro'yxat javobi ~100 KB atrofida
# qoladi va 4.4k obyekt ~22 ta yengil so'rovga bo'linadi.
SAHIFA_HAJMI = 200

# Imzolangan havola muddati. Brauzer bitta sahifani bir necha daqiqada
# yuklab oladi, shuning uchun 6 soat ortig'i bilan yetadi (keyingi
# sahifalar uchun imzolar QAYTA yasaladi).
HAVOLA_MUDDATI_SEK = 6 * 3600

# Zaxiralarning o'zi zaxiraga kirmasin — bu shunchaki takror.
CHIQARIB_TASHLANADIGAN_PREFIKSLAR = ("zaxiralar/",)


def _bucket():
    """R2 sozlangan bo'lsa (bucket nomi va boto3 ulanishi bor) —
    (client, bucket_nomi), aks holda (None, None)."""
    bucket_nomi = getattr(default_storage, "bucket_name", None)
    ulanish = getattr(default_storage, "connection", None)
    if not bucket_nomi or ulanish is None:
        return None, None
    return ulanish.meta.client, bucket_nomi


def _tashlanadimi(yol):
    return not yol or yol.endswith("/") or yol.startswith(CHIQARIB_TASHLANADIGAN_PREFIKSLAR)


def _lokal_fayllar():
    """Lokal disk rejimi — MEDIA_ROOT bo'ylab barcha fayllar (nisbiy
    yo'l, hajm). Tartib barqaror bo'lishi uchun saralanadi: sahifalash
    indeks bo'yicha ketadi."""
    kok = str(settings.MEDIA_ROOT)
    natija = []
    for papka, _, fayllar in os.walk(kok):
        for f in fayllar:
            toliq = os.path.join(papka, f)
            yol = os.path.relpath(toliq, kok).replace(os.sep, "/")
            if _tashlanadimi(yol):
                continue
            try:
                natija.append((yol, os.path.getsize(toliq)))
            except OSError:
                continue
    natija.sort()
    return natija


class ZaxiraMediaRoyxatView(APIView):
    """GET — media fayllarning bir SAHIFASI, imzolangan havolalari bilan.

    So'rov: `?kursor=<oldingi javobdagi keyingi>&hisob=1`
      * `hisob=1` — fayllarni sanab, JAMI soni va hajmini qaytaradi
        (havolalar yasalmaydi). Brauzer jarayon ko'rsatkichi uchun
        maxrajni shundan oladi. R2'da bu faqat ro'yxat so'rovlari,
        ya'ni ma'lumot oqmaydi.
      * kursorsiz — birinchi sahifa.

    Javob: `{fayllar: [{yol, hajm, url}], keyingi: <kursor|null>}`
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        client, bucket = _bucket()
        if request.query_params.get("hisob"):
            return Response(self._hisob(client, bucket))
        if client:
            return Response(self._r2_sahifa(client, bucket, request.query_params.get("kursor")))
        return Response(self._lokal_sahifa(request.query_params.get("kursor")))

    # ── Jami hisob ────────────────────────────────────────────────
    def _hisob(self, client, bucket):
        if not client:
            fayllar = _lokal_fayllar()
            return {
                "jami_soni": len(fayllar),
                "jami_hajm": sum(h for _, h in fayllar),
                "manba": "lokal",
            }
        soni = hajm = 0
        kursor = None
        while True:
            kw = {"Bucket": bucket, "MaxKeys": 1000}
            if kursor:
                kw["ContinuationToken"] = kursor
            javob = client.list_objects_v2(**kw)
            for obj in javob.get("Contents", []):
                if _tashlanadimi(obj["Key"]):
                    continue
                soni += 1
                hajm += obj["Size"]
            kursor = javob.get("NextContinuationToken")
            if not javob.get("IsTruncated") or not kursor:
                break
        return {"jami_soni": soni, "jami_hajm": hajm, "manba": "r2"}

    # ── R2 sahifasi ───────────────────────────────────────────────
    def _r2_sahifa(self, client, bucket, kursor):
        kw = {"Bucket": bucket, "MaxKeys": SAHIFA_HAJMI}
        if kursor:
            kw["ContinuationToken"] = kursor
        javob = client.list_objects_v2(**kw)
        fayllar = []
        for obj in javob.get("Contents", []):
            yol = obj["Key"]
            if _tashlanadimi(yol):
                continue
            fayllar.append({
                "yol": yol,
                "hajm": obj["Size"],
                "url": client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": yol},
                    ExpiresIn=HAVOLA_MUDDATI_SEK,
                ),
            })
        keyingi = javob.get("NextContinuationToken") if javob.get("IsTruncated") else None
        return {"fayllar": fayllar, "keyingi": keyingi}

    # ── Lokal sahifa (faqat ishlab chiqish) ───────────────────────
    def _lokal_sahifa(self, kursor):
        fayllar = _lokal_fayllar()
        try:
            boshlanish = int(kursor or 0)
        except (TypeError, ValueError):
            boshlanish = 0
        bolak = fayllar[boshlanish:boshlanish + SAHIFA_HAJMI]
        oxiri = boshlanish + len(bolak)
        return {
            "fayllar": [
                {
                    "yol": yol,
                    "hajm": hajm,
                    # Lokalda imzolangan havola yo'q — faylni serverning
                    # o'zi beradi (faqat sinov uchun, prodda ishlatilmaydi).
                    "url": f"/api/zaxira/media-fayl/?yol={quote(yol)}",
                }
                for yol, hajm in bolak
            ],
            "keyingi": str(oxiri) if oxiri < len(fayllar) else None,
        }


class ZaxiraMediaFaylView(APIView):
    """GET — bitta media faylni beradi (owner uchun).

    FAQAT lokal ishlab chiqish uchun zaxira yo'li: R2 sozlangan bo'lsa
    brauzer imzolangan havola orqali TO'G'RIDAN-TO'G'RI R2'dan oladi va
    bu endpoint umuman chaqirilmaydi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        yol = request.query_params.get("yol") or ""
        # Yo'ldan chiqib ketishga yo'l qo'ymaymiz ("../" bilan boshqa
        # kataloglarga o'tish urinishi).
        if not yol or yol.startswith("/") or ".." in yol.split("/"):
            return Response({"detail": "Yo'l noto'g'ri"}, status=400)
        if _tashlanadimi(yol):
            return Response({"detail": "Bu fayl zaxiraga kirmaydi"}, status=400)
        if not default_storage.exists(yol):
            raise Http404
        return FileResponse(default_storage.open(yol, "rb"), as_attachment=True,
                            filename=yol.rsplit("/", 1)[-1])
