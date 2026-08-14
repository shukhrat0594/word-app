import datetime

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Markaz, User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from audit.utils import logla, maydon_diff

from courses.models import KursTugun

from .models import Davomat, Guruh, GuruhAzoligi


def _foydalanuvchi_dict(u):
    return {
        "id": u.id,
        "ism": u.get_full_name() or u.username,
        "rasm_url": f"/api/foydalanuvchilar/{u.id}/rasm/" if u.rasm else None,
    }


def _guruh_dict(g, toliq=False, talaba_soni=None):
    """2026-08-15: `talaba_soni` — ro'yxat ko'rinishida N+1'dan qochish
    uchun chaqiruvchi tomonidan oldindan (`annotate(Count(...))` bilan)
    hisoblab beriladi; berilmasa (masalan bitta guruh — detail view)
    oddiy `.count()` bilan hisoblanadi."""
    d = {
        "id": g.id,
        "name": g.name,
        "faol": g.faol,
        "oqituvchi": _foydalanuvchi_dict(g.oqituvchi) if g.oqituvchi else None,
        "talaba_soni": talaba_soni if talaba_soni is not None else g.talabalar.count(),
        "fan": {"id": g.fan_id, "nomi": g.fan.nomi, "kalit": g.fan.kalit} if g.fan_id else None,
        "daraja": {"id": g.daraja_id, "nomi": g.daraja.nomi, "kalit": g.daraja.kalit} if g.daraja_id else None,
    }
    if toliq:
        # `boshlanish_unit_id` (2026-08-02) — talaba shu guruh darajasi
        # ichida qaysi Unit'dan boshlaydi (oldingilar qulfsiz, lekin
        # "tugallangan" emas). Guruhga qo'shilganda avtomatik Unit 1.
        azolik_map = {
            a.talaba_id: a.boshlanish_unit_id
            for a in GuruhAzoligi.objects.filter(guruh=g)
        }
        d["talabalar"] = [
            {**_foydalanuvchi_dict(t), "boshlanish_unit_id": azolik_map.get(t.id)}
            for t in g.talabalar.all()
        ]
        if g.daraja_id:
            d["daraja_unitlari"] = [
                {"id": u.id, "nomi": u.nomi, "tartib": u.tartib}
                for u in KursTugun.objects.filter(
                    parent_id=g.daraja_id, unit_darsi=True
                ).order_by("tartib", "id")
            ]
    return d


class GuruhFanlarView(APIView):
    """Guruh yaratish/tahrirlashda "Fan" va "Daraja" tanlash uchun — Kurslar
    bo'limining daraxtidan FAQAT 2 qatlam (fan + uning bevosita darajalari),
    boshqa hech narsa (mashqlar/fayllar) — `KursDaraxtiView` bilan farqi shu,
    u butun daraxtni (Unit'largacha) qaytaradi, bu yerga ortiqcha (2026-08-02).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        ildiz = KursTugun.objects.filter(parent__isnull=True).first()
        if not ildiz:
            return Response([])
        fanlar = KursTugun.objects.filter(parent=ildiz).order_by("tartib", "id")
        darajalar_qs = KursTugun.objects.filter(parent__in=fanlar).order_by("tartib", "id")
        darajalar_keshi = {}
        for d in darajalar_qs:
            darajalar_keshi.setdefault(d.parent_id, []).append(
                {"id": d.id, "nomi": d.nomi, "kalit": d.kalit, "tez_kunda": d.tez_kunda}
            )
        return Response([
            {
                "id": f.id, "nomi": f.nomi, "kalit": f.kalit, "tez_kunda": f.tez_kunda,
                "darajalar": darajalar_keshi.get(f.id, []),
            }
            for f in fanlar
        ])


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
        # `?arxiv=1` — faqat arxivlangan (faol=False) guruhlar (2026-08-02).
        # Standart holatda faqat FAOL guruhlar ko'rinadi.
        qs = qs.filter(faol=False) if request.query_params.get("arxiv") else qs.filter(faol=True)
        # 2026-08-15: avval har guruh uchun `oqituvchi`/`fan`/`daraja`
        # (FK) va `talabalar.count()` alohida so'rov berardi (N+1) —
        # endi select_related + annotate bilan bitta so'rovda.
        qs = qs.select_related("oqituvchi", "fan", "daraja").annotate(
            _talaba_soni=Count("talabalar", distinct=True)
        )
        return Response([_guruh_dict(g, talaba_soni=g._talaba_soni) for g in qs])

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
        fan_xato = _fan_darajani_saqla(request, guruh)
        if fan_xato:
            return fan_xato
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
        if "faol" in request.data:
            guruh.faol = bool(request.data.get("faol"))
            guruh.save(update_fields=["faol"])
        fan_xato = _fan_darajani_saqla(request, guruh)
        if fan_xato:
            return fan_xato
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

    def delete(self, request, pk):
        """Guruhni BUTUNLAY o'chirish (2026-08-02) — Davomat va GuruhAzoligi
        (a'zolik/boshlanish_unit) yozuvlari ham CASCADE bilan o'chadi,
        qaytarilmaydi. Arxivlash (`PATCH {faol: false}`) — qaytariladigan
        muqobil, tarixni saqlab qoladi."""
        guruh = get_object_or_404(Guruh, pk=pk)
        ochira_oladimi = owner_mi(request.user) or (
            request.user.role == User.Role.ADMIN
            and guruh.markaz_id == request.user.markaz_id
        )
        if not ochira_oladimi:
            return Response({"detail": "Faqat admin o'chira oladi"}, status=403)

        nomi = guruh.name
        guruh_id = guruh.id
        guruh.delete()
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="Guruh",
            obyekt_id=guruh_id,
            obyekt_nomi=nomi,
        )
        return Response(status=204)


def _fan_darajani_saqla(request, guruh):
    """`fan_id`/`daraja_id` berilgan bo'lsa guruhga biriktiradi (2026-08-02).
    `daraja_id` — MAJBURIY ravishda tanlangan `fan_id`ning bevosita bolasi
    bo'lishi kerak (boshqa fanning darajasini qo'shib qo'yish xato).
    Xato bo'lsa Response qaytaradi, muvaffaqiyatli bo'lsa None."""
    if "fan_id" in request.data:
        fan_id = request.data.get("fan_id")
        if fan_id:
            fan = get_object_or_404(KursTugun, pk=fan_id, parent__parent__isnull=True)
            guruh.fan = fan
        else:
            guruh.fan = None
            guruh.daraja = None
        guruh.save(update_fields=["fan", "daraja"])

    if "daraja_id" in request.data:
        daraja_id = request.data.get("daraja_id")
        if daraja_id:
            if not guruh.fan_id:
                return Response({"detail": "Avval fan tanlanishi kerak"}, status=400)
            daraja = get_object_or_404(KursTugun, pk=daraja_id, parent_id=guruh.fan_id)
            guruh.daraja = daraja
        else:
            guruh.daraja = None
        guruh.save(update_fields=["daraja"])
    return None


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
        # markaz_id filtri yo'q (2026-08-02) — talaba markazga bog'lanmaydi,
        # istalgan markazdagi admin istalgan talabani guruhga qo'sha oladi.
        talabalar = User.objects.filter(pk__in=idlar, role=User.Role.STUDENT)
        # `guruh.talabalar.set(...)` ishlatilmaydi — u yangi qo'shilgan
        # a'zolarning `boshlanish_unit`ini NULL qilib qo'yardi (through
        # modelning qo'shimcha maydoni e'tiborga olinmaydi). Shuning uchun
        # qo'lda diff: mavjud a'zoning `boshlanish_unit`i TEGILMAYDI, yangi
        # qo'shilganga esa guruh darajasining BIRINCHI Unit'i (standart,
        # 2026-08-02 talabi) beriladi.
        yangi_idlar = set(talabalar.values_list("id", flat=True))
        eski_idlar = set(
            GuruhAzoligi.objects.filter(guruh=guruh).values_list("talaba_id", flat=True)
        )
        olib_tashlanadigan = eski_idlar - yangi_idlar
        qoshiladigan = yangi_idlar - eski_idlar
        if olib_tashlanadigan:
            GuruhAzoligi.objects.filter(
                guruh=guruh, talaba_id__in=olib_tashlanadigan
            ).delete()
        if qoshiladigan:
            birinchi_unit = None
            if guruh.daraja_id:
                birinchi_unit = (
                    KursTugun.objects.filter(parent_id=guruh.daraja_id, unit_darsi=True)
                    .order_by("tartib", "id")
                    .first()
                )
            GuruhAzoligi.objects.bulk_create(
                [
                    GuruhAzoligi(guruh=guruh, talaba_id=tid, boshlanish_unit=birinchi_unit)
                    for tid in qoshiladigan
                ]
            )


class GuruhAzoligiDetailView(APIView):
    """Bitta talabaning shu guruhdagi `boshlanish_unit`ini o'zgartirish
    (2026-08-02) — admin talabani guruhga qo'shgandan keyin, standart
    Unit 1 o'rniga boshqa Unit'ni tanlashi uchun."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, talaba_id):
        guruh = get_object_or_404(Guruh, pk=pk)
        tahrirlay_oladimi = owner_mi(request.user) or (
            request.user.role == User.Role.ADMIN
            and guruh.markaz_id == request.user.markaz_id
        )
        if not tahrirlay_oladimi:
            return Response({"detail": "Faqat admin tahrirlay oladi"}, status=403)

        azolik = get_object_or_404(GuruhAzoligi, guruh=guruh, talaba_id=talaba_id)
        unit_id = request.data.get("boshlanish_unit_id")
        if unit_id:
            if not guruh.daraja_id:
                return Response({"detail": "Guruhda daraja tanlanmagan"}, status=400)
            unit = get_object_or_404(
                KursTugun, pk=unit_id, parent_id=guruh.daraja_id, unit_darsi=True
            )
            azolik.boshlanish_unit = unit
        else:
            azolik.boshlanish_unit = None
        azolik.save(update_fields=["boshlanish_unit"])
        return Response({"boshlanish_unit_id": azolik.boshlanish_unit_id})


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
        # Talabalar markazga bog'lanmaydi (2026-08-02) — BARCHA talabalar
        # ko'rinadi ("Utmost talabasi"), faqat o'qituvchilar shu markaz
        # bilan cheklanadi (ular admin kabi markazga tegishli xodim).
        return Response(
            {
                "oqituvchilar": [
                    _foydalanuvchi_dict(u)
                    for u in User.objects.filter(markaz_id=markaz_id, role=User.Role.TEACHER)
                ],
                "talabalar": [
                    _foydalanuvchi_dict(u)
                    for u in User.objects.filter(role=User.Role.STUDENT)
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
            if not markaz_id:
                # Owner odatda hech qanday markazga biriktirilmagan —
                # bitta-markaz rejimida yagona mavjud markazga tushamiz
                # (accounts.XodimlarView._markaz_ol bilan bir xil konvensiya).
                markaz = Markaz.objects.first()
                markaz_id = markaz.id if markaz else None
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
