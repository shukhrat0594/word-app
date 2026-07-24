import json
import re

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Markaz, User
from accounts.permissions import owner_mi
from audit.models import FaoliyatYozuvi
from audit.utils import logla, maydon_diff

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
        "sun_iy_intellekt_yaratgan": m.sun_iy_intellekt_yaratgan,
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

        markaz = Markaz.objects.first()
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
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=mashq,
            obyekt_turi="Mashq",
            snapshot={"name": mashq.name, "bolim": mashq.bolim, "tur": mashq.tur, "korinish": mashq.korinish},
        )

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
        kuzatiladigan = ("name", "bolim", "tur", "korinish", "matn", "namuna_javob")
        eski_qiymatlar = {m: getattr(mashq, m) for m in kuzatiladigan}
        fayl_ozgardi = {}

        for maydon in kuzatiladigan:
            if maydon in request.data:
                setattr(mashq, maydon, request.data[maydon])
        if "savollar" in request.data:
            try:
                mashq.savollar = json.loads(request.data["savollar"])
            except json.JSONDecodeError:
                return Response({"detail": "savollar noto'g'ri JSON"}, status=400)
            fayl_ozgardi["savollar"] = {"eski": "—", "yangi": "yangilandi"}
        if request.FILES.get("audio_fayl"):
            mashq.audio_fayl = request.FILES["audio_fayl"]
            fayl_ozgardi["audio_fayl"] = {"eski": "—", "yangi": "yangilandi"}
        if request.FILES.get("rasm"):
            mashq.rasm = request.FILES["rasm"]
            fayl_ozgardi["rasm"] = {"eski": "—", "yangi": "yangilandi"}

        try:
            mashq.full_clean()
        except ValidationError as e:
            return Response(e.message_dict, status=400)
        mashq.save()

        yangi_qiymatlar = {m: getattr(mashq, m) for m in kuzatiladigan}
        ozgarishlar = maydon_diff(eski_qiymatlar, yangi_qiymatlar)
        ozgarishlar.update(fayl_ozgardi)
        if ozgarishlar:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=mashq,
                obyekt_turi="Mashq",
                obyekt_nomi=mashq.name,
                ozgarishlar=ozgarishlar,
            )

        return Response(_mashq_qisqa(mashq))

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(Mashq, pk=pk)
        mashq_id, nomi = mashq.id, mashq.name
        snapshot = {"name": mashq.name, "bolim": mashq.bolim, "tur": mashq.tur}
        mashq.delete()
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="Mashq",
            obyekt_id=mashq_id,
            obyekt_nomi=nomi,
            ozgarishlar=snapshot,
        )
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
        tur = request.query_params.get("tur")
        if tur:
            qs = qs.filter(tur=tur)
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
                "sun_iy_intellekt_yaratgan": mashq.sun_iy_intellekt_yaratgan,
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
        "tur": q.tur,
        "audio_url": f"/api/imtihon/qism/{q.id}/audio/" if q.audio_fayl else None,
        "rasm_url": f"/api/imtihon/qism/{q.id}/rasm/" if q.rasm else None,
        "savollar": q.savollar,
        "maxsus_format": q.maxsus_format,
    }


def _test_admin_dict(t):
    return {
        "id": t.id,
        "name": t.name,
        "bolim": t.bolim,
        "korinish": t.korinish,
        "qismlar": [_qism_admin_dict(q) for q in t.qismlar.all()],
        "created_at": t.created_at,
        "yaratuvchi": t.yaratuvchi.username if t.yaratuvchi_id else None,
    }


def _qism_talaba_dict(q):
    return {
        "id": q.id,
        "tartib": q.tartib,
        "sarlavha": q.sarlavha,
        "yoriqnoma": q.yoriqnoma,
        "matn": q.matn,
        "tur": q.tur,
        "audio_url": f"/api/imtihon/qism/{q.id}/audio/" if q.audio_fayl else None,
        "rasm_url": f"/api/imtihon/qism/{q.id}/rasm/" if q.rasm else None,
        "savollar": savollar_talaba_uchun(q.savollar),
        "maxsus_format": q.maxsus_format,
    }


def _test_talaba_dict(t):
    return {
        "id": t.id,
        "name": t.name,
        "bolim": t.bolim,
        "qismlar": [_qism_talaba_dict(q) for q in t.qismlar.all()],
    }


def _raqam_top(nom):
    """Fayl nomidan bo'lim/qism raqamini chiqarib olishga urinadi — avval
    "Section N"/"Part N" andozasini qidiradi (rasm fayllarida ko'p
    uchraydi, masalan "Listening_Section _2 _Questions _14-20.png" — bu
    yerda to'g'ri raqam 2, matndagi oxirgi raqam emas), topilmasa nomdagi
    ENG OXIRGI raqamni oladi (audio fayllarida odatda track raqami oxirida
    bo'ladi, masalan "CD1Track_02"). Kengaytma (".mp3" va h.k.) qidiruvdan
    OLDIN olib tashlanadi — aks holda "mp3"dagi "3" oxirgi raqam sifatida
    xato o'qilib, barcha fayllarga bir xil (noto'g'ri) raqam berib qo'yardi."""
    nom_kengaytmasiz = re.sub(r"\.[A-Za-z0-9]+$", "", nom)
    mos = re.search(r"(?:section|part)[\s_]*0*(\d+)", nom_kengaytmasiz, re.IGNORECASE)
    if mos:
        return int(mos.group(1))
    barcha = re.findall(r"\d+", nom_kengaytmasiz)
    return int(barcha[-1]) if barcha else None


def _fayllarni_taqsimla(qismlar, fayllar, maydon, birini_hammaga_bering=False):
    """`fayllar` — {fayl_nomi: bytes} lug'ati, `qismlar`dan `maydon`i
    (masalan "audio_fayl" yoki "rasm") hali bo'sh bo'lganlariga avtomatik
    taqsimlaydi: fayl nomidagi raqam (`_raqam_top`) mos qismning "tartib"i
    bilan taqqoslanadi; mos kelmasa nomlarni tabiiy tartibda saralab
    ketma-ket biriktiradi. `birini_hammaga_bering=True` bo'lsa va FAQAT
    bitta fayl bo'lsa — hammasiga bir xil fayl beriladi (masalan
    Listening'da bitta uzluksiz audio barcha qismlarga)."""
    from django.core.files.base import ContentFile

    bosh_qismlar = [q for q in qismlar if not getattr(q, maydon)]
    nomlar = list(fayllar.keys())
    if not bosh_qismlar or not nomlar:
        return

    if birini_hammaga_bering and len(nomlar) == 1:
        nom = nomlar[0]
        malumot = fayllar[nom]
        for qism in bosh_qismlar:
            setattr(qism, maydon, ContentFile(malumot, name=nom))
            qism.save()
        return

    tartib_bolib = {q.tartib: q for q in bosh_qismlar}
    raqam_mos = {}
    band_raqamlar = set()
    for nom in nomlar:
        raqam = _raqam_top(nom)
        if raqam is not None and raqam in tartib_bolib and raqam not in band_raqamlar:
            raqam_mos[nom] = raqam
            band_raqamlar.add(raqam)

    if len(raqam_mos) == len(nomlar):
        for nom, raqam in raqam_mos.items():
            qism = tartib_bolib[raqam]
            setattr(qism, maydon, ContentFile(fayllar[nom], name=nom))
            qism.save()
        return

    # Fallback: nomiga qarab aniq mos kelmasa — nomlarni tabiiy tartibda
    # saralab, qismlarga "tartib" bo'yicha ketma-ket biriktiramiz.
    for nom, qism in zip(sorted(nomlar), sorted(bosh_qismlar, key=lambda q: q.tartib)):
        setattr(qism, maydon, ContentFile(fayllar[nom], name=nom))
        qism.save()


def _test_yarat(data, markaz, rasm_fayllar=None, audio_fayllar=None, yaratuvchi=None):
    """`ImtihonTest`+`TestQismi`larni JSON ma'lumotdan yaratadi.

    `rasm_fayllar` — {fayl_nomi: ContentFile} lug'ati (ZIP orqali yuklashda,
    qismning "rasm" maydonidagi nomga mos fayl). Oddiy JSON yuklashda None.

    `audio_fayllar` — {fayl_nomi: bytes} lug'ati (ZIP orqali yuklashda,
    Listening uchun) — `_fayllarni_taqsimla` orqali qismlarga avtomatik
    taqsimlanadi. JSON'da "rasm" maydoni orqali aniq ko'rsatilmagan rasm
    fayllari ham xuddi shunday (fayl nomidagi raqamga qarab) avtomatik
    taqsimlanadi (2026-07-22, AI odatda "rasm" maydonini bilmay/unutib
    qoldirgani uchun qo'shildi).

    Bir xil nomdagi test allaqachon bo'lsa — nomga avtomatik "_1", "_2" ...
    qo'shiladi (foydalanuvchi so'rovi, 2026-07-22).

    Writing/Speaking uchun har bir qism "tur" (task1/task2/part1/part2/part3)
    ko'rsatishi shart — Reading/Listening'da "savollar" ishlatiladi, bu
    ikkalasi mos ravishda bo'sh qoladi.

    Xato bo'lsa (None, {"detail": "..."}) qaytaradi, aks holda (test, None).
    """
    rasm_fayllar = rasm_fayllar or {}
    audio_fayllar = audio_fayllar or {}
    name = data.get("name", "")
    bolim = data.get("bolim", "")
    korinish = data.get("korinish", "private")
    qismlar_data = data.get("qismlar") or []
    if not name or bolim not in Bolim.values:
        return None, {"detail": "name va bolim (reading/listening/writing/speaking) majburiy"}
    if not isinstance(qismlar_data, list) or not qismlar_data:
        return None, {"detail": "kamida bitta qism kerak"}

    yozgap_mi = bolim in (Bolim.WRITING, Bolim.SPEAKING)
    if yozgap_mi:
        for q in qismlar_data:
            if not q.get("tur"):
                return None, {
                    "detail": "Writing/Speaking qismlarida 'tur' (task1/task2/part1/part2/part3) majburiy"
                }

    asl_nomi = name
    band = 1
    while ImtihonTest.objects.filter(name=name, markaz=markaz).exists():
        name = f"{asl_nomi}_{band}"
        band += 1

    test = ImtihonTest.objects.create(
        name=name, bolim=bolim, markaz=markaz, korinish=korinish, yaratuvchi=yaratuvchi
    )
    qism_obyektlari = []
    ishlatilgan_rasm_nomlari = set()
    for i, q in enumerate(qismlar_data, start=1):
        qism = TestQismi(
            test=test,
            tartib=q.get("tartib") or i,
            sarlavha=q.get("sarlavha", ""),
            yoriqnoma=q.get("yoriqnoma", ""),
            matn=q.get("matn", ""),
            tur=q.get("tur", ""),
            savollar=q.get("savollar") or [],
            maxsus_format=q.get("maxsus_format") or None,
        )
        rasm_nomi = q.get("rasm")
        if rasm_nomi and rasm_nomi in rasm_fayllar:
            qism.rasm = rasm_fayllar[rasm_nomi]
            ishlatilgan_rasm_nomlari.add(rasm_nomi)
        qism.save()
        qism_obyektlari.append(qism)

    if bolim == Bolim.LISTENING and audio_fayllar:
        _fayllarni_taqsimla(qism_obyektlari, audio_fayllar, "audio_fayl", birini_hammaga_bering=True)

    qoldiq_rasm_fayllar = {
        nom: fayl.read() for nom, fayl in rasm_fayllar.items() if nom not in ishlatilgan_rasm_nomlari
    }
    if qoldiq_rasm_fayllar:
        _fayllarni_taqsimla(qism_obyektlari, qoldiq_rasm_fayllar, "rasm")

    return test, None


class ImtihonBoshqaruvView(APIView):
    """Owner/admin uchun — to'liq testlar ro'yxati va yaratish (qismlari
    bilan birga, bitta JSON so'rovda). Audio/rasm har qismga keyinroq
    TestQismiFayllarBoshqaruvView orqali biriktiriladi (yoki ZIP yuklashda
    — ImtihonZipBoshqaruvView — bitta so'rovda birga keladi)."""

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

        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        test, xato = _test_yarat(request.data, markaz, yaratuvchi=request.user)
        if xato:
            return Response(xato, status=400)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=test,
            obyekt_turi="ImtihonTest",
            snapshot={"name": test.name, "bolim": test.bolim, "qismlar_soni": test.qismlar.count()},
        )
        return Response(_test_admin_dict(test), status=201)


def _rasm_fayllarni_ol(arxiv, fayl_nomlari):
    """Berilgan fayl nomlari ro'yxatidan (arxiv ichidagi to'liq yo'llar)
    rasm fayllarni {asosiy_nom: ContentFile} lug'atiga aylantiradi."""
    from django.core.files.base import ContentFile

    rasm_fayllar = {}
    for nom in fayl_nomlari:
        asosiy_nom = nom.rsplit("/", 1)[-1]
        if asosiy_nom.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            rasm_fayllar[asosiy_nom] = ContentFile(arxiv.read(nom), name=asosiy_nom)
    return rasm_fayllar


def _audio_fayllarni_ol(arxiv, fayl_nomlari):
    """Berilgan fayl nomlari ro'yxatidan (arxiv ichidagi to'liq yo'llar)
    audio fayllarni {asosiy_nom: bytes} lug'atiga aylantiradi — Listening
    ZIP yuklashda `_audioni_taqsimla` orqali qismlarga taqsimlanadi."""
    audio_fayllar = {}
    for nom in fayl_nomlari:
        asosiy_nom = nom.rsplit("/", 1)[-1]
        if asosiy_nom.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".aac")):
            audio_fayllar[asosiy_nom] = arxiv.read(nom)
    return audio_fayllar


class ImtihonZipBoshqaruvView(APIView):
    """Owner/admin uchun — ZIP arxiv orqali test(lar) yaratish.

    Ikki rejim (arxiv tuzilishiga qarab avtomatik aniqlanadi):
    1. **Ko'p mashqli** — arxivning tepasida papkalar bo'lsa (masalan
       `Mashq1/test.json`+`Mashq1/rasm1.png`, `Mashq2/test.json`+...), HAR
       BIR papka — mustaqil bitta test (JSON + o'sha papkadagi rasmlar,
       rasm nomlari faqat shu papka doirasida ko'riladi, papkalar orasida
       to'qnashmaydi). Bir so'rovda bir nechta test yaratiladi.
    2. **Yakka mashq** (eski, orqaga moslashuvchan) — arxiv tepasida
       to'g'ridan-to'g'ri bitta .json fayl + rasm fayllar bo'lsa, xuddi
       avvalgidek bitta test yaratiladi.

    Har bir testning JSON'i — oddiy JSON yuklashdagi bilan bir xil format,
    qismlarda ixtiyoriy "rasm": "fayl_nomi.png" maydoni bilan."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        fayl = request.FILES.get("zip_fayl")
        if not fayl:
            return Response({"detail": "zip_fayl majburiy"}, status=400)

        import io
        import zipfile

        try:
            arxiv = zipfile.ZipFile(io.BytesIO(fayl.read()))
        except zipfile.BadZipFile:
            return Response({"detail": "Fayl to'g'ri ZIP arxiv emas"}, status=400)

        # Katalog (papka) belgisi bo'lgan yozuvlarni (ular bo'sh, faqat "/"
        # bilan tugaydi) tashlab, real fayllarni papka bo'yicha guruhlaymiz.
        fayllar = [n for n in arxiv.namelist() if not n.endswith("/")]
        papkalar = {}
        tepa_json = None
        for n in fayllar:
            bo_laklar = n.split("/")
            if len(bo_laklar) == 1:
                if n.lower().endswith(".json"):
                    tepa_json = n
            else:
                papkalar.setdefault(bo_laklar[0], []).append(n)

        yaratilgan = []
        xatolar = []

        if papkalar:
            for papka_nomi, papka_fayllari in papkalar.items():
                json_nomlari = [n for n in papka_fayllari if n.lower().endswith(".json")]
                if len(json_nomlari) != 1:
                    xatolar.append(f"{papka_nomi}: aynan bitta .json fayl bo'lishi kerak")
                    continue
                try:
                    data = json.loads(arxiv.read(json_nomlari[0]).decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    xatolar.append(f"{papka_nomi}: JSON fayl noto'g'ri formatda")
                    continue
                rasm_fayllar = _rasm_fayllarni_ol(arxiv, papka_fayllari)
                audio_fayllar = _audio_fayllarni_ol(arxiv, papka_fayllari)
                test, xato = _test_yarat(
                    data, markaz,
                    rasm_fayllar=rasm_fayllar, audio_fayllar=audio_fayllar,
                    yaratuvchi=request.user,
                )
                if xato:
                    xatolar.append(f"{papka_nomi}: {xato['detail']}")
                else:
                    yaratilgan.append(test)
        elif tepa_json:
            try:
                data = json.loads(arxiv.read(tepa_json).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return Response({"detail": "JSON fayl noto'g'ri formatda"}, status=400)
            rasm_fayllar = _rasm_fayllarni_ol(arxiv, fayllar)
            audio_fayllar = _audio_fayllarni_ol(arxiv, fayllar)
            test, xato = _test_yarat(
                data, markaz,
                rasm_fayllar=rasm_fayllar, audio_fayllar=audio_fayllar,
                yaratuvchi=request.user,
            )
            if xato:
                xatolar.append(xato["detail"])
            else:
                yaratilgan.append(test)
        else:
            return Response(
                {"detail": "Arxivda .json fayl topilmadi (tepada yoki har bir mashq papkasi ichida bo'lishi kerak)"},
                status=400,
            )

        if not yaratilgan:
            return Response({"detail": "; ".join(xatolar) or "Hech narsa yaratilmadi"}, status=400)

        for test in yaratilgan:
            biriktirilgan_rasmlar = sum(1 for q in test.qismlar.all() if q.rasm)
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.YARATISH,
                obyekt=test,
                obyekt_turi="ImtihonTest",
                snapshot={
                    "name": test.name,
                    "bolim": test.bolim,
                    "qismlar_soni": test.qismlar.count(),
                    "manba": "zip",
                    "rasmlar_soni": biriktirilgan_rasmlar,
                },
            )

        return Response(
            {
                "yaratildi": [_test_admin_dict(t) for t in yaratilgan],
                "xatolar": xatolar,
            },
            status=201,
        )


class ImtihonBoshqaruvDetailView(APIView):
    """Owner/admin uchun — to'liq testni butunlay o'chirish."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        test_id, nomi, bolim = test.id, test.name, test.bolim
        test.delete()
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="ImtihonTest",
            obyekt_id=test_id,
            obyekt_nomi=nomi,
            ozgarishlar={"name": nomi, "bolim": bolim},
        )
        return Response(status=204)


class TestQismiFayllarBoshqaruvView(APIView):
    """Owner/admin uchun — bitta test qismiga audio (listening) va/yoki
    rasm (Map/Diagram Labelling, Writing Task 1 grafigi) biriktirish."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qism = get_object_or_404(TestQismi, pk=pk)
        ozgarishlar = {}
        if request.FILES.get("audio_fayl"):
            qism.audio_fayl = request.FILES["audio_fayl"]
            ozgarishlar["audio_fayl"] = {"eski": "—", "yangi": "yangilandi"}
        if request.FILES.get("rasm"):
            qism.rasm = request.FILES["rasm"]
            ozgarishlar["rasm"] = {"eski": "—", "yangi": "yangilandi"}
        if ozgarishlar:
            qism.save()
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=qism.test,
                obyekt_turi="ImtihonTest",
                obyekt_nomi=f"{qism.test.name} — {qism.sarlavha or qism.tartib}-qism",
                ozgarishlar=ozgarishlar,
            )
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


class TestQismRasmView(APIView):
    """Test qismi rasmi — autentifikatsiyalangan stream (B3.2 bilan bir xil)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        qism = get_object_or_404(
            TestQismi, pk=pk, test__in=korinadigan_testlar(request.user)
        )
        if not qism.rasm:
            raise Http404
        javob = FileResponse(qism.rasm.open("rb"))
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


class ImtihonYozGapTekshirishView(APIView):
    """Writing/Speaking to'liq testga javob — har bir qism (Task1+Task2 yoki
    Part1/2/3) uchun AI orqali baholanadi (assessment.providers — Writing/
    Speaking AI-tekshiruv paneli bilan bir xil mexanizm, mavzuga moslik
    tekshiruvi bilan birga).

    Har bir qism uchun alohida `WritingTekshiruv`/`SpeakingTekshiruv` yozuvi
    yaratiladi — shunda mavjud XP/tarix/statistika infratuzilmasi (signal
    orqali) avtomatik ishlaydi, alohida "natija" modeli kerak emas. Paket
    (agar aktiv bo'lsa) BUTUN test uchun bir marta yechiladi (real IELTS'da
    Writing/Speaking — bitta yaxlit sessiya, har qism uchun alohida emas)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from assessment.models import SpeakingTekshiruv, WritingTekshiruv
        from assessment.providers import ProviderXatosi, provider_tanla
        from packages.models import paketdan_ishlat

        test = get_object_or_404(korinadigan_testlar(request.user), pk=pk)
        if test.bolim not in (Bolim.WRITING, Bolim.SPEAKING):
            return Response({"detail": "Bu endpoint faqat Writing/Speaking testlar uchun"}, status=400)

        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, dict):
            return Response({"detail": "javoblar {qism_id: matn} lug'ati majburiy"}, status=400)

        qismlar = list(test.qismlar.all())
        for qism in qismlar:
            matn = (javoblar.get(str(qism.id)) or "").strip()
            if len(matn.split()) < 20:
                return Response(
                    {"detail": f"\"{qism.sarlavha or qism.tur}\" uchun matn juda qisqa — kamida 20 so'z"},
                    status=400,
                )

        try:
            provider = provider_tanla(request.user)
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)

        natijalar = []
        bandlar = []
        try:
            for qism in qismlar:
                matn = javoblar[str(qism.id)].strip()
                if test.bolim == Bolim.WRITING:
                    rasm_bytes, rasm_mime = None, None
                    if qism.rasm:
                        rasm_bytes, rasm_mime = qism.rasm.read(), "image/png"
                    baho = provider.writing_baholash(
                        matn, savol_matni=qism.matn, tur=qism.tur,
                        rasm_bytes=rasm_bytes, rasm_mime=rasm_mime,
                    )
                    natija = baho["natija"]
                    WritingTekshiruv.objects.create(
                        talaba=request.user,
                        matn=matn,
                        natija=natija,
                        task_type=str(natija.get("task_type", qism.tur)),
                        overall_band=natija.get("overall_band"),
                        provider=baho["provider"],
                        model=baho["model"],
                        input_tokens=baho["input_tokens"],
                        output_tokens=baho["output_tokens"],
                    )
                    bandlar.append(natija.get("overall_band"))
                else:
                    baho = provider.speaking_matn_baholash(matn, savol_matni=qism.matn, tur=qism.tur)
                    natija = baho["natija"]
                    SpeakingTekshiruv.objects.create(
                        talaba=request.user,
                        rejim=SpeakingTekshiruv.Rejim.MATN,
                        matn=matn,
                        natija=natija,
                        part_type=str(natija.get("part_type", qism.tur)),
                        overall_band=natija.get("overall_band_no_pronunciation"),
                        provider=baho["provider"],
                        model=baho["model"],
                        input_tokens=baho["input_tokens"],
                        output_tokens=baho["output_tokens"],
                    )
                    bandlar.append(natija.get("overall_band_no_pronunciation"))
                natijalar.append({"qism_id": qism.id, "tur": qism.tur, "sarlavha": qism.sarlavha, "natija": natija})
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)

        bandlar = [b for b in bandlar if b is not None]
        umumiy_band = round(sum(bandlar) / len(bandlar) * 2) / 2 if bandlar else None

        xizmat = "w" if test.bolim == Bolim.WRITING else "s"
        paket = paketdan_ishlat(request.user, xizmat)

        return Response(
            {
                "natijalar": natijalar,
                "umumiy_band": umumiy_band,
                "paketdan": paket is not None,
            }
        )
