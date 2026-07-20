import json

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Markaz, User
from accounts.permissions import owner_mi

from .models import (
    Bolim,
    ImtihonTest,
    LimitTopUp,
    Mashq,
    MashqYechim,
    TestQismi,
    TestYechim,
    band_hisobla,
    javoblarni_tekshir,
    korinadigan_mashqlar,
    korinadigan_testlar,
    kunlik_limit_holati,
)


def _mashq_admin_mi(user):
    return owner_mi(user) or user.role == User.Role.ADMIN


def _mashq_qisqa(m):
    return {
        "id": m.id,
        "name": m.name,
        "bolim": m.bolim,
        "tur": m.tur,
        "korinish": m.korinish,
        "matn": m.matn,
        "namuna_javob": m.namuna_javob,
        "audio_url": f"/api/mashqlar/{m.id}/audio/" if m.audio_fayl else None,
        "rasm_url": f"/api/mashqlar/{m.id}/rasm/" if m.rasm else None,
        "savollar": m.savollar,
        "created_at": m.created_at,
    }


class MashqBoshqaruvView(APIView):
    """Owner/admin uchun — mashqlar ro'yxati (to'liq, savollar bilan) va
    yaratish. Bitta so'rov = bitta mashq; bir nechtasini kiritish uchun
    frontend shu endpointga ketma-ket so'rov yuboradi ("bulk" forma)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qs = Mashq.objects.all().order_by("-created_at")
        bolim = request.query_params.get("bolim")
        if bolim:
            qs = qs.filter(bolim=bolim)
        return Response([_mashq_qisqa(m) for m in qs[:300]])

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = request.user.markaz or Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        try:
            savollar = json.loads(request.data.get("savollar") or "[]")
        except json.JSONDecodeError:
            return Response({"detail": "savollar noto'g'ri JSON"}, status=400)

        mashq = Mashq(
            name=request.data.get("name", ""),
            bolim=request.data.get("bolim", ""),
            tur=request.data.get("tur", ""),
            markaz=markaz,
            korinish=request.data.get("korinish", "private"),
            matn=request.data.get("matn", ""),
            namuna_javob=request.data.get("namuna_javob", ""),
            savollar=savollar,
        )
        if request.FILES.get("audio_fayl"):
            mashq.audio_fayl = request.FILES["audio_fayl"]
        if request.FILES.get("rasm"):
            mashq.rasm = request.FILES["rasm"]

        try:
            mashq.full_clean()
        except ValidationError as e:
            return Response(e.message_dict, status=400)
        mashq.save()

        return Response(_mashq_qisqa(mashq), status=201)


class MashqBoshqaruvDetailView(APIView):
    """Owner/admin uchun — mashqni o'chirish yoki tahrirlash.

    PATCH — JSON orqali matn/savollar bilan yaratilgan mashqqa keyinroq
    audio/rasm biriktirish uchun (yoki istalgan maydonni yangilash uchun).
    Faqat yuborilgan maydonlar o'zgaradi.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(Mashq, pk=pk)

        for maydon in ("name", "bolim", "tur", "korinish", "matn", "namuna_javob"):
            if maydon in request.data:
                setattr(mashq, maydon, request.data[maydon])
        if "savollar" in request.data:
            try:
                mashq.savollar = json.loads(request.data["savollar"])
            except json.JSONDecodeError:
                return Response({"detail": "savollar noto'g'ri JSON"}, status=400)
        if request.FILES.get("audio_fayl"):
            mashq.audio_fayl = request.FILES["audio_fayl"]
        if request.FILES.get("rasm"):
            mashq.rasm = request.FILES["rasm"]

        try:
            mashq.full_clean()
        except ValidationError as e:
            return Response(e.message_dict, status=400)
        mashq.save()

        return Response(_mashq_qisqa(mashq))

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(Mashq, pk=pk)
        mashq.delete()
        return Response(status=204)


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
                "namuna_javob": mashq.namuna_javob,
                "audio_url": (
                    f"/api/mashqlar/{mashq.id}/audio/" if mashq.audio_fayl else None
                ),
                "rasm_url": (
                    f"/api/mashqlar/{mashq.id}/rasm/" if mashq.rasm else None
                ),
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


class MashqRasmView(APIView):
    """Mashq rasmi (masalan Map Labelling xaritasi) — /media/ ochiq emas
    (faqat markaz logolari ochiq, B3.2), shuning uchun audio kabi
    autentifikatsiyalangan stream orqali beriladi."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        mashq = get_object_or_404(korinadigan_mashqlar(request.user), pk=pk)
        if not mashq.rasm:
            raise Http404
        javob = FileResponse(mashq.rasm.open("rb"))
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


def _qism_admin_dict(q):
    return {
        "id": q.id,
        "tartib": q.tartib,
        "sarlavha": q.sarlavha,
        "yoriqnoma": q.yoriqnoma,
        "matn": q.matn,
        "audio_url": f"/api/imtihon/qism/{q.id}/audio/" if q.audio_fayl else None,
        "savollar": q.savollar,
    }


def _test_admin_dict(t):
    return {
        "id": t.id,
        "name": t.name,
        "bolim": t.bolim,
        "korinish": t.korinish,
        "qismlar": [_qism_admin_dict(q) for q in t.qismlar.all()],
        "created_at": t.created_at,
    }


def _qism_talaba_dict(q):
    return {
        "id": q.id,
        "tartib": q.tartib,
        "sarlavha": q.sarlavha,
        "yoriqnoma": q.yoriqnoma,
        "matn": q.matn,
        "audio_url": f"/api/imtihon/qism/{q.id}/audio/" if q.audio_fayl else None,
        "savollar": savollar_talaba_uchun(q.savollar),
    }


def _test_talaba_dict(t):
    return {
        "id": t.id,
        "name": t.name,
        "bolim": t.bolim,
        "qismlar": [_qism_talaba_dict(q) for q in t.qismlar.all()],
    }


class ImtihonBoshqaruvView(APIView):
    """Owner/admin uchun — to'liq testlar ro'yxati va yaratish (qismlari
    bilan birga, bitta JSON so'rovda). Audio har qismga keyinroq
    TestQismiAudioBoshqaruvView orqali biriktiriladi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qs = ImtihonTest.objects.all().order_by("-created_at")
        bolim = request.query_params.get("bolim")
        if bolim:
            qs = qs.filter(bolim=bolim)
        return Response([_test_admin_dict(t) for t in qs[:100]])

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = request.user.markaz or Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        name = request.data.get("name", "")
        bolim = request.data.get("bolim", "")
        korinish = request.data.get("korinish", "private")
        qismlar_data = request.data.get("qismlar") or []
        if not name or bolim not in (Bolim.READING, Bolim.LISTENING):
            return Response({"detail": "name va bolim (reading/listening) majburiy"}, status=400)
        if not isinstance(qismlar_data, list) or not qismlar_data:
            return Response({"detail": "kamida bitta qism kerak"}, status=400)

        test = ImtihonTest.objects.create(name=name, bolim=bolim, markaz=markaz, korinish=korinish)
        for i, q in enumerate(qismlar_data, start=1):
            TestQismi.objects.create(
                test=test,
                tartib=q.get("tartib") or i,
                sarlavha=q.get("sarlavha", ""),
                yoriqnoma=q.get("yoriqnoma", ""),
                matn=q.get("matn", ""),
                savollar=q.get("savollar") or [],
            )
        return Response(_test_admin_dict(test), status=201)


class ImtihonBoshqaruvDetailView(APIView):
    """Owner/admin uchun — to'liq testni butunlay o'chirish."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        test.delete()
        return Response(status=204)


class TestQismiAudioBoshqaruvView(APIView):
    """Owner/admin uchun — bitta test qismiga audio biriktirish (listening)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qism = get_object_or_404(TestQismi, pk=pk)
        if request.FILES.get("audio_fayl"):
            qism.audio_fayl = request.FILES["audio_fayl"]
            qism.save()
        return Response(_qism_admin_dict(qism))


class ImtihonListView(APIView):
    """Talabaga ko'rinadigan to'liq testlar ro'yxati (nomi, bo'limi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = korinadigan_testlar(request.user)
        bolim = request.query_params.get("bolim")
        if bolim:
            qs = qs.filter(bolim=bolim)
        return Response([{"id": t.id, "name": t.name, "bolim": t.bolim} for t in qs])


class ImtihonDetailView(APIView):
    """Bitta to'liq test — barcha qismlar, savollar 'togri'siz."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        test = get_object_or_404(korinadigan_testlar(request.user), pk=pk)
        return Response(_test_talaba_dict(test))


class TestQismAudioView(APIView):
    """Test qismi audiosi — autentifikatsiyalangan stream (B3.2 bilan bir xil)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        qism = get_object_or_404(
            TestQismi, pk=pk, test__in=korinadigan_testlar(request.user)
        )
        if not qism.audio_fayl:
            raise Http404
        javob = FileResponse(qism.audio_fayl.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class ImtihonYechishView(APIView):
    """Butun testga javob yuborish — flat ro'yxat, barcha qismlar bo'yicha
    uzluksiz tartibda. Kunlik limitga bog'liq emas (mustaqil, cheklovsiz)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        test = get_object_or_404(korinadigan_testlar(request.user), pk=pk)
        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, list):
            return Response({"detail": "javoblar ro'yxati majburiy"}, status=400)

        barcha_savollar = []
        for qism in test.qismlar.all():
            barcha_savollar.extend(qism.savollar)

        natija = javoblarni_tekshir(barcha_savollar, javoblar)
        band = band_hisobla(natija["ball"], natija["jami"], test.bolim)
        TestYechim.objects.create(
            talaba=request.user,
            test=test,
            javoblar=javoblar,
            ball=natija["ball"],
            jami=natija["jami"],
            natijalar=natija["natijalar"],
            band=band,
        )
        return Response(
            {
                "ball": natija["ball"],
                "jami": natija["jami"],
                "natijalar": natija["natijalar"],
                "band": band,
            }
        )
