from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GrammatikaSavoli, Soz


class SozlarView(APIView):
    """O'yin uchun tasodifiy so'zlar to'plami.

    ?daraja=A1&soni=8 — shu darajadan N ta tasodifiy so'z qaytaradi
    (Juftini top va Flashcard o'yinlari shu ro'yxatdan foydalanadi).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        daraja = request.query_params.get("daraja") or Soz.Daraja.A1
        try:
            soni = min(int(request.query_params.get("soni", 8)), 20)
        except ValueError:
            soni = 8

        sozlar = list(
            Soz.objects.filter(daraja=daraja).order_by("?")[:soni]
        )
        return Response(
            [
                {
                    "id": s.id,
                    "en": s.en,
                    "uz": s.uz,
                    "turkum": s.turkum,
                    "misol": s.misol,
                }
                for s in sozlar
            ]
        )


class DarajalarView(APIView):
    """Mavjud CEFR darajalari va har birida nechta so'z borligi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        natija = (
            Soz.objects.values("daraja")
            .annotate(soni=Count("id"))
            .order_by("daraja")
        )
        return Response(list(natija))


class GrammatikaMavzulariView(APIView):
    """Mavjud grammatika mavzulari va har birida nechta savol borligi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        natija = (
            GrammatikaSavoli.objects.values("mavzu")
            .annotate(soni=Count("id"))
            .order_by("mavzu")
        )
        return Response(list(natija))


class GrammatikaSavollariView(APIView):
    """O'yin uchun tasodifiy grammatika savollari — to'g'ri javob YO'Q
    (B3.2 qoidasi — javob faqat tekshirish endpoint orqali biladi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        mavzu = request.query_params.get("mavzu")
        try:
            soni = min(int(request.query_params.get("soni", 10)), 20)
        except ValueError:
            soni = 10

        qs = GrammatikaSavoli.objects.all()
        if mavzu:
            qs = qs.filter(mavzu=mavzu)
        savollar = list(qs.order_by("?")[:soni])
        return Response(
            [
                {"id": s.id, "savol": s.savol, "variantlar": s.variantlar}
                for s in savollar
            ]
        )


class GrammatikaTekshirishView(APIView):
    """Berilgan javoblarni tekshiradi: {javoblar: [{id, javob}]} -> natijalar."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        javoblar = request.data.get("javoblar") or []
        idlar = [j.get("id") for j in javoblar]
        savollar = {s.id: s for s in GrammatikaSavoli.objects.filter(pk__in=idlar)}

        natijalar = []
        for j in javoblar:
            savol = savollar.get(j.get("id"))
            if not savol:
                continue
            natijalar.append(
                {
                    "id": savol.id,
                    "togrimi": j.get("javob") == savol.togri,
                    "togri_javob": savol.togri,
                }
            )
        return Response({"natijalar": natijalar})
