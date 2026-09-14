"""CRM API — hammasi `/api/crm/` prefiksi ostida.

Loyiha konvensiyasi bo'yicha DRF serializer'lari EMAS, oddiy dict
quruvchilar ishlatiladi (qarang `academics/views.py: _guruh_dict`).

Har bir pul harakati `audit.utils.logla()` orqali yozib boriladi —
mavjud audit ilovasi qayta ishlatiladi, unga tegilmaydi.
"""

from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response

from academics.models import Guruh, GuruhAzoligi
from accounts.models import User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from audit.utils import logla
from courses.models import KursTugun

from . import eksport, mantiq
from .models import (
    AzolikMoliya,
    DarsJadvali,
    Filial,
    GuruhMoliya,
    Hisob,
    KursNarxi,
    Tolov,
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


def _jadval_dict(j):
    return {
        "hafta_kuni": j.hafta_kuni,
        "hafta_kuni_nomi": j.get_hafta_kuni_display(),
        "boshlanish_vaqti": j.boshlanish_vaqti.strftime("%H:%M"),
        "tugash_vaqti": j.tugash_vaqti.strftime("%H:%M"),
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
        "talaba": h.talaba_ism,
        "guruh_id": h.guruh_id,
        "guruh": h.guruh_nomi,
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
        "talaba": t.talaba_ism,
        "guruh_id": t.guruh_id,
        "guruh": t.guruh_nomi,
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
            yangilar.append(
                DarsJadvali(
                    guruh=guruh,
                    hafta_kuni=hafta_kuni,
                    boshlanish_vaqti=boshlanish,
                    tugash_vaqti=tugash,
                )
            )

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
            Hisob.objects.select_related("filial").all()
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
            qs = qs.filter(Q(talaba_ism__icontains=qidiruv) | Q(guruh_nomi__icontains=qidiruv))

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
        qs = Tolov.objects.select_related("hisob", "kim_kiritdi").all()
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
            hisoblar = Hisob.objects.all()
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
                    "talaba": h.talaba_ism,
                    "guruh_id": h.guruh_id,
                    "guruh": h.guruh_nomi,
                    "hisob_id": h.id,
                    "oy": h.oy,
                    "sana": h.oy,
                    "summa": h.summa,
                    "turi": "hisob",
                    "turi_nomi": "Qarzdorlik",
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


class TalabaView(CrmView):
    def get(self, request, pk):
        talaba = get_object_or_404(User, pk=pk)
        hisoblar = list(
            _tolangan_bilan(Hisob.objects.filter(talaba=talaba).select_related("filial"))
        )
        tolovlar = Tolov.objects.filter(talaba=talaba).select_related("hisob", "kim_kiritdi")

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
                    "jadval": [_jadval_dict(j) for j in guruh.crm_jadval.all()],
                    "darslar_taqvimi": _darslar_taqvimi(am, hisoblar),
                }
            )

        return Response(
            {
                "id": talaba.id,
                "ism": talaba.get_full_name() or talaba.username,
                "telefon": talaba.telefon,
                "ota_ona_telefon": talaba.ota_ona_telefon,
                "balans_jami": mantiq.balans(talaba),
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

        hisoblar_qs = _tolangan_bilan(Hisob.objects.select_related("filial").all())
        tolovlar_qs = Tolov.objects.select_related("hisob", "kim_kiritdi").all()
        if oy:
            hisoblar_qs = hisoblar_qs.filter(oy=oy)
            tolovlar_qs = tolovlar_qs.filter(hisob__oy=oy)
        if filial_id:
            hisoblar_qs = hisoblar_qs.filter(filial_id=filial_id)
            tolovlar_qs = tolovlar_qs.filter(hisob__filial_id=filial_id)
        if request.query_params.get("holat"):
            hisoblar_qs = hisoblar_qs.filter(holat=request.query_params["holat"])

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
