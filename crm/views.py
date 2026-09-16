"""CRM API — hammasi `/api/crm/` prefiksi ostida.

Loyiha konvensiyasi bo'yicha DRF serializer'lari EMAS, oddiy dict
quruvchilar ishlatiladi (qarang `academics/views.py: _guruh_dict`).

Har bir pul harakati `audit.utils.logla()` orqali yozib boriladi —
mavjud audit ilovasi qayta ishlatiladi, unga tegilmaydi.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response

from academics.models import Davomat, Guruh, GuruhAzoligi
from accounts.models import User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from audit.utils import logla
from courses.models import KursTugun
from exercises.models import Bolim, MashqYechim
from stats.services import talaba_statistikasi

from . import eksport, mantiq
from .models import (
    AzolikMoliya,
    DarsJadvali,
    Eslatma,
    Filial,
    GuruhMoliya,
    Hisob,
    KursNarxi,
    Tolov,
    Xona,
)
from .permissions import CrmView, FaqatOwner

NOL = Decimal("0")


# ── Yordamchilar ─────────────────────────────────────────────────────


def _son(qiymat, nom):
    """Kelgan summani Decimal'ga aylantiradi. Xato bo'lsa — ValueError.

    Pul `float` orqali O'TKAZILMAYDI: 0.1 + 0.2 kabi yaxlitlash xatolari
    hisobotda tiyinlab farq keltiradi va sababini topib bo'lmaydi.
    """
    try:
        return Decimal(str(qiymat))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{nom}: son bo'lishi kerak")


def _sana(qiymat, nom, majburiy=True):
    if qiymat in (None, ""):
        if majburiy:
            raise ValueError(f"{nom}: sana kerak")
        return None
    from datetime import date

    try:
        return date.fromisoformat(str(qiymat)[:10])
    except ValueError:
        raise ValueError(f"{nom}: sana YYYY-MM-DD shaklida bo'lsin")


def _vaqt(qiymat, nom):
    """'14:00' -> datetime.time.

    ATAYLAB satr solishtiruvi ishlatilmaydi: "9:00" > "10:00" degan
    satr taqqoslash dars vaqtlarini noto'g'ri tartiblab yuborardi.
    """
    from datetime import time

    try:
        bolaklar = str(qiymat).split(":")
        return time(int(bolaklar[0]), int(bolaklar[1]))
    except (IndexError, TypeError, ValueError):
        raise ValueError(f"{nom}: vaqt HH:MM shaklida bo'lsin")


def _oy(qiymat, nom="oy"):
    """'2026-09' yoki '2026-09-01' -> oyning 1-sanasi."""
    matn = str(qiymat or "")
    if len(matn) == 7:
        matn += "-01"
    return mantiq.oy_boshi(_sana(matn, nom))


def _xato(matn, kod=400):
    return Response({"detail": matn}, status=kod)


def _filial_dict(f):
    return {
        "id": f.id,
        "nomi": f.nomi,
        "manzil": f.manzil,
        "telefon": f.telefon,
        "faol": f.faol,
    }


def _xona_dict(x):
    return {
        "id": x.id,
        "nomi": x.nomi,
        "filial_id": x.filial_id,
        "filial": x.filial.nomi,
        "sigimi": x.sigimi,
        "tartib": x.tartib,
        "faol": x.faol,
    }


def _tirik_talaba(yozuv):
    """Talaba ismi — LMS'dagi HOZIRGI qiymat.

    2026-09-16, Shuhrat topdi: `Hisob`/`Tolov` da `talaba_ism` snapshot
    saqlanadi (talaba LMS'da o'chirilsa yozuv o'qiladigan bo'lib
    qolishi uchun). Lekin ro'yxatlarda AYNAN SHU snapshot
    ko'rsatilardi — ya'ni admin LMS'da ismni tuzatsa, CRM eskisini
    ko'rsatib turardi va ikki joyda ikki xil ism chiqardi.

    Endi: FK tirik bo'lsa LMS'dan olinadi, snapshot FAQAT zaxira —
    talaba o'chirilgan holat uchun.
    """
    if yozuv.talaba_id and yozuv.talaba:
        return yozuv.talaba.get_full_name() or yozuv.talaba.username
    return yozuv.talaba_ism


def _tirik_guruh(yozuv):
    """Guruh nomi — LMS'dagi HOZIRGI qiymat (`_tirik_talaba` bilan bir xil sabab)."""
    if yozuv.guruh_id and yozuv.guruh:
        return yozuv.guruh.name
    return yozuv.guruh_nomi


def _yaxlit(qiymat, xona=1):
    """Band ballari 6.333333 emas, 6.3 bo'lib ko'rinsin."""
    return round(qiymat, xona) if qiymat is not None else None


def _eslatma_dict(e):
    return {
        "id": e.id,
        "matn": e.matn,
        "guruh_id": e.guruh_id,
        "talaba_id": e.talaba_id,
        "kim_id": e.kim_id,
        "kim": (e.kim.get_full_name() or e.kim.username) if e.kim_id else None,
        "vaqt": e.created_at,
    }


def _jadval_dict(j):
    return {
        "hafta_kuni": j.hafta_kuni,
        "hafta_kuni_nomi": j.get_hafta_kuni_display(),
        "boshlanish_vaqti": j.boshlanish_vaqti.strftime("%H:%M"),
        "tugash_vaqti": j.tugash_vaqti.strftime("%H:%M"),
        "xona_id": j.xona_id,
        "xona": j.xona.nomi if j.xona_id else None,
    }


def _guruh_dict(g, talaba_soni=None):
    """CRM ko'rinishidagi guruh: LMS ma'lumoti + moliya sozlamalari."""
    moliya = getattr(g, "moliya", None)
    narx, manba = mantiq.guruh_narxi(g)
    return {
        "id": g.id,
        "nomi": g.name,
        "faol": g.faol,
        "oqituvchi": (g.oqituvchi.get_full_name() or g.oqituvchi.username) if g.oqituvchi_id else None,
        "daraja": {"id": g.daraja_id, "nomi": g.daraja.nomi} if g.daraja_id else None,
        "talaba_soni": talaba_soni if talaba_soni is not None else g.talabalar.count(),
        "filial": _filial_dict(moliya.filial) if moliya and moliya.filial_id else None,
        # Narx MANBASI ham yuboriladi: admin narx qayerdan kelayotganini
        # ko'rmasa, nega o'zgartirgani ishlamaganini tushunmaydi.
        "narx": narx,
        "narx_manbasi": manba,
        "narx_guruhga": moliya.narx if moliya else None,
        "boshlanish_sana": moliya.boshlanish_sana if moliya else None,
        "tugash_sana": moliya.tugash_sana if moliya else None,
        "jadval": [_jadval_dict(j) for j in g.crm_jadval.all()],
        "sozlangan": bool(moliya and narx and g.crm_jadval.exists()),
    }


def _azolik_dict(am, balans=None):
    talaba = am.azolik.talaba
    narx, manba = mantiq.narx_va_manba(am)
    return {
        "id": am.id,
        "azolik_id": am.azolik_id,
        "talaba_id": talaba.id,
        "talaba": talaba.get_full_name() or talaba.username,
        "telefon": talaba.telefon,
        "guruh_id": am.azolik.guruh_id,
        "guruh": am.azolik.guruh.name,
        "holat": am.holat,
        "holat_nomi": am.get_holat_display(),
        "boshlanish_sana": am.boshlanish_sana,
        "tugash_sana": am.tugash_sana,
        "narx": narx,
        "narx_manbasi": manba,
        "narx_talabaga": am.narx,
        "balans": balans,
    }


def _hisob_dict(h, tolangan=None, balans=None):
    tolangan = NOL if tolangan is None else tolangan
    return {
        "id": h.id,
        "talaba_id": h.talaba_id,
        "talaba": _tirik_talaba(h),
        "guruh_id": h.guruh_id,
        "guruh": _tirik_guruh(h),
        "filial": h.filial.nomi if h.filial_id else None,
        "oy": h.oy,
        "summa": h.summa,
        "tolangan": tolangan,
        "qoldiq": h.summa - tolangan,
        "holat": h.holat,
        "proporsional": h.proporsional,
        "darslar_jami": h.darslar_jami,
        "darslar_talaba": h.darslar_talaba,
        "qolda": h.qolda,
        "balans": balans,
    }


def _tolov_dict(t):
    return {
        "id": t.id,
        "talaba_id": t.talaba_id,
        "talaba": _tirik_talaba(t),
        "guruh_id": t.guruh_id,
        "guruh": _tirik_guruh(t),
        "hisob_id": t.hisob_id,
        "oy": t.hisob.oy if t.hisob_id else None,
        "sana": t.sana,
        "summa": t.summa,
        "turi": t.turi,
        "turi_nomi": t.get_turi_display(),
        "izoh": t.izoh,
        "kim": (t.kim_kiritdi.get_full_name() or t.kim_kiritdi.username) if t.kim_kiritdi_id else None,
        "vaqt": t.created_at,
    }


def _tolangan_bilan(qs):
    """`Hisob` so'roviga "to'langan" ustunini qo'shadi — N+1'dan qochish."""
    return qs.annotate(
        tolangan=Sum(
            "tolovlar__summa",
            filter=Q(tolovlar__turi__in=Tolov.YOPUVCHI_TURLAR),
            default=NOL,
        )
    )


# ── Filiallar ────────────────────────────────────────────────────────


class FiliallarView(CrmView):
    def get(self, request):
        qs = Filial.objects.all()
        if request.query_params.get("faqat_faol") == "1":
            qs = qs.filter(faol=True)
        return Response([_filial_dict(f) for f in qs])

    def post(self, request):
        nomi = (request.data.get("nomi") or "").strip()
        if not nomi:
            return _xato("Filial nomi kerak")
        markaz_id = request.user.markaz_id
        if not markaz_id:
            from accounts.models import Markaz

            birinchi = Markaz.objects.first()
            markaz_id = birinchi.id if birinchi else None
        if not markaz_id:
            return _xato("Markaz topilmadi")

        filial = Filial.objects.create(
            markaz_id=markaz_id,
            nomi=nomi,
            manzil=(request.data.get("manzil") or "").strip(),
            telefon=(request.data.get("telefon") or "").strip(),
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=filial,
            obyekt_turi="CRM Filial",
            snapshot=_filial_dict(filial),
        )
        return Response(_filial_dict(filial), status=201)


class FilialDetailView(CrmView):
    def patch(self, request, pk):
        filial = get_object_or_404(Filial, pk=pk)
        eski = _filial_dict(filial)
        for maydon in ("nomi", "manzil", "telefon"):
            if maydon in request.data:
                setattr(filial, maydon, (request.data.get(maydon) or "").strip())
        if "faol" in request.data:
            filial.faol = bool(request.data["faol"])
        filial.save()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=filial,
            obyekt_turi="CRM Filial",
            eski_qiymatlar=eski,
            yangi_qiymatlar=_filial_dict(filial),
        )
        return Response(_filial_dict(filial))


# ── Kurs narxlari ────────────────────────────────────────────────────


def _darajalar_qs():
    """Kurslar daraxtining UCHINCHI qatlami: Kurslar > Fan > Daraja.

    `academics.Guruh.daraja` aynan shu qatlamga ishora qiladi, ya'ni narx
    shu yerga osiladi va o'sha darajaning barcha guruhlari uni oladi.
    """
    fanlar = KursTugun.objects.filter(parent__parent__isnull=True, parent__isnull=False)
    return (
        KursTugun.objects.filter(parent__in=fanlar)
        .select_related("parent", "crm_narxi")
        .order_by("parent__tartib", "tartib", "id")
    )


class KursNarxlariView(CrmView):
    def get(self, request):
        guruh_sonlari = dict(
            Guruh.objects.filter(faol=True)
            .exclude(daraja__isnull=True)
            .values("daraja_id")
            .annotate(soni=Count("id"))
            .values_list("daraja_id", "soni")
        )
        return Response(
            [
                {
                    "daraja_id": d.id,
                    "daraja": d.nomi,
                    "fan": d.parent.nomi if d.parent_id else None,
                    "narx": getattr(d, "crm_narxi", None).narx if hasattr(d, "crm_narxi") else None,
                    "guruh_soni": guruh_sonlari.get(d.id, 0),
                }
                for d in _darajalar_qs()
            ]
        )

    def put(self, request):
        daraja = get_object_or_404(KursTugun, pk=request.data.get("daraja_id"))
        xom = request.data.get("narx")

        if xom in (None, ""):
            KursNarxi.objects.filter(daraja=daraja).delete()
            return Response({"daraja_id": daraja.id, "narx": None})

        try:
            narx = _son(xom, "narx")
        except ValueError as e:
            return _xato(str(e))
        if narx <= 0:
            return _xato("Narx noldan katta bo'lishi kerak")

        yozuv, _ = KursNarxi.objects.update_or_create(
            daraja=daraja, defaults={"narx": narx}
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=yozuv,
            obyekt_turi="CRM Kurs narxi",
            obyekt_nomi=daraja.nomi,
            ozgarishlar={"narx": {"eski": None, "yangi": str(narx)}},
        )
        return Response({"daraja_id": daraja.id, "narx": narx})


# ── Guruhlar ─────────────────────────────────────────────────────────


class GuruhlarView(CrmView):
    def get(self, request):
        qs = (
            Guruh.objects.filter(faol=True)
            .select_related("daraja", "oqituvchi", "moliya", "moliya__filial", "daraja__crm_narxi")
            .prefetch_related("crm_jadval")
            .annotate(_talaba_soni=Count("talabalar", distinct=True))
            .order_by("name")
        )
        filial = request.query_params.get("filial")
        if filial:
            qs = qs.filter(moliya__filial_id=filial)
        qidiruv = (request.query_params.get("q") or "").strip()
        if qidiruv:
            qs = qs.filter(name__icontains=qidiruv)

        return Response([_guruh_dict(g, talaba_soni=g._talaba_soni) for g in qs])


class GuruhMoliyaView(CrmView):
    """Guruhning CRM sozlamalari — narx, sanalar, filial.

    Guruhning O'ZI (nomi, o'qituvchi, talabalar tarkibi) bu yerdan
    TAHRIRLANMAYDI: u LMS'ning ishi, ikki joyda tahrirlash chalkashlik
    keltiradi (TZ 6.4).
    """

    def patch(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        # Yozuv guruh yaratilganda emas, AYNAN shu yerda paydo bo'ladi —
        # signal ishlatilmaydi (TZ 3.0, 3-qoida).
        moliya, _ = GuruhMoliya.objects.get_or_create(guruh=guruh)
        eski = _guruh_dict(guruh)

        try:
            if "filial_id" in request.data:
                qiymat = request.data["filial_id"]
                moliya.filial = get_object_or_404(Filial, pk=qiymat) if qiymat else None
            if "narx" in request.data:
                xom = request.data["narx"]
                moliya.narx = None if xom in (None, "") else _son(xom, "narx")
            if "boshlanish_sana" in request.data:
                moliya.boshlanish_sana = _sana(
                    request.data["boshlanish_sana"], "boshlanish_sana", majburiy=False
                )
            if "tugash_sana" in request.data:
                moliya.tugash_sana = _sana(
                    request.data["tugash_sana"], "tugash_sana", majburiy=False
                )
        except ValueError as e:
            return _xato(str(e))

        if moliya.boshlanish_sana and moliya.tugash_sana and moliya.tugash_sana < moliya.boshlanish_sana:
            return _xato("Tugash sanasi boshlanish sanasidan oldin bo'la olmaydi")

        moliya.save()
        guruh.refresh_from_db()
        yangi = _guruh_dict(guruh)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=guruh,
            obyekt_turi="CRM Guruh moliyasi",
            obyekt_nomi=guruh.name,
            eski_qiymatlar={k: str(eski[k]) for k in ("narx_guruhga", "boshlanish_sana", "tugash_sana")},
            yangi_qiymatlar={k: str(yangi[k]) for k in ("narx_guruhga", "boshlanish_sana", "tugash_sana")},
        )
        return Response(yangi)


def _toqnashuv_bormi(guruh, hafta_kuni, boshlanish, tugash, xona_id):
    """Shu xonada, shu kunda, shu vaqtda BOSHQA guruh darsi bormi.

    Ikki dars kesishadi, agar biri ikkinchisi tugashidan OLDIN boshlansa
    va aksincha: `a.boshlanish < b.tugash AND b.boshlanish < a.tugash`.
    Chegara teginishi (10:30 tugadi — 10:30 boshlandi) to'qnashuv EMAS.
    """
    if not xona_id:
        return None  # xonasiz darslar to'qnashmaydi — joyi belgilanmagan

    raqib = (
        DarsJadvali.objects.filter(
            xona_id=xona_id,
            hafta_kuni=hafta_kuni,
            boshlanish_vaqti__lt=tugash,
            tugash_vaqti__gt=boshlanish,
        )
        .exclude(guruh=guruh)
        .select_related("guruh", "xona")
        .first()
    )
    return raqib


class XonalarView(CrmView):
    def get(self, request):
        qs = Xona.objects.select_related("filial").all()
        if request.query_params.get("filial"):
            qs = qs.filter(filial_id=request.query_params["filial"])
        if request.query_params.get("faqat_faol") == "1":
            qs = qs.filter(faol=True)
        return Response([_xona_dict(x) for x in qs])

    def post(self, request):
        nomi = (request.data.get("nomi") or "").strip()
        if not nomi:
            return _xato("Xona nomi kerak")
        filial = get_object_or_404(Filial, pk=request.data.get("filial_id"))
        if Xona.objects.filter(filial=filial, nomi=nomi).exists():
            return _xato("Bu filialda shunday nomli xona allaqachon bor")

        xona = Xona.objects.create(
            filial=filial,
            nomi=nomi,
            sigimi=request.data.get("sigimi") or None,
            tartib=request.data.get("tartib") or 0,
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=xona,
            obyekt_turi="CRM Xona",
            snapshot=_xona_dict(xona),
        )
        return Response(_xona_dict(xona), status=201)


class XonaDetailView(CrmView):
    def patch(self, request, pk):
        xona = get_object_or_404(Xona, pk=pk)
        eski = _xona_dict(xona)
        if "nomi" in request.data:
            nomi = (request.data.get("nomi") or "").strip()
            if not nomi:
                return _xato("Xona nomi kerak")
            if Xona.objects.filter(filial=xona.filial, nomi=nomi).exclude(pk=pk).exists():
                return _xato("Bu filialda shunday nomli xona allaqachon bor")
            xona.nomi = nomi
        if "sigimi" in request.data:
            xona.sigimi = request.data["sigimi"] or None
        if "tartib" in request.data:
            xona.tartib = request.data["tartib"] or 0
        if "faol" in request.data:
            xona.faol = bool(request.data["faol"])
        xona.save()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=xona,
            obyekt_turi="CRM Xona",
            eski_qiymatlar={k: str(v) for k, v in eski.items()},
            yangi_qiymatlar={k: str(v) for k, v in _xona_dict(xona).items()},
        )
        return Response(_xona_dict(xona))


class JadvalSetkaView(CrmView):
    """Haftalik setka — barcha guruhlarning darslari xona kesimida.

    SoffCRM'ning bosh sahifasidagi ko'rinish: kun tablari, soatlar
    ustunda, xonalar qatorda.
    """

    def get(self, request):
        filial_id = request.query_params.get("filial")

        xonalar = Xona.objects.filter(faol=True).select_related("filial")
        darslar = DarsJadvali.objects.select_related(
            "guruh", "guruh__oqituvchi", "guruh__moliya", "guruh__moliya__filial", "xona"
        ).filter(guruh__faol=True)
        if filial_id:
            xonalar = xonalar.filter(filial_id=filial_id)
            # Filial bo'yicha filtr GURUHNING filiali bo'yicha: xonasiz
            # darslar ham shu filialda ko'rinishi kerak.
            darslar = darslar.filter(guruh__moliya__filial_id=filial_id)

        return Response(
            {
                "xonalar": [_xona_dict(x) for x in xonalar],
                "darslar": [
                    {
                        "id": d.id,
                        "guruh_id": d.guruh_id,
                        "guruh": d.guruh.name,
                        "oqituvchi": (
                            d.guruh.oqituvchi.get_full_name() or d.guruh.oqituvchi.username
                        ) if d.guruh.oqituvchi_id else None,
                        "hafta_kuni": d.hafta_kuni,
                        "boshlanish_vaqti": d.boshlanish_vaqti.strftime("%H:%M"),
                        "tugash_vaqti": d.tugash_vaqti.strftime("%H:%M"),
                        "xona_id": d.xona_id,
                        "filial": (
                            d.guruh.moliya.filial.nomi
                            if getattr(d.guruh, "moliya", None) and d.guruh.moliya.filial_id
                            else None
                        ),
                    }
                    for d in darslar
                ],
            }
        )


class GuruhJadvalView(CrmView):
    """Guruhning haftalik dars kunlari — to'liq almashtiriladi (PUT)."""

    def put(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        kunlar = request.data.get("jadval") or []
        if not isinstance(kunlar, list):
            return _xato("jadval ro'yxat bo'lishi kerak")

        yangilar = []
        korilgan = set()
        for band in kunlar:
            try:
                hafta_kuni = int(band.get("hafta_kuni"))
            except (TypeError, ValueError):
                return _xato("hafta_kuni 0..6 oralig'ida son bo'lsin")
            if hafta_kuni not in dict(DarsJadvali.HaftaKuni.choices):
                return _xato("hafta_kuni 0..6 oralig'ida bo'lsin")
            try:
                boshlanish = _vaqt(band.get("boshlanish_vaqti"), "boshlanish_vaqti")
                tugash = _vaqt(band.get("tugash_vaqti"), "tugash_vaqti")
            except ValueError as e:
                return _xato(str(e))
            if tugash <= boshlanish:
                return _xato("Dars tugash vaqti boshlanish vaqtidan keyin bo'lsin")
            kalit = (hafta_kuni, boshlanish)
            if kalit in korilgan:
                return _xato("Bir kunda bir xil vaqt ikki marta kiritilgan")
            korilgan.add(kalit)

            xona_id = band.get("xona_id") or None
            if xona_id:
                xona = Xona.objects.filter(pk=xona_id).first()
                if xona is None:
                    return _xato("Xona topilmadi")
                # BOSHQA guruh bilan to'qnashuv — shu guruhning o'z eski
                # yozuvlari hisobga olinmaydi (ular pastda o'chiriladi).
                raqib = _toqnashuv_bormi(guruh, hafta_kuni, boshlanish, tugash, xona_id)
                if raqib is not None:
                    return _xato(
                        f"{xona.nomi}: {raqib.get_hafta_kuni_display()} "
                        f"{raqib.boshlanish_vaqti:%H:%M}-{raqib.tugash_vaqti:%H:%M} da "
                        f"«{raqib.guruh.name}» guruhi dars qilyapti"
                    )

            yangilar.append(
                DarsJadvali(
                    guruh=guruh,
                    hafta_kuni=hafta_kuni,
                    boshlanish_vaqti=boshlanish,
                    tugash_vaqti=tugash,
                    xona_id=xona_id,
                )
            )

        # Bitta so'rov ichida ikki dars bir xonada kesishmasin.
        for i, a in enumerate(yangilar):
            for b in yangilar[i + 1:]:
                if (
                    a.xona_id
                    and a.xona_id == b.xona_id
                    and a.hafta_kuni == b.hafta_kuni
                    and a.boshlanish_vaqti < b.tugash_vaqti
                    and b.boshlanish_vaqti < a.tugash_vaqti
                ):
                    return _xato("Bir xonada ikkita dars bir vaqtda kiritilgan")

        DarsJadvali.objects.filter(guruh=guruh).delete()
        DarsJadvali.objects.bulk_create(yangilar)

        # Jadval o'zgarsa, KELGUSI oylar boshqacha hisoblanadi. Allaqachon
        # ochilgan hisoblar ATAYLAB o'zgarmaydi: ular o'sha paytdagi
        # kelishuvni aks ettiradi va ba'zilari to'langan bo'lishi mumkin.
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=guruh,
            obyekt_turi="CRM Dars jadvali",
            obyekt_nomi=guruh.name,
            ozgarishlar={"jadval": {"eski": "—", "yangi": [_jadval_dict(j) for j in yangilar]}},
        )
        return Response({"jadval": [_jadval_dict(j) for j in yangilar]})


# ── A'zoliklar ───────────────────────────────────────────────────────


class GuruhAzoliklariView(CrmView):
    def get(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        azoliklar = (
            GuruhAzoligi.objects.filter(guruh=guruh)
            .select_related("talaba", "guruh", "guruh__moliya", "guruh__daraja__crm_narxi", "moliya")
            .order_by("talaba__first_name", "talaba__username")
        )

        natija = []
        # A'zolik moliyasi yozuvi hali yo'q bo'lsa — shu yerda paydo
        # bo'ladi (signal emas). `boshlanish_sana` standart qiymati
        # a'zolik yaratilgan kun, keyin admin tahrirlashi mumkin.
        for azolik in azoliklar:
            am = getattr(azolik, "moliya", None)
            if am is None:
                am = AzolikMoliya.objects.create(
                    azolik=azolik, boshlanish_sana=azolik.created_at.date()
                )
                am.azolik = azolik
            natija.append(am)

        balanslar = mantiq.balanslarni_ol([a.azolik.talaba_id for a in natija])
        return Response(
            [_azolik_dict(am, balans=balanslar.get(am.azolik.talaba_id)) for am in natija]
        )


class EslatmalarView(CrmView):
    """Guruh yoki talaba haqidagi erkin izohlar.

    SoffCRM'dagi "ESLATMALAR" tabi. Bu — LMS'da ham, CRM'da ham
    bo'lmagan yagona narsa edi.
    """

    def get(self, request):
        qs = Eslatma.objects.select_related("kim", "guruh", "talaba")
        guruh_id = request.query_params.get("guruh")
        talaba_id = request.query_params.get("talaba")
        if not guruh_id and not talaba_id:
            return _xato("guruh yoki talaba ko'rsatilishi kerak")
        if guruh_id:
            qs = qs.filter(guruh_id=guruh_id)
        if talaba_id:
            qs = qs.filter(talaba_id=talaba_id)
        return Response([_eslatma_dict(e) for e in qs[:200]])

    def post(self, request):
        matn = (request.data.get("matn") or "").strip()
        if not matn:
            return _xato("Eslatma matni bo'sh bo'lmasin")

        guruh = talaba = None
        if request.data.get("guruh_id"):
            guruh = get_object_or_404(Guruh, pk=request.data["guruh_id"])
        if request.data.get("talaba_id"):
            talaba = get_object_or_404(User, pk=request.data["talaba_id"])
        if guruh is None and talaba is None:
            return _xato("Eslatma guruhga yoki talabaga bog'lanishi kerak")

        eslatma = Eslatma.objects.create(
            guruh=guruh, talaba=talaba, matn=matn[:2000], kim=request.user
        )
        return Response(_eslatma_dict(eslatma), status=201)


class EslatmaDetailView(CrmView):
    def delete(self, request, pk):
        eslatma = get_object_or_404(Eslatma, pk=pk)
        # O'z eslatmasini har kim o'chira oladi, boshqanikini — faqat
        # owner. Admin hamkasbining izohini jimgina yo'q qila olmasligi
        # kerak.
        if eslatma.kim_id != request.user.pk and not owner_mi(request.user):
            return _xato("Faqat o'z eslatmangizni o'chira olasiz", kod=403)
        eslatma.delete()
        return Response({"detail": "O'chirildi"})


class GuruhDavomatView(CrmView):
    """Guruh davomati — FAQAT O'QISH uchun (SoffCRM'dagi DAVOMAT tabi).

    MUHIM: davomat CRM'da BELGILANMAYDI — uni o'qituvchi LMS'da
    belgilaydi (`academics.Davomat`). Bu yerda admin CRM'dan chiqmasdan
    ko'ra oladi, xolos. Ikki joyda belgilash ikki xil raqam degani
    bo'lardi — aynan biz qochayotgan muammo.
    """

    def get(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        try:
            oy = _oy(request.query_params.get("oy") or timezone.localdate().strftime("%Y-%m"))
        except ValueError as e:
            return _xato(str(e))

        yozuvlar = list(
            Davomat.objects.filter(
                guruh=guruh, sana__gte=oy, sana__lte=mantiq.oy_oxiri(oy)
            ).values("talaba_id", "sana", "holat")
        )
        # Ustunlar — AYNAN dars bo'lgan sanalar (SoffCRM ham shunday:
        # 01, 03, 05, 08...). Jadvaldagi hamma kunni ko'rsatsak, dars
        # o'tmagan kunlar ham bo'sh ustun bo'lib turardi.
        sanalar = sorted({y["sana"] for y in yozuvlar})
        katak = {(y["talaba_id"], y["sana"]): y["holat"] for y in yozuvlar}

        talabalar = guruh.talabalar.all().order_by("first_name", "username")
        return Response(
            {
                "oy": oy,
                "sanalar": sanalar,
                "talabalar": [
                    {
                        "id": t.id,
                        "ism": t.get_full_name() or t.username,
                        "kunlar": [katak.get((t.id, s)) for s in sanalar],
                        "keldi": sum(
                            1 for s in sanalar if katak.get((t.id, s)) == Davomat.Holat.KELDI
                        ),
                        "kelmadi": sum(
                            1 for s in sanalar if katak.get((t.id, s)) == Davomat.Holat.KELMADI
                        ),
                    }
                    for t in talabalar
                ],
            }
        )


class GuruhNatijalarView(CrmView):
    """Guruh natijalari — FAQAT O'QISH (SoffCRM'dagi BAHO/TEST tablari).

    Natija LMS'da hosil bo'ladi (mashqlar, Writing/Speaking tekshiruvi).
    Bu yerda faqat yig'ma ko'rsatkich.

    Har talaba uchun `stats.services.talaba_statistikasi` chaqirilmaydi:
    u talabaga ~6 ta so'rov qiladi, ya'ni 20 kishilik guruhda 120 so'rov
    bo'lardi. Bu yerda hammasi guruh bo'yicha TO'PLAM so'rovlar bilan —
    guruh kattaligidan qat'i nazar 5 ta so'rov.
    """

    def get(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        talabalar = list(guruh.talabalar.all().order_by("first_name", "username"))
        idlar = [t.id for t in talabalar]
        if not idlar:
            return Response({"talabalar": []})

        writing = {
            q["talaba_id"]: q
            for q in WritingTekshiruv.objects.filter(talaba_id__in=idlar)
            .values("talaba_id")
            .annotate(soni=Count("id"), ortacha=Avg("overall_band"))
        }
        speaking = {
            q["talaba_id"]: q
            for q in SpeakingTekshiruv.objects.filter(talaba_id__in=idlar)
            .values("talaba_id")
            .annotate(soni=Count("id"), ortacha=Avg("overall_band"))
        }
        mashqlar = {}
        for q in (
            MashqYechim.objects.filter(talaba_id__in=idlar)
            .values("talaba_id", "mashq__bolim")
            .annotate(ball=Sum("ball"), jami=Sum("jami"), soni=Count("id"))
        ):
            mashqlar.setdefault(q["talaba_id"], {})[q["mashq__bolim"]] = q
        davomat = {
            q["talaba_id"]: q
            for q in Davomat.objects.filter(guruh=guruh, talaba_id__in=idlar)
            .values("talaba_id")
            .annotate(
                keldi=Count("id", filter=Q(holat=Davomat.Holat.KELDI)),
                kelmadi=Count("id", filter=Q(holat=Davomat.Holat.KELMADI)),
            )
        }

        def foiz(yozuv):
            if not yozuv or not yozuv["jami"]:
                return None
            return round(yozuv["ball"] / yozuv["jami"] * 100)

        def band(yozuv):
            return round(yozuv["ortacha"], 1) if yozuv and yozuv["ortacha"] else None

        natija = []
        for t in talabalar:
            bolimlar = mashqlar.get(t.id, {})
            d = davomat.get(t.id, {"keldi": 0, "kelmadi": 0})
            jami_dars = d["keldi"] + d["kelmadi"]
            natija.append(
                {
                    "id": t.id,
                    "ism": t.get_full_name() or t.username,
                    "writing_band": band(writing.get(t.id)),
                    "writing_soni": (writing.get(t.id) or {}).get("soni", 0),
                    "speaking_band": band(speaking.get(t.id)),
                    "speaking_soni": (speaking.get(t.id) or {}).get("soni", 0),
                    "listening_foiz": foiz(bolimlar.get(Bolim.LISTENING)),
                    "reading_foiz": foiz(bolimlar.get(Bolim.READING)),
                    "mashq_soni": sum(b["soni"] for b in bolimlar.values()),
                    "keldi": d["keldi"],
                    "kelmadi": d["kelmadi"],
                    "davomat_foizi": round(d["keldi"] / jami_dars * 100) if jami_dars else None,
                }
            )
        return Response({"talabalar": natija})


class AzolikView(CrmView):
    """A'zolikning moliyaviy holati — holat, sanalar, individual narx."""

    def patch(self, request, pk):
        am = get_object_or_404(
            AzolikMoliya.objects.select_related(
                "azolik__talaba", "azolik__guruh__moliya", "azolik__guruh__daraja__crm_narxi"
            ),
            pk=pk,
        )
        eski_holat = am.holat
        eski = _azolik_dict(am)

        try:
            if "holat" in request.data:
                holat = request.data["holat"]
                if holat not in dict(AzolikMoliya.Holat.choices):
                    return _xato("Noma'lum holat")
                am.holat = holat
            if "boshlanish_sana" in request.data:
                am.boshlanish_sana = _sana(request.data["boshlanish_sana"], "boshlanish_sana")
            if "tugash_sana" in request.data:
                am.tugash_sana = _sana(request.data["tugash_sana"], "tugash_sana", majburiy=False)
            if "narx" in request.data:
                xom = request.data["narx"]
                am.narx = None if xom in (None, "") else _son(xom, "narx")
        except ValueError as e:
            return _xato(str(e))

        if am.tugash_sana and am.tugash_sana < am.boshlanish_sana:
            return _xato("Tugash sanasi boshlanish sanasidan oldin bo'la olmaydi")

        # Muzlatishdan qayta ochilganda — o'sha oy shu sanadan boshlab
        # hisoblanadi (TZ 4.6).
        if eski_holat == AzolikMoliya.Holat.MUZLATILGAN and am.holat == AzolikMoliya.Holat.FAOL:
            am.qayta_faol_sana = timezone.localdate()

        am.save()

        # Chiqish yoki muzlatish — joriy oyning TO'LANMAGAN hisobi
        # proporsional qayta hisoblanadi. Buni generatsiya qila olmaydi:
        # holat `arxiv`/`muzlatilgan` bo'lgach u bu a'zolikni ko'rmaydi.
        if am.holat in (AzolikMoliya.Holat.ARXIV, AzolikMoliya.Holat.MUZLATILGAN):
            mantiq.azolikni_qayta_hisobla(am)

        am.refresh_from_db()
        yangi = _azolik_dict(am)
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=am,
            obyekt_turi="CRM A'zolik",
            obyekt_nomi=f"{eski['talaba']} — {eski['guruh']}",
            eski_qiymatlar={k: str(eski[k]) for k in ("holat", "boshlanish_sana", "tugash_sana", "narx_talabaga")},
            yangi_qiymatlar={k: str(yangi[k]) for k in ("holat", "boshlanish_sana", "tugash_sana", "narx_talabaga")},
        )
        return Response(yangi)


# ── Hisoblar (qarzdorlar) ────────────────────────────────────────────


class HisoblarView(CrmView):
    def get(self, request):
        qs = _tolangan_bilan(
            Hisob.objects.select_related("filial", "talaba", "guruh").all()
        )

        oy = request.query_params.get("oy")
        if oy:
            try:
                qs = qs.filter(oy=_oy(oy))
            except ValueError as e:
                return _xato(str(e))
        if request.query_params.get("guruh"):
            qs = qs.filter(guruh_id=request.query_params["guruh"])
        if request.query_params.get("filial"):
            qs = qs.filter(filial_id=request.query_params["filial"])
        if request.query_params.get("holat"):
            qs = qs.filter(holat=request.query_params["holat"])
        qidiruv = (request.query_params.get("q") or "").strip()
        if qidiruv:
            # Qidiruv AVVALO LMS'dagi tirik maydonlar bo'yicha: admin
            # ismni saytda tuzatsa, CRM'da ham yangi nom bilan topilishi
            # kerak. Snapshot (`talaba_ism`) ham qo'shiladi — o'chirilgan
            # talabaning yozuvi faqat shu orqali topiladi.
            qs = qs.filter(
                Q(talaba__first_name__icontains=qidiruv)
                | Q(talaba__last_name__icontains=qidiruv)
                | Q(talaba__username__icontains=qidiruv)
                | Q(guruh__name__icontains=qidiruv)
                | Q(talaba_ism__icontains=qidiruv)
                | Q(guruh_nomi__icontains=qidiruv)
            )

        hisoblar = list(qs[:1000])
        balanslar = mantiq.balanslarni_ol({h.talaba_id for h in hisoblar if h.talaba_id})
        return Response(
            [
                _hisob_dict(h, tolangan=h.tolangan, balans=balanslar.get(h.talaba_id))
                for h in hisoblar
            ]
        )

    def post(self, request):
        """Qo'lda hisob — boshlang'ich (eski) qarzlar uchun (TZ 4.7).

        Tizim yoqilgan kunda ba'zi talabalarning eski qarzi bo'ladi.
        Avtomatik generatsiya `Sozlama.boshlangich_oy`dan oldinga
        o'tmaydi, shuning uchun eski qarz shu yo'l bilan kiritiladi.
        Yaratilgach u oddiy hisobdek ishlaydi — to'lash ham, chegirma
        bilan yopish ham mumkin.
        """
        try:
            oy = _oy(request.data.get("oy"))
            summa = _son(request.data.get("summa"), "summa")
        except ValueError as e:
            return _xato(str(e))
        if summa <= 0:
            return _xato("Summa noldan katta bo'lishi kerak")

        talaba = get_object_or_404(User, pk=request.data.get("talaba_id"))
        guruh = get_object_or_404(Guruh, pk=request.data.get("guruh_id"))
        if Hisob.objects.filter(talaba=talaba, guruh=guruh, oy=oy).exists():
            return _xato("Bu talabaga shu guruhda shu oy uchun hisob allaqachon bor")

        moliya = getattr(guruh, "moliya", None)
        hisob = Hisob.objects.create(
            talaba=talaba,
            talaba_ism=talaba.get_full_name() or talaba.username,
            guruh=guruh,
            guruh_nomi=guruh.name,
            filial=moliya.filial if moliya else None,
            oy=oy,
            summa=summa,
            holat=Hisob.Holat.QARZDOR,
            qolda=True,
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=hisob,
            obyekt_turi="CRM Hisob (qo'lda)",
            snapshot={"talaba": hisob.talaba_ism, "guruh": hisob.guruh_nomi,
                      "oy": str(oy), "summa": str(summa)},
        )
        return Response(_hisob_dict(hisob), status=201)


class HisobDetailView(CrmView):
    """Hisob summasini tuzatish — FAQAT owner.

    Kerak bo'ladigan holatlar: narx xato kiritilgan; bitta talabaga
    boshqacha kelishilgan; oyda kutilganidan kam dars bo'lgan. Busiz
    yagona qurol `chegirma` bo'lardi, u esa hisobotdagi chegirma
    ustunini ifloslaydi va markaz bermagan chegirmani ko'rsatadi.
    """

    permission_classes = CrmView.permission_classes + [FaqatOwner]

    def patch(self, request, pk):
        hisob = get_object_or_404(Hisob, pk=pk)
        try:
            summa = _son(request.data.get("summa"), "summa")
        except ValueError as e:
            return _xato(str(e))
        if summa < 0:
            return _xato("Summa manfiy bo'la olmaydi")

        eski = hisob.summa
        hisob.summa = summa
        hisob.save(update_fields=["summa"])
        mantiq.hisobni_yangila(hisob)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=hisob,
            obyekt_turi="CRM Hisob",
            obyekt_nomi=f"{hisob.talaba_ism} — {hisob.oy:%Y-%m}",
            ozgarishlar={"summa": {"eski": str(eski), "yangi": str(summa)},
                         "izoh": request.data.get("izoh", "")},
        )
        hisob.refresh_from_db()
        return Response(_hisob_dict(hisob))


# ── To'lovlar ────────────────────────────────────────────────────────


class TolovlarView(CrmView):
    def get(self, request):
        """To'lov tarixi.

        `hisoblar=1` bo'lsa — hisob-fakturalar ham qo'shiladi
        (SoffCRM'dagidek bitta ro'yxatda), admin ko'nikkan ko'rinish.
        """
        qs = Tolov.objects.select_related("hisob", "kim_kiritdi", "talaba", "guruh").all()
        try:
            dan = _sana(request.query_params.get("dan"), "dan", majburiy=False)
            gacha = _sana(request.query_params.get("gacha"), "gacha", majburiy=False)
        except ValueError as e:
            return _xato(str(e))
        if dan:
            qs = qs.filter(sana__gte=dan)
        if gacha:
            qs = qs.filter(sana__lte=gacha)
        if request.query_params.get("guruh"):
            qs = qs.filter(guruh_id=request.query_params["guruh"])
        if request.query_params.get("talaba"):
            qs = qs.filter(talaba_id=request.query_params["talaba"])
        if request.query_params.get("turi"):
            qs = qs.filter(turi=request.query_params["turi"])

        qatorlar = [_tolov_dict(t) for t in qs[:2000]]

        if request.query_params.get("hisoblar") == "1":
            hisoblar = Hisob.objects.select_related("talaba", "guruh").all()
            if dan:
                hisoblar = hisoblar.filter(oy__gte=mantiq.oy_boshi(dan))
            if gacha:
                hisoblar = hisoblar.filter(oy__lte=gacha)
            if request.query_params.get("guruh"):
                hisoblar = hisoblar.filter(guruh_id=request.query_params["guruh"])
            if request.query_params.get("talaba"):
                hisoblar = hisoblar.filter(talaba_id=request.query_params["talaba"])
            qatorlar += [
                {
                    "id": f"h{h.id}",
                    "talaba_id": h.talaba_id,
                    "talaba": _tirik_talaba(h),
                    "guruh_id": h.guruh_id,
                    "guruh": _tirik_guruh(h),
                    "hisob_id": h.id,
                    "oy": h.oy,
                    "sana": h.oy,
                    "summa": h.summa,
                    "turi": "hisob",
                    "turi_nomi": "Qarzdorlik",
                    # Holat — talaba kartasidagi birlashgan ro'yxatda
                    # "To'lov qilish" tugmasi faqat to'lanmagan oyga chiqishi uchun.
                    "holat": h.holat,
                    "izoh": "Qo'lda kiritilgan" if h.qolda else "",
                    "kim": None,
                    "vaqt": h.created_at,
                }
                for h in hisoblar[:2000]
            ]
            qatorlar.sort(key=lambda x: (x["sana"], str(x["id"])), reverse=True)

        return Response(qatorlar)

    def post(self, request):
        try:
            summa = _son(request.data.get("summa"), "summa")
            sana = _sana(request.data.get("sana") or timezone.localdate().isoformat(), "sana")
        except ValueError as e:
            return _xato(str(e))
        if summa <= 0:
            return _xato("Summa noldan katta bo'lishi kerak")

        turi = request.data.get("turi") or Tolov.Turi.TOLOV
        if turi not in dict(Tolov.Turi.choices):
            return _xato("Noma'lum to'lov turi")

        talaba = get_object_or_404(User, pk=request.data.get("talaba_id"))
        guruh = get_object_or_404(Guruh, pk=request.data.get("guruh_id"))

        hisob = None
        if request.data.get("hisob_id"):
            hisob = get_object_or_404(Hisob, pk=request.data["hisob_id"])
        elif request.data.get("oy") and turi != Tolov.Turi.QAYTARISH:
            # `qaytarish` ATAYLAB oyga bog'lanmaydi — u umumiy hisob-kitob
            # (TZ 3.8), oy holatini o'zgartirmaydi.
            try:
                hisob = Hisob.objects.filter(
                    talaba=talaba, guruh=guruh, oy=_oy(request.data["oy"])
                ).first()
            except ValueError as e:
                return _xato(str(e))

        tolov = Tolov.objects.create(
            talaba=talaba,
            talaba_ism=talaba.get_full_name() or talaba.username,
            guruh=guruh,
            guruh_nomi=guruh.name,
            hisob=hisob,
            sana=sana,
            summa=summa,
            turi=turi,
            izoh=(request.data.get("izoh") or "").strip()[:300],
            kim_kiritdi=request.user,
        )
        if hisob is not None:
            mantiq.hisobni_yangila(hisob)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=tolov,
            obyekt_turi="CRM To'lov",
            snapshot={"talaba": tolov.talaba_ism, "guruh": tolov.guruh_nomi,
                      "turi": turi, "summa": str(summa), "sana": str(sana),
                      "oy": str(hisob.oy) if hisob else None},
        )
        return Response(_tolov_dict(tolov), status=201)


class TolovDetailView(CrmView):
    """To'lov yozuvini o'chirish — FAQAT owner, audit'ga yoziladi.

    Chegirmani bekor qilish ham shu yo'l bilan: yozuv o'chgach
    `hisobni_yangila()` qayta chaqiriladi va qarz tiklanadi.
    """

    permission_classes = CrmView.permission_classes + [FaqatOwner]

    def patch(self, request, pk):
        """Summa / sana / izohni tuzatish (SoffCRM'dagi qalam). Turi va
        talaba O'ZGARMAYDI — ular o'zgarsa bu boshqa yozuv, eskisini
        o'chirib yangisini kiritish kerak."""
        tolov = get_object_or_404(Tolov, pk=pk)
        eski = {"summa": str(tolov.summa), "sana": str(tolov.sana), "izoh": tolov.izoh}
        try:
            if "summa" in request.data:
                summa = _son(request.data.get("summa"), "summa")
                if summa <= 0:
                    return _xato("summa: musbat bo'lsin")
                tolov.summa = summa
            if "sana" in request.data:
                tolov.sana = _sana(request.data.get("sana"), "sana")
        except ValueError as e:
            return _xato(str(e))
        if "izoh" in request.data:
            tolov.izoh = (request.data.get("izoh") or "").strip()[:300]
        tolov.save(update_fields=["summa", "sana", "izoh"])
        if tolov.hisob_id:
            mantiq.hisobni_yangila(tolov.hisob)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=tolov.hisob or request.user,
            obyekt_turi="CRM To'lov",
            obyekt_nomi=f"{tolov.talaba_ism} — {tolov.turi} {tolov.summa}",
            eski_qiymatlar=eski,
            yangi_qiymatlar={"summa": str(tolov.summa), "sana": str(tolov.sana), "izoh": tolov.izoh},
        )
        return Response(_tolov_dict(tolov))

    def delete(self, request, pk):
        tolov = get_object_or_404(Tolov, pk=pk)
        hisob = tolov.hisob
        snapshot = {"talaba": tolov.talaba_ism, "guruh": tolov.guruh_nomi,
                    "turi": tolov.turi, "summa": str(tolov.summa), "sana": str(tolov.sana)}
        tolov.delete()
        if hisob is not None:
            mantiq.hisobni_yangila(hisob)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt=hisob or request.user,
            obyekt_turi="CRM To'lov",
            obyekt_nomi=f"{snapshot['talaba']} — {snapshot['turi']} {snapshot['summa']}",
            snapshot=snapshot,
        )
        return Response({"detail": "O'chirildi"})


# ── Talaba kartasi ───────────────────────────────────────────────────


class TalabalarView(CrmView):
    """CRM'dagi barcha talabalar — hisobi BO'LMAGANLARI ham.

    Ro'yxat ATAYLAB `Hisob`dan emas, `AzolikMoliya`dan yig'iladi: sinov
    yoki muzlatilgan talabaga hisob ochilmaydi, lekin ular ham CRM'da
    ko'rinishi kerak — aks holda admin ularni umuman topa olmaydi va
    holatini o'zgartira olmaydi.
    """

    def get(self, request):
        qs = (
            AzolikMoliya.objects.select_related(
                "azolik__talaba", "azolik__guruh", "azolik__guruh__moliya"
            )
            .filter(azolik__guruh__faol=True)
        )
        if request.query_params.get("filial"):
            qs = qs.filter(azolik__guruh__moliya__filial_id=request.query_params["filial"])
        qidiruv = (request.query_params.get("q") or "").strip()
        if qidiruv:
            qs = qs.filter(
                Q(azolik__talaba__first_name__icontains=qidiruv)
                | Q(azolik__talaba__last_name__icontains=qidiruv)
                | Q(azolik__talaba__username__icontains=qidiruv)
            )
        if request.query_params.get("holat"):
            qs = qs.filter(holat=request.query_params["holat"])

        azoliklar = list(qs[:2000])
        balanslar = mantiq.balanslarni_ol({a.azolik.talaba_id for a in azoliklar})

        talabalar = {}
        for am in azoliklar:
            talaba = am.azolik.talaba
            yozuv = talabalar.setdefault(
                talaba.id,
                {
                    "id": talaba.id,
                    "ism": talaba.get_full_name() or talaba.username,
                    "telefon": talaba.telefon,
                    "balans": balanslar.get(talaba.id, NOL),
                    "guruhlar": [],
                },
            )
            yozuv["guruhlar"].append(
                {
                    "azolik_moliya_id": am.id,
                    "guruh_id": am.azolik.guruh_id,
                    "guruh": am.azolik.guruh.name,
                    "holat": am.holat,
                }
            )

        return Response(sorted(talabalar.values(), key=lambda x: x["ism"]))


class HisobotDinamikaView(CrmView):
    """Oylar kesimida dinamika — "Hisobotlar" bo'limi uchun.

    `HisobotView` BITTA oyni guruhlar kesimida ko'rsatadi; bu esa bir
    necha oyni yonma-yon. Ikkalasi boshqa savolga javob beradi: birinchisi
    "shu oyda kim qarzdor", ikkinchisi "yig'ilish yaxshilanyaptimi".
    """

    ENG_KOP_OY = 24

    def get(self, request):
        try:
            oylar_soni = min(int(request.query_params.get("oylar") or 12), self.ENG_KOP_OY)
        except ValueError:
            return _xato("oylar: son bo'lishi kerak")
        filial_id = request.query_params.get("filial")

        oxirgi = mantiq.oy_boshi(timezone.localdate())
        # Tizim yoqilgan oydan OLDINGI oylar ko'rsatilmaydi: u yerda
        # ma'lumot bo'lishi mumkin emas, nol qatorlar esa "o'sha oyda
        # hech kim to'lamagan" degan yolg'on taassurot beradi.
        boshlangich = mantiq.sozlama_ol().boshlangich_oy
        oylar = []
        oy = oxirgi
        for _ in range(max(oylar_soni, 1)):
            if oy < boshlangich:
                break
            oylar.append(oy)
            oy = mantiq.oy_boshi(oy - timedelta(days=1))
        oylar.reverse()
        if not oylar:
            oylar = [oxirgi]

        hisoblar = Hisob.objects.filter(oy__gte=oylar[0])
        tolovlar = Tolov.objects.filter(hisob__oy__gte=oylar[0])
        if filial_id:
            hisoblar = hisoblar.filter(filial_id=filial_id)
            tolovlar = tolovlar.filter(hisob__filial_id=filial_id)

        hisoblangan = {
            q["oy"]: q for q in hisoblar.values("oy").annotate(
                jami=Sum("summa", default=NOL), talabalar=Count("talaba", distinct=True)
            )
        }
        pul = {
            q["hisob__oy"]: q for q in tolovlar.values("hisob__oy").annotate(
                olingan=Sum("summa", filter=Q(turi=Tolov.Turi.TOLOV), default=NOL),
                chegirma=Sum("summa", filter=Q(turi=Tolov.Turi.CHEGIRMA), default=NOL),
                bonus=Sum("summa", filter=Q(turi=Tolov.Turi.BONUS), default=NOL),
            )
        }

        qatorlar = []
        for oy in oylar:
            h = hisoblangan.get(oy, {})
            p = pul.get(oy, {})
            jami = h.get("jami", NOL)
            olingan = p.get("olingan", NOL)
            chegirma = p.get("chegirma", NOL)
            bonus = p.get("bonus", NOL)
            qatorlar.append(
                {
                    "oy": oy,
                    "talabalar": h.get("talabalar", 0),
                    "hisoblangan": jami,
                    "olingan": olingan,
                    "chegirma": chegirma,
                    "bonus": bonus,
                    "qarz": jami - olingan - chegirma - bonus,
                    "yigilish_foizi": round(float(olingan / jami * 100), 1) if jami else 0.0,
                }
            )
        return Response(qatorlar)


class TalabaView(CrmView):
    def get(self, request, pk):
        talaba = get_object_or_404(User, pk=pk)
        hisoblar = list(
            _tolangan_bilan(
                Hisob.objects.filter(talaba=talaba).select_related(
                    "filial", "talaba", "guruh"
                )
            )
        )
        tolovlar = Tolov.objects.filter(talaba=talaba).select_related(
            "hisob", "kim_kiritdi", "talaba", "guruh"
        )

        azoliklar = (
            AzolikMoliya.objects.filter(azolik__talaba=talaba)
            .select_related("azolik__guruh__moliya", "azolik__guruh__daraja__crm_narxi", "azolik__talaba")
            .prefetch_related("azolik__guruh__crm_jadval")
        )

        guruhlar = []
        for am in azoliklar:
            guruh = am.azolik.guruh
            guruhlar.append(
                {
                    **_azolik_dict(am, balans=mantiq.balans(talaba, guruh=guruh)),
                    # O'qituvchi — SoffCRM'dagi guruh kartasida ko'rsatiladi,
                    # sayt ma'lumoti, CRM faqat o'qiydi.
                    "oqituvchi": (guruh.oqituvchi.get_full_name() or guruh.oqituvchi.username)
                    if guruh.oqituvchi_id else None,
                    "jadval": [_jadval_dict(j) for j in guruh.crm_jadval.all()],
                    "darslar_taqvimi": _darslar_taqvimi(am, hisoblar),
                    "keyingi_tolov": mantiq.keyingi_tolov_sanasi(talaba, guruh),
                }
            )

        # Talabaning UMUMIY o'quv natijasi (SoffCRM kartasidagi "Baho").
        # Bu yerda `stats.services.talaba_statistikasi` QAYTA
        # ISHLATILADI — u BITTA talaba uchun yozilgan va aynan shu
        # holatda o'rinli (guruh ro'yxatida esa u N+1 bo'lardi, shuning
        # uchun `GuruhNatijalarView`da to'plam so'rovlar ishlatilgan).
        stat = talaba_statistikasi(talaba)
        natijalar = {
            "writing_band": _yaxlit(stat["writing"]["ortacha_band"]),
            "speaking_band": _yaxlit(stat["speaking"]["ortacha_band"]),
            "listening_foiz": stat["listening"]["ortacha_foiz"],
            "reading_foiz": stat["reading"]["ortacha_foiz"],
            "mashq_soni": stat["listening"]["jami_yechildi"] + stat["reading"]["jami_yechildi"],
            "keldi": stat["davomat"]["keldi"],
            "kelmadi": stat["davomat"]["kelmadi"],
        }
        jami_dars = natijalar["keldi"] + natijalar["kelmadi"]
        natijalar["davomat_foizi"] = (
            round(natijalar["keldi"] / jami_dars * 100) if jami_dars else None
        )

        return Response(
            {
                "id": talaba.id,
                "ism": talaba.get_full_name() or talaba.username,
                "telefon": talaba.telefon,
                "ota_ona_telefon": talaba.ota_ona_telefon,
                "balans_jami": mantiq.balans(talaba),
                "natijalar": natijalar,
                "guruhlar": guruhlar,
                "hisoblar": [_hisob_dict(h, tolangan=h.tolangan) for h in hisoblar],
                "tolovlar": [_tolov_dict(t) for t in tolovlar],
            }
        )


def _darslar_taqvimi(am, hisoblar):
    """Joriy oyning dars sanalari va ularning to'lov holati.

    Rang oyning hisobidan olinadi. Hisob umuman yo'q bo'lsa (kelajakdagi
    oy) — "kutilayotgan" (kulrang): aks holda kelajakdagi darslar qizil
    chiqib, hamma qarzdorga o'xshab ketardi (TZ 6.6).
    """
    oy = mantiq.oy_boshi(timezone.localdate())
    guruh = am.azolik.guruh
    kunlar = mantiq.oylik_dars_kunlari(guruh, oy)
    talaba_kunlar = set(mantiq.talaba_dars_kunlari(am, oy, kunlar))

    hisob = next(
        (h for h in hisoblar if h.guruh_id == guruh.id and h.oy == oy), None
    )
    holat = hisob.holat if hisob else "kutilayotgan"
    return [
        {"sana": kun, "holat": holat if kun in talaba_kunlar else "kutilayotgan"}
        for kun in kunlar
    ]


# ── Hisobot ──────────────────────────────────────────────────────────


def _hisobot_qatorlari(oy=None, filial_id=None):
    """Filial va guruh kesimida moliyaviy sarhisob.

    MUHIM: "olingan pul" FAQAT `turi="tolov"` bo'yicha sanaladi.
    Chegirma va bonus alohida ustunlarda — aks holda hisobot markaz
    OLMAGAN pulni daromad qilib ko'rsatardi (TZ 3.8).
    """
    hisoblar = Hisob.objects.all()
    tolovlar = Tolov.objects.all()
    if oy:
        hisoblar = hisoblar.filter(oy=oy)
        tolovlar = tolovlar.filter(hisob__oy=oy)
    if filial_id:
        hisoblar = hisoblar.filter(filial_id=filial_id)
        tolovlar = tolovlar.filter(hisob__filial_id=filial_id)

    hisoblangan = {
        (q["filial_id"], q["guruh_id"]): q
        for q in hisoblar.values("filial_id", "guruh_id", "guruh_nomi").annotate(
            jami=Sum("summa", default=NOL), soni=Count("id")
        )
    }
    pul = {
        (q["hisob__filial_id"], q["guruh_id"]): q
        for q in tolovlar.values("hisob__filial_id", "guruh_id").annotate(
            olingan=Sum("summa", filter=Q(turi=Tolov.Turi.TOLOV), default=NOL),
            chegirma=Sum("summa", filter=Q(turi=Tolov.Turi.CHEGIRMA), default=NOL),
            bonus=Sum("summa", filter=Q(turi=Tolov.Turi.BONUS), default=NOL),
            qaytarilgan=Sum("summa", filter=Q(turi=Tolov.Turi.QAYTARISH), default=NOL),
        )
    }
    filial_nomlari = dict(Filial.objects.values_list("id", "nomi"))

    qatorlar = []
    for kalit, h in hisoblangan.items():
        p = pul.get(kalit, {})
        jami = h["jami"]
        olingan = p.get("olingan", NOL)
        chegirma = p.get("chegirma", NOL)
        bonus = p.get("bonus", NOL)
        qatorlar.append(
            {
                "filial_id": kalit[0],
                "filial": filial_nomlari.get(kalit[0]) or "—",
                "guruh_id": kalit[1],
                "guruh": h["guruh_nomi"],
                "talaba_soni": h["soni"],
                "hisoblangan": jami,
                "olingan": olingan,
                "chegirma": chegirma,
                "bonus": bonus,
                "qaytarilgan": p.get("qaytarilgan", NOL),
                "qarz": jami - olingan - chegirma - bonus,
                # Yig'ilish foizi — HAQIQIY pul bo'yicha (chegirma
                # qo'shilmaydi), aks holda ko'rsatkich soxta yaxshi chiqardi.
                "yigilish_foizi": round(float(olingan / jami * 100), 1) if jami else 0.0,
            }
        )
    qatorlar.sort(key=lambda x: (x["filial"], x["guruh"]))
    return qatorlar


class HisobotView(CrmView):
    def get(self, request):
        oy = None
        if request.query_params.get("oy"):
            try:
                oy = _oy(request.query_params["oy"])
            except ValueError as e:
                return _xato(str(e))
        qatorlar = _hisobot_qatorlari(oy=oy, filial_id=request.query_params.get("filial"))

        jami = {
            kalit: sum((q[kalit] for q in qatorlar), NOL)
            for kalit in ("hisoblangan", "olingan", "chegirma", "bonus", "qaytarilgan", "qarz")
        }
        jami["yigilish_foizi"] = (
            round(float(jami["olingan"] / jami["hisoblangan"] * 100), 1)
            if jami["hisoblangan"]
            else 0.0
        )
        return Response({"qatorlar": qatorlar, "jami": jami})


# ── Ogohlantirishlar ─────────────────────────────────────────────────


class EksportView(CrmView):
    """Uch varaqli .xlsx — qarzdorlar, to'lovlar, hisobot.

    Filtrlar `HisoblarView` bilan bir xil ishlaydi, ya'ni ekranda
    ko'rinayotgan narsa aynan shu holda faylga tushadi.
    """

    def get(self, request):
        oy = None
        if request.query_params.get("oy"):
            try:
                oy = _oy(request.query_params["oy"])
            except ValueError as e:
                return _xato(str(e))
        filial_id = request.query_params.get("filial")

        hisoblar_qs = _tolangan_bilan(Hisob.objects.select_related("filial", "talaba", "guruh").all())
        tolovlar_qs = Tolov.objects.select_related("hisob", "kim_kiritdi", "talaba", "guruh").all()
        if oy:
            hisoblar_qs = hisoblar_qs.filter(oy=oy)
            tolovlar_qs = tolovlar_qs.filter(hisob__oy=oy)
        if filial_id:
            hisoblar_qs = hisoblar_qs.filter(filial_id=filial_id)
            tolovlar_qs = tolovlar_qs.filter(hisob__filial_id=filial_id)
        if request.query_params.get("holat"):
            hisoblar_qs = hisoblar_qs.filter(holat=request.query_params["holat"])
        # Talaba kartasidagi "Excel" — faqat shu talabaning yozuvlari.
        if request.query_params.get("talaba"):
            hisoblar_qs = hisoblar_qs.filter(talaba_id=request.query_params["talaba"])
            tolovlar_qs = tolovlar_qs.filter(talaba_id=request.query_params["talaba"])

        kitob = eksport.qarzdorlar_kitobi(
            hisoblar=[_hisob_dict(h, tolangan=h.tolangan) for h in hisoblar_qs[:5000]],
            hisobot_qatorlari=_hisobot_qatorlari(oy=oy, filial_id=filial_id),
            tolovlar=[_tolov_dict(t) for t in tolovlar_qs[:5000]],
        )
        nomi = f"CRM-moliya-{oy:%Y-%m}.xlsx" if oy else "CRM-moliya.xlsx"
        return eksport.javob_qil(kitob, nomi)


class OgohlantirishlarView(CrmView):
    """Sozlanmagan guruhlar — narxi yoki dars jadvali yo'q.

    Bunday guruhlarga hisob OCHILMAYDI, ya'ni ular jimgina pul
    yo'qotadi. Shuning uchun alohida ro'yxat kerak.
    """

    def get(self, request):
        guruhlar = (
            Guruh.objects.filter(faol=True)
            .select_related("moliya", "daraja__crm_narxi")
            .prefetch_related("crm_jadval")
            .annotate(_talaba_soni=Count("talabalar", distinct=True))
        )
        natija = []
        for g in guruhlar:
            if g._talaba_soni == 0:
                continue  # a'zosi yo'q guruh — muammo emas
            sabablar = []
            if mantiq.guruh_narxi(g)[0] is None:
                sabablar.append("narx yo'q")
            if not g.crm_jadval.all():
                sabablar.append("dars jadvali yo'q")
            if getattr(g, "moliya", None) is None:
                sabablar.append("CRM'da sozlanmagan")
            if sabablar:
                natija.append(
                    {"guruh_id": g.id, "guruh": g.name,
                     "talaba_soni": g._talaba_soni, "sabablar": sabablar}
                )
        return Response(natija)
