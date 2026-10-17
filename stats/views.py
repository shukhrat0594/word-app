from django.apps import apps as django_apps
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import talaba_statistikasi


def _balans(talaba):
    """`crm.mantiq.balans()` bilan bir xil formula. `stats` `crm`ni statik
    import qilmaydi (crm.tests.IzolyatsiyaTest) — modellar runtime'da olinadi."""
    if not django_apps.is_installed("crm"):
        return 0
    Tolov = django_apps.get_model("crm", "Tolov")
    Hisob = django_apps.get_model("crm", "Hisob")
    tolovlar = Tolov.objects.filter(talaba=talaba)
    kirim = tolovlar.filter(turi__in=Tolov.YOPUVCHI_TURLAR).aggregate(j=Sum("summa"))["j"] or 0
    chiqim = tolovlar.filter(turi=Tolov.Turi.QAYTARISH).aggregate(j=Sum("summa"))["j"] or 0
    hisoblangan = Hisob.objects.filter(talaba=talaba).aggregate(j=Sum("summa"))["j"] or 0
    return kirim - chiqim - hisoblangan


class MeningStatistikamView(APIView):
    """Talabaning o'z statistikasi (B6). Har doim ochiq (B3.2)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(talaba_statistikasi(request.user))


class FarzandlarView(APIView):
    """Ota-onaning bog'langan farzandlari ro'yxati (B6.1)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "parent":
            return Response({"detail": "Faqat Ota-ona roli uchun"}, status=403)
        return Response(
            [
                {
                    "id": f.id,
                    "username": f.username,
                    "ism": f.get_full_name() or f.username,
                }
                for f in request.user.farzandlar.all()
            ]
        )


class FarzandStatistikasiView(APIView):
    """Ota-ona o'z farzandining statistikasini ko'radi — faqat o'qish (B6.1).

    Faqat bog'langan farzand — boshqa talabalar 404 (B3.2 qoidasi).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role != "parent":
            return Response({"detail": "Faqat Ota-ona roli uchun"}, status=403)
        farzand = get_object_or_404(request.user.farzandlar, pk=pk)
        data = talaba_statistikasi(farzand)
        # Video-TZ IMG_2217: ota-ona farzandning to'lov/qarz holatini va
        # faol guruhlari ustozining ismi-telefonini ham ko'radi.
        bal = _balans(farzand)
        data["tolov"] = {"balans": int(bal), "qarz": int(-bal) if bal < 0 else 0}
        data["ustozlar"] = [
            {
                "guruh": g.name,
                "ism": (g.oqituvchi.get_full_name() or g.oqituvchi.username) if g.oqituvchi else None,
                "telefon": (g.oqituvchi.telefon or None) if g.oqituvchi else None,
            }
            for g in farzand.talaba_guruhlari.filter(faol=True).select_related("oqituvchi").order_by("name")
        ]
        return Response(data)
