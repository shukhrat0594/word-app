import logging

from django.conf import settings
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SpeakingTekshiruv, WritingTekshiruv
from .providers import (
    GEMINI_MODEL,
    GEMINI_MODEL_TANLOVLARI,
    GeminiProvider,
    ProviderXatosi,
    gemini_provider_ol,
    provider_tanla,
    writing_provider_ol,
)

logger = logging.getLogger(__name__)


def ai_xatosi_javobi(e, kontekst):
    """AI chaqiruvidagi KUTILMAGAN xato uchun javob (2026-07-26).

    Nega kerak: avval faqat `ProviderXatosi` ushlanardi, SDK'ning o'z
    xatolari (429 kunlik limit, 400, tarmoq uzilishi, R2'dagi yo'q rasm)
    esa umuman ushlanmasdan 500 ga aylanardi. 500 javobida DRF `detail`
    bermaydi, frontend esa `detail` bo'lmasa generik "Xatolik yuz berdi,
    qayta urinib ko'ring" ko'rsatadi — natijada haqiqiy sabab na talabaga,
    na logga chiqmasdi.

    Xato matni foydalanuvchiga BERILMAYDI (unda kalit/ichki manzil bo'lishi
    mumkin) — faqat sinf nomi beriladi, to'liq traceback logga tushadi."""
    logger.exception("%s — AI baholashda kutilmagan xato", kontekst)
    return Response(
        {
            "detail": f"AI xizmatida kutilmagan xato ({type(e).__name__}). "
            f"Birozdan so'ng qayta urinib ko'ring — muammo takrorlansa "
            f"administratorga xabar bering."
        },
        status=502,
    )


def _tanlangan_providerlar(request):
    """Frontend `model` maydoni bo'yicha bitta yoki ikkita (modelKaliti,
    provider) juftligini qaytaradi. `model` yuborilmasa — eski xatti-harakat
    (markaz sozlamasidagi provider) saqlanadi (orqaga moslik uchun)."""
    model_kaliti = request.data.get("model")
    if not model_kaliti:
        return [(None, provider_tanla(request.user))]
    if model_kaliti == "both":
        return [(k, gemini_provider_ol(k)) for k in GEMINI_MODEL_TANLOVLARI]
    return [(model_kaliti, gemini_provider_ol(model_kaliti))]


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
                # `with` — deskriptor yopilishi uchun (2026-07-26): ochiq
                # qolgan fayl Windows'da o'chirilmaydi, R2'da ulanish oqadi.
                with mashq.rasm.open("rb") as f:
                    return f.read(), "image/png"
            return None, None

        grafik_b64 = request.data.get("grafik_rasm")
        if grafik_b64:
            # 2026-07-27: MIME avval har doim "image/png" deb qattiq yozilgan
            # edi. "O'z mavzuyim" bo'limida talaba o'z faylini yuklaydi va u
            # JPEG bo'lishi mumkin — noto'g'ri MIME bilan yuborsak AI rasmni
            # o'qiy olmasligi mumkin. Endi frontend `grafik_mime` yuboradi,
            # faqat oq ro'yxatdagi qiymat qabul qilinadi (yuborilmasa —
            # avvalgidek PNG, orqaga moslik uchun).
            mime = request.data.get("grafik_mime") or "image/png"
            if mime not in ("image/png", "image/jpeg", "image/webp"):
                mime = "image/png"
            try:
                return base64.b64decode(grafik_b64), mime
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

        # 2026-08-15: AI chaqirishdan OLDIN talabaning matnini "kutilmoqda"
        # holatida saqlab qo'yamiz — AI xato bersa ham matn yo'qolmaydi.
        tekshiruv = WritingTekshiruv.objects.create(
            talaba=request.user,
            matn=matn,
            holat=WritingTekshiruv.Holat.KUTILMOQDA,
        )

        try:
            # 2026-07-29(7): Task 1/Task 2 ENDI avtomatik turli model
            # bilan tekshiriladi (frontend "model" tanlovidan mustaqil) —
            # qarang assessment/providers.py:writing_provider_ol.
            provider = writing_provider_ol(tur)
            baho = provider.writing_baholash(
                matn, savol_matni=savol_matni, tur=tur, rasm_bytes=rasm_bytes, rasm_mime=rasm_mime
            )
            tekshiruv.natija = baho["natija"]
            tekshiruv.task_type = str(baho["natija"].get("task_type", ""))
            tekshiruv.overall_band = baho["natija"].get("overall_band")
            tekshiruv.provider = baho["provider"]
            tekshiruv.model = baho["model"]
            tekshiruv.input_tokens = baho["input_tokens"]
            tekshiruv.output_tokens = baho["output_tokens"]
            tekshiruv.holat = WritingTekshiruv.Holat.TAYYOR
            tekshiruv.save()
            natijalar = [{"model_kaliti": None, "id": tekshiruv.id, "natija": baho["natija"]}]
        except ProviderXatosi as e:
            tekshiruv.holat = WritingTekshiruv.Holat.XATO
            tekshiruv.save(update_fields=["holat"])
            return Response({"detail": str(e)}, status=502)
        except Exception as e:
            tekshiruv.holat = WritingTekshiruv.Holat.XATO
            tekshiruv.save(update_fields=["holat"])
            return ai_xatosi_javobi(e, f"Writing tekshiruvi (talaba id={request.user.id})")

        return Response({"natijalar": natijalar})


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

        # 2026-08-15: har bir model uchun AI chaqirishdan OLDIN talabaning
        # matnini "kutilmoqda" holatida saqlab qo'yamiz.
        tekshiruv = None
        try:
            providerlar = _tanlangan_providerlar(request)
            natijalar = []
            for model_kaliti, provider in providerlar:
                tekshiruv = SpeakingTekshiruv.objects.create(
                    talaba=request.user,
                    rejim=SpeakingTekshiruv.Rejim.MATN,
                    matn=matn,
                    holat=SpeakingTekshiruv.Holat.KUTILMOQDA,
                )
                baho = provider.speaking_matn_baholash(matn, savol_matni=savol_matni, tur=tur)
                tekshiruv.natija = baho["natija"]
                tekshiruv.part_type = str(baho["natija"].get("part_type", ""))
                tekshiruv.overall_band = baho["natija"].get("overall_band_no_pronunciation")
                tekshiruv.provider = baho["provider"]
                tekshiruv.model = baho["model"]
                tekshiruv.input_tokens = baho["input_tokens"]
                tekshiruv.output_tokens = baho["output_tokens"]
                tekshiruv.holat = SpeakingTekshiruv.Holat.TAYYOR
                tekshiruv.save()
                natijalar.append(
                    {"model_kaliti": model_kaliti, "id": tekshiruv.id, "natija": baho["natija"]}
                )
        except ProviderXatosi as e:
            if tekshiruv is not None and tekshiruv.holat == SpeakingTekshiruv.Holat.KUTILMOQDA:
                tekshiruv.holat = SpeakingTekshiruv.Holat.XATO
                tekshiruv.save(update_fields=["holat"])
            return Response({"detail": str(e)}, status=502)
        except Exception as e:
            if tekshiruv is not None and tekshiruv.holat == SpeakingTekshiruv.Holat.KUTILMOQDA:
                tekshiruv.holat = SpeakingTekshiruv.Holat.XATO
                tekshiruv.save(update_fields=["holat"])
            return ai_xatosi_javobi(e, f"Speaking tekshiruvi (talaba id={request.user.id})")

        return Response({"natijalar": natijalar})


class SpeakingTranskripsiyaView(APIView):
    """Faqat TRANSKRIPSIYA (baholashsiz), 2026-07-30: "IELTS testlari"/"AI
    mashqlari" bo'limidagi HAQIQIY imtihon oqimi (`ImtihonYozGap.jsx`)
    barcha Part 1/2/3'ni BITTA so'rovda ('/api/imtihon/testlar/{id}/
    yozgap-tekshirish/') baholaydi — shuning uchun bu yerda faqat audio ->
    matn o'giriladi, natija talabaning matn maydoniga qo'yiladi (u xohlasa
    tahrirlaydi), keyin MAVJUD tekshirish oqimi O'ZGARISHSIZ ishlaydi.
    Hech qanday `SpeakingTekshiruv` yozuvi SAQLANMAYDI — bu faqat
    yordamchi vosita."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio = request.FILES.get("audio")
        if not audio:
            return Response({"detail": "audio fayli majburiy"}, status=400)
        try:
            kalit = getattr(settings, "GEMINI_API_KEY", "")
            if not kalit:
                raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
            provider = GeminiProvider(kalit, model=GEMINI_MODEL)
            transkript = provider.audio_transkripsiya_qil(
                audio.read(), audio.content_type or "audio/webm"
            )
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)
        except Exception as e:
            return ai_xatosi_javobi(e, f"Audio transkripsiya (talaba id={request.user.id})")
        return Response({"transkript": transkript})


class SpeakingAudioView(APIView):
    """Speaking — Mikrofon rejimi (2026-07-29): talaba brauzerda ovoz
    yozib oladi, audio bu yerga yuboriladi -> Gemini transkripsiya qiladi
    -> xuddi Matn rejimidagi 3 mezon (Pronunciation'siz) bilan baholanadi.

    Bu — Azure Pronunciation Assessment EMAS ("Tezkor tahlil" nomi bilan
    rejalashtirilgan, Azure hisobi kerak) — foydalanuvchi ANIQ so'ragan
    sodda variant: "faqat textga o'girib textni tekshirish". Shuning
    uchun `pronunciation` maydoni bo'sh qoladi, `overall_band` esa Matn
    rejimi bilan bir xil (Pronunciation'siz) hisoblanadi.

    Har doim `gemini-3.1-flash-lite` ishlatiladi (frontend "model"
    tanlovidan mustaqil) — Claude audio-inputni qo'llab-quvvatlamaydi,
    va bu Writing Task1/Task2 uchun tanlangan modellardan alohida."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio = request.FILES.get("audio")
        if not audio:
            return Response({"detail": "audio fayli majburiy"}, status=400)

        savol_matni = (request.data.get("savol_matni") or "").strip()
        tur = request.data.get("tur") or "part1"

        # 2026-08-15: AI chaqirishdan OLDIN xom audio faylni "kutilmoqda"
        # holatida saqlab qo'yamiz — AI (transkripsiya yoki baholash) xato
        # bersa ham talabaning audiosi yo'qolmaydi (matn hali yo'q, chunki
        # transkripsiya AI natijasining bir qismi).
        audio_bytes = audio.read()
        tekshiruv = SpeakingTekshiruv.objects.create(
            talaba=request.user,
            rejim=SpeakingTekshiruv.Rejim.TEZKOR,
            matn="",
            holat=SpeakingTekshiruv.Holat.KUTILMOQDA,
        )
        audio.seek(0)
        tekshiruv.audio_fayl.save(f"{tekshiruv.id}.webm", audio, save=True)

        try:
            kalit = getattr(settings, "GEMINI_API_KEY", "")
            if not kalit:
                raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
            provider = GeminiProvider(kalit, model=GEMINI_MODEL)
            baho = provider.speaking_audio_baholash(
                audio_bytes, audio.content_type or "audio/webm",
                savol_matni=savol_matni, tur=tur,
            )
            tekshiruv.matn = baho["transkript"]
            tekshiruv.natija = baho["natija"]
            tekshiruv.part_type = str(baho["natija"].get("part_type", ""))
            tekshiruv.overall_band = baho["natija"].get("overall_band_no_pronunciation")
            tekshiruv.provider = baho["provider"]
            tekshiruv.model = baho["model"]
            tekshiruv.input_tokens = baho["input_tokens"]
            tekshiruv.output_tokens = baho["output_tokens"]
            tekshiruv.holat = SpeakingTekshiruv.Holat.TAYYOR
            tekshiruv.save()
        except ProviderXatosi as e:
            tekshiruv.holat = SpeakingTekshiruv.Holat.XATO
            tekshiruv.save(update_fields=["holat"])
            return Response({"detail": str(e)}, status=502)
        except Exception as e:
            tekshiruv.holat = SpeakingTekshiruv.Holat.XATO
            tekshiruv.save(update_fields=["holat"])
            return ai_xatosi_javobi(e, f"Speaking audio tekshiruvi (talaba id={request.user.id})")

        return Response(
            {
                "transkript": baho["transkript"],
                "natija": baho["natija"],
                "id": tekshiruv.id,
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
                    "matn": t.matn,
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
