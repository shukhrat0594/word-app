from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from audit.utils import logla
from exercises.models import javoblarni_tekshir

from .models import KursMashq, KursMashqYechim, KursProgress, KursTugun

OTISH_FOIZ = 0.6


def _kurslar_korinadimi(user):
    """Kurslar bo'limi — "oddiy foydalanuvchi"dan boshqa hamma
    (talaba/o'qituvchi/admin/owner) ko'radi (IELTS testlari bilan bir xil qoida)."""
    return user.role != User.Role.ODDIY


def _mashq_admin_mi(user):
    return owner_mi(user) or user.role == User.Role.ADMIN


def _unit_otildimi(user, unit_tugun):
    """Talaba shu Unit'ning BARCHA bo'limlaridagi (Grammar/Vocabulary/
    Reading/Listening/Speaking-Writing/Everyday English) mashqlaridan
    jami OTISH_FOIZ (60%) dan ko'p ball olganmi — Unit'ning har bir
    bo'limiga qo'yilgan barcha mashqlarga javob yuborgan va o'rtacha ball
    yetarli bo'lishi shart (bitta maxsus "Test/Exam" bo'limi endi yo'q —
    2026-07-22, darslik bo'limlari real Headway strukturasiga moslashtirildi)."""
    mashqlar = list(KursMashq.objects.filter(tugun__parent_id=unit_tugun.id))
    if not mashqlar:
        return False
    jami_ball = 0
    jami_savol = 0
    for m in mashqlar:
        yechim = KursMashqYechim.objects.filter(talaba=user, mashq=m).order_by("-created_at").first()
        if not yechim:
            return False
        jami_ball += yechim.ball
        jami_savol += yechim.jami
    return jami_savol > 0 and (jami_ball / jami_savol) >= OTISH_FOIZ


def _unit_qulflanganmi(user, unit_tugun):
    """Faqat talaba uchun: shu Unit'dan oldingi (bir xil ota-tugun ostidagi,
    tartibi kichikroq) Unit hali o'tilmagan bo'lsa — qulflangan."""
    if user.role != User.Role.STUDENT:
        return False
    oldingi = (
        KursTugun.objects.filter(
            parent_id=unit_tugun.parent_id, unit_darsi=True, tartib__lt=unit_tugun.tartib
        )
        .order_by("-tartib")
        .first()
    )
    if not oldingi:
        return False
    return not _unit_otildimi(user, oldingi)


def _eng_yaqin_unit(tugun):
    """Berilgan tugunning eng yaqin unit_darsi=True ota-tuguni (o'zi hisobga
    olinmaydi) — yo'q bo'lsa None."""
    node = tugun.parent
    while node:
        if node.unit_darsi:
            return node
        node = node.parent
    return None


def _talaba_tugun_qulflanganmi(user, tugun):
    """Himoya qatlami: talaba uchun shu tugun (yoki uning eng yaqin Unit
    ota-tuguni) hali qulflanganmi — fayl/mashq amallarini to'g'ridan-to'g'ri
    ID orqali chaqirishga urinishdan himoyalaydi."""
    if user.role != User.Role.STUDENT:
        return False
    unit = tugun if tugun.unit_darsi else _eng_yaqin_unit(tugun)
    if not unit:
        return False
    return _unit_qulflanganmi(user, unit)


def _tugun_dict(tugun, user, bolalar_keshi, tugatgan_idlar, qulflangan=False):
    bolalar = bolalar_keshi.get(tugun.id, [])
    oxirgi_qatlammi = len(bolalar) == 0
    natija = {
        "id": tugun.id,
        "nomi": tugun.nomi,
        "ikonka": tugun.ikonka,
        "tez_kunda": tugun.tez_kunda,
        "unit_darsi": tugun.unit_darsi,
        "oxirgi_qatlammi": oxirgi_qatlammi,
        "qulflangan": qulflangan,
    }
    if qulflangan:
        return natija

    if oxirgi_qatlammi:
        natija["fayl_url"] = f"/api/kurslar/{tugun.id}/fayl/" if tugun.fayl else None
        mashqlar_soni = KursMashq.objects.filter(tugun=tugun).count()
        if mashqlar_soni:
            natija["mashqlar_soni"] = mashqlar_soni
        if user.role == User.Role.STUDENT:
            natija["tugallandimi"] = tugun.id in tugatgan_idlar
    else:
        children = []
        for b in bolalar:
            b_qulflangan = _unit_qulflanganmi(user, b) if b.unit_darsi else False
            children.append(_tugun_dict(b, user, bolalar_keshi, tugatgan_idlar, b_qulflangan))
        natija["children"] = children
    return natija


class KursDaraxtiView(APIView):
    """Kurslar bo'limining to'liq daraxti — talaba/admin/owner/teacher uchun.
    "Oddiy foydalanuvchi" ko'rmaydi (IELTS testlari bilan bir xil qoida)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        tugatgan_idlar = set()
        if request.user.role == User.Role.STUDENT:
            tugatgan_idlar = set(
                KursProgress.objects.filter(talaba=request.user).values_list("tugun_id", flat=True)
            )

        barcha = list(KursTugun.objects.all().order_by("tartib", "id"))
        bolalar_keshi = {}
        ildizlar = []
        for t in barcha:
            if t.parent_id:
                bolalar_keshi.setdefault(t.parent_id, []).append(t)
            else:
                ildizlar.append(t)

        if not ildizlar:
            return Response({"children": []})

        # "Kurslar" — yagona ildiz tugun, uni o'zini emas, farzandlarini qaytaramiz.
        ildiz = ildizlar[0]
        bolalar = bolalar_keshi.get(ildiz.id, [])
        return Response(
            {
                "id": ildiz.id,
                "nomi": ildiz.nomi,
                "children": [
                    _tugun_dict(b, request.user, bolalar_keshi, tugatgan_idlar) for b in bolalar
                ],
            }
        )


class KursFaylView(APIView):
    """Oxirgi qatlam tuguniga biriktirilgan fayl — autentifikatsiyalangan
    stream (B3.2 qoidasiga mos, xom /media/ orqali emas)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        if not tugun.fayl:
            raise Http404
        javob = FileResponse(tugun.fayl.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class KursTugunFaylBoshqaruvView(APIView):
    """Admin/owner uchun — oxirgi qatlam tuguniga fayl biriktirish/almashtirish."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response(
                {"detail": "Faqat oxirgi qatlam (farzandsiz) tugunga fayl biriktiriladi"},
                status=400,
            )
        fayl = request.FILES.get("fayl")
        if not fayl:
            return Response({"detail": "fayl majburiy"}, status=400)

        eski_bormi = bool(tugun.fayl)
        tugun.fayl = fayl
        tugun.save()

        yol = []
        node = tugun
        while node:
            yol.append(node.nomi)
            node = node.parent
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=" > ".join(reversed(yol)),
            ozgarishlar={"fayl": {"eski": "bor" if eski_bormi else "—", "yangi": "yangilandi"}},
        )
        return Response({"id": tugun.id, "fayl_url": f"/api/kurslar/{tugun.id}/fayl/"})


class KursTugunTugallandiView(APIView):
    """Talaba uchun — oxirgi qatlam tugunini tugallandi/tugallanmadi deb belgilaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != User.Role.STUDENT:
            return Response({"detail": "Faqat talaba uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response({"detail": "Faqat oxirgi qatlam belgilanadi"}, status=400)
        if _talaba_tugun_qulflanganmi(request.user, tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)

        mavjud = KursProgress.objects.filter(talaba=request.user, tugun=tugun).first()
        if mavjud:
            mavjud.delete()
            return Response({"tugallandimi": False})
        KursProgress.objects.create(talaba=request.user, tugun=tugun)
        return Response({"tugallandimi": True})


def _kurs_mashq_admin_dict(m):
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.rasm else None,
        "savollar": m.savollar,
    }


def _kurs_mashq_talaba_dict(m):
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.rasm else None,
        "savollar": [{k: v for k, v in s.items() if k != "togri"} for s in m.savollar],
    }


class KursMashqBoshqaruvView(APIView):
    """Admin/owner uchun — bitta tugunning mashqlari ro'yxati va yangi
    mashq(lar) qo'shish (JSON, bir nechtasi birga — "mashqlar" ro'yxati)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        return Response([_kurs_mashq_admin_dict(m) for m in tugun.mashqlar.all()])

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response(
                {"detail": "Faqat oxirgi qatlam (farzandsiz) tugunga mashq qo'shiladi"}, status=400
            )
        qatorlar = request.data.get("mashqlar")
        if not isinstance(qatorlar, list) or not qatorlar:
            return Response({"detail": "'mashqlar' ro'yxati majburiy"}, status=400)

        boshlangich = tugun.mashqlar.count()
        yaratilganlar = []
        for i, q in enumerate(qatorlar, start=1):
            savollar = q.get("savollar") or []
            if not isinstance(savollar, list) or not savollar:
                return Response({"detail": f"{i}-mashqda savollar bo'sh"}, status=400)
            m = KursMashq.objects.create(
                tugun=tugun,
                tartib=q.get("tartib") or boshlangich + i,
                matn=q.get("matn", ""),
                savollar=savollar,
            )
            yaratilganlar.append(m)

        yol = []
        node = tugun
        while node:
            yol.append(node.nomi)
            node = node.parent
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=" > ".join(reversed(yol)),
            snapshot={"yangi_mashqlar_soni": len(yaratilganlar)},
        )
        return Response([_kurs_mashq_admin_dict(m) for m in yaratilganlar], status=201)


class KursMashqDetailBoshqaruvView(APIView):
    """Admin/owner uchun — bitta mashqni o'chirish."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        mashq.delete()
        return Response(status=204)


class KursMashqRasmBoshqaruvView(APIView):
    """Admin/owner uchun — mashqqa rasm biriktirish."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        rasm = request.FILES.get("rasm")
        if not rasm:
            return Response({"detail": "rasm majburiy"}, status=400)
        mashq.rasm = rasm
        mashq.save()
        return Response(_kurs_mashq_admin_dict(mashq))


class KursMashqRasmView(APIView):
    """Mashq rasmi — autentifikatsiyalangan stream (B3.2 qoidasiga mos)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, mashq.tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        if not mashq.rasm:
            raise Http404
        javob = FileResponse(mashq.rasm.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class KursMashqRoyxatiView(APIView):
    """Talaba uchun — bitta tugunning mashqlari ro'yxati (savollar 'togri'siz)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        return Response([_kurs_mashq_talaba_dict(m) for m in tugun.mashqlar.all()])


class KursMashqYechishView(APIView):
    """Talaba uchun — bitta mashqqa javob yuborish va natija olish."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != User.Role.STUDENT:
            return Response({"detail": "Faqat talaba uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, mashq.tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)

        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, list):
            return Response({"detail": "javoblar ro'yxati majburiy"}, status=400)

        natija = javoblarni_tekshir(mashq.savollar, javoblar)
        KursMashqYechim.objects.create(
            talaba=request.user,
            mashq=mashq,
            javoblar=javoblar,
            ball=natija["ball"],
            jami=natija["jami"],
            natijalar=natija["natijalar"],
        )
        return Response(natija)
