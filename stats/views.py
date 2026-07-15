from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import talaba_statistikasi


class MeningStatistikamView(APIView):
    """Talabaning o'z statistikasi (B6). Har doim ochiq (B3.2)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(talaba_statistikasi(request.user))
