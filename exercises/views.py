from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Bolim,
    LimitTopUp,
    MashqYechim,
    korinadigan_mashqlar,
    kunlik_limit_holati,
)


def savollar_talaba_uchun(savollar):
    """B3.2: to'g'ri javoblarni olib tashlab, talabaga yuboriladigan ko'rinish."""
    return [{k: v for k, v in s.items() if k != "togri"} for s in savollar]


class MashqListView(APIView):
    """Talabaga ko'rinadigan mashqlar ro'yxati (savollarsiz)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = korinadigan_mashqlar(request.user)
        bolim = request.query_params.get("bolim")
        if bolim:
            qs = qs.filter(bolim=bolim)
        return Response(
            [
                {"id": m.id, "name": m.name, "bolim": m.bolim, "tur": m.tur}
                for m in qs
            ]
        )


class MashqDetailView(APIView):
    """Bitta mashq — savollar 'togri'siz (B3.2).

    Audio to'g'ridan-to'g'ri media URL sifatida BERILMAYDI — faqat
    autentifikatsiyalangan stream endpoint orqali (B3.2: ochiq havola yo'q).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        mashq = get_object_or_404(korinadigan_mashqlar(request.user), pk=pk)
        return Response(
            {
                "id": mashq.id,
                "name": mashq.name,
                "bolim": mashq.bolim,
                "tur": mashq.tur,
                "matn": mashq.matn,
                "audio_url": (
                    f"/api/mashqlar/{mashq.id}/audio/" if mashq.audio_fayl else None
                ),
                "rasm_url": mashq.rasm.url if mashq.rasm else None,
                "savollar": savollar_talaba_uchun(mashq.savollar),
            }
        )


class MashqAudioView(APIView):
    """Audio stream — faqat autentifikatsiyalangan va ko'rish huquqi bor
    foydalanuvchiga (B3.2). Yuklab olish emas, inline eshitish uchun."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        mashq = get_object_or_404(korinadigan_mashqlar(request.user), pk=pk)
        if not mashq.audio_fayl:
            raise Http404
        javob = FileResponse(mashq.audio_fayl.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class MashqYechishView(APIView):
    """Javob yuborish — kunlik limit shu yerda tekshiriladi (B4.1)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        mashq = get_object_or_404(korinadigan_mashqlar(request.user), pk=pk)
        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, list):
            return Response({"detail": "javoblar ro'yxati majburiy"}, status=400)

        holat = kunlik_limit_holati(request.user, mashq.bolim)
        if holat[mashq.tur]["qolgan"] <= 0:
            return Response(
                {
                    "detail": (
                        "Bugungi limit tugadi. 500 so'm evaziga har turdan "
                        "+1 ta ochishingiz mumkin."
                    ),
                    "limit": holat,
                },
                status=429,
            )

        yechim = MashqYechim.yechish(request.user, mashq, javoblar)
        return Response(
            {
                "ball": yechim.ball,
                "jami": yechim.jami,
                "natijalar": yechim.natijalar,
            }
        )


class LimitHolatiView(APIView):
    """Bugungi limit holati (ikkala bo'lim bo'yicha)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                str(b): kunlik_limit_holati(request.user, b)
                for b in (Bolim.LISTENING, Bolim.READING)
            }
        )


class LimitTopUpView(APIView):
    """Limit to'ldirish (+har turdan 1). DIQQAT: to'lov tizimi 2-fazada —
    hozircha bu endpoint to'lovsiz yaratadi (test rejimi)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        bolim = request.data.get("bolim")
        if bolim not in Bolim.values:
            return Response({"detail": "bolim: listening yoki reading"}, status=400)
        LimitTopUp.objects.create(talaba=request.user, bolim=bolim)
        return Response(
            {"detail": "+1 har turga qo'shildi (bugunga)",
             "limit": kunlik_limit_holati(request.user, bolim)}
        )
