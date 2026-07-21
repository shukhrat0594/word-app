from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import owner_mi

from .models import FaoliyatYozuvi

# XPYozuv.sabab -> o'qiladigan nom (owner hisobotida ko'rsatish uchun)
SABAB_NOMI = {
    "mashq_yechildi": "Mashq yechdi",
    "mashq_mukammal": "Mashqni mukammal yechdi",
    "writing_tekshiruv": "Writing tekshiruvi",
    "speaking_tekshiruv": "Speaking tekshiruvi",
    "material_tugatildi": "Material tugatdi",
    "davomat_keldi": "Darsga keldi",
}


def _foydalanuvchi_dict(u):
    if u is None:
        return None
    return {"id": u.id, "ism": u.get_full_name() or u.username, "username": u.username}


class AuditHisobotView(APIView):
    """Owner uchun — birlashtirilgan faoliyat hisoboti.

    Ikki manbadan birlashtiriladi: (1) `FaoliyatYozuvi` — admin/owner
    boshqaruv harakatlari (nima qo'shildi/o'chirildi/o'zgartirildi, diff
    bilan), (2) `gamification.XPYozuv` — talaba/oddiy foydalanuvchining
    bajargan mashqlari (yangi jadval yozilmaydi, mavjudidan o'qiladi).

    Filtrlar: `foydalanuvchi` (id), `sana_dan`/`sana_gacha` (YYYY-MM-DD),
    `turi` (`boshqaruv`/`mashq`), `obyekt_turi` (faqat boshqaruv uchun).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        foydalanuvchi_id = request.query_params.get("foydalanuvchi")
        sana_dan = request.query_params.get("sana_dan")
        sana_gacha = request.query_params.get("sana_gacha")
        turi = request.query_params.get("turi")
        obyekt_turi = request.query_params.get("obyekt_turi")
        try:
            limit = min(int(request.query_params.get("limit", 50)), 200)
        except ValueError:
            limit = 50
        try:
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            offset = 0

        yozuvlar = []

        if turi != "mashq":
            qs = FaoliyatYozuvi.objects.select_related("foydalanuvchi", "markaz").all()
            if foydalanuvchi_id:
                qs = qs.filter(foydalanuvchi_id=foydalanuvchi_id)
            if obyekt_turi:
                qs = qs.filter(obyekt_turi=obyekt_turi)
            if sana_dan:
                qs = qs.filter(vaqt__date__gte=sana_dan)
            if sana_gacha:
                qs = qs.filter(vaqt__date__lte=sana_gacha)
            for y in qs:
                yozuvlar.append(
                    {
                        "turi": "boshqaruv",
                        "vaqt": y.vaqt,
                        "foydalanuvchi": _foydalanuvchi_dict(y.foydalanuvchi),
                        "harakat": y.harakat,
                        "harakat_nomi": y.get_harakat_display(),
                        "obyekt_turi": y.obyekt_turi,
                        "obyekt_nomi": y.obyekt_nomi,
                        "ozgarishlar": y.ozgarishlar,
                    }
                )

        if turi != "boshqaruv" and not obyekt_turi:
            from gamification.models import XPYozuv

            qs = XPYozuv.objects.select_related("talaba").all()
            if foydalanuvchi_id:
                qs = qs.filter(talaba_id=foydalanuvchi_id)
            if sana_dan:
                qs = qs.filter(created_at__date__gte=sana_dan)
            if sana_gacha:
                qs = qs.filter(created_at__date__lte=sana_gacha)
            for x in qs:
                yozuvlar.append(
                    {
                        "turi": "mashq",
                        "vaqt": x.created_at,
                        "foydalanuvchi": _foydalanuvchi_dict(x.talaba),
                        "harakat": x.sabab,
                        "harakat_nomi": SABAB_NOMI.get(x.sabab, x.sabab),
                        "obyekt_turi": None,
                        "obyekt_nomi": None,
                        "ozgarishlar": {"xp": x.miqdor},
                    }
                )

        yozuvlar.sort(key=lambda y: y["vaqt"], reverse=True)
        jami = len(yozuvlar)
        sahifa = yozuvlar[offset : offset + limit]

        return Response({"jami": jami, "natijalar": sahifa})


class AuditFiltrlarView(APIView):
    """Frontend'dagi filtr dropdown'lari uchun — mavjud obyekt turlari
    ro'yxati (statik, kod bilan bir xil qiladigan qiymatlar)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        return Response(
            {
                "obyekt_turlari": [
                    "Markaz",
                    "Foydalanuvchi",
                    "Mashq",
                    "ImtihonTest",
                    "Guruh",
                ],
                "mashq_sabablari": list(SABAB_NOMI.items()),
            }
        )
