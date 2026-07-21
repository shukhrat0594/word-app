import datetime

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from audit.utils import logla, maydon_diff

from .models import Davomat, Guruh


def _foydalanuvchi_dict(u):
    return {"id": u.id, "ism": u.get_full_name() or u.username}


def _guruh_dict(g, toliq=False):
    d = {
        "id": g.id,
        "name": g.name,
        "oqituvchi": _foydalanuvchi_dict(g.oqituvchi) if g.oqituvchi else None,
        "talaba_soni": g.talabalar.count(),
    }
    if toliq:
        d["talabalar"] = [_foydalanuvchi_dict(t) for t in g.talabalar.all()]
    return d


def _guruhga_ruxsat_bormi(user, guruh):
    """Owner — hammasiga, admin — o'z markazidagi istalgan guruhga,
    o'qituvchi — faqat o'ziniki."""
    if owner_mi(user):
        return True
    if user.role == User.Role.ADMIN:
        return guruh.markaz_id == user.markaz_id
    if user.role == User.Role.TEACHER:
        return guruh.oqituvchi_id == user.id
    return False


class GuruhlarView(APIView):
    """Guruhlar ro'yxati va yaratish (F2.1).

    Owner (platforma egasi) — barcha markazlardagi barcha guruhlar. Admin —
    o'z markazidagi barcha guruhlar. O'qituvchi — faqat o'zi biriktirilgan
    guruhlar. Yaratish admin (o'z markazi) yoki owner (istalgan markaz,
    markaz_id ko'rsatib) uchun.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if owner_mi(request.user):
            qs = Guruh.objects.all()
        elif request.user.role == User.Role.ADMIN:
            qs = Guruh.objects.filter(markaz_id=request.user.markaz_id)
        elif request.user.role == User.Role.TEACHER:
            qs = Guruh.objects.filter(oqituvchi=request.user)
        else:
            return Response({"detail": "Faqat admin yoki o'qituvchi uchun"}, status=403)
        return Response([_guruh_dict(g) for g in qs])

    def post(self, request):
        if owner_mi(request.user):
            markaz_id = request.data.get("markaz_id") or request.user.markaz_id
            if not markaz_id:
                return Response({"detail": "markaz_id majburiy"}, status=400)
        elif request.user.role == User.Role.ADMIN:
            if not request.user.markaz_id:
                return Response({"detail": "Sizning markazingiz belgilanmagan"}, status=400)
            markaz_id = request.user.markaz_id
        else:
            return Response({"detail": "Faqat admin guruh yarata oladi"}, status=403)

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "name majburiy"}, status=400)

        guruh = Guruh.objects.create(name=name, markaz_id=markaz_id)
        _azolarni_saqla(request, guruh)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=guruh,
            obyekt_turi="Guruh",
            snapshot={
                "name": guruh.name,
                "oqituvchi": guruh.oqituvchi.username if guruh.oqituvchi else None,
                "talaba_soni": guruh.talabalar.count(),
            },
        )
        return Response(_guruh_dict(guruh, toliq=True), status=201)


class GuruhDetailView(APIView):
    """Bitta guruh — batafsil ko'rish va tahrirlash (owner yoki o'z markazi admini)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        if not _guruhga_ruxsat_bormi(request.user, guruh):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        return Response(_guruh_dict(guruh, toliq=True))

    def patch(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        tahrirlay_oladimi = owner_mi(request.user) or (
            request.user.role == User.Role.ADMIN
            and guruh.markaz_id == request.user.markaz_id
        )
        if not tahrirlay_oladimi:
            return Response({"detail": "Faqat admin tahrirlay oladi"}, status=403)

        eski_nomi = guruh.name
        eski_oqituvchi = guruh.oqituvchi.username if guruh.oqituvchi else None
        eski_talaba_soni = guruh.talabalar.count()

        name = request.data.get("name")
        if name is not None:
            guruh.name = name.strip()
            guruh.save(update_fields=["name"])
        _azolarni_saqla(request, guruh)

        ozgarishlar = maydon_diff({"name": eski_nomi}, {"name": guruh.name})
        yangi_oqituvchi = guruh.oqituvchi.username if guruh.oqituvchi else None
        if yangi_oqituvchi != eski_oqituvchi:
            ozgarishlar["oqituvchi"] = {"eski": eski_oqituvchi, "yangi": yangi_oqituvchi}
        yangi_talaba_soni = guruh.talabalar.count()
        if yangi_talaba_soni != eski_talaba_soni:
            ozgarishlar["talaba_soni"] = {"eski": eski_talaba_soni, "yangi": yangi_talaba_soni}
        if ozgarishlar:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=guruh,
                obyekt_turi="Guruh",
                obyekt_nomi=guruh.name,
                ozgarishlar=ozgarishlar,
            )
        return Response(_guruh_dict(guruh, toliq=True))


def _azolarni_saqla(request, guruh):
    """oqituvchi_id / talaba_idlar berilgan bo'lsa guruhga biriktiradi."""
    if "oqituvchi_id" in request.data:
        oqituvchi_id = request.data.get("oqituvchi_id")
        if oqituvchi_id:
            oqituvchi = get_object_or_404(
                User, pk=oqituvchi_id, role=User.Role.TEACHER, markaz_id=guruh.markaz_id
            )
            guruh.oqituvchi = oqituvchi
        else:
            guruh.oqituvchi = None
        guruh.save(update_fields=["oqituvchi"])

    if "talaba_idlar" in request.data:
        idlar = request.data.get("talaba_idlar") or []
        talabalar = User.objects.filter(
            pk__in=idlar, role=User.Role.STUDENT, markaz_id=guruh.markaz_id
        )
        guruh.talabalar.set(talabalar)


class MarkazAzolariView(APIView):
    """Admin uchun — guruhga biriktirish uchun markazdagi o'qituvchi/talabalar.

    Owner (platforma egasi) `?markaz=<id>` bilan istalgan markazni so'rashi
    mumkin (yangi markaz qo'shilganda ham avtomatik ishlaydi). Oddiy admin —
    faqat o'z markazi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if owner_mi(request.user):
            markaz_id = request.query_params.get("markaz") or request.user.markaz_id
        elif request.user.role == User.Role.ADMIN:
            markaz_id = request.user.markaz_id
        else:
            return Response({"detail": "Faqat admin uchun"}, status=403)

        if not markaz_id:
            return Response({"detail": "markaz belgilanmagan"}, status=400)
        azolar = User.objects.filter(markaz_id=markaz_id)
        return Response(
            {
                "oqituvchilar": [
                    _foydalanuvchi_dict(u) for u in azolar.filter(role=User.Role.TEACHER)
                ],
                "talabalar": [
                    _foydalanuvchi_dict(u) for u in azolar.filter(role=User.Role.STUDENT)
                ],
            }
        )


class DavomatView(APIView):
    """Kunlik davomat — ko'rish va belgilash (B2.2, F2.1).

    GET  ?guruh=<id>&sana=YYYY-MM-DD — guruh talabalari + shu kungi holati.
    POST {guruh, sana, yozuvlar: [{talaba, holat}]} — bir nechta yozuvni saqlaydi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        guruh = get_object_or_404(Guruh, pk=request.query_params.get("guruh"))
        if not _guruhga_ruxsat_bormi(request.user, guruh):
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        sana = request.query_params.get("sana") or str(datetime.date.today())
        mavjud = {
            d.talaba_id: d.holat
            for d in Davomat.objects.filter(guruh=guruh, sana=sana)
        }
        return Response(
            {
                "guruh": _guruh_dict(guruh),
                "sana": sana,
                "talabalar": [
                    {
                        "id": t.id,
                        "ism": t.get_full_name() or t.username,
                        "holat": mavjud.get(t.id),
                    }
                    for t in guruh.talabalar.all()
                ],
            }
        )

    def post(self, request):
        guruh = get_object_or_404(Guruh, pk=request.data.get("guruh"))
        if not _guruhga_ruxsat_bormi(request.user, guruh):
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        sana = request.data.get("sana") or str(datetime.date.today())
        yozuvlar = request.data.get("yozuvlar") or []
        azo_idlar = set(guruh.talabalar.values_list("id", flat=True))

        saqlandi = 0
        for y in yozuvlar:
            talaba_id = y.get("talaba")
            holat = y.get("holat")
            if talaba_id not in azo_idlar or holat not in Davomat.Holat.values:
                continue
            Davomat.objects.update_or_create(
                sana=sana,
                guruh=guruh,
                talaba_id=talaba_id,
                defaults={"holat": holat, "belgilagan": request.user},
            )
            saqlandi += 1

        return Response({"saqlandi": saqlandi, "sana": sana})


class DavomatHisobotView(APIView):
    """Markaz admini (yoki owner) uchun — davomat hisoboti.

    Har bir guruh va uning har bir talabasi bo'yicha jami keldi/kelmadi soni
    va foizi — o'qituvchi kunlik belgilagan davomatning umumiy ko'rinishi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if owner_mi(request.user):
            markaz_id = request.query_params.get("markaz") or request.user.markaz_id
        elif request.user.role == User.Role.ADMIN:
            markaz_id = request.user.markaz_id
        else:
            return Response({"detail": "Faqat admin uchun"}, status=403)

        if not markaz_id:
            return Response({"detail": "markaz belgilanmagan"}, status=400)

        natija = []
        for g in Guruh.objects.filter(markaz_id=markaz_id):
            talabalar = []
            for t in g.talabalar.all():
                agg = Davomat.objects.filter(guruh=g, talaba=t).aggregate(
                    keldi=Count("id", filter=Q(holat="keldi")),
                    kelmadi=Count("id", filter=Q(holat="kelmadi")),
                )
                jami = agg["keldi"] + agg["kelmadi"]
                talabalar.append(
                    {
                        "id": t.id,
                        "ism": t.get_full_name() or t.username,
                        "keldi": agg["keldi"],
                        "kelmadi": agg["kelmadi"],
                        "foiz": round(agg["keldi"] / jami * 100) if jami else None,
                    }
                )
            natija.append({"id": g.id, "name": g.name, "talabalar": talabalar})

        return Response({"guruhlar": natija})
