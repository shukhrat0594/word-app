"""Qurilma limiti — admin oynasi, so'rovlar va kalit yangilash (2026-10-20).

Mantiq `accounts/qurilmalar.py`da; bu yerda faqat ruxsat va javob shakli.
Owner va admin boshqaradi; admin owner'ning qurilmalariga tega olmaydi
(`QurilmaTiklashView` bilan bir xil qoida)."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from audit.models import FaoliyatYozuvi
from audit.utils import logla

from . import qurilmalar as qurilma_mantiq
from .models import QurilmaSorovi, User
from .permissions import owner_mi


def _boshqaruvchi(u):
    return owner_mi(u) or u.role == User.Role.ADMIN


def _ruxsat_xatosi(request, user):
    if not _boshqaruvchi(request.user):
        return Response({"detail": "Faqat owner/admin uchun"}, status=403)
    if user.is_superuser and not owner_mi(request.user):
        return Response({"detail": "Owner'ning qurilmasiga tega olmaysiz"}, status=403)
    return None


def _kim(u):
    return (u.get_full_name() or u.username).strip() if u else None


def _sorov_json(s):
    return {
        "id": s.id,
        "nom": s.nom,
        "holat": s.holat,
        "urinishlar": s.urinishlar,
        "yaratilgan": s.yaratilgan,
        "oxirgi_urinish": s.oxirgi_urinish,
        "almashtirilgan_nom": s.almashtirilgan_nom,
        "hal_qildi": _kim(s.hal_qildi),
        "hal_vaqti": s.hal_vaqti,
    }


def _qurilmalar_json(user):
    sorovlar = list(user.qurilma_sorovlari.select_related("hal_qildi")[:30])
    yozuvlar = qurilma_mantiq.royxat(user)
    # "Hozir ochiq" — faqat bir paytda bitta qurilma qoidasi tegishli bo'lganlarga.
    faol = user.faol_qurilma if qurilma_mantiq.bir_paytda_bitta(user) else ""
    return {
        "foydalanuvchi": {"id": user.id, "ism": _kim(user), "username": user.username, "rol": user.role},
        "owner": user.is_superuser,
        "limit": user.qurilma_limiti,
        # Brauzer ID'si ham, belgilar ham tashqariga BERILMAYDI — faqat nom va vaqtlar.
        "qurilmalar": [
            {
                "k": d.get("k"), "nom": d.get("nom"), "qoshilgan": d.get("qoshilgan"), "oxirgi": d.get("oxirgi"),
                "faol": bool(faol) and d.get("k") == faol,
                "brauzerlar": [{"nom": b.get("brauzer", ""), "oxirgi": b.get("oxirgi")} for b in d["brauzerlar"]],
            }
            for d in yozuvlar
        ],
        "sorovlar": [_sorov_json(s) for s in sorovlar if s.holat == QurilmaSorovi.Holat.KUTILMOQDA],
        "bloklangan": [_sorov_json(s) for s in qurilma_mantiq.bloklanganlar(sorovlar)],
        "jurnal": [_sorov_json(s) for s in sorovlar if s.holat != QurilmaSorovi.Holat.KUTILMOQDA][:10],
        "oy_almashtirishlari": qurilma_mantiq.oy_almashtirishlari(user),
    }


class QurilmalarView(APIView):
    """GET — foydalanuvchining qurilmalari, kutilayotgan so'rovlari va jurnali.
    POST {amal: "ochir", k} — bitta qurilmani o'chiradi (u darhol chiqarib yuboriladi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if xato := _ruxsat_xatosi(request, user):
            return xato
        return Response(_qurilmalar_json(user))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if xato := _ruxsat_xatosi(request, user):
            return xato
        if request.data.get("amal") != "ochir":
            return Response({"detail": "Noma'lum amal"}, status=400)
        ochirilgan = qurilma_mantiq.qurilmani_ochir(user, str(request.data.get("k") or ""))
        if ochirilgan is None:
            return Response({"detail": "Bu qurilma ro'yxatda yo'q — sahifani yangilang"}, status=400)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"qurilma": {"eski": ochirilgan.get("nom"), "yangi": "o'chirildi"}},
        )
        user.refresh_from_db()
        return Response(_qurilmalar_json(user))


class QurilmaSorovlariView(APIView):
    """GET — kutilayotgan va hozir bloklangan (24 soat ichida rad etilgan)
    qurilma so'rovlari, hamma foydalanuvchilar bo'yicha (admin bildirishnomasi
    shu sahifaga olib keladi; blokdan chiqarish ham shu yerdan — 2026-10-27)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _boshqaruvchi(request.user):
            return Response({"detail": "Faqat owner/admin uchun"}, status=403)
        qs = QurilmaSorovi.objects.filter(
            Q(holat=QurilmaSorovi.Holat.KUTILMOQDA)
            | Q(holat=QurilmaSorovi.Holat.RAD, hal_vaqti__gt=timezone.now() - qurilma_mantiq.RAD_AMAL_QILADI)
        ).select_related("foydalanuvchi")
        if not owner_mi(request.user):
            qs = qs.filter(foydalanuvchi__is_superuser=False)
        return Response([
            {**_sorov_json(s), "foydalanuvchi": {"id": s.foydalanuvchi_id, "ism": _kim(s.foydalanuvchi),
                                                 "username": s.foydalanuvchi.username, "rol": s.foydalanuvchi.role}}
            for s in qs
        ])


class QurilmaSoroviQarorView(APIView):
    """POST {amal: "almashtir", k} | {amal: "limit"} | {amal: "rad"} — admin qarori;
    {amal: "blokdan_chiqar"} — rad etilgan qurilma so'rovi yana kutilayotganlarga qaytadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sorov = get_object_or_404(QurilmaSorovi.objects.select_related("foydalanuvchi"), pk=pk)
        user = sorov.foydalanuvchi
        if xato := _ruxsat_xatosi(request, user):
            return xato
        amal = request.data.get("amal")
        try:
            if amal == "blokdan_chiqar":
                sorov = qurilma_mantiq.blokdan_chiqar(sorov)
            else:
                sorov = qurilma_mantiq.sorovni_hal_qil(sorov, amal, request.user, kalit=request.data.get("k"))
        except qurilma_mantiq.QarorXatosi as e:
            return Response({"detail": str(e)}, status=400)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"qurilma_sorovi": {"eski": sorov.nom, "yangi": sorov.get_holat_display()},
                         "amal": amal, "almashtirilgan": sorov.almashtirilgan_nom},
        )
        user.refresh_from_db()
        return Response(_qurilmalar_json(user))


class QurilmaliTokenRefreshView(TokenRefreshView):
    """Kalit yangilash — kalitdagi brauzer (`qid`) ro'yxatda bo'lmasa (admin
    o'chirgan/almashtirgan yoki 2026-10-20 dan oldingi belgisiz kalit) yoki
    talaba boshqa qurilmasidan kirgan bo'lsa rad etiladi — `authentication.py`
    bilan bir xil `kalit_xatosi`. Muvaffaqiyatda qurilmaning "oxirgi
    faolligi" yoziladi — usiz faol qurilma 60 kunda "eskirgan" bo'lib qolardi."""

    def post(self, request, *args, **kwargs):
        xom = request.data.get("refresh") if hasattr(request.data, "get") else None
        try:
            payload = RefreshToken(xom).payload if xom else {}
        except TokenError:
            payload = {}  # yaroqsiz kalit — standart javobni ota-klass beradi
        user_id, qid = payload.get(api_settings.USER_ID_CLAIM), payload.get("qid")
        if user_id:
            user = User.objects.filter(pk=user_id).only(
                "id", "is_superuser", "role", "faol_qurilma", "qurilmalar").first()
            if user is not None and not user.is_superuser and (xato := qurilma_mantiq.kalit_xatosi(user, qid)):
                return Response(xato, status=401)
        javob = super().post(request, *args, **kwargs)
        if javob.status_code == 200 and user_id and qid:
            qurilma_mantiq.faollikni_yoz(user_id, qid)
        return javob
