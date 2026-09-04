"""Zaxira endpointlari — faqat owner uchun (2026-09-03).

Bu yerda AVTOMATIK zaxiralar bilan ishlash: ro'yxat, yuklab olish,
"hozir olish" va tepadagi doimiy tasma uchun holat.

Bazani BEVOSITA kompyuterga yuklab olish (`/api/backup/yuklab-olish/`)
va tiklash (`/api/backup/tiklash/`) avvaldan `backup_views.py`da —
ular o'zgarmadi.
"""

from django.http import FileResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import zaxira as zaxira_mantiq
from .models import Zaxira
from .permissions import owner_mi


def _zaxira_dict(z):
    return {
        "id": z.id,
        "sana": z.sana,
        "turi": z.turi,
        "hajm": z.hajm,
        "yuklab_olindi": z.yuklab_olindi,
        "yuklab_olingan_at": z.yuklab_olingan_at,
        "xato": z.xato,
        "fayl_bor": bool(z.fayl),
    }


class ZaxiralarView(APIView):
    """GET — zaxiralar ro'yxati. POST — hoziroq zaxira olish.

    POST ATAYLAB sinxron: owner tugmani bosib natijani kutadi, fon
    oqimida qilinsa "bo'ldimi yoki yo'qmi" noaniq qolardi. Baza dumpi
    bir necha sekund (lokal sinovda 13 MB JSON -> 1.8 MB ZIP), ya'ni
    so'rov chegarasiga yaqin ham emas.

    QO'LDA ZAXIRA AVTOMATIKDAN ALOHIDA va HECH QACHON to'silmaydi
    (2026-09-03 (2), foydalanuvchi talabi). Avval kunda bitta qo'lda
    zaxira cheklovi bor edi va u xato bo'lgan urinishdan keyin owner'ni
    ertagagacha zaxirasiz qoldirardi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        markaz = zaxira_mantiq._markaz()
        qs = Zaxira.objects.filter(markaz=markaz) if markaz else Zaxira.objects.none()
        return Response([_zaxira_dict(z) for z in qs])

    def post(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        z = zaxira_mantiq.zaxira_yarat(turi=Zaxira.Turi.QOLDA)
        if z is None:
            # Qo'lda zaxira uchun bu faqat "markaz topilmadi" degani —
            # kunlik cheklov qo'lda zaxiraga umuman qo'llanmaydi.
            return Response({"detail": "Markaz topilmadi"}, status=400)
        if z.xato:
            return Response({"detail": z.xato}, status=500)
        return Response(_zaxira_dict(z), status=201)


class ZaxiraYuklabOlishView(APIView):
    """GET — zaxira faylini (R2'dan) owner kompyuteriga beradi va
    "yuklab olindi" deb belgilaydi. Tepadagi tasma aynan shu belgiga
    qaraydi, ya'ni yuklab olingach tasma yo'qoladi."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        z = Zaxira.objects.filter(pk=pk).first()
        if not z or not z.fayl:
            return Response({"detail": "Zaxira topilmadi"}, status=404)

        if not z.yuklab_olindi:
            z.yuklab_olindi = True
            z.yuklab_olingan_at = timezone.now()
            z.save(update_fields=["yuklab_olindi", "yuklab_olingan_at"])

        nomi = z.fayl.name.rsplit("/", 1)[-1] or f"zaxira_{z.sana}.zip"
        return FileResponse(z.fayl.open("rb"), as_attachment=True, filename=nomi)


class ZaxiraHolatView(APIView):
    """GET — tepadagi doimiy tasma uchun: yuklab olinmagan ENG YANGI
    zaxira (bo'lsa) va sozlama holati.

    Nega alohida endpoint: bu ma'lumot HAR sahifada kerak, `/api/profil/`
    esa boshqa maqsadga xizmat qiladi va uni og'irlashtirmaslik kerak.
    Javob juda kichik — bitta yozuv yoki `null`."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"yuklab_olinmagan": None})
        markaz = zaxira_mantiq._markaz()
        if not markaz:
            return Response({"yuklab_olinmagan": None})
        z = (
            Zaxira.objects.filter(markaz=markaz, yuklab_olindi=False, xato="")
            .exclude(fayl="")
            .order_by("-sana", "-id")
            .first()
        )
        return Response({
            "avtomatik": markaz.zaxira_avtomatik,
            "yuklab_olinmagan": _zaxira_dict(z) if z else None,
        })
