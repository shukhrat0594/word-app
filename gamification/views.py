from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import KursTugun

from .models import BADGES, jami_xp

User = get_user_model()

TURLAR = ("ielts", "kurs")
DAVRLAR = ("oy", "hammasi")


def oy_boshi():
    """Joriy oyning boshi (Toshkent vaqti bilan) — "Shu oy" reytingi shundan hisoblanadi."""
    return timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _leaderboard(talabalar_qs, joriy_user, tur="ielts", boshi=None, top=10):
    """Berilgan talabalar to'plami uchun XP reytingi + joriy foydalanuvchi o'rni.

    `tur` — qaysi reyting ("ielts" | "kurs"); "umumiy" XP (davomat) ikkalasiga ham qo'shiladi.
    `boshi` — shu paytdan keyingi XP (oylik reyting); None — hamma vaqt."""
    shart = Q(xp_yozuvlar__tur__in=[tur, "umumiy"])
    if boshi is not None:
        shart &= Q(xp_yozuvlar__created_at__gte=boshi)
    # Talabalar to'plami `talaba_guruhlari__...` kabi bog'lanish orqali tuzilgan bo'lsa, XP bilan
    # qo'shilganda qatorlar KO'PAYIB ketadi (bir necha guruh -> XP ikki hisoblanadi). Shuning uchun
    # avval faqat ID'lar olinadi.
    idlar = talabalar_qs.filter(role="student").values("pk")
    reyting = list(
        User.objects.filter(pk__in=idlar)
        # Coalesce SHART: XP yozuvi yo'q talabada Sum() NULL qaytaradi,
        # PostgreSQL'da esa `DESC` tartibida NULL BIRINCHI turadi — ya'ni
        # prodda 0 XP'lilar reyting tepasiga chiqib ketardi (2026-09-16
        # da topildi). SQLite'da NULL oxirida, shuning uchun lokalda
        # ko'rinmasdi.
        .annotate(xp=Coalesce(Sum("xp_yozuvlar__miqdor", filter=shart), Value(0)))
        .order_by("-xp", "id")
        .values("id", "username", "first_name", "last_name", "xp", "rasm")
    )
    for i, r in enumerate(reyting, start=1):
        r["orin"] = i
        r["xp"] = r["xp"] or 0
        rasm = r.pop("rasm")
        r["rasm_url"] = f"/api/foydalanuvchilar/{r['id']}/rasm/" if rasm else None
    mening = next((r for r in reyting if r["id"] == joriy_user.id), None)
    return {"top": reyting[:top], "mening_ornim": mening, "ishtirokchilar": len(reyting)}


def _daraja_tartibi(qs):
    return qs.distinct().order_by("parent__tartib", "tartib", "id")


def talaba_darajalari(user):
    """Talabaning darajalari — FAOL guruhlaridagi `daraja` (Beginner, Elementary, IELTS...)."""
    return _daraja_tartibi(KursTugun.objects.filter(
        guruhlar_daraja__talabalar=user, guruhlar_daraja__faol=True,
    ))


def barcha_darajalar():
    """Hech bo'lmasa bitta faol guruhi bor darajalar (admin/o'qituvchi ko'radi)."""
    return _daraja_tartibi(KursTugun.objects.filter(guruhlar_daraja__faol=True))


def daraja_talabalari(daraja):
    """Shu darajadagi faol guruhlarda o'qiydigan faol talabalar. `daraja=None` — hech qanday
    darajali faol guruhi yo'q talabalar ("Darajasiz")."""
    talabalar = User.objects.filter(role="student", is_active=True)
    if daraja is None:
        return talabalar.exclude(
            talaba_guruhlari__in=_faol_darajali_guruhlar()
        )
    return talabalar.filter(talaba_guruhlari__daraja=daraja, talaba_guruhlari__faol=True)


def _faol_darajali_guruhlar():
    from academics.models import Guruh

    return Guruh.objects.filter(faol=True, daraja__isnull=False)


class GamifikatsiyaView(APIView):
    """Talabaning XP, badge va oxirgi hodisalari."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        badges = [
            {
                "kod": b.kod,
                "nom": BADGES.get(b.kod, (b.kod, ""))[0],
                "tavsif": BADGES.get(b.kod, ("", ""))[1],
                "sana": b.created_at.date(),
            }
            for b in request.user.badges.all()
        ]
        oxirgi = [
            {"miqdor": y.miqdor, "sabab": y.sabab, "sana": y.created_at}
            for y in request.user.xp_yozuvlar.all()[:20]
        ]
        return Response(
            {"jami_xp": jami_xp(request.user), "badges": badges, "oxirgi": oxirgi}
        )


class LeaderboardView(APIView):
    """Reyting DARAJA bo'yicha (Beginner, Elementary, IELTS...) — platforma bo'yicha umumiy reyting yo'q.

    Parametrlar: `tur` = ielts | kurs (standart ielts), `davr` = oy | hammasi (standart oy).
    Talaba faqat O'Z darajalari (faol guruhlari) reytingini ko'radi; darajasi bo'lmasa — "Darajasiz".
    Admin/o'qituvchi/owner hamma darajani ko'radi. Ham guruh bo'yicha reyting qoladi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tur = request.query_params.get("tur") or "ielts"
        davr = request.query_params.get("davr") or "oy"
        if tur not in TURLAR:
            return Response({"detail": f"tur {', '.join(TURLAR)} dan biri bo'lsin"}, status=400)
        if davr not in DAVRLAR:
            return Response({"detail": f"davr {', '.join(DAVRLAR)} dan biri bo'lsin"}, status=400)
        boshi = oy_boshi() if davr == "oy" else None

        talaba_mi = request.user.role == "student"
        darajalar = list(talaba_darajalari(request.user) if talaba_mi else barcha_darajalar())
        guruhlar_qs = request.user.talaba_guruhlari.filter(faol=True) if talaba_mi else []

        natija_darajalar = []
        for d in darajalar:
            r = _leaderboard(daraja_talabalari(d), request.user, tur, boshi)
            r["daraja"] = {"id": d.id, "nomi": d.nomi}
            natija_darajalar.append(r)
        if talaba_mi and not darajalar:
            r = _leaderboard(daraja_talabalari(None), request.user, tur, boshi)
            r["daraja"] = None  # "Darajasiz"
            natija_darajalar.append(r)

        guruhlar = []
        for guruh in guruhlar_qs:
            g = _leaderboard(guruh.talabalar.all(), request.user, tur, boshi)
            g["guruh"] = {"id": guruh.id, "name": guruh.name}
            guruhlar.append(g)

        return Response({
            "tur": tur,
            "davr": davr,
            "darajalar": natija_darajalar,
            # Bosh sahifa uchun: talabaning birinchi darajasi (yoki bo'sh)
            "asosiy": natija_darajalar[0] if natija_darajalar else {"top": [], "mening_ornim": None, "daraja": None},
            "guruhlar": guruhlar,
        })
