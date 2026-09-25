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
from django.utils.dateparse import parse_datetime
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
    GuruhdanChiqish,
    Hisob,
    KursNarxi,
    Lid,
    TalabaProfil,
    Tolov,
    Xona,
)
from .filial import (
    cheklanganmi, filial_korinadimi, filial_q, filial_tekshir, guruh_q, guruh_tekshir, lid_tekshir,
    ruxsat_filiallari, talaba_boshqa_filialda, talaba_guruhga_bogliqmi, talaba_korinadimi, talaba_tekshir,
    tolov_filiali_q, tolov_q,
)
from .permissions import CrmView, FaqatOwner
from .ruxsatlar import ruxsatlar

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


def _ruxsatsiz(request, kalit, matn="Bu amalga ruxsat yo'q"):
    """Amal darajasidagi ruxsat (`guruhlar.tahrirlash` kabi). Bo'lim
    darajasini `CrmRuxsati` tekshiradi; bu — undan keyingi qadam.
    Ruxsat yo'q bo'lsa 403 javob, bor bo'lsa `None`."""
    return None if kalit in ruxsatlar(request.user) else _xato(matn, kod=403)


def _markaz_sozlamasi_taqiq(request):
    """Butun markazga ta'sir qiladigan sozlama (kurs narxi, filiallar,
    rollar) — filialga bog'langan xodim faqat KO'RADI (2026-09-23)."""
    if cheklanganmi(request.user):
        return _xato("Bu sozlama butun markazga ta'sir qiladi — uni faqat owner o'zgartiradi", kod=403)
    return None


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
        "lid_id": e.lid_id,
        "eslatish_vaqti": e.eslatish_vaqti,
        "bajarildi": e.bajarildi,
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
        "oqituvchi_id": g.oqituvchi_id,
        # "Support ustoz" ustuni (video 13:40) — yordamchi o'qituvchilar.
        "yordamchilar": [
            o.oqituvchi.get_full_name() or o.oqituvchi.username
            for o in g.crm_oqituvchilar.all() if o.turi == "yordamchi"
        ],
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
        "baholash_tizimi": moliya.baholash_tizimi if moliya else "",
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
        # Saytdagi Kurslar bo'limida qaysi Unit'dan boshlaydi (LMS
        # `GuruhAzoligi.boshlanish_unit`; bo'sh — Unit 1, odatiy tartib).
        "boshlanish_unit_id": am.azolik.boshlanish_unit_id,
        "muzlatish_sana": am.muzlatish_sana,
        "muzlatish_izoh": am.muzlatish_izoh,
        "balans": balans,
    }


def daraja_unitlari(guruh):
    """Guruh darajasining Unit'lari — `boshlanish_unit` shulardan biri
    bo'la oladi. Qoida LMS'dagi bilan AYNAN bir xil
    (`academics.views.GuruhAzoligiDetailView`): daraja bolasi,
    `unit_darsi=True`."""
    if not guruh.daraja_id:
        return KursTugun.objects.none()
    return KursTugun.objects.filter(parent_id=guruh.daraja_id, unit_darsi=True).order_by("tartib", "id")


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
        "izoh": h.izoh,
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
        "usul": t.usul,
        "usul_nomi": t.get_usul_display() if t.usul else "",
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
    bolim = "sozlamalar"
    oqish_ochiq = True

    def get(self, request):
        qs = Filial.objects.all()
        # Filialga bog'langan xodim — faqat o'z filiallari (tanlovda ham).
        ruxsat = ruxsat_filiallari(request.user)
        if ruxsat is not None:
            qs = qs.filter(id__in=ruxsat)
        if request.query_params.get("faqat_faol") == "1":
            qs = qs.filter(faol=True)
        return Response([_filial_dict(f) for f in qs])

    def post(self, request):
        if xato := _ruxsatsiz(request, "sozlamalar.filiallar") or _markaz_sozlamasi_taqiq(request):
            return xato
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
    bolim = "sozlamalar"

    def patch(self, request, pk):
        if xato := _ruxsatsiz(request, "sozlamalar.filiallar") or _markaz_sozlamasi_taqiq(request):
            return xato
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
    bolim = "sozlamalar"
    oqish_ochiq = True

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
        if xato := _ruxsatsiz(request, "sozlamalar.narxlar") or _markaz_sozlamasi_taqiq(request):
            return xato
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
    bolim = "guruhlar"
    # Ro'yxatni o'qish hamma CRM xodimiga: marketolog lidni guruhga
    # qo'shadi, kassir talaba kartasida guruhni tanlaydi (2026-09-23).
    oqish_ochiq = True

    def get(self, request):
        # `?arxiv=1` — arxivlangan guruhlar (video-TZ: arxivlash endi CRM'da).
        qs = (
            Guruh.objects.filter(faol=not request.query_params.get("arxiv"))
            .select_related("daraja", "oqituvchi", "moliya", "moliya__filial", "daraja__crm_narxi")
            .prefetch_related("crm_jadval", "crm_oqituvchilar__oqituvchi")
            .annotate(_talaba_soni=Count("talabalar", distinct=True))
            .order_by("name")
            .filter(guruh_q(request.user))
        )
        filial = request.query_params.get("filial")
        if filial:
            # Filiali hali qo'yilmagan (saytda ochilgan, CRM'da sozlanmagan)
            # guruhlar ham chiqadi (video-TZ 2026-09-25): bosh sahifa ular
            # haqida ogohlantiradi, lekin filial tanlanganda ro'yxatda
            # ko'rinmay, ularni sozlashning iloji qolmasdi.
            qs = qs.filter(Q(moliya__filial_id=filial) | Q(moliya__isnull=True) | Q(moliya__filial__isnull=True))
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

    pk_turi = "guruh"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

    def patch(self, request, pk):
        if xato := _ruxsatsiz(request, "guruhlar.tahrirlash", "Guruhni tahrirlashga ruxsat yo'q"):
            return xato
        guruh = get_object_or_404(Guruh, pk=pk)
        guruh_tekshir(request.user, guruh)
        # Yozuv guruh yaratilganda emas, AYNAN shu yerda paydo bo'ladi —
        # signal ishlatilmaydi (TZ 3.0, 3-qoida).
        moliya, _ = GuruhMoliya.objects.get_or_create(guruh=guruh)
        eski = _guruh_dict(guruh)

        try:
            if "filial_id" in request.data:
                qiymat = request.data["filial_id"]
                filial_tekshir(request.user, qiymat)
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
            if "baholash_tizimi" in request.data:
                tizim = request.data.get("baholash_tizimi") or ""
                if tizim not in ("", "5", "10", "100"):
                    raise ValueError("Baholash tizimi noto'g'ri")
                moliya.baholash_tizimi = tizim
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
    bolim = "sozlamalar"
    oqish_ochiq = True

    def get(self, request):
        qs = Xona.objects.select_related("filial").filter(filial_q(request.user, "filial", filialsiz_ham=False))
        if request.query_params.get("filial"):
            qs = qs.filter(filial_id=request.query_params["filial"])
        if request.query_params.get("faqat_faol") == "1":
            qs = qs.filter(faol=True)
        return Response([_xona_dict(x) for x in qs])

    def post(self, request):
        if xato := _ruxsatsiz(request, "sozlamalar.filiallar"):
            return xato
        nomi = (request.data.get("nomi") or "").strip()
        if not nomi:
            return _xato("Xona nomi kerak")
        try:
            filial_tekshir(request.user, request.data.get("filial_id"))
        except ValueError as e:
            return _xato(str(e), kod=403)
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
    bolim = "sozlamalar"

    def patch(self, request, pk):
        if xato := _ruxsatsiz(request, "sozlamalar.filiallar"):
            return xato
        xona = get_object_or_404(Xona, filial_q(request.user, "filial", filialsiz_ham=False), pk=pk)
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

        xonalar = Xona.objects.filter(faol=True).filter(
            filial_q(request.user, "filial", filialsiz_ham=False)
        ).select_related("filial")
        darslar = DarsJadvali.objects.select_related(
            "guruh", "guruh__oqituvchi", "guruh__moliya", "guruh__moliya__filial", "xona", "guruh__daraja"
        ).filter(guruh__faol=True).filter(guruh_q(request.user, "guruh__"))
        sonlar = {}
        for x in (
            GuruhAzoligi.objects.filter(guruh__faol=True)
            .values("guruh_id")
            .annotate(jami=Count("id"), faol=Count("id", filter=Q(moliya__holat=AzolikMoliya.Holat.FAOL)))
        ):
            sonlar[x["guruh_id"]] = x
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
                        # Tooltip (video 16:46): kurs, o'quvchilar soni, xona sig'imi.
                        "kurs": d.guruh.daraja.nomi if d.guruh.daraja_id else None,
                        "jami": sonlar.get(d.guruh_id, {}).get("jami", 0),
                        "faol": sonlar.get(d.guruh_id, {}).get("faol", 0),
                        "sigim": d.xona.sigimi if d.xona_id else None,
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


def jadvalni_tekshir(guruh, kunlar, user=None):
    """Haftalik jadvalni tekshiradi va `DarsJadvali` obyektlarini
    (hali saqlanmagan) qaytaradi: `(yangilar, None)` yoki `(None, xato)`.

    Guruh yaratishda ham (`crm.boshqaruv`), jadval tahririda ham AYNAN
    shu funksiya ishlaydi — xona to'qnashuvi qoidasi bitta joyda.

    `user` — filial cheklovi: filial xodimi faqat o'z filiali xonasini
    tanlaydi, to'qnashuv xabarida boshqa filial guruhining nomi chiqmaydi.
    """
    if not isinstance(kunlar, list):
        return None, "jadval ro'yxat bo'lishi kerak"

    yangilar = []
    korilgan = set()
    for band in kunlar:
        try:
            hafta_kuni = int(band.get("hafta_kuni"))
        except (TypeError, ValueError):
            return None, "hafta_kuni 0..6 oralig'ida son bo'lsin"
        if hafta_kuni not in dict(DarsJadvali.HaftaKuni.choices):
            return None, "hafta_kuni 0..6 oralig'ida bo'lsin"
        try:
            boshlanish = _vaqt(band.get("boshlanish_vaqti"), "boshlanish_vaqti")
            tugash = _vaqt(band.get("tugash_vaqti"), "tugash_vaqti")
        except ValueError as e:
            return None, str(e)
        if tugash <= boshlanish:
            return None, "Dars tugash vaqti boshlanish vaqtidan keyin bo'lsin"
        kalit = (hafta_kuni, boshlanish)
        if kalit in korilgan:
            return None, "Bir kunda bir xil vaqt ikki marta kiritilgan"
        korilgan.add(kalit)

        xona_id = band.get("xona_id") or None
        if xona_id:
            xona = Xona.objects.filter(pk=xona_id).first()
            if xona is None or (user is not None and ruxsat_filiallari(user) is not None
                                and xona.filial_id not in ruxsat_filiallari(user)):
                return None, "Xona topilmadi"
            # BOSHQA guruh bilan to'qnashuv — shu guruhning o'z eski
            # yozuvlari hisobga olinmaydi (ular pastda o'chiriladi).
            raqib = _toqnashuv_bormi(guruh, hafta_kuni, boshlanish, tugash, xona_id)
            if raqib is not None:
                if user is not None and not filial_korinadimi(
                    user, getattr(getattr(raqib.guruh, "moliya", None), "filial_id", None)
                ):
                    return None, f"{xona.nomi}: {raqib.get_hafta_kuni_display()} shu vaqtda band"
                return None, (
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
                return None, "Bir xonada ikkita dars bir vaqtda kiritilgan"
    return yangilar, None


class GuruhJadvalView(CrmView):
    """Guruhning haftalik dars kunlari — to'liq almashtiriladi (PUT)."""

    pk_turi = "guruh"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

    def put(self, request, pk):
        if javob := _ruxsatsiz(request, "guruhlar.tahrirlash", "Guruhni tahrirlashga ruxsat yo'q"):
            return javob
        guruh = get_object_or_404(Guruh, pk=pk)
        yangilar, xato = jadvalni_tekshir(guruh, request.data.get("jadval") or [], request.user)
        if xato:
            return _xato(xato)

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


class GuruhUnitlariView(CrmView):
    """A'zolar jadvalidagi "Boshlanish uniti" tanlovi uchun."""

    pk_turi = "guruh"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

    def get(self, request, pk):
        guruh = get_object_or_404(Guruh, pk=pk)
        return Response([{"id": u.id, "nomi": u.nomi} for u in daraja_unitlari(guruh)])


class GuruhAzoliklariView(CrmView):
    pk_turi = "guruh"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

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
        lid_id = request.query_params.get("lid")
        if not guruh_id and not talaba_id and not lid_id:
            return _xato("guruh, talaba yoki lid ko'rsatilishi kerak")
        if any(x and not str(x).isdigit() for x in (guruh_id, talaba_id, lid_id)):
            return _xato("guruh, talaba va lid — son (ID) bo'lishi kerak")
        # Filial cheklovi: boshqa filial yozuvining eslatmalari — 404.
        if guruh_id:
            guruh_tekshir(request.user, get_object_or_404(Guruh.objects.select_related("moliya"), pk=guruh_id))
        if talaba_id:
            talaba_tekshir(request.user, talaba_id, oqish=True)
        if lid_id:
            lid_tekshir(request.user, get_object_or_404(Lid, pk=lid_id), oqish=True)
        if guruh_id:
            qs = qs.filter(guruh_id=guruh_id)
        if talaba_id:
            qs = qs.filter(talaba_id=talaba_id)
        if lid_id:
            qs = qs.filter(lid_id=lid_id)
        return Response([_eslatma_dict(e) for e in qs[:200]])

    def post(self, request):
        matn = (request.data.get("matn") or "").strip()
        if not matn:
            return _xato("Eslatma matni bo'sh bo'lmasin")

        guruh = talaba = lid = None
        if request.data.get("guruh_id"):
            guruh = get_object_or_404(Guruh, pk=request.data["guruh_id"])
        if request.data.get("talaba_id"):
            talaba = get_object_or_404(User, pk=request.data["talaba_id"])
        if request.data.get("lid_id"):
            lid = get_object_or_404(Lid, pk=request.data["lid_id"])
        if guruh is None and talaba is None and lid is None:
            return _xato("Eslatma guruh, talaba yoki lidga bog'lanishi kerak")
        if guruh is not None:
            guruh_tekshir(request.user, guruh)
        if talaba is not None:
            talaba_tekshir(request.user, talaba.id)
        if lid is not None:
            lid_tekshir(request.user, lid)

        eslatish_vaqti = None
        if request.data.get("eslatish_vaqti"):
            eslatish_vaqti = parse_datetime(str(request.data["eslatish_vaqti"]))
            if eslatish_vaqti is None:
                return _xato("eslatish_vaqti: noto'g'ri format")
            if timezone.is_naive(eslatish_vaqti):
                eslatish_vaqti = timezone.make_aware(eslatish_vaqti)

        eslatma = Eslatma.objects.create(
            guruh=guruh, talaba=talaba, lid=lid, matn=matn[:2000], kim=request.user,
            eslatish_vaqti=eslatish_vaqti,
        )
        return Response(_eslatma_dict(eslatma), status=201)


class EslatmaDetailView(CrmView):
    pk_turi = "eslatma"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    def patch(self, request, pk):
        """Eslatmani tahrirlash (video 09:05: "Eslatmani tahrirlash" —
        matn, eslatish vaqti; 2026-09-25 dan "bajarildi"). Faqat O'Z eslatmasini."""
        eslatma = get_object_or_404(Eslatma, pk=pk)
        if eslatma.kim_id != request.user.pk:
            return _xato("Faqat o'z eslatmangizni tahrirlay olasiz", kod=403)
        if "matn" in request.data:
            matn = (request.data.get("matn") or "").strip()
            if not matn:
                return _xato("Eslatma matni bo'sh bo'lmasin")
            eslatma.matn = matn[:2000]
        if "eslatish_vaqti" in request.data:
            xom = request.data.get("eslatish_vaqti")
            vaqt = None
            if xom:
                vaqt = parse_datetime(str(xom))
                if vaqt is None:
                    return _xato("eslatish_vaqti: noto'g'ri format")
                if timezone.is_naive(vaqt):
                    vaqt = timezone.make_aware(vaqt)
            eslatma.eslatish_vaqti = vaqt
        if "bajarildi" in request.data:
            eslatma.bajarildi = bool(request.data["bajarildi"])
        eslatma.save(update_fields=["matn", "eslatish_vaqti", "bajarildi"])
        return Response(_eslatma_dict(eslatma))

    def delete(self, request, pk):
        eslatma = get_object_or_404(Eslatma, pk=pk)
        # O'z eslatmasini har kim o'chira oladi, boshqanikini — faqat
        # owner. Admin hamkasbining izohini jimgina yo'q qila olmasligi
        # kerak.
        if eslatma.kim_id != request.user.pk and not owner_mi(request.user):
            return _xato("Faqat o'z eslatmangizni o'chira olasiz", kod=403)
        eslatma.delete()
        return Response({"detail": "O'chirildi"})


class GuruhNatijalarView(CrmView):
    """Guruh natijalari — FAQAT O'QISH (SoffCRM'dagi BAHO/TEST tablari).

    Natija LMS'da hosil bo'ladi (mashqlar, Writing/Speaking tekshiruvi).
    Bu yerda faqat yig'ma ko'rsatkich.

    Har talaba uchun `stats.services.talaba_statistikasi` chaqirilmaydi:
    u talabaga ~6 ta so'rov qiladi, ya'ni 20 kishilik guruhda 120 so'rov
    bo'lardi. Bu yerda hammasi guruh bo'yicha TO'PLAM so'rovlar bilan —
    guruh kattaligidan qat'i nazar 5 ta so'rov.
    """

    pk_turi = "guruh"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

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


_AZOLIK_AUDIT = ("holat", "boshlanish_sana", "tugash_sana", "narx_talabaga", "boshlanish_unit_id")


class AzolikView(CrmView):
    """A'zolikning moliyaviy holati — holat, sanalar, individual narx."""

    pk_turi = "azolik"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "guruhlar"

    # Maydon -> amal ruxsati (2026-09-23, Shuhrat). Narx va sanalar pulga
    # ta'sir qiladi — faqat `guruhlar.tahrirlash`; holatni (sinov/faol/
    # muzlatish) guruhga o'quvchi qo'shadigan ham o'zgartiradi — u
    # "O'quvchilarni faollashtirish"ni ham boshqaradi.
    _MAYDON_RUXSATI = {
        "holat": ("guruhlar.tahrirlash", "guruhlar.talaba_qoshish"),
        "narx": ("guruhlar.tahrirlash",),
        "boshlanish_sana": ("guruhlar.tahrirlash",),
        "tugash_sana": ("guruhlar.tahrirlash",),
        "boshlanish_unit_id": ("guruhlar.tahrirlash",),
        "muzlatish_sana": ("guruhlar.tahrirlash", "guruhlar.talaba_qoshish"),
        "muzlatish_izoh": ("guruhlar.tahrirlash", "guruhlar.talaba_qoshish"),
    }

    def patch(self, request, pk):
        berilgan = ruxsatlar(request.user)
        for maydon, kerak in self._MAYDON_RUXSATI.items():
            if maydon in request.data and not berilgan.intersection(kerak):
                return _xato("Bu o'zgarishga ruxsat yo'q", kod=403)
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
                # Arxivlash CRM'dan EMAS (Shuhrat, 2026-09-16): talaba
                # guruhdan SAYTDA chiqariladi — a'zolik o'chadi, CRM
                # yozuvi u bilan ketadi, pul tarixi (Hisob/Tolov) qoladi.
                # CRM'da alohida "arxiv" bo'lsa, sayt bilan CRM ikki xil
                # ro'yxat ko'rsatardi.
                if holat == AzolikMoliya.Holat.ARXIV:
                    return _xato("Arxivlash bu yerda emas — guruh sahifasidagi «Guruhdan chiqarish» tugmasidan foydalaning")
                am.holat = holat
            # Muzlatish oynasi: sana (standart — bugun) va izoh. Faqat
            # ma'lumot, hisob-kitobga ta'sir qilmaydi; muzlatishdan
            # chiqqanda tozalanadi.
            if am.holat == AzolikMoliya.Holat.MUZLATILGAN:
                if eski_holat != AzolikMoliya.Holat.MUZLATILGAN or "muzlatish_sana" in request.data:
                    am.muzlatish_sana = (
                        _sana(request.data.get("muzlatish_sana"), "muzlatish_sana", majburiy=False)
                        or timezone.localdate()
                    )
                if "muzlatish_izoh" in request.data:
                    am.muzlatish_izoh = str(request.data.get("muzlatish_izoh") or "").strip()[:300]
            else:
                am.muzlatish_sana = None
                am.muzlatish_izoh = ""
            if "boshlanish_sana" in request.data:
                am.boshlanish_sana = _sana(request.data["boshlanish_sana"], "boshlanish_sana")
            if "tugash_sana" in request.data:
                am.tugash_sana = _sana(request.data["tugash_sana"], "tugash_sana", majburiy=False)
            if "narx" in request.data:
                xom = request.data["narx"]
                am.narx = None if xom in (None, "") else _son(xom, "narx")
            # Boshlanish uniti (2026-09-23): LMS'dagi "Guruhlar" sahifasi
            # admin menyusidan olingani uchun endi CRM'da tanlanadi. Yozuv
            # o'sha LMS jadvaliga (`GuruhAzoligi`) tushadi — `crm -> LMS`.
            yangi_unit = None
            unit_ozgardi = "boshlanish_unit_id" in request.data
            if unit_ozgardi:
                unit_id = request.data.get("boshlanish_unit_id") or None
                if unit_id:
                    yangi_unit = daraja_unitlari(am.azolik.guruh).filter(pk=unit_id).first()
                    if yangi_unit is None:
                        raise ValueError("Bu Unit guruh darajasiga tegishli emas")
        except ValueError as e:
            return _xato(str(e))

        if am.tugash_sana and am.tugash_sana < am.boshlanish_sana:
            return _xato("Tugash sanasi boshlanish sanasidan oldin bo'la olmaydi")

        # Muzlatishdan qayta ochilganda — o'sha oy shu sanadan boshlab
        # hisoblanadi (TZ 4.6).
        if eski_holat == AzolikMoliya.Holat.MUZLATILGAN and am.holat == AzolikMoliya.Holat.FAOL:
            am.qayta_faol_sana = timezone.localdate()

        am.save()
        if unit_ozgardi:
            am.azolik.boshlanish_unit = yangi_unit
            am.azolik.save(update_fields=["boshlanish_unit"])

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
            eski_qiymatlar={k: str(eski[k]) for k in _AZOLIK_AUDIT},
            yangi_qiymatlar={k: str(yangi[k]) for k in _AZOLIK_AUDIT},
        )
        return Response(yangi)


# ── Hisoblar (qarzdorlar) ────────────────────────────────────────────


class HisoblarView(CrmView):
    bolim = "moliya"

    def get(self, request):
        qs = _tolangan_bilan(
            Hisob.objects.select_related("filial", "talaba", "guruh").filter(filial_q(request.user, "filial"))
        )

        oy = request.query_params.get("oy")
        if oy:
            try:
                qs = qs.filter(oy=_oy(oy))
            except ValueError as e:
                return _xato(str(e))
        if request.query_params.get("guruh"):
            qs = qs.filter(guruh_id=request.query_params["guruh"])
        # To'lov oynasidagi "Qaysi oy uchun" tanlovi — shu talaba, shu
        # guruh bo'yicha barcha oylar.
        if request.query_params.get("talaba"):
            qs = qs.filter(talaba_id=request.query_params["talaba"])
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
        if xato := _ruxsatsiz(request, "moliya.hisob"):
            return xato
        try:
            oy = _oy(request.data.get("oy"))
            summa = _son(request.data.get("summa"), "summa")
        except ValueError as e:
            return _xato(str(e))
        if summa <= 0:
            return _xato("Summa noldan katta bo'lishi kerak")

        talaba = get_object_or_404(User, pk=request.data.get("talaba_id"))
        guruh = get_object_or_404(Guruh, pk=request.data.get("guruh_id"))
        guruh_tekshir(request.user, guruh)
        if not talaba_guruhga_bogliqmi(talaba.id, guruh.id):
            return _xato("Talaba bu guruhda o'qimagan")
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
    """Hisob summasini tuzatish ("Qarzdorlikni tahrirlash").

    Kerak bo'ladigan holatlar: narx xato kiritilgan; bitta talabaga
    boshqacha kelishilgan; oyda kutilganidan kam dars bo'lgan. Busiz
    yagona qurol `chegirma` bo'lardi, u esa hisobotdagi chegirma
    ustunini ifloslaydi va markaz bermagan chegirmani ko'rsatadi.

    Avval faqat owner edi; video-TZ (2026-09-25) dan — "Qarzdorlik
    yozuvlari" (`moliya.hisob`) ruxsati borlar ham: qo'lda hisob qo'sha
    oladigan xodim uni tuzata ham olsin. IZOH MAJBURIY — nega
    o'zgargani to'lov tarixida ko'rinsin; o'zgarish audit jurnalida.
    """

    pk_turi = "hisob"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "moliya"

    def patch(self, request, pk):
        if xato := _ruxsatsiz(request, "moliya.hisob", "Qarzdorlikni tahrirlashga ruxsat yo'q"):
            return xato
        hisob = get_object_or_404(Hisob, pk=pk)
        try:
            summa = _son(request.data.get("summa"), "summa")
        except ValueError as e:
            return _xato(str(e))
        if summa < 0:
            return _xato("Summa manfiy bo'la olmaydi")
        if not str(request.data.get("izoh") or "").strip():
            return _xato("Izoh yozilsin — nega o'zgargani to'lov tarixida ko'rinadi")

        eski = hisob.summa
        hisob.summa = summa
        # `qolda` — endi avtomatik qayta hisoblash (chegirma, muzlatish,
        # guruhdan chiqish) bu summaga TEGMAYDI: owner nima yozgan bo'lsa
        # shu qoladi (`mantiq.azolikni_qayta_hisobla`).
        hisob.qolda = True
        hisob.izoh = str(request.data.get("izoh")).strip()[:300]
        hisob.save(update_fields=["summa", "izoh", "qolda"])
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
    bolim = "moliya"

    def get(self, request):
        """To'lov tarixi.

        `hisoblar=1` bo'lsa — hisob-fakturalar ham qo'shiladi
        (SoffCRM'dagidek bitta ro'yxatda), admin ko'nikkan ko'rinish.
        """
        qs = Tolov.objects.select_related("hisob", "kim_kiritdi", "talaba", "guruh").filter(tolov_q(request.user))
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

        tolovlar = list(qs[:2000])
        # Balans — Moliya > To'lovlar ro'yxatida ustun (admin talabi,
        # 2026-09-17). Bitta so'rovda, N+1 emas.
        balanslar = mantiq.balanslarni_ol({t.talaba_id for t in tolovlar if t.talaba_id})
        qatorlar = [
            {**_tolov_dict(t), "balans": balanslar.get(t.talaba_id) if t.talaba_id else None}
            for t in tolovlar
        ]

        if request.query_params.get("hisoblar") == "1":
            hisoblar = Hisob.objects.select_related("talaba", "guruh").filter(filial_q(request.user, "filial"))
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
                    # `qolda` — eski qarz ham, owner tuzatgan summa ham
                    # (ikkalasi ham avtomatik qayta hisoblanmaydi).
                    "izoh": h.izoh or ("Qo'lda belgilangan summa" if h.qolda else ""),
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
        usul = request.data.get("usul") or Tolov.Usul.NAQD
        if usul not in dict(Tolov.Usul.choices):
            return _xato("Noma'lum to'lov usuli")
        if xato := _ruxsatsiz(request, "moliya.qaytarish" if turi == Tolov.Turi.QAYTARISH else "moliya.tolov"):
            return xato

        talaba = get_object_or_404(User, pk=request.data.get("talaba_id"))
        guruh = get_object_or_404(Guruh, pk=request.data.get("guruh_id"))
        guruh_tekshir(request.user, guruh)
        if not talaba_guruhga_bogliqmi(talaba.id, guruh.id):
            return _xato("Talaba bu guruhda o'qimagan")

        hisob = None
        if request.data.get("hisob_id"):
            hisob = get_object_or_404(Hisob, pk=request.data["hisob_id"])
            # Hisob AYNAN shu talaba va guruhniki bo'lishi shart (2026-09-17
            # tekshiruvda topildi): aks holda to'lov bir talabaga yozilib,
            # BOSHQA talabaning oyi "to'landi" bo'lib qolardi.
            if hisob.talaba_id != talaba.id or hisob.guruh_id != guruh.id:
                return _xato("Hisob boshqa talaba yoki guruhga tegishli")
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
            usul=usul,
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

    pk_turi = "tolov"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "moliya"

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
        if "usul" in request.data:
            if request.data["usul"] not in dict(Tolov.Usul.choices):
                return _xato("Noma'lum to'lov usuli")
            tolov.usul = request.data["usul"]
        tolov.save(update_fields=["summa", "sana", "izoh", "usul"])
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

    bolim = "talabalar"

    def get(self, request):
        qs = (
            AzolikMoliya.objects.select_related(
                "azolik__talaba", "azolik__guruh", "azolik__guruh__moliya", "azolik__guruh__oqituvchi"
            )
            .filter(azolik__guruh__faol=True)
        )
        # `?arxiv=1` — arxivlangan (CRM'da "Arxivlash" bosilgan, saytga kira
        # olmaydigan) talabalar. Busiz ular hech qayerda chiqmasdi va
        # "Arxivdan chiqarish"ga yetib bo'lmasdi (2026-09-23).
        arxiv = bool(request.query_params.get("arxiv"))
        # Qora ro'yxat — filial cheklovidan ISTISNO: hamma filialga ko'rinadi
        # (Shuhrat, 2026-09-23), boshqa filialda qayta yozilmasin.
        qora = bool(request.query_params.get("qora_royxat"))
        qs = qs.filter(azolik__talaba__is_active=not arxiv)
        if qora:
            qs = qs.filter(azolik__talaba__crm_talaba__qora_royxat=True)
        else:
            qs = qs.filter(guruh_q(request.user, "azolik__guruh__"))
        if request.query_params.get("filial"):
            qs = qs.filter(azolik__guruh__moliya__filial_id=request.query_params["filial"])
        qidiruv = (request.query_params.get("q") or "").strip()
        if qidiruv:
            qs = qs.filter(
                Q(azolik__talaba__first_name__icontains=qidiruv)
                | Q(azolik__talaba__last_name__icontains=qidiruv)
                | Q(azolik__talaba__username__icontains=qidiruv)
                | Q(azolik__talaba__telefon__icontains=qidiruv)
            )
        if request.query_params.get("holat"):
            qs = qs.filter(holat=request.query_params["holat"])
        # Video-TZ (17:15): guruh, ustoz, kurs va maktab bo'yicha filtr.
        p = request.query_params
        qo_shimcha_filtr = bool(p.get("guruh") or p.get("oqituvchi") or p.get("kurs") or p.get("maktab"))
        if p.get("guruh"):
            qs = qs.filter(azolik__guruh_id=p["guruh"])
        if p.get("oqituvchi"):
            qs = qs.filter(azolik__guruh__oqituvchi_id=p["oqituvchi"])
        if p.get("kurs"):
            qs = qs.filter(azolik__guruh__daraja_id=p["kurs"])
        if p.get("maktab"):
            qs = qs.filter(azolik__talaba__crm_talaba__maktab__icontains=p["maktab"])

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
                    "izoh": talaba.izoh,
                    "balans": balanslar.get(talaba.id, NOL),
                    "guruhlar": [],
                },
            )
            yozuv["guruhlar"].append(
                {
                    "azolik_moliya_id": am.id,
                    "guruh_id": am.azolik.guruh_id,
                    "guruh": am.azolik.guruh.name,
                    "oqituvchi": (am.azolik.guruh.oqituvchi.get_full_name() or am.azolik.guruh.oqituvchi.username)
                    if am.azolik.guruh.oqituvchi_id else None,
                    "holat": am.holat,
                    # Filial — "To'lov qo'shish" oynasida guruh yonida ko'rsatiladi.
                    "filial_id": getattr(getattr(am.azolik.guruh, "moliya", None), "filial_id", None),
                }
            )

        # 2026-09-23 (video-TZ): CRM endi talabalar RO'YXATINING asosiy
        # joyi — guruhsiz talabalar (endi qo'shilgan, yoki guruhdan
        # chiqqan) ham ko'rinishi kerak. Holat/filial filtri berilganda
        # ular chiqmaydi: guruhsizning holati ham, filiali ham yo'q.
        guruhsiz = request.query_params.get("guruhsiz")
        # Arxivlangan o'quvchi guruhlaridan chiqariladi (2026-09-25) — ya'ni
        # u doim "guruhsiz". Filial tanlanganda — o'sha filial guruhidan
        # chiqqanlari (aks holda arxiv ro'yxati filial bilan bo'sh chiqardi).
        arxiv_filiali = request.query_params.get("filial") if arxiv else None
        if guruhsiz or arxiv_filiali or not (request.query_params.get("holat") or request.query_params.get("filial")
                                             or qo_shimcha_filtr):
            qolganlar = User.objects.filter(role=User.Role.STUDENT, is_active=not arxiv).exclude(pk__in=talabalar.keys())
            if arxiv_filiali:
                qolganlar = qolganlar.filter(
                    pk__in=GuruhdanChiqish.objects.filter(filial_id=arxiv_filiali).values("talaba_id"))
            if qora:
                qolganlar = qolganlar.filter(crm_talaba__qora_royxat=True)
            elif cheklanganmi(request.user):
                # Filial xodimiga "guruhsiz" — faqat HAQIQATAN guruhsizlar:
                # boshqa filial guruhidagi talaba bu yerga tushib qolmasin.
                # Istisno — o'z filiali guruhida ham a'zoligi bor (CRM yozuvi
                # hali ochilmagan, saytda qo'shilgan) talaba: aks holda u
                # ro'yxatning hech qayerida chiqmasdi.
                qolganlar = qolganlar.exclude(
                    Q(pk__in=GuruhAzoligi.objects.exclude(guruh_q(request.user, "guruh__")).values("talaba_id"))
                    & ~Q(pk__in=GuruhAzoligi.objects.filter(guruh_q(request.user, "guruh__")).values("talaba_id"))
                )
            if qidiruv:
                qolganlar = qolganlar.filter(
                    Q(first_name__icontains=qidiruv) | Q(username__icontains=qidiruv) | Q(telefon__icontains=qidiruv)
                )
            qolganlar = list(qolganlar[:2000])
            qb = mantiq.balanslarni_ol({t.id for t in qolganlar})
            for t in qolganlar:
                talabalar[t.id] = {
                    "id": t.id, "ism": t.get_full_name() or t.username, "telefon": t.telefon,
                    "izoh": t.izoh, "balans": qb.get(t.id, NOL), "guruhlar": [],
                }
            if guruhsiz:
                talabalar = {k: v for k, v in talabalar.items() if not v["guruhlar"]}

        # Baho va keyingi to'lov (video 23:52: ro'yxat ustunlari) — to'plam
        # so'rovlar bilan, har talabaga alohida so'rov emas.
        from .models import DarsBahosi

        idlar = list(talabalar.keys())
        baholar = dict(
            DarsBahosi.objects.filter(talaba_id__in=idlar).values("talaba_id")
            .annotate(o=Avg("ball")).values_list("talaba_id", "o")
        )
        tolanmagan, oxirgi = {}, {}
        for h in Hisob.objects.filter(talaba_id__in=idlar).values("talaba_id", "oy", "holat"):
            tid = h["talaba_id"]
            if h["holat"] != Hisob.Holat.TOLANDI:
                tolanmagan[tid] = min(tolanmagan.get(tid, h["oy"]), h["oy"])
            oxirgi[tid] = max(oxirgi.get(tid, h["oy"]), h["oy"])
        for tid, yozuv in talabalar.items():
            yozuv["baho"] = _yaxlit(baholar.get(tid))
            if tid in tolanmagan:
                yozuv["keyingi_tolov"] = tolanmagan[tid]
            elif tid in oxirgi:
                yozuv["keyingi_tolov"] = mantiq.keyingi_oy(oxirgi[tid])
            else:
                yozuv["keyingi_tolov"] = None

        # Qora ro'yxat va CRM profili — bitta so'rovda.
        profillar = dict(
            TalabaProfil.objects.filter(user_id__in=talabalar.keys()).values_list("user_id", "qora_royxat")
        )
        for yozuv in talabalar.values():
            yozuv["qora_royxat"] = bool(profillar.get(yozuv["id"]))
        if request.query_params.get("qarzdor"):
            talabalar = {k: v for k, v in talabalar.items() if v["balans"] < 0}
        if request.query_params.get("qora_royxat"):
            talabalar = {k: v for k, v in talabalar.items() if v["qora_royxat"]}

        return Response(sorted(talabalar.values(), key=lambda x: x["ism"]))


class HisobotDinamikaView(CrmView):
    """Oylar kesimida dinamika — "Hisobotlar" bo'limi uchun.

    `HisobotView` BITTA oyni guruhlar kesimida ko'rsatadi; bu esa bir
    necha oyni yonma-yon. Ikkalasi boshqa savolga javob beradi: birinchisi
    "shu oyda kim qarzdor", ikkinchisi "yig'ilish yaxshilanyaptimi".
    """

    bolim = "hisobotlar"

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

        hisoblar = Hisob.objects.filter(oy__gte=oylar[0]).filter(filial_q(request.user, "filial"))
        tolovlar = Tolov.objects.filter(hisob__oy__gte=oylar[0]).filter(filial_q(request.user, "hisob__filial"))
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
    pk_turi = "talaba"  # filial cheklovi: `crm.filial.obyekt_tekshir`
    bolim = "talabalar"

    def get(self, request, pk):
        # `?oy=YYYY-MM` — dars taqvimi qaysi oy uchun (standart: joriy).
        try:
            taqvim_oyi = _oy(request.query_params["oy"]) if request.query_params.get("oy") else None
        except ValueError as e:
            return _xato(str(e))
        talaba = get_object_or_404(User, pk=pk)
        hisoblar = list(
            _tolangan_bilan(
                Hisob.objects.filter(talaba=talaba).filter(filial_q(request.user, "filial")).select_related(
                    "filial", "talaba", "guruh"
                )
            )
        )
        tolovlar = Tolov.objects.filter(talaba=talaba).filter(tolov_q(request.user)).select_related(
            "hisob", "kim_kiritdi", "talaba", "guruh"
        )

        # Ikki filialda o'qiydigan talabada — filial xodimi faqat o'z
        # filiali guruhlari va hisoblarini ko'radi.
        azoliklar = (
            AzolikMoliya.objects.filter(azolik__talaba=talaba).filter(guruh_q(request.user, "azolik__guruh__"))
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
                    "darslar_taqvimi": (taqvim := _darslar_taqvimi(am, hisoblar, taqvim_oyi)),
                    "taqvim_sanogi": _taqvim_sanogi(taqvim),
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
                "username": talaba.username,
                "telefon": talaba.telefon,
                "ota_ona_telefon": talaba.ota_ona_telefon,
                "ota_ona_ismi": talaba.ota_ona_ismi,
                # 2026-09-17: SAYT ma'lumoti (LMS Talabalar kartasi bilan
                # bir xil). CRM faqat o'qiydi; tahrirlash LMS'ning
                # `PATCH /api/talabalar/<id>/` orqali — bitta manba.
                "tugilgan_sana": talaba.tugilgan_sana,
                "manba": talaba.manba,
                "izoh": talaba.izoh,
                # Balans — UMUMIY (hamma filial). Filial xodimi boshqa
                # filialdagi yozuvlarni ko'rmaydi, faqat belgi oladi
                # (Shuhrat qarori, 2026-09-23): aks holda karta ichidagi
                # hisoblar yig'indisi balansga mos kelmay, sababi noaniq qolardi.
                "balans_jami": mantiq.balans(talaba),
                "boshqa_filialda": talaba_boshqa_filialda(request.user, talaba.id),
                # Boshqa filialning qora ro'yxatdagi o'quvchisi — faqat ko'rish.
                "faqat_korish": not talaba_korinadimi(request.user, talaba.id),
                # CRM profili (video-TZ): jins, maktab, qora ro'yxat, arxiv.
                "faol": talaba.is_active,
                "crm": _talaba_profil_dict(talaba),
                # SoffCRM "Ilova holati" o'rnida — saytdan foydalanadimi.
                "sayt": {
                    "oxirgi_kirish": talaba.last_login,
                    "oxirgi_faollik": talaba.oxirgi_faollik,
                },
                "ota_ona": {
                    "id": talaba.ota_ona_id,
                    "ism": (talaba.ota_ona.get_full_name() or talaba.ota_ona.username) if talaba.ota_ona_id else None,
                    "username": talaba.ota_ona.username if talaba.ota_ona_id else None,
                },
                "ortacha_baho": _yaxlit(talaba.crm_baholar.aggregate(o=Avg("ball"))["o"]),
                "natijalar": natijalar,
                "guruhlar": guruhlar,
                "hisoblar": [_hisob_dict(h, tolangan=h.tolangan) for h in hisoblar],
                "tolovlar": [_tolov_dict(t) for t in tolovlar],
            }
        )


def _talaba_profil_dict(talaba):
    p = getattr(talaba, "crm_talaba", None)
    lid = talaba.crm_lid_manbasi.first()
    return {
        "jins": p.jins if p else "",
        "maktab": p.maktab if p else "",
        "qora_royxat": p.qora_royxat if p else False,
        "qora_royxat_sabab": p.qora_royxat_sabab if p else "",
        "arxiv_sabab": p.arxiv_sabab if p else "",
        "arxiv_izoh": p.arxiv_izoh if p else "",
        "lid_id": lid.id if lid else None,
    }


def _darslar_taqvimi(am, hisoblar, oy=None):
    """Oyning dars sanalari: to'lov holati + davomat + baho.

    Rang oyning hisobidan olinadi. Hisob umuman yo'q bo'lsa (kelajakdagi
    oy) — "kutilayotgan" (kulrang): aks holda kelajakdagi darslar qizil
    chiqib, hamma qarzdorga o'xshab ketardi (TZ 6.6).

    Video (12:50): SoffCRM katagi ustida davomat va baho ham turadi
    ("Holat: To'langan, Davomat: Kelgan, Baho: 0"), kartadan turib
    davomat belgilanadi. Ustidagi sanoq: kelgan / kelmagan / sababli /
    qilinmagan (o'tgan, lekin belgilanmagan dars).
    """
    from .boshqaruv import guruh_dars_sanalari
    from .models import DarsBahosi

    oy = oy or mantiq.oy_boshi(timezone.localdate())
    guruh = am.azolik.guruh
    talaba_id = am.azolik.talaba_id
    kunlar = sorted(guruh_dars_sanalari(guruh, oy))
    talaba_kunlar = set(mantiq.talaba_dars_kunlari(am, oy, mantiq.oylik_dars_kunlari(guruh, oy)))
    oxiri = mantiq.oy_oxiri(oy)
    davomat = {
        d.sana: ("sababli" if getattr(d, "crm_izoh", None) and d.crm_izoh.sababli else d.holat)
        for d in Davomat.objects.filter(guruh=guruh, talaba_id=talaba_id, sana__range=(oy, oxiri))
        .select_related("crm_izoh")
    }
    baholar = dict(
        DarsBahosi.objects.filter(guruh=guruh, talaba_id=talaba_id, sana__range=(oy, oxiri))
        .values_list("sana", "ball")
    )
    hisob = next(
        (h for h in hisoblar if h.guruh_id == guruh.id and h.oy == oy), None
    )
    holat = hisob.holat if hisob else "kutilayotgan"
    bugun = timezone.localdate()
    boshi = am.boshlanish_sana
    natija = []
    for kun in kunlar:
        natija.append({
            "sana": kun,
            "holat": holat if kun in talaba_kunlar else "kutilayotgan",
            "davomat": davomat.get(kun),
            "baho": baholar.get(kun),
            "qulf": bool(boshi and kun < boshi) and kun not in davomat,
            "kelajak": kun > bugun,
        })
    return natija


def _taqvim_sanogi(kunlar):
    return {
        "keldi": sum(1 for k in kunlar if k["davomat"] == "keldi"),
        "kelmadi": sum(1 for k in kunlar if k["davomat"] == "kelmadi"),
        "sababli": sum(1 for k in kunlar if k["davomat"] == "sababli"),
        "qilinmagan": sum(1 for k in kunlar if not k["davomat"] and not k["kelajak"] and not k["qulf"]),
    }


# ── Hisobot ──────────────────────────────────────────────────────────


def _hisobot_qatorlari(oy=None, filial_id=None, user=None):
    """Filial va guruh kesimida moliyaviy sarhisob.

    MUHIM: "olingan pul" FAQAT `turi="tolov"` bo'yicha sanaladi.
    Chegirma va bonus alohida ustunlarda — aks holda hisobot markaz
    OLMAGAN pulni daromad qilib ko'rsatardi (TZ 3.8).
    """
    # `user` — filial cheklovi (2026-09-23): filial xodimi faqat o'z filiallari.
    hisoblar = Hisob.objects.filter(filial_q(user, "filial")) if user else Hisob.objects.all()
    tolovlar = Tolov.objects.filter(filial_q(user, "hisob__filial")) if user else Tolov.objects.all()
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
    bolim = "hisobotlar"

    def get(self, request):
        oy = None
        if request.query_params.get("oy"):
            try:
                oy = _oy(request.query_params["oy"])
            except ValueError as e:
                return _xato(str(e))
        qatorlar = _hisobot_qatorlari(oy=oy, filial_id=request.query_params.get("filial"), user=request.user)

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

    bolim = "hisobotlar"

    def get(self, request):
        oy = None
        if request.query_params.get("oy"):
            try:
                oy = _oy(request.query_params["oy"])
            except ValueError as e:
                return _xato(str(e))
        filial_id = request.query_params.get("filial")

        hisoblar_qs = _tolangan_bilan(
            Hisob.objects.select_related("filial", "talaba", "guruh").filter(filial_q(request.user, "filial"))
        )
        tolovlar_qs = Tolov.objects.select_related("hisob", "kim_kiritdi", "talaba", "guruh").filter(
            tolov_q(request.user)
        )
        if oy:
            hisoblar_qs = hisoblar_qs.filter(oy=oy)
            tolovlar_qs = tolovlar_qs.filter(hisob__oy=oy)
        if filial_id:
            hisoblar_qs = hisoblar_qs.filter(filial_id=filial_id)
            tolovlar_qs = tolovlar_qs.filter(tolov_filiali_q(filial_id))
        if request.query_params.get("holat"):
            hisoblar_qs = hisoblar_qs.filter(holat=request.query_params["holat"])
        # Talaba kartasidagi "Excel" — faqat shu talabaning yozuvlari.
        if request.query_params.get("talaba"):
            hisoblar_qs = hisoblar_qs.filter(talaba_id=request.query_params["talaba"])
            tolovlar_qs = tolovlar_qs.filter(talaba_id=request.query_params["talaba"])

        kitob = eksport.qarzdorlar_kitobi(
            hisoblar=[_hisob_dict(h, tolangan=h.tolangan) for h in hisoblar_qs[:5000]],
            hisobot_qatorlari=_hisobot_qatorlari(oy=oy, filial_id=filial_id, user=request.user),
            tolovlar=[_tolov_dict(t) for t in tolovlar_qs[:5000]],
        )
        nomi = f"CRM-moliya-{oy:%Y-%m}.xlsx" if oy else "CRM-moliya.xlsx"
        return eksport.javob_qil(kitob, nomi)
