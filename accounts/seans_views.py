"""Seanslar — chiqish, "Aktiv foydalanuvchilar" ro'yxati va seansni
yopish (2026-09-03, foydalanuvchi talabi).

MUAMMO (foydalanuvchi topib berdi): "Kimdadir saytdan chiqqanda seans
qolib ketish holati bo'lishi mumkinmi?" — HA. Frontenddagi "Chiqish"
faqat brauzerdagi kalitlarni tozalardi (`Layout.jsx`), serverga hech
narsa aytilmasdi. Server tomonda refresh kalit o'z muddatigacha AMAL
QILARDI — ya'ni "chiqib ketgan" odam aslida hamon kira olardi.

Bu yerda ikkala tomon hal qilinadi:
  1. `ChiqishView` — chiqishda kalit DARHOL bekor qilinadi (ildiz
     yechim: yangi "qolib ketgan" seanslar deyarli paydo bo'lmaydi).
  2. `AktivFoydalanuvchilarView` — owner ochiq seanslarni ko'radi va
     kerakligini yopadi (eski, allaqachon qolib ketganlar uchun).

SEANS = amaldagi (muddati o'tmagan, bekor qilinmagan) refresh kalit.
Bitta odamda bir nechta bo'lishi mumkin — har brauzer/qurilma uchun
bittadan.

YOPISH DARHOL EMAS: kirish (access) kaliti 30 daqiqa amal qiladi, ya'ni
odam eng ko'p 30 daqiqadan keyin chiqarib yuboriladi. Har so'rovda
bazaga qarash bu vaqtni nolga tushirardi, lekin har so'rovni
sekinlashtiradi — shuning uchun ATAYLAB shunday qoldirildi va
interfeysda yozib qo'yilgan.
"""

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import FaoliyatYozuvi
from audit.utils import logla

from .models import User
from .permissions import owner_mi


def amaldagi_kalitlar(user_id=None):
    """Amaldagi (muddati o'tmagan va bekor qilinmagan) refresh kalitlar.

    `values("user_id").distinct()` bilan bir xil natijani
    `SaytHolatiView._aktiv_foydalanuvchilar_soni` ham hisoblaydi —
    ta'rif bitta joyda bo'lishi uchun shu yordamchi ishlatiladi."""
    qs = OutstandingToken.objects.filter(
        expires_at__gt=timezone.now(),
        blacklistedtoken__isnull=True,
        user__isnull=False,
    )
    return qs.filter(user_id=user_id) if user_id else qs


def kalitlarni_bekor_qil(user_id):
    """Foydalanuvchining BARCHA amaldagi kalitlarini qora ro'yxatga
    qo'yadi. Qaytaradi: nechta kalit bekor qilindi."""
    sanoq = 0
    for kalit in amaldagi_kalitlar(user_id):
        BlacklistedToken.objects.get_or_create(token=kalit)
        sanoq += 1
    return sanoq


class ChiqishView(APIView):
    """POST — chaqiruvchining refresh kalitini bekor qiladi.

    Frontend "Chiqish" bosilganda shu yerga murojaat qiladi va
    NATIJANI KUTMAYDI: so'rov muvaffaqiyatsiz bo'lsa ham odam baribir
    chiqadi (brauzerdagi kalitlar tozalanadi) — chiqib ketishga
    to'sqinlik bo'lmasligi kerak.

    `refresh` berilmasa — chaqiruvchining barcha kalitlari bekor
    qilinadi (masalan brauzer refresh kalitini yo'qotib qo'ygan bo'lsa
    ham seans qolib ketmaydi)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        xom = (request.data.get("refresh") or "").strip()
        if xom:
            try:
                RefreshToken(xom).blacklist()
                return Response({"bekor_qilindi": 1})
            except TokenError:
                # Kalit allaqachon eskirgan/bekor qilingan — bu xato
                # emas, natija baribir kerakli holat.
                return Response({"bekor_qilindi": 0})
        return Response({"bekor_qilindi": kalitlarni_bekor_qil(request.user.pk)})


class AktivFoydalanuvchilarView(APIView):
    """GET — ochiq seansi bor foydalanuvchilar (faqat owner).

    Har yozuvda `oxirgi_faollik` ham qaytadi: seans ochiq, lekin odam
    uzoq vaqt ko'rinmagan bo'lsa — bu QOLIB KETGAN seans. Frontend shu
    ikkisini solishtirib ogohlantirish belgisini chiqaradi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        # Har foydalanuvchi uchun amaldagi kalitlar soni.
        seanslar = {}
        for user_id in amaldagi_kalitlar().values_list("user_id", flat=True):
            seanslar[user_id] = seanslar.get(user_id, 0) + 1
        if not seanslar:
            return Response([])

        foydalanuvchilar = User.objects.filter(pk__in=seanslar).only(
            "id", "username", "first_name", "last_name", "role",
            "is_superuser", "oxirgi_faollik", "qurilmalar",
        )
        natija = [
            {
                "id": u.id,
                "login": u.username,
                "ism": (u.get_full_name() or u.username).strip(),
                "rol": "owner" if u.is_superuser else u.role,
                "oxirgi_faollik": u.oxirgi_faollik,
                "seans_soni": seanslar.get(u.id, 0),
                "qurilma_soni": len(u.qurilmalar or []),
                # O'zini tasodifan chiqarib yubormasligi uchun (foydalanuvchi
                # qarori) — o'z qatorida "Yopish" ko'rsatilmaydi.
                "ozim": u.id == request.user.pk,
            }
            for u in foydalanuvchilar
        ]
        # Eng yaqinda faol bo'lganlar tepada; hech qachon ko'rinmaganlar
        # OXIRIDA (ular ham eng shubhalilar — seans ochiq, lekin odam
        # hech qachon so'rov yubormagan).
        natija.sort(key=lambda x: (
            x["oxirgi_faollik"] is None,
            -(x["oxirgi_faollik"].timestamp() if x["oxirgi_faollik"] else 0),
        ))
        return Response(natija)


class SeansniYopishView(APIView):
    """POST — foydalanuvchining barcha ochiq seanslarini yopadi (faqat
    owner). Qurilmalar ro'yxatiga TEGILMAYDI — u boshqa maqsad uchun
    (hisobni bo'lishmaslik) va uni tozalash "Qurilmani tiklash" tugmasi
    orqali bo'ladi (foydalanuvchi qarori, 2026-09-03)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        if pk == request.user.pk:
            return Response(
                {"detail": "O'z seansingizni bu yerdan yopib bo'lmaydi — "
                           "\"Chiqish\" tugmasidan foydalaning"},
                status=400,
            )
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({"detail": "Foydalanuvchi topilmadi"}, status=404)

        sanoq = kalitlarni_bekor_qil(user.pk)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="User",
            obyekt_nomi=f"Seans yopildi: {user.username}",
            # `snapshot` faqat yaratish/o'chirish uchun — OZGARTIRISH'da
            # diff bo'sh bo'lsa `logla` yozuv YARATMAYDI (audit/utils.py).
            # Shuning uchun tayyor `ozgarishlar` beriladi.
            ozgarishlar={"seans": {"eski": f"{sanoq} ta ochiq", "yangi": "yopildi"}},
        )
        return Response({"bekor_qilindi": sanoq})
