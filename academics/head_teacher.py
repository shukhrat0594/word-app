"""Head Teacher dashboard API (Matn-TZ 779, 2026-11-27).

TZ: head_teacher roli bilan kirganda o'quvchi kabineti o'rniga markaz
bo'yicha guruhlar, talabalar, natijalar, ustozlar punktualligi va
o'qitish sifatini ko'rsatadigan dashboard.

Ruxsat: head_teacher, admin, owner. `/api/head-teacher/` yo'llarida
head_teacher'ning asl roli saqlanadi (accounts/authentication.py —
bu yo'l admin simulyatsiyasi ro'yxatida emas), ya'ni bu yerda rol
to'g'ridan-to'g'ri tekshiriladi. Yozish faqat punktuallik yozuvlariga
(yaratish/yangilash); o'chirish endpointi ATAYLAB yo'q.

Hamma ko'rsatkichlar bitta davr (`dan`..`gacha`) va filtrlar (`daraja`,
`guruh`, `oqituvchi`, `q`) bo'yicha hisoblanadi — TZ 2.2/5: "sana
oralig'i o'zgarganda grafik va KPI sinxron yangilanadi".
"""

from collections import defaultdict
from datetime import date, time, timedelta

from django.apps import apps as django_apps
from django.db.models import Avg, Count, Max, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import owner_mi

from .models import Davomat, DarsPunktualligi, Guruh, GuruhAzoligi

# O'qitish sifati / diqqat ro'yxati chegaralari (TZ raqam bermagan — faraz).
YAXSHI_CHEGARA = 80
DIQQAT_NATIJA = 60
DIQQAT_DAVOMAT = 70
STANDART_DAVR_KUN = 30
HAFTA_KUNLARI = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"]


def head_teacher_ruxsati(user):
    return owner_mi(user) or user.role in (User.Role.HEAD_TEACHER, User.Role.ADMIN)


class HeadTeacherRuxsati(IsAuthenticated):
    message = "Bu bo'lim faqat Head Teacher uchun."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and head_teacher_ruxsati(request.user)


# ── Yordamchilar ─────────────────────────────────────────────────────


def _sana(qiymat):
    try:
        return date.fromisoformat(str(qiymat)) if qiymat else None
    except ValueError:
        return None


def _davr(request):
    """(dan, gacha) — standart: oxirgi 30 kun. Teskari tartib tuzatiladi."""
    gacha = _sana(request.query_params.get("gacha")) or timezone.localdate()
    dan = _sana(request.query_params.get("dan")) or gacha - timedelta(days=STANDART_DAVR_KUN - 1)
    if dan > gacha:
        dan, gacha = gacha, dan
    return dan, gacha


def _id(qiymat):
    try:
        return int(qiymat)
    except (TypeError, ValueError):
        return None


def _guruhlar(request):
    """Filtrlarga mos FAOL guruhlar (markaz doirasida)."""
    qs = Guruh.objects.filter(faol=True).select_related("daraja", "oqituvchi")
    user = request.user
    if user.markaz_id:
        qs = qs.filter(markaz_id=user.markaz_id)
    p = request.query_params
    if (d := _id(p.get("daraja"))) is not None:
        qs = qs.filter(daraja_id=d)
    if (g := _id(p.get("guruh"))) is not None:
        qs = qs.filter(id=g)
    if (o := _id(p.get("oqituvchi"))) is not None:
        qs = qs.filter(oqituvchi_id=o)
    return qs


def _filtr_bormi(request):
    p = request.query_params
    return any(_id(p.get(k)) is not None for k in ("daraja", "guruh", "oqituvchi"))


def _talabalar(request, guruhlar):
    """Filtr bo'lsa — shu guruhlar a'zolari; bo'lmasa markazdagi barcha
    faol talabalar (guruhsizlari ham — "barcha talabalar", TZ 1)."""
    qs = User.objects.filter(role=User.Role.STUDENT, is_active=True)
    if request.user.markaz_id:
        qs = qs.filter(markaz_id=request.user.markaz_id)
    if _filtr_bormi(request):
        qs = qs.filter(talaba_guruhlari__in=guruhlar).distinct()
    q = (request.query_params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
        )
    return qs


def _ball_manbalari():
    """Ball/jami bilan baholanadigan barcha natija modellari."""
    from courses.models import KursMashqYechim, KursSozYechim
    from exercises.models import MashqYechim, TestYechim

    return (MashqYechim, TestYechim, KursMashqYechim, KursSozYechim)


def _natijalar_talaba_boyicha(talaba_idlar, dan, gacha):
    """{talaba_id: [ball, jami, soni]} — davrdagi barcha test/mashqlar."""
    jamlanma = defaultdict(lambda: [0, 0, 0])
    for model in _ball_manbalari():
        qatorlar = (
            model.objects.filter(
                talaba_id__in=talaba_idlar, created_at__date__range=(dan, gacha), jami__gt=0
            )
            .values("talaba_id")
            .annotate(b=Sum("ball"), j=Sum("jami"), n=Count("id"))
        )
        for r in qatorlar:
            s = jamlanma[r["talaba_id"]]
            s[0] += r["b"] or 0
            s[1] += r["j"] or 0
            s[2] += r["n"]
    return jamlanma


def _foiz(ball, jami):
    return round(100 * ball / jami, 1) if jami else None


def _guruh_foizi(talaba_idlar, jamlanma):
    b = sum(jamlanma[t][0] for t in talaba_idlar if t in jamlanma)
    j = sum(jamlanma[t][1] for t in talaba_idlar if t in jamlanma)
    return _foiz(b, j)


def _azolar(guruhlar):
    """{guruh_id: [talaba_id, ...]}"""
    azolar = defaultdict(list)
    for g_id, t_id in GuruhAzoligi.objects.filter(
        guruh__in=guruhlar, talaba__is_active=True
    ).values_list("guruh_id", "talaba_id"):
        azolar[g_id].append(t_id)
    return azolar


def _davomat_foizi(guruhlar, dan, gacha, guruh_boyicha=False):
    qs = Davomat.objects.filter(guruh__in=guruhlar, sana__range=(dan, gacha))
    if guruh_boyicha:
        natija = {}
        for r in qs.values("guruh_id").annotate(
            jami=Count("id"), keldi=Count("id", filter=Q(holat=Davomat.Holat.KELDI))
        ):
            natija[r["guruh_id"]] = _foiz(r["keldi"], r["jami"])
        return natija
    r = qs.aggregate(jami=Count("id"), keldi=Count("id", filter=Q(holat=Davomat.Holat.KELDI)))
    return _foiz(r["keldi"] or 0, r["jami"] or 0)


def _konikmalar(talaba_idlar, dan, gacha):
    """Markaz bo'yicha o'rtacha IELTS bandlari (Writing/Speaking — AI
    tekshiruvlar, Reading/Listening — testlar)."""
    from assessment.models import SpeakingTekshiruv, WritingTekshiruv
    from exercises.models import TestYechim

    davr = {"talaba_id__in": talaba_idlar, "created_at__date__range": (dan, gacha)}

    def ortacha(qs, maydon):
        v = qs.aggregate(o=Avg(maydon))["o"]
        return round(float(v), 1) if v is not None else None

    test = TestYechim.objects.filter(band__isnull=False, **davr)
    return {
        "writing_band": ortacha(
            WritingTekshiruv.objects.filter(overall_band__isnull=False, **davr), "overall_band"
        ),
        "speaking_band": ortacha(
            SpeakingTekshiruv.objects.filter(overall_band__isnull=False, **davr), "overall_band"
        ),
        "reading_band": ortacha(test.filter(test__bolim="reading"), "band"),
        "listening_band": ortacha(test.filter(test__bolim="listening"), "band"),
    }


def _punktuallik_qs(request, guruhlar, dan, gacha):
    qs = DarsPunktualligi.objects.filter(guruh__in=guruhlar, sana__range=(dan, gacha))
    return qs.select_related("guruh", "oqituvchi")


def _punktuallik_xulosa(yozuvlar):
    """Faqat amaliy vaqti kiritilgan darslar hisobga olinadi."""
    olchangan = [y for y in yozuvlar if y.amaliy_vaqt is not None]
    kech = [y for y in olchangan if y.kechikish_daqiqa > 0]
    n = len(olchangan)
    return {
        "darslar": n,
        "oz_vaqtida_foiz": _foiz(n - len(kech), n),
        "kechikishlar": len(kech),
        "ortacha_kechikish": round(sum(y.kechikish_daqiqa for y in olchangan) / n, 1) if n else None,
        "ortacha_kechikish_kechlarda": (
            round(sum(y.kechikish_daqiqa for y in kech) / len(kech), 1) if kech else None
        ),
    }


def _ism(u):
    return (u.get_full_name() or u.username) if u else None


def _ustozlar_kesimi(yozuvlar):
    guruhlangan = defaultdict(list)
    for y in yozuvlar:
        guruhlangan[y.oqituvchi_id].append(y)
    natija = []
    for o_id, ys in guruhlangan.items():
        x = _punktuallik_xulosa(ys)
        x.update({"oqituvchi": {"id": o_id, "ism": _ism(ys[0].oqituvchi) or "—"}})
        natija.append(x)
    natija.sort(key=lambda r: (r["oz_vaqtida_foiz"] is None, r["oz_vaqtida_foiz"] or 0))
    return natija


def _davr_kaliti(sana, guruhlash):
    if guruhlash == "oy":
        return sana.replace(day=1).isoformat()
    if guruhlash == "hafta":
        return (sana - timedelta(days=sana.weekday())).isoformat()
    return sana.isoformat()


def _dinamika(yozuvlar, guruhlash):
    guruhlangan = defaultdict(list)
    for y in yozuvlar:
        guruhlangan[_davr_kaliti(y.sana, guruhlash)].append(y)
    return [
        {"davr": k, **_punktuallik_xulosa(guruhlangan[k])} for k in sorted(guruhlangan)
    ]


def _sifat(natija, davomat, punktuallik):
    """O'qitish sifati indeksi — mavjud uchta ko'rsatkich o'rtachasi."""
    qismlar = [v for v in (natija, davomat, punktuallik) if v is not None]
    if not qismlar:
        return {"indeks": None, "holat": None}
    indeks = round(sum(qismlar) / len(qismlar), 1)
    holat = "yaxshi" if indeks >= YAXSHI_CHEGARA else "orta" if indeks >= DIQQAT_NATIJA else "diqqat"
    return {"indeks": indeks, "holat": holat}


def _jadvallar(guruh_idlar):
    """{guruh_id: "Du 14:00–15:30, Chor 14:00–15:30"} — CRM jadvalidan
    (LMS crm'ni statik import qilmaydi, `academics.views._dars_sanalari`)."""
    try:
        jadval = django_apps.get_model("crm", "DarsJadvali")
    except LookupError:
        return {}
    natija = defaultdict(list)
    for j in jadval.objects.filter(guruh_id__in=guruh_idlar).order_by("hafta_kuni", "boshlanish_vaqti"):
        natija[j.guruh_id].append(
            f"{HAFTA_KUNLARI[j.hafta_kuni]} {j.boshlanish_vaqti:%H:%M}–{j.tugash_vaqti:%H:%M}"
        )
    return {k: ", ".join(v) for k, v in natija.items()}


def _rejadagi_vaqt(guruh, sana):
    """Shu kunga jadvaldagi birinchi dars boshlanishi (yoki `None`)."""
    try:
        jadval = django_apps.get_model("crm", "DarsJadvali")
    except LookupError:
        return None
    j = jadval.objects.filter(guruh=guruh, hafta_kuni=sana.weekday()).order_by("boshlanish_vaqti").first()
    return j.boshlanish_vaqti if j else None


def _daraja_dict(g):
    return {"id": g.daraja_id, "nomi": g.daraja.nomi} if g.daraja_id else None


# ── Endpointlar ──────────────────────────────────────────────────────


class FiltrlarView(APIView):
    """Filtr tanlovlari: darajalar, guruhlar, ustozlar."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request):
        guruhlar = Guruh.objects.filter(faol=True).select_related("daraja", "oqituvchi")
        if request.user.markaz_id:
            guruhlar = guruhlar.filter(markaz_id=request.user.markaz_id)
        darajalar, ustozlar = {}, {}
        for g in guruhlar:
            if g.daraja_id:
                darajalar[g.daraja_id] = g.daraja.nomi
            if g.oqituvchi_id:
                ustozlar[g.oqituvchi_id] = _ism(g.oqituvchi)
        return Response({
            "darajalar": [{"id": k, "nomi": v} for k, v in sorted(darajalar.items(), key=lambda x: x[1])],
            "guruhlar": [{"id": g.id, "nomi": g.name} for g in sorted(guruhlar, key=lambda g: g.name)],
            "ustozlar": [{"id": k, "ism": v} for k, v in sorted(ustozlar.items(), key=lambda x: x[1])],
        })


class DashboardView(APIView):
    """Bosh sahifa (TZ 2): KPI, ko'nikmalar grafigi, pastki bloklar."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request):
        dan, gacha = _davr(request)
        uzunlik = (gacha - dan).days + 1
        oldin_gacha = dan - timedelta(days=1)
        oldin_dan = oldin_gacha - timedelta(days=uzunlik - 1)

        guruhlar = list(_guruhlar(request))
        talaba_idlar = list(_talabalar(request, guruhlar).values_list("id", flat=True))
        azolar = _azolar(guruhlar)

        # 1. Guruhlar va talabalar, darajalar bo'yicha taqsimot
        darajalar = {}
        for g in guruhlar:
            kalit = g.daraja_id or 0
            d = darajalar.setdefault(kalit, {
                "id": g.daraja_id, "nomi": g.daraja.nomi if g.daraja_id else None,
                "guruhlar": 0, "_talabalar": set(),
            })
            d["guruhlar"] += 1
            d["_talabalar"].update(azolar.get(g.id, []))

        # 2. O'rtacha o'quv natijasi va o'tgan davrga nisbatan o'zgarish
        joriy = _natijalar_talaba_boyicha(talaba_idlar, dan, gacha)
        oldingi = _natijalar_talaba_boyicha(talaba_idlar, oldin_dan, oldin_gacha)
        natija = _guruh_foizi(talaba_idlar, joriy)
        oldingi_natija = _guruh_foizi(talaba_idlar, oldingi)
        ozgarish = (
            round(natija - oldingi_natija, 1)
            if natija is not None and oldingi_natija is not None else None
        )

        # Darajalar kesimidagi o'rtacha natija (grafik uchun)
        daraja_royxati = []
        for d in darajalar.values():
            talabalar = d.pop("_talabalar")
            daraja_royxati.append({**d, "talabalar": len(talabalar),
                                   "natija_foiz": _guruh_foizi(talabalar, joriy)})
        daraja_royxati.sort(key=lambda d: (d["nomi"] is None, d["nomi"] or ""))

        # 3. Punktuallik
        yozuvlar = list(_punktuallik_qs(request, guruhlar, dan, gacha))
        punktuallik = _punktuallik_xulosa(yozuvlar)

        # 4. O'qitish sifati
        davomat = _davomat_foizi(guruhlar, dan, gacha)
        sifat = _sifat(natija, davomat, punktuallik["oz_vaqtida_foiz"])

        # Diqqat talab qiluvchi guruhlar
        guruh_davomati = _davomat_foizi(guruhlar, dan, gacha, guruh_boyicha=True)
        diqqat = []
        for g in guruhlar:
            g_natija = _guruh_foizi(azolar.get(g.id, []), joriy)
            g_davomat = guruh_davomati.get(g.id)
            sabablar = []
            if g_natija is None:
                sabablar.append("natija_yoq")
            elif g_natija < DIQQAT_NATIJA:
                sabablar.append("past_natija")
            if g_davomat is not None and g_davomat < DIQQAT_DAVOMAT:
                sabablar.append("past_davomat")
            if sabablar:
                diqqat.append({
                    "id": g.id, "nomi": g.name, "daraja": _daraja_dict(g),
                    "oqituvchi": {"id": g.oqituvchi_id, "ism": _ism(g.oqituvchi)} if g.oqituvchi_id else None,
                    "talaba_soni": len(azolar.get(g.id, [])),
                    "natija_foiz": g_natija, "davomat_foiz": g_davomat, "sabablar": sabablar,
                })
        diqqat.sort(key=lambda r: (r["natija_foiz"] is not None, r["natija_foiz"] or 0))

        return Response({
            "davr": {"dan": dan, "gacha": gacha, "oldingi_dan": oldin_dan, "oldingi_gacha": oldin_gacha},
            "kpi": {
                "guruhlar": len(guruhlar),
                "talabalar": len(talaba_idlar),
                "darajalar": daraja_royxati,
                "natija_foiz": natija,
                "oldingi_natija_foiz": oldingi_natija,
                "natija_ozgarish": ozgarish,
                "bajarilgan": sum(v[2] for v in joriy.values()),
                "punktuallik": punktuallik,
                "davomat_foiz": davomat,
                "sifat": sifat,
            },
            "konikmalar": _konikmalar(talaba_idlar, dan, gacha),
            "ustozlar_punktualligi": _ustozlar_kesimi(yozuvlar)[:8],
            "diqqat_guruhlar": diqqat[:10],
        })


class GuruhlarView(APIView):
    """TZ 3: markazdagi barcha guruhlar — daraja, ustoz, jadval, talabalar
    soni, davrdagi o'rtacha natija."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request):
        dan, gacha = _davr(request)
        guruhlar = list(_guruhlar(request))
        q = (request.query_params.get("q") or "").strip().lower()
        if q:
            guruhlar = [
                g for g in guruhlar
                if q in g.name.lower() or (g.oqituvchi_id and q in _ism(g.oqituvchi).lower())
            ]
        azolar = _azolar(guruhlar)
        barcha = {t for ts in azolar.values() for t in ts}
        jamlanma = _natijalar_talaba_boyicha(barcha, dan, gacha)
        jadvallar = _jadvallar([g.id for g in guruhlar])
        davomat = _davomat_foizi(guruhlar, dan, gacha, guruh_boyicha=True)
        return Response([
            {
                "id": g.id, "nomi": g.name, "daraja": _daraja_dict(g),
                "oqituvchi": {"id": g.oqituvchi_id, "ism": _ism(g.oqituvchi)} if g.oqituvchi_id else None,
                "jadval": jadvallar.get(g.id, ""),
                "talaba_soni": len(azolar.get(g.id, [])),
                "natija_foiz": _guruh_foizi(azolar.get(g.id, []), jamlanma),
                "davomat_foiz": davomat.get(g.id),
            }
            for g in sorted(guruhlar, key=lambda g: g.name)
        ])


class TalabalarView(APIView):
    """TZ 3: barcha talabalar; guruh/daraja/ustoz filtri va ism bo'yicha
    qidiruv (`q`)."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request):
        dan, gacha = _davr(request)
        guruhlar = list(_guruhlar(request))
        talabalar = list(_talabalar(request, guruhlar).order_by("first_name", "last_name", "username"))
        idlar = [t.id for t in talabalar]
        jamlanma = _natijalar_talaba_boyicha(idlar, dan, gacha)
        talaba_guruhlari = defaultdict(list)
        for a in GuruhAzoligi.objects.filter(
            talaba_id__in=idlar, guruh__faol=True
        ).select_related("guruh__daraja", "guruh__oqituvchi"):
            talaba_guruhlari[a.talaba_id].append(a.guruh)
        natija = []
        for t in talabalar:
            gs = talaba_guruhlari.get(t.id, [])
            b, j, n = jamlanma.get(t.id, (0, 0, 0))
            natija.append({
                "id": t.id, "ism": _ism(t), "username": t.username,
                "guruhlar": [{"id": g.id, "nomi": g.name} for g in gs],
                "darajalar": sorted({g.daraja.nomi for g in gs if g.daraja_id}),
                "ustozlar": sorted({_ism(g.oqituvchi) for g in gs if g.oqituvchi_id}),
                "natija_foiz": _foiz(b, j),
                "bajarilgan": n,
                "oxirgi_faollik": t.oxirgi_faollik,
            })
        return Response(natija)


class TalabaProfilView(APIView):
    """Talaba profili: shaxsiy va guruh ma'lumotlari, faollik, AI
    trenajyorlar tarixi. Test/mashq natijalari ro'yxatini frontend mavjud
    `/api/foydalanuvchilar/<id>/natijalar/` dan oladi (NatijalarRoyxati)."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request, pk):
        qs = User.objects.filter(role=User.Role.STUDENT)
        if request.user.markaz_id:
            qs = qs.filter(markaz_id=request.user.markaz_id)
        t = get_object_or_404(qs, pk=pk)
        from assessment.models import AiTrenajyorYozuvi

        guruhlar = [
            a.guruh for a in GuruhAzoligi.objects.filter(talaba=t).select_related(
                "guruh__daraja", "guruh__oqituvchi"
            )
        ]
        bugun = timezone.localdate()
        jamlanma = _natijalar_talaba_boyicha([t.id], bugun - timedelta(days=STANDART_DAVR_KUN - 1), bugun)
        b, j, n = jamlanma.get(t.id, (0, 0, 0))
        oxirgi_natija = None
        for model in _ball_manbalari():
            s = model.objects.filter(talaba=t).aggregate(m=Max("created_at"))["m"]
            if s and (oxirgi_natija is None or s > oxirgi_natija):
                oxirgi_natija = s
        ai = AiTrenajyorYozuvi.objects.filter(talaba=t)[:100]
        return Response({
            "id": t.id, "ism": _ism(t), "username": t.username,
            "telefon": getattr(t, "telefon", "") or "",
            "rasm_url": f"/api/foydalanuvchilar/{t.id}/rasm/" if getattr(t, "rasm", None) else None,
            "guruhlar": [
                {
                    "id": g.id, "nomi": g.name, "faol": g.faol, "daraja": _daraja_dict(g),
                    "oqituvchi": {"id": g.oqituvchi_id, "ism": _ism(g.oqituvchi)} if g.oqituvchi_id else None,
                }
                for g in guruhlar
            ],
            "faollik": {
                "oxirgi_faollik": t.oxirgi_faollik,
                "oxirgi_natija": oxirgi_natija,
                "oxirgi_30_kun_bajarilgan": n,
                "oxirgi_30_kun_natija_foiz": _foiz(b, j),
            },
            "ai_trenajyorlar": [
                {
                    "id": y.id, "tur": y.tur, "mavzu": y.mavzu, "xabar_soni": y.xabar_soni,
                    "oxirgi_javob": y.oxirgi_javob, "boshlangan": y.created_at, "yangilangan": y.updated_at,
                }
                for y in ai
            ],
        })


def _vaqt(qiymat):
    """"HH:MM" -> time; bo'sh -> None; noto'g'ri -> ValueError."""
    if qiymat in (None, ""):
        return None
    if isinstance(qiymat, time):
        return qiymat
    return time.fromisoformat(str(qiymat)[:5])


def _punktuallik_dict(y):
    return {
        "id": y.id, "sana": y.sana,
        "guruh": {"id": y.guruh_id, "nomi": y.guruh.name},
        "oqituvchi": {"id": y.oqituvchi_id, "ism": _ism(y.oqituvchi)} if y.oqituvchi_id else None,
        "rejadagi_vaqt": y.rejadagi_vaqt.strftime("%H:%M"),
        "amaliy_vaqt": y.amaliy_vaqt.strftime("%H:%M") if y.amaliy_vaqt else None,
        "kechikish_daqiqa": y.kechikish_daqiqa,
        "sabab": y.sabab,
    }


class PunktuallikView(APIView):
    """TZ 4: darslar punktualligi — ro'yxat, ustozlar kesimi va dinamika
    (GET, `guruhlash`=kun|hafta|oy); yangi yozuv (POST — shu guruh/sana/
    rejadagi vaqt uchun yozuv bo'lsa yangilanadi). DELETE yo'q."""

    permission_classes = [HeadTeacherRuxsati]

    def get(self, request):
        dan, gacha = _davr(request)
        guruhlar = _guruhlar(request)
        yozuvlar = list(_punktuallik_qs(request, guruhlar, dan, gacha))
        guruhlash = request.query_params.get("guruhlash")
        if guruhlash not in ("kun", "hafta", "oy"):
            guruhlash = "kun"
        return Response({
            "davr": {"dan": dan, "gacha": gacha},
            "xulosa": _punktuallik_xulosa(yozuvlar),
            "ustozlar": _ustozlar_kesimi(yozuvlar),
            "dinamika": _dinamika(yozuvlar, guruhlash),
            "yozuvlar": [_punktuallik_dict(y) for y in yozuvlar],
        })

    def post(self, request):
        d = request.data
        guruhlar = Guruh.objects.all()
        if request.user.markaz_id:
            guruhlar = guruhlar.filter(markaz_id=request.user.markaz_id)
        guruh = guruhlar.filter(id=_id(d.get("guruh"))).select_related("oqituvchi").first()
        if guruh is None:
            return Response({"detail": "Guruhni tanlang"}, status=400)
        sana = _sana(d.get("sana")) or timezone.localdate()
        try:
            rejadagi = _vaqt(d.get("rejadagi_vaqt")) or _rejadagi_vaqt(guruh, sana)
            amaliy = _vaqt(d.get("amaliy_vaqt"))
        except ValueError:
            return Response({"detail": "Vaqt HH:MM ko'rinishida bo'lishi kerak"}, status=400)
        if rejadagi is None:
            return Response({"detail": "Bu kunga dars jadvali yo'q — rejadagi vaqtni kiriting"}, status=400)
        sabab = str(d.get("sabab") or "")[:300]
        y, yangi = DarsPunktualligi.objects.get_or_create(
            guruh=guruh, sana=sana, rejadagi_vaqt=rejadagi,
            defaults={"oqituvchi": guruh.oqituvchi, "amaliy_vaqt": amaliy, "sabab": sabab, "kim": request.user},
        )
        if not yangi:
            y.amaliy_vaqt = amaliy
            y.sabab = sabab
            y.kim = request.user
            y.save()
        return Response(_punktuallik_dict(y), status=201 if yangi else 200)


class PunktuallikDetailView(APIView):
    """Yozuvni yangilash (amaliy vaqt, rejadagi vaqt, sabab). DELETE yo'q."""

    permission_classes = [HeadTeacherRuxsati]

    def patch(self, request, pk):
        qs = DarsPunktualligi.objects.select_related("guruh", "oqituvchi")
        if request.user.markaz_id:
            qs = qs.filter(guruh__markaz_id=request.user.markaz_id)
        y = get_object_or_404(qs, pk=pk)
        d = request.data
        try:
            if "amaliy_vaqt" in d:
                y.amaliy_vaqt = _vaqt(d.get("amaliy_vaqt"))
            if d.get("rejadagi_vaqt"):
                y.rejadagi_vaqt = _vaqt(d.get("rejadagi_vaqt"))
        except ValueError:
            return Response({"detail": "Vaqt HH:MM ko'rinishida bo'lishi kerak"}, status=400)
        if "sabab" in d:
            y.sabab = str(d.get("sabab") or "")[:300]
        y.kim = request.user
        if DarsPunktualligi.objects.filter(
            guruh_id=y.guruh_id, sana=y.sana, rejadagi_vaqt=y.rejadagi_vaqt
        ).exclude(pk=y.pk).exists():
            return Response({"detail": "Bu dars uchun yozuv allaqachon bor"}, status=400)
        y.save()
        return Response(_punktuallik_dict(y))
