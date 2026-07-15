from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SpeakingTekshiruv, WritingTekshiruv
from .providers import ProviderXatosi, provider_tanla


class WritingTekshirishView(APIView):
    """Insho/xat yuboriladi -> AI baholaydi -> natija saqlanadi va qaytadi.

    B8.1: talaba Task turini tanlamaydi — AI kontekstdan aniqlaydi.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        matn = (request.data.get("matn") or "").strip()
        if len(matn.split()) < 20:
            return Response(
                {"detail": "Matn juda qisqa — kamida 20 so'z yuboring"},
                status=400,
            )

        try:
            provider = provider_tanla(request.user)
            baho = provider.writing_baholash(matn)
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)

        natija = baho["natija"]
        tekshiruv = WritingTekshiruv.objects.create(
            talaba=request.user,
            matn=matn,
            natija=natija,
            task_type=str(natija.get("task_type", "")),
            overall_band=natija.get("overall_band"),
            provider=baho["provider"],
            model=baho["model"],
            input_tokens=baho["input_tokens"],
            output_tokens=baho["output_tokens"],
        )

        # B9: aktiv paket bo'lsa, undan 1 ta Writing yechiladi.
        # Paket bo'lmasa — alohida to'lov (600 so'm, to'lov tizimi 2-fazada).
        from packages.models import paketdan_ishlat

        paket = paketdan_ishlat(request.user, "w")
        return Response(
            {
                "id": tekshiruv.id,
                "natija": natija,
                "paketdan": paket is not None,
                "paket_w_qolgan": paket.w_qolgan if paket else None,
            }
        )


class SpeakingMatnView(APIView):
    """Speaking — Matn rejimi (600 so'm): matn -> 3 mezon (Pronunciation'siz).

    B8.1: talaba Part turini tanlamaydi — AI kontekstdan aniqlaydi.
    Tezkor tahlil (audio+Azure) — Azure hisobi ochilganda alohida endpoint.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        matn = (request.data.get("matn") or "").strip()
        if len(matn.split()) < 20:
            return Response(
                {"detail": "Matn juda qisqa — kamida 20 so'z yuboring"},
                status=400,
            )

        try:
            provider = provider_tanla(request.user)
            baho = provider.speaking_matn_baholash(matn)
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)

        natija = baho["natija"]
        tekshiruv = SpeakingTekshiruv.objects.create(
            talaba=request.user,
            rejim=SpeakingTekshiruv.Rejim.MATN,
            matn=matn,
            natija=natija,
            part_type=str(natija.get("part_type", "")),
            overall_band=natija.get("overall_band_no_pronunciation"),
            provider=baho["provider"],
            model=baho["model"],
            input_tokens=baho["input_tokens"],
            output_tokens=baho["output_tokens"],
        )

        # B9: aktiv paket bo'lsa, undan 1 ta Speaking yechiladi
        from packages.models import paketdan_ishlat

        paket = paketdan_ishlat(request.user, "s")
        return Response(
            {
                "id": tekshiruv.id,
                "natija": natija,
                "paketdan": paket is not None,
                "paket_s_qolgan": paket.s_qolgan if paket else None,
            }
        )


class SpeakingTarixView(APIView):
    """Talabaning o'z Speaking tekshiruvlari tarixi (B3.2: har doim ochiq)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SpeakingTekshiruv.objects.filter(talaba=request.user)[:50]
        return Response(
            [
                {
                    "id": t.id,
                    "rejim": t.rejim,
                    "part_type": t.part_type,
                    "overall_band": t.overall_band,
                    "created_at": t.created_at,
                    "natija": t.natija,
                }
                for t in qs
            ]
        )


class WritingTarixView(APIView):
    """Talabaning o'z tekshiruvlari tarixi (B3.2: har doim ochiq)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = WritingTekshiruv.objects.filter(talaba=request.user)[:50]
        return Response(
            [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "overall_band": t.overall_band,
                    "created_at": t.created_at,
                    "natija": t.natija,
                }
                for t in qs
            ]
        )
