from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import talaba_statistikasi


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
        return Response(talaba_statistikasi(farzand))
