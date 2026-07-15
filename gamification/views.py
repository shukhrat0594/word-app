from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BADGES, jami_xp

User = get_user_model()


def _leaderboard(talabalar_qs, joriy_user, top=10):
    """Berilgan talabalar to'plami uchun XP reytingi + joriy foydalanuvchi o'rni."""
    reyting = list(
        talabalar_qs.filter(role="student")
        .annotate(xp=Sum("xp_yozuvlar__miqdor"))
        .order_by("-xp", "id")
        .values("id", "username", "first_name", "last_name", "xp")
    )
    for i, r in enumerate(reyting, start=1):
        r["orin"] = i
        r["xp"] = r["xp"] or 0
    mening = next((r for r in reyting if r["id"] == joriy_user.id), None)
    return {"top": reyting[:top], "mening_ornim": mening}


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
    """Reyting: platforma bo'yicha va foydalanuvchining har bir guruhi ichida."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        umumiy = _leaderboard(User.objects.all(), request.user)

        guruhlar = []
        for guruh in request.user.talaba_guruhlari.all():
            g = _leaderboard(guruh.talabalar.all(), request.user)
            g["guruh"] = {"id": guruh.id, "name": guruh.name}
            guruhlar.append(g)

        return Response({"umumiy": umumiy, "guruhlar": guruhlar})
