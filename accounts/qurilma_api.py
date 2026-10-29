"""Qurilmalar limiti, 2-tizim — API (2026-10-29). Mantiq `accounts/qurilma_tizimi.py`da,
bu yerda faqat ruxsat va javob shakli. «Qurilmalar» oynasini owner va admin boshqaradi;
brauzer ID'lari va kalitlar tashqariga hech qachon berilmaydi."""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from audit.models import FaoliyatYozuvi, LoginHistory
from audit.utils import logla

from . import qurilma_kaliti, qurilma_tizimi
from .models import FaolSeans, KirishJurnali, Markaz, Qurilma, User
from .permissions import owner_mi


def kirish_cheklangan_javobi():
    """«Kirish vaqtincha cheklangan» (2026-08-15) — owner'dan boshqa hech kim kirmaydi."""
    markaz = Markaz.objects.first()
    if markaz and markaz.kirish_cheklangan:
        return Response({"detail": "Saytga kirish vaqtincha cheklangan", "kod": "kirish_cheklangan"}, status=403)
    return None


class KalitBilanKirishView(APIView):
    """Login'ning ikkinchi bosqichi — «Qurilmangizni tasdiqlang» (yangi brauzer yoki tarixi
    tozalangan brauzer). POST {chipta, javob} — telefon qulfi bilan tasdiqlangan kalit;
    {chipta, kalitsiz: true} — talaba «Bu yangi qurilma»ni bosdi."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        if cheklov := kirish_cheklangan_javobi():
            return cheklov
        try:
            user, qid, natija = qurilma_tizimi.kalit_bilan_kirish(
                request.data.get("chipta"), request.data.get("javob"), kalitsiz=request.data.get("kalitsiz") is True)
        except qurilma_kaliti.KalitXatosi as e:
            return Response({"detail": str(e), "kod": "kalit_xatosi"}, status=400)
        if not natija.kirdi:
            return Response(natija.javob, status=natija.status)
        javob = qurilma_tizimi.kalit_ber(user, qid, natija.qurilma, natija.brauzer)
        LoginHistory.objects.create(foydalanuvchi=user, rol=user.role)
        return Response(javob)


class TokenniYangilashView(TokenRefreshView):
    """Kalit yangilash — `authentication.py` bilan bir xil tekshiruv (`kalit_xatosi`): qurilma
    o'chirilgan/bloklangan yoki talaba boshqa joydan kirgan bo'lsa rad etiladi."""

    def post(self, request, *args, **kwargs):
        xom = request.data.get("refresh") if hasattr(request.data, "get") else None
        try:
            payload = RefreshToken(xom).payload if xom else {}
        except TokenError:
            payload = {}  # yaroqsiz kalit — standart javobni ota-klass beradi
        user_id, qid = payload.get(api_settings.USER_ID_CLAIM), payload.get("qid")
        if user_id:
            user = User.objects.filter(pk=user_id).only("id", "is_superuser", "role").first()
            if user is not None and not user.is_superuser and (xato := qurilma_tizimi.kalit_xatosi(user, payload)):
                return Response(xato, status=401)
        javob = super().post(request, *args, **kwargs)
        if javob.status_code == 200 and user_id and qid:
            qurilma_tizimi.faollikni_yoz(user_id, qid)
        return javob


class KalitYaratishView(APIView):
    """«Bu qurilmani eslab qolish»: POST .../boshlash/ — telefonga yuboriladigan so'rov,
    POST .../saqlash/ {chipta, javob} — yaratilgan kalitni joriy qurilmaga bog'lash."""

    permission_classes = [IsAuthenticated]

    def post(self, request, bosqich):
        if bosqich not in ("boshlash", "saqlash"):
            return Response({"detail": "Topilmadi"}, status=404)
        kalit = request.auth
        try:
            if bosqich == "boshlash":
                origin = qurilma_kaliti.manzil(request)
                if origin is None:
                    raise qurilma_kaliti.KalitXatosi("Bu manzilda qurilma kaliti ishlamaydi")
                qid = kalit.get("qid") if kalit is not None else None
                return Response(qurilma_tizimi.kalit_yaratish_boshla(request.user, qid, origin))
            q = qurilma_tizimi.kalit_saqla(request.user, request.data.get("chipta"), request.data.get("javob"))
        except qurilma_kaliti.KalitXatosi as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"nom": q.nom, "kalit_bor": True})


# ── «Qurilmalar» oynasi ────────────────────────────────────────────────

def _boshqaruvchi(u):
    return owner_mi(u) or u.role == User.Role.ADMIN


def _kim(u):
    return (u.get_full_name() or u.username).strip() if u else None


def _qurilma_json(q, ruxsatlar, seans):
    oxshash = qurilma_tizimi.oxshashi(q, ruxsatlar) if q.holat == Qurilma.Holat.KUTILMOQDA else None
    return {
        "id": q.pk, "nom": q.nom, "tizim": q.tizim, "holat": q.holat, "kalit_bor": q.kalit_soni > 0,
        "brauzerlar": [{"nom": b.brauzer, "oxirgi": b.oxirgi}
                       for b in sorted(q.brauzerlar.all(), key=lambda b: b.oxirgi, reverse=True)],
        "yaratilgan": q.yaratilgan, "oxirgi": q.oxirgi, "urinishlar": q.urinishlar,
        "oxshash": {"id": oxshash.pk, "nom": oxshash.nom} if oxshash else None,
        "hal_qildi": _kim(q.hal_qildi), "hal_vaqti": q.hal_vaqti,
        "seans": bool(seans and seans.qurilma_id == q.pk),
    }


class QurilmalarOynasiView(APIView):
    """GET ?holat=hammasi|kutilmoqda|blok|kalitsiz &rol=hammasi|talaba|xodim &q=qidiruv
    &foydalanuvchi=id — foydalanuvchilar o'z qurilmalari, seansi va limiti bilan. Standart
    holatda faqat qurilmasi borlar; qidiruv va `foydalanuvchi` qurilmasizni ham ko'rsatadi."""

    permission_classes = [IsAuthenticated]
    CHEGARA = 200

    def get(self, request):
        if not _boshqaruvchi(request.user):
            return Response({"detail": "Faqat owner/admin uchun"}, status=403)
        p = request.query_params
        odamlar = User.objects.filter(is_superuser=False)
        rol = p.get("rol") or "hammasi"
        if rol == "talaba":
            odamlar = odamlar.filter(role=User.Role.STUDENT)
        elif rol == "xodim":
            odamlar = odamlar.filter(role__in=(User.Role.TEACHER, User.Role.ADMIN))

        barchasi = Qurilma.objects.filter(foydalanuvchi__in=odamlar)
        tanlov = {
            "kutilmoqda": barchasi.filter(holat=Qurilma.Holat.KUTILMOQDA),
            "blok": barchasi.filter(holat=Qurilma.Holat.BLOK),
            "kalitsiz": barchasi.filter(holat=Qurilma.Holat.RUXSAT, kalitlar__isnull=True),
        }
        sanoq = {"hammasi": barchasi.count(), **{k: v.count() for k, v in tanlov.items()}}
        holat = p.get("holat") if p.get("holat") in tanlov else "hammasi"
        tanlangan = tanlov.get(holat, barchasi)

        fid, qidiruv = p.get("foydalanuvchi"), (p.get("q") or "").strip()
        if fid:
            odamlar = odamlar.filter(pk=int(fid) if fid.isdigit() else 0)
        else:
            for soz in qidiruv.split():
                odamlar = odamlar.filter(Q(username__icontains=soz) | Q(first_name__icontains=soz)
                                         | Q(last_name__icontains=soz))
            if not qidiruv or holat != "hammasi":
                odamlar = odamlar.filter(pk__in=tanlangan.values("foydalanuvchi_id"))
        odamlar = list(odamlar.order_by("first_name", "last_name", "username")[:self.CHEGARA + 1])
        kesildi = len(odamlar) > self.CHEGARA
        odamlar = odamlar[:self.CHEGARA]

        ids = [u.pk for u in odamlar]
        qurilmalar = {}
        for q in (Qurilma.objects.filter(foydalanuvchi_id__in=ids).select_related("hal_qildi")
                  .prefetch_related("brauzerlar").annotate(kalit_soni=Count("kalitlar"))):
            qurilmalar.setdefault(q.foydalanuvchi_id, []).append(q)
        seanslar = {s.foydalanuvchi_id: s for s in FaolSeans.objects.filter(foydalanuvchi_id__in=ids)
                    .select_related("qurilma")}

        natija = []
        for u in odamlar:
            royxat = qurilmalar.get(u.pk, [])
            ruxsatlar = [q for q in royxat if q.holat == Qurilma.Holat.RUXSAT]
            seans = seanslar.get(u.pk)
            natija.append({
                "id": u.pk, "ism": _kim(u), "username": u.username, "rol": u.role,
                "limit": u.qurilma_limiti, "ruxsat_soni": len(ruxsatlar),
                "seans": ({"qurilma": seans.qurilma.nom, "brauzer": seans.brauzer, "boshlangan": seans.boshlangan}
                          if seans and seans.qurilma else None),
                "qurilmalar": [_qurilma_json(q, ruxsatlar, seans) for q in royxat],
            })
        # So'rov kutayotganlar tepada, keyin oxirgi faollik bo'yicha.
        natija.sort(key=lambda x: (
            not any(q["holat"] == Qurilma.Holat.KUTILMOQDA for q in x["qurilmalar"]),
            -max((q["oxirgi"].timestamp() for q in x["qurilmalar"]), default=0),
        ))
        return Response({"sanoq": sanoq, "foydalanuvchilar": natija, "kesildi": kesildi})


def _ruxsat_xatosi(request, user):
    if not _boshqaruvchi(request.user):
        return Response({"detail": "Faqat owner/admin uchun"}, status=403)
    if user.is_superuser:
        return Response({"detail": "Owner uchun qurilma cheklovi yo'q"}, status=400)
    return None


class QurilmaAmaliView(APIView):
    """POST {amal: ruxsat|orniga|shu_qurilmaga|blokla|blokdan_chiqar|ochir, boshqa: id}."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        q = get_object_or_404(Qurilma.objects.select_related("foydalanuvchi"), pk=pk)
        if xato := _ruxsat_xatosi(request, q.foydalanuvchi):
            return xato
        amal, nom = request.data.get("amal"), q.nom
        try:
            user = qurilma_tizimi.qurilma_amali(q.pk, amal, request.user, boshqa_id=request.data.get("boshqa"))
        except qurilma_tizimi.AmalXatosi as e:
            return Response({"detail": str(e)}, status=400)
        logla(
            foydalanuvchi=request.user, harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH, obyekt=user,
            obyekt_turi="Foydalanuvchi", ozgarishlar={"qurilma": {"eski": nom, "yangi": amal}},
        )
        return Response({"ok": True})


class FoydalanuvchiQurilmaView(APIView):
    """GET — foydalanuvchining kirish jurnali (oxirgi 30). POST {amal: "limit", limit} yoki
    {amal: "seans_yop"} — limitni o'zgartirish yoki ochiq seansni yopish."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if xato := _ruxsat_xatosi(request, user):
            return xato
        jurnal = KirishJurnali.objects.filter(foydalanuvchi=user).select_related("kim")[:30]
        return Response([
            {"vaqt": j.vaqt, "natija": j.natija, "sabab": j.sabab, "qurilma": j.qurilma_nomi, "kim": _kim(j.kim)}
            for j in jurnal
        ])

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if xato := _ruxsat_xatosi(request, user):
            return xato
        amal = request.data.get("amal")
        if amal == "limit":
            eski = user.qurilma_limiti
            try:
                qurilma_tizimi.limitni_ozgartir(user, request.data.get("limit"), request.user)
            except qurilma_tizimi.AmalXatosi as e:
                return Response({"detail": str(e)}, status=400)
            ozgarish = {"qurilma_limiti": {"eski": eski, "yangi": user.qurilma_limiti}}
        elif amal == "seans_yop":
            qurilma_tizimi.seansni_yop(user, request.user)
            ozgarish = {"seans": {"eski": "ochiq", "yangi": "yopildi"}}
        else:
            return Response({"detail": "Noma'lum amal"}, status=400)
        logla(foydalanuvchi=request.user, harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH, obyekt=user,
              obyekt_turi="Foydalanuvchi", ozgarishlar=ozgarish)
        return Response({"ok": True})
