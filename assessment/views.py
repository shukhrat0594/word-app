from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SpeakingTekshiruv, WritingTekshiruv
from .providers import ProviderXatosi, provider_tanla


class WritingTekshirishView(APIView):
    """Insho/xat yuboriladi -> AI baholaydi -> natija saqlanadi va qaytadi.

    2026-07-20 (v5): frontend `savol_matni` (mashqning asl savol matni) va
    `tur` (task1/task2) ni ham yuboradi — AI endi mavzuni matndan taxmin
    qilmaydi, mavzuga mos-kelishini ANIQ tekshiradi (avval mavjud bug:
    mavzudan chetga chiqqan javoblar ham yuqori ball olar edi).
    """

    permission_classes = [IsAuthenticated]

    def _grafik_rasmini_ol(self, request):
        """Writing Task 1 grafigini AI'ga rasm sifatida yuborish uchun bytes
        qaytaradi — "IELTS testlari" bo'limidan `mashq_id` (Mashq.rasm fayli
        bo'lsa) yoki `grafik_rasm` (frontendda SVG'dan aylantirilgan base64
        PNG) yuborilishi mumkin."""
        import base64

        mashq_id = request.data.get("mashq_id")
        if mashq_id:
            from exercises.models import korinadigan_mashqlar

            mashq = korinadigan_mashqlar(request.user).filter(pk=mashq_id).first()
            if mashq and mashq.rasm:
                return mashq.rasm.read(), "image/png"
            return None, None

        grafik_b64 = request.data.get("grafik_rasm")
        if grafik_b64:
            try:
                return base64.b64decode(grafik_b64), "image/png"
            except (ValueError, TypeError):
                return None, None
        return None, None

    def post(self, request):
        matn = (request.data.get("matn") or "").strip()
        if len(matn.split()) < 20:
            return Response(
                {"detail": "Matn juda qisqa — kamida 20 so'z yuboring"},
                status=400,
            )

        rasm_bytes, rasm_mime = self._grafik_rasmini_ol(request)
        savol_matni = (request.data.get("savol_matni") or "").strip()
        tur = request.data.get("tur") or "task2"

        try:
            provider = provider_tanla(request.user)
            baho = provider.writing_baholash(
                matn, savol_matni=savol_matni, tur=tur, rasm_bytes=rasm_bytes, rasm_mime=rasm_mime
            )
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
        # Paket bo'lmasa — alohida to'lov (narx: config/narxlar.WRITING_TEZKOR,
        # to'lov tizimi 2-fazada).
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

    2026-07-20 (v5): Writing bilan bir xil sababga ko'ra, frontend
    `savol_matni` (mashqning asl savol/cue card matni) va `tur`
    (part1/part2) ni ham yuboradi — AI mavzuni taxmin qilmaydi.
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

        savol_matni = (request.data.get("savol_matni") or "").strip()
        tur = request.data.get("tur") or "part1"

        try:
            provider = provider_tanla(request.user)
            baho = provider.speaking_matn_baholash(matn, savol_matni=savol_matni, tur=tur)
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
                    "audio_url": t.audio_fayl.url if t.audio_fayl else None,
                }
                for t in qs
            ]
        )


class TarixView(APIView):
    """Talabaning barcha mashq tarixi — Writing + Speaking bitta ro'yxatda,
    sana bo'yicha tartiblangan (B3.2: har doim faqat o'ziniki, ochiq).

    Speaking'da audio fayl bo'lsa (Tezkor tahlil rejimi) — `audio_url` bilan
    birga qaytadi, frontend audio pleyer ko'rsatishi uchun.

    ESLATMA (2026-07-18): Tezkor tahlil (audio) hali qurilmagani uchun
    `audio_fayl` amalda doim bo'sh — shuning uchun `.url` to'g'ridan-to'g'ri
    ishlatilgan (media serving hozircha yo'q). B8-audio bosqichi qurilganda
    B3.2 qoidasiga ko'ra bu **authenticated stream endpoint**ga
    (exercises.MashqAudioView kabi) almashtirilishi kerak — xom /media/ havola
    orqali emas.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        yozuvlar = []
        for t in WritingTekshiruv.objects.filter(talaba=request.user)[:100]:
            yozuvlar.append(
                {
                    "turi": "writing",
                    "id": t.id,
                    "sarlavha": t.task_type or "Writing",
                    "overall_band": t.overall_band,
                    "created_at": t.created_at,
                    "natija": t.natija,
                    "audio_url": None,
                }
            )
        for t in SpeakingTekshiruv.objects.filter(talaba=request.user)[:100]:
            yozuvlar.append(
                {
                    "turi": "speaking",
                    "id": t.id,
                    "sarlavha": t.part_type or "Speaking",
                    "rejim": t.rejim,
                    "overall_band": t.overall_band,
                    "created_at": t.created_at,
                    "natija": t.natija,
                    "audio_url": t.audio_fayl.url if t.audio_fayl else None,
                }
            )
        yozuvlar.sort(key=lambda y: y["created_at"], reverse=True)
        return Response(yozuvlar[:100])


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
