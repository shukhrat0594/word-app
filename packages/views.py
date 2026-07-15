from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MUDDATLAR, PAKETLAR, PaketXarid


class PaketKatalogView(APIView):
    """Paket katalogi — turlar, narxlar, muddat tanlovlari."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "paketlar": [
                    {"turi": k, "writing": v["w"], "speaking": v["s"], "narx": v["narx"]}
                    for k, v in PAKETLAR.items()
                ],
                "muddatlar": list(MUDDATLAR),
                "eslatma": "Muddat narxga ta'sir qilmaydi — faqat foydalanish oynasi",
            }
        )


class PaketXaridView(APIView):
    """Paket xarid qilish. DIQQAT: to'lov 2-fazada — hozircha to'lovsiz (test)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        paket_turi = request.data.get("paket_turi")
        muddat = request.data.get("muddat_kun")

        if paket_turi not in PAKETLAR:
            return Response(
                {"detail": f"paket_turi: {' yoki '.join(PAKETLAR)}"}, status=400
            )
        if muddat not in MUDDATLAR:
            return Response(
                {"detail": f"muddat_kun: {', '.join(map(str, MUDDATLAR))}"}, status=400
            )

        xarid = PaketXarid.xarid_qil(request.user, paket_turi, muddat)
        return Response(
            {
                "id": xarid.id,
                "paket_turi": xarid.paket_turi,
                "narx": xarid.narx,
                "muddat_kun": xarid.muddat_kun,
                "tugash_sanasi": xarid.tugash_sanasi,
                "w_qolgan": xarid.w_qolgan,
                "s_qolgan": xarid.s_qolgan,
            }
        )


class MeningPaketlarimView(APIView):
    """Talabaning paketlari — aktiv va o'tganlar."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            [
                {
                    "id": p.id,
                    "paket_turi": p.paket_turi,
                    "narx": p.narx,
                    "boshlanish": p.boshlanish,
                    "tugash_sanasi": p.tugash_sanasi,
                    "w_qolgan": p.w_qolgan,
                    "s_qolgan": p.s_qolgan,
                    "aktivmi": p.aktivmi,
                }
                for p in request.user.paket_xaridlar.all()
            ]
        )
