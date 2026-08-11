import json
import logging
import re

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Markaz, User
from accounts.permissions import owner_mi
from assessment.providers import ProviderXatosi
from audit.models import FaoliyatYozuvi
from audit.utils import logla, maydon_diff

from .models import (
    Bolim,
    ImtihonMock,
    ImtihonTest,
    LimitTopUp,
    Manba,
    Mashq,
    MashqYechim,
    MockYechim,
    TestPapkasi,
    TestQismi,
    TestYechim,
    band_hisobla,
    javoblarni_tekshir,
    korinadigan_mashqlar,
    korinadigan_moklar,
    korinadigan_testlar,
    kunlik_limit_holati,
)

logger = logging.getLogger(__name__)


def _manba_ol(request):
    """So'rovdan `manba` ni oladi — query parametrdan yoki tanadan
    (2026-07-27). Noto'g'ri/bo'sh qiymatda `admin` qaytaradi, ya'ni eski
    mijozlar (manba yubormaydiganlar) avvalgidek "IELTS testlari"ga
    yozadi — orqaga moslik."""
    qiymat = request.query_params.get("manba") or (
        request.data.get("manba") if hasattr(request, "data") else None
    )
    return qiymat if qiymat in Manba.values else Manba.ADMIN


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
        # 2026-08-11: "Javobsiz savollar hisoboti" uchun qo'shildi —
        # `MashqTolaTahrir` ichidagi `<ImtihonOtish manba={manba} .../>`
        # oldindan-ko'rish uchun kerak, avval ro'yxat sahifasi buni
        # o'zining `manba` propidan (butun sahifa uchun bitta qiymat)
        # olardi, yangi hisobot sahifasi esa bir nechta manba aralash
        # ro'yxatni ko'rsatadi — har test o'z manbasini bilishi shart.
        "manba": t.manba,
        "korinish": t.korinish,
        "papka": t.papka_id,
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


def _mock_nomini_chiqar(nomlar):
    """4 ta test nomidan (masalan "Cambridge IELTS 13 Test 1 Listening",
    "... Reading" va h.k.) umumiy mock nomini chiqarib olishga urinadi —
    oxiridagi bolim so'zini olib tashlaydi. Barchasi bir xilga tushmasa,
    birinchi test nomini ishlatadi."""
    tozalar = [
        re.sub(r"\s*[-—]?\s*(Reading|Listening|Writing|Speaking)\s*$", "", n, flags=re.IGNORECASE).strip()
        for n in nomlar
    ]
    if len(set(tozalar)) == 1 and tozalar[0]:
        return tozalar[0]
    return nomlar[0] if nomlar else "Mock imtihon"


def _test_yarat(data, markaz, rasm_fayllar=None, audio_fayllar=None, yaratuvchi=None,
                manba=Manba.ADMIN):
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
        name=name, bolim=bolim, markaz=markaz, korinish=korinish,
        yaratuvchi=yaratuvchi, manba=manba,
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


def _savol_javobsizmi(savol):
    """`togri` maydoni bo'sh — string ("") ham, ro'yxat ([]) ham, umuman
    yo'q ham bo'lishi mumkin (`RoyxatMaydoni` ba'zi savol turlarida
    massiv beradi — `imtihon_variantlar_izoh` atrofidagi kodga qarang)."""
    togri = savol.get("togri")
    if isinstance(togri, list):
        return not any(str(x).strip() for x in togri)
    return not str(togri or "").strip()


def _savol_matni_qisqart(matn, uzunlik=90):
    matn = (matn or "").strip()
    return matn if len(matn) <= uzunlik else matn[:uzunlik].rstrip() + "…"


class JavobsizSavollarHisobotiView(APIView):
    """Owner/admin uchun — Reading/Listening testlarida to'g'ri javobi
    (`togri`) belgilanmagan savollarni topib, jadval qatorlari sifatida
    qaytaradi (2026-08-11, foydalanuvchi talabi: "IELTS mashqlari
    bo'limidagi R/L mashqlarida qaysi mashqdagi qaysi savolning javobi
    berilmaganini topib bersin").

    FAQAT Reading/Listening — Writing/Speaking'da `togri` maydoni
    umuman yo'q (AI baholaydi), shuning uchun ular tekshirilmaydi.

    "Savol raqami" — foydalanuvchi aniq ko'rsatdi: "shu testdagi umumiy
    raqam, passage'ga bog'lanmagan, 1-40 gacha bo'lgan son". Bazada bu
    saqlanmaydi (har qism o'z `savollar` massividagi o'rnini biladi,
    xolos) — shu yerda QISMLAR TARTIB BO'YICHA aylanib, o'sib boruvchi
    hisoblagich bilan HISOBLANADI (talaba tomonidagi raqamlash bilan
    bir xil mantiq: oldingi qismlar savol sonini yig'ib boriladi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        qatorlar = []
        testlar = ImtihonTest.objects.filter(
            bolim__in=[Bolim.READING, Bolim.LISTENING]
        ).order_by("bolim", "name")
        for test in testlar:
            raqam = 0
            for qism in test.qismlar.order_by("tartib"):
                for savol in qism.savollar or []:
                    raqam += 1
                    if _savol_javobsizmi(savol):
                        qatorlar.append({
                            "bolim": test.bolim,
                            "test_id": test.id,
                            "test_nomi": test.name,
                            "manba": test.manba,
                            "savol_raqami": raqam,
                            "savol_matni": _savol_matni_qisqart(savol.get("savol")),
                        })
        return Response(qatorlar)


class ImtihonBoshqaruvView(APIView):
    """Owner/admin uchun — to'liq testlar ro'yxati va yaratish (qismlari
    bilan birga, bitta JSON so'rovda). Audio/rasm har qismga keyinroq
    TestQismiFayllarBoshqaruvView orqali biriktiriladi (yoki ZIP yuklashda
    — ImtihonZipBoshqaruvView — bitta so'rovda birga keladi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qs = ImtihonTest.objects.filter(manba=_manba_ol(request)).order_by("-created_at")
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

        test, xato = _test_yarat(
            request.data, markaz, yaratuvchi=request.user, manba=_manba_ol(request)
        )
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

        # Qaysi bo'limga yuklanmoqda — "IELTS testlari" (admin) yoki
        # "AI mashqlari" (ai). Yaratilgan testlar va avtomatik mock ham
        # shu manba bilan belgilanadi.
        manba = _manba_ol(request)

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
                    yaratuvchi=request.user, manba=manba,
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
                yaratuvchi=request.user, manba=manba,
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

        # Agar ko'p-papkali ZIP'da har 4 bo'lim (L/R/W/S) aynan bittadan
        # yaratilgan bo'lsa — bularni avtomatik bitta Mock imtihonga
        # bog'laymiz (2026-07-25, "4 turdagi mashqni bitta mock qilish").
        mock = None
        if papkalar:
            bolim_testlari = {}
            bir_martalik = True
            for test in yaratilgan:
                if test.bolim in bolim_testlari:
                    bir_martalik = False
                    break
                bolim_testlari[test.bolim] = test
            if bir_martalik and set(bolim_testlari) == set(Bolim.values):
                mock = ImtihonMock.objects.create(
                    name=_mock_nomini_chiqar([t.name for t in yaratilgan]),
                    markaz=markaz,
                    listening=bolim_testlari[Bolim.LISTENING],
                    reading=bolim_testlari[Bolim.READING],
                    writing=bolim_testlari[Bolim.WRITING],
                    speaking=bolim_testlari[Bolim.SPEAKING],
                    korinish="private",
                    yaratuvchi=request.user,
                    manba=manba,
                )

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
                "mock": {"id": mock.id, "name": mock.name} if mock else None,
            },
            status=201,
        )


class ImtihonPdfBoshqaruvView(APIView):
    """Owner/admin uchun — Reading/Listening testini PDF'dan yaratish
    (2026-07-31, foydalanuvchi talabi).

    Prinsip Kurslar'dagi "rasmdan mashq qo'shish" bilan bir xil: bitta
    fayl -> bitta sinxron AI chaqiruvi -> natija darhol bazaga yoziladi.
    ZIP'dagi ko'p-bosqichli jarayon shart emas.

    Farqi ZIP yo'lidan: bu yerda JSON'ni tashqi AI emas, PDF'ni O'ZI
    ko'rgan Claude tayyorlaydi — passage chegaralari chalkashmasligi
    uchun (tafsilot: `pdf_generatsiya` modul izohi)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        fayl = request.FILES.get("pdf_fayl")
        if not fayl:
            return Response({"detail": "pdf_fayl majburiy"}, status=400)

        from django.core.files.base import ContentFile

        from .pdf_generatsiya import pdfdan_test_chiqar, pdfdan_yozgap_chiqar, qism_rasmini_kes

        nom = (request.data.get("name") or "").strip()
        bolim = request.data.get("bolim") or ""
        pdf_bytes = fayl.read()

        if bolim in (Bolim.WRITING, Bolim.SPEAKING):
            # Writing/Speaking'da savol raqamlash yo'q (Task1/Task2 yoki
            # Part1/2/3 — sonli tugun), shuning uchun Reading/Listening'dagi
            # "qismlar" (savol oraliqlari) shart emas.
            data, xato = pdfdan_yozgap_chiqar(pdf_bytes, bolim, nom=nom)
            xatolar = []
        else:
            # Admin yuklash oynasida test nomini va har qismning savol
            # oralig'ini kiritadi (2026-07-31). Bular AI taxminidan ustun —
            # AI nomni noto'g'ri olib, 40 o'rniga 38 savol chiqargan edi.
            try:
                oraliqlar = json.loads(request.data.get("qismlar") or "[]")
            except (json.JSONDecodeError, TypeError):
                return Response({"detail": "qismlar noto'g'ri formatda"}, status=400)
            if not isinstance(oraliqlar, list):
                return Response({"detail": "qismlar ro'yxat bo'lishi kerak"}, status=400)
            for o in oraliqlar:
                if (not isinstance(o, dict)
                        or not isinstance(o.get("boshi"), int)
                        or not isinstance(o.get("oxiri"), int)
                        or not 0 < o["boshi"] <= o["oxiri"]):
                    return Response(
                        {"detail": "Har qism uchun to'g'ri savol oralig'i kerak"},
                        status=400,
                    )
            data, xato, xatolar = pdfdan_test_chiqar(
                pdf_bytes, bolim, nom=nom, oraliqlar=oraliqlar,
            )
        if xato:
            return Response({"detail": xato}, status=502)

        manba = _manba_ol(request)
        test, yaratish_xatosi = _test_yarat(
            data, markaz, yaratuvchi=request.user, manba=manba
        )
        if yaratish_xatosi:
            return Response(yaratish_xatosi, status=400)

        # 2026-07-31 talabi: PDF'dagi xarita/diagramma/grafik ham chiqsin.
        # AI 1-chaqiruvda faqat SAHIFA raqamini aytadi, rasmning o'zi shu
        # yerda — sahifa bo'yicha alohida chaqiruv bilan — kesib olinadi
        # (tafsilot: `pdf_generatsiya.qism_rasmini_kes`). Bir xil sahifa
        # bir necha qismga tegishli bo'lsa, faqat BIR MARTA kesiladi.
        kesilganlar = {}
        rasmli_qismlar = 0
        qismlar_data = data.get("qismlar") or []
        for qism, q_data in zip(test.qismlar.all(), qismlar_data):
            sahifa = q_data.get("rasm_sahifasi")
            if not isinstance(sahifa, int) or sahifa < 1:
                continue
            if sahifa not in kesilganlar:
                kesilganlar[sahifa] = qism_rasmini_kes(pdf_bytes, sahifa)
            kesilgan = kesilganlar[sahifa]
            if not kesilgan:
                continue
            qism.rasm.save(
                f"{test.id}_{qism.tartib}_s{sahifa}.jpg", ContentFile(kesilgan), save=True
            )
            rasmli_qismlar += 1

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=test,
            obyekt_turi="ImtihonTest",
            snapshot={
                "name": test.name,
                "bolim": test.bolim,
                "qismlar_soni": test.qismlar.count(),
                "manba": "pdf",
                "rasmli_qismlar": rasmli_qismlar,
                "xatolar": xatolar,
            },
        )
        # `xatolar` — chiqarilmagan qismlar (vaqt budjeti tugadi yoki AI
        # xato berdi). Test baribir yaratiladi, lekin admin NIMA
        # yetishmaganini ko'rishi shart — avval bu jim qolib, "faqat bir
        # qismi yuklandi" degan tushunarsiz holat chiqardi.
        return Response(
            {**_test_admin_dict(test), "xatolar": xatolar}, status=201
        )


class MashqGeneratsiyaView(APIView):
    """Owner/admin uchun — "AI mashqlari" sahifasida bitta tugma orqali
    AI'dan YANGI mini-test so'rash (2026-08-02, foydalanuvchi talabi).

    PDF/ZIP/JSON'dan farqi: manba matn YO'Q — AI mavzuni o'zi o'ylab
    topadi. Reading/Listening — 1 qism, Writing — Task1+Task2,
    Speaking — Part1+2+3 (tafsilot: `mashq_generatsiya` moduli)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        bolim = request.data.get("bolim") or ""
        band = request.data.get("band") or ""

        from django.core.files.base import ContentFile

        from .mashq_generatsiya import mashq_yarat

        # Takrorlanmaslik uchun (2026-08-02) — shu bo'limda avval AI
        # tomonidan yaratilgan testlarning nomlari promtga qo'shiladi.
        oldingi_mavzular = list(
            ImtihonTest.objects.filter(manba=Manba.AI, bolim=bolim)
            .order_by("-created_at")
            .values_list("name", flat=True)[:25]
        )
        data, rasm_bytes, audio_royxati, xato = mashq_yarat(bolim, band, oldingi_mavzular)
        # 2026-08-08: Listening 4 part'dan iborat va har part uchun AI +
        # TTS sarflanadi (Gemini TTS KUNLIK limitga ega). Avval 4-part
        # xato bersa, tayyor bo'lgan 3 tasi ham tashlanardi. Endi
        # `listening_yarat` qisman natijani qaytaradi: test SAQLANADI,
        # admin esa "Davom ettirish" bilan qolgan part'larni qo'shadi.
        chala_xato = None
        if xato:
            if not (data and data.get("qismlar")):
                return Response({"detail": xato}, status=502)
            chala_xato = xato

        test, yaratish_xatosi = _test_yarat(
            data, markaz, yaratuvchi=request.user, manba=Manba.AI,
        )
        if yaratish_xatosi:
            return Response(yaratish_xatosi, status=400)

        qismlar_tartib_boyicha = list(test.qismlar.order_by("tartib"))
        if rasm_bytes and qismlar_tartib_boyicha:
            qismlar_tartib_boyicha[0].rasm.save(
                f"{test.id}_ai_diagramma.png", ContentFile(rasm_bytes), save=True
            )
        # Listening — har part (qism) o'zining audiosi bilan (2026-08-02,
        # to'liq test — 4 part, har biri boshqa audio).
        if audio_royxati:
            for qism, audio_bytes in zip(qismlar_tartib_boyicha, audio_royxati):
                if audio_bytes:
                    qism.audio_fayl.save(f"{test.id}_{qism.tartib}_ai_audio.wav", ContentFile(audio_bytes), save=True)

        # Band bo'yicha papkaga avtomatik joylash (2026-08-02, foydalanuvchi
        # talabi) — "Band 5-6" kabi papka shu manbada yo'q bo'lsa yaratiladi.
        # 2026-08-11: `bolim` KIRITILMAYDI — endi bitta "Band 5-6" papkasi
        # Reading/Listening/Writing/Speaking'ning HAMMASINI birga saqlaydi
        # (avval har bo'lim o'zining "Band 5-6" papkasini olardi, ya'ni
        # bir xil nomli 4 ta alohida papka bo'lib chiqardi). Admin xohlasa
        # keyin tahrirlashda boshqa papkaga ko'chirishi mumkin.
        papka, _yaratildimi = TestPapkasi.objects.get_or_create(
            nomi=f"Band {band}", manba=Manba.AI, markaz=markaz,
        )
        test.papka = papka
        test.save(update_fields=["papka"])

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=test,
            obyekt_turi="ImtihonTest",
            snapshot={"name": test.name, "bolim": test.bolim, "manba": "ai-generatsiya", "band": band},
        )
        javob = _test_admin_dict(test)
        if chala_xato:
            javob["chala_xato"] = chala_xato
        return Response(javob, status=201)


# Listening testda nechta part bo'lishi kerak — `mashq_generatsiya.
# LISTENING_ORALIQLAR` bilan bir xil. Shu son bo'yicha testning CHALA
# ekani aniqlanadi (alohida bayroq/migratsiya kerak emas).
LISTENING_PART_SONI = 4


def _chala_listening_mi(test):
    return (
        test.bolim == "listening"
        and test.manba == Manba.AI
        and test.qismlar.count() < LISTENING_PART_SONI
    )


class ListeningDavomEttirishView(APIView):
    """CHALA qolgan AI Listening testini davom ettiradi (2026-08-08,
    foydalanuvchi talabi: "AI Listening qisman saqlash").

    Nega kerak: test 4 part, har part uchun AI chaqiruvi + TTS audio
    sarflanadi, Gemini TTS esa KUNLIK limitga ega. Avval 4-part xato
    bersa (masalan limit tugasa) tayyor 3 tasi ham yo'q qilinardi va
    hammasini boshidan qilishga to'g'ri kelardi. Endi qisman test
    saqlanadi va shu endpoint faqat YETISHMAYDIGAN part'larni
    generatsiya qilib, mavjud testga qo'shadi.

    `band` — so'rov tanasida berilishi mumkin; berilmasa test
    papkasidan ("Band 5-6") olinadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        if not _chala_listening_mi(test):
            return Response({"detail": "Bu test chala emas yoki AI Listening emas"}, status=400)

        from django.core.files.base import ContentFile

        from .mashq_generatsiya import BAND_GURUHLAR, listening_yarat

        # Band TESTNING O'ZIDAN olinadi — AI testlari "Band 5-6" nomli
        # papkaga avtomatik joylanadi. So'rovdagi qiymat faqat ZAXIRA
        # (masalan test papkadan chiqarib qo'yilgan bo'lsa): sahifadagi
        # tanlov shu testning haqiqiy darajasidan farq qilishi mumkin,
        # shuning uchun papka USTUN turadi.
        band = ""
        if test.papka and test.papka.nomi.startswith("Band "):
            band = test.papka.nomi[len("Band "):].strip()
        if band not in BAND_GURUHLAR:
            band = (request.data.get("band") or "").strip()
        if band not in BAND_GURUHLAR:
            return Response(
                {"detail": (
                    "Testning band darajasi aniqlanmadi. Testni \"Band 5-6\" "
                    "kabi papkaga joylang yoki band'ni so'rovda yuboring."
                )},
                status=400,
            )

        mavjud = test.qismlar.count()
        try:
            data, audio_royxati, xato = listening_yarat(
                band, oldingi_mavzular=None, boshlanuvchi_part=mavjud + 1,
            )
        except ValueError as e:  # band noto'g'ri
            return Response({"detail": str(e)}, status=400)

        if not (data and data.get("qismlar")):
            return Response({"detail": xato or "Yangi part chiqmadi"}, status=502)

        # Yangi part'lar MAVJUD testga qo'shiladi — `tartib` davom etadi.
        qoshilgan = 0
        for qism_data, audio_bytes in zip(data["qismlar"], audio_royxati or []):
            qism = TestQismi.objects.create(
                test=test,
                tartib=qism_data["tartib"],
                sarlavha=qism_data.get("sarlavha") or "",
                yoriqnoma=qism_data.get("yoriqnoma") or "",
                matn=qism_data.get("matn") or "",
                savollar=qism_data.get("savollar") or [],
                maxsus_format=qism_data.get("maxsus_format") or None,
            )
            if audio_bytes:
                qism.audio_fayl.save(
                    f"{test.id}_{qism.tartib}_ai_audio.wav", ContentFile(audio_bytes), save=True
                )
            qoshilgan += 1

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=test,
            obyekt_turi="ImtihonTest",
            obyekt_nomi=test.name,
            snapshot={"davom_ettirildi": qoshilgan, "jami_qism": test.qismlar.count()},
        )
        javob = _test_admin_dict(test)
        javob["qoshilgan_partlar"] = qoshilgan
        if xato:
            javob["chala_xato"] = xato
        return Response(javob)


class TestPapkaBoshqaruvView(APIView):
    """Owner/admin uchun — test papkalari ro'yxati va yaratish (2026-08-01,
    2026-08-11: bo'lim bo'yicha ajratish olib tashlandi; 2026-08-11 kech:
    2 darajali ichki papka qo'shildi, `TestPapkasi.parent` izohiga qarang).

    Papkalar BITTA manbaga tegishli — `TestPapkasi` izohiga qarang. Bo'lim
    bo'yicha filtr ENDI YO'Q: ro'yxat har doim shu manbadagi BARCHA
    papkalarni qaytaradi (qaysi bo'limlarning testi borligidan qat'i
    nazar) — frontend buni joriy bo'lim testlari bilan kesishtirib, faqat
    mos papkalarni/testlarni ko'rsatadi. `parent` maydoni javobda
    qaytariladi — frontend shu orqali 1/2-darajani ajratadi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qs = TestPapkasi.objects.filter(manba=_manba_ol(request))
        return Response(
            [
                {
                    "id": p.id,
                    "nomi": p.nomi,
                    "tartib": p.tartib,
                    "parent": p.parent_id,
                    "mock_id": p.mock.id if hasattr(p, "mock") else None,
                }
                for p in qs
            ]
        )

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)
        nomi = (request.data.get("nomi") or "").strip()
        if not nomi:
            return Response({"detail": "Papka nomi majburiy"}, status=400)

        parent = None
        parent_id = request.data.get("parent")
        if parent_id not in (None, "", "null"):
            parent = get_object_or_404(TestPapkasi, pk=parent_id, manba=_manba_ol(request))
            if parent.parent_id:
                # Ichki (2-darajali) papkaning o'ziga yana ichki papka
                # qo'shib bo'lmaydi — foydalanuvchi talabi, chuqurlik 2.
                return Response(
                    {"detail": "Ichki papkaning ichiga yana papka qo'shib bo'lmaydi (chuqurlik faqat 2 daraja)."},
                    status=400,
                )

        papka = TestPapkasi.objects.create(
            nomi=nomi, manba=_manba_ol(request), markaz=markaz, parent=parent,
        )
        return Response(
            {"id": papka.id, "nomi": papka.nomi, "tartib": papka.tartib, "parent": papka.parent_id},
            status=201,
        )


class TestPapkaDetailView(APIView):
    """Owner/admin uchun — papkani o'chirish/nomini o'zgartirish.

    O'chirilganda ichidagi testlar YO'QOLMAYDI — `papka` maydoni null
    bo'lib, ular "papkasiz" ro'yxatiga qaytadi (`SET_NULL`)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        papka = get_object_or_404(TestPapkasi, pk=pk)
        nomi = (request.data.get("nomi") or "").strip()
        if not nomi:
            return Response({"detail": "Papka nomi majburiy"}, status=400)
        papka.nomi = nomi
        papka.save(update_fields=["nomi"])
        return Response({"id": papka.id, "nomi": papka.nomi})

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        papka = get_object_or_404(TestPapkasi, pk=pk)
        papka.delete()
        return Response(status=204)


def _papka_bolim_testlari(papka):
    """Ichki papkadagi testlar — {bolim: ImtihonTest}. Har bo'limdan
    bittadan qoidasi papkaga qo'shishda allaqachon majburlangan
    (`ImtihonBoshqaruvDetailView.patch`) — shu yerda ikkilanish bo'lsa
    ham (masalan eski ma'lumot) oxirgisi olinadi."""
    return {t.bolim: t for t in papka.testlar.all()}


def _papkadan_mock_tayyorla(papka, foydalanuvchi):
    """Ichki papkadagi testlardan `ImtihonMock`ni yaratadi yoki
    mavjudini joriy holatga yangilaydi — IDEMPOTENT (`TestPapkasi.mock`
    OneToOne orqali get_or_create). `PapkadanMockYaratishView` (qo'lda,
    API uchun saqlangan) va `MockPapkalarView` (2026-08-11 kech,
    AVTOMATIK — admin tugma bosishi shart emas) ikkalasi ham shu
    funksiyani ishlatadi, mock yaratish mantig'i BITTA joyda."""
    bolim_testlari = _papka_bolim_testlari(papka)
    markaz = Markaz.objects.first()
    if not markaz:
        return None, bolim_testlari

    mock, yaratildimi = ImtihonMock.objects.get_or_create(
        papka=papka,
        defaults={
            "name": papka.nomi,
            "markaz": markaz,
            "korinish": "private",
            "yaratuvchi": foydalanuvchi,
            "manba": papka.manba,
        },
    )
    mock.listening = bolim_testlari.get(Bolim.LISTENING)
    mock.reading = bolim_testlari.get(Bolim.READING)
    mock.writing = bolim_testlari.get(Bolim.WRITING)
    mock.speaking = bolim_testlari.get(Bolim.SPEAKING)
    mock.name = papka.nomi
    mock.save(update_fields=["listening", "reading", "writing", "speaking", "name"])

    logla(
        foydalanuvchi=foydalanuvchi,
        harakat=(
            FaoliyatYozuvi.Harakat.YARATISH if yaratildimi else FaoliyatYozuvi.Harakat.OZGARTIRISH
        ),
        obyekt=mock,
        obyekt_turi="ImtihonMock",
        obyekt_nomi=mock.name,
        snapshot={"papka": papka.nomi, "bolimlar": list(bolim_testlari)},
    )
    return mock, bolim_testlari


def _papka_mock_moslashtir(papka, foydalanuvchi):
    """Ichki papkaning test tarkibi o'zgarganda (test qo'shildi/olib
    tashlandi/almashtirildi) Mock holatini shu voqeaning O'ZIDA moslaydi
    (2026-08-11, foydalanuvchi qarori: "bitta papkaga 4 ta mashqning
    hammasi qo'shilgandan keyin AVTOMATIK mock yaratilsin, agar qaysidir
    mashq olib tashlanib o'rniga boshqa mashq qo'shilsa, eski mock
    o'rniga yangisini qo'shsin" — ya'ni Mock tabi ochilishini KUTMAYDI,
    yaratish/yangilash yozish operatsiyasining o'zida bo'ladi).

    Faqat 2 holatda ishlaydi:
      * Papka ENDI 4/4 to'liq (barcha bo'limdan bittadan) — mock hali
        yo'q bo'lsa YARATILADI.
      * Mock ALLAQACHON bor (avval 4/4 bo'lgan) — tarkib o'zgargan
        bo'lsa (masalan bitta bo'lim olib tashlanib, boshqasi qo'shilgan)
        QAYTA YANGILANADI, hatto vaqtincha 4/4 dan pastga tushib
        qolgan bo'lsa ham (aks holda eski, endi noto'g'ri testga ishora
        stale FK qolib ketardi).
    Hech qachon 4/4 ga YETMAGAN va mock hali YO'Q papka uchun YANGI mock
    OCHIB QO'YMAYDI — "hammasi qo'shilgandan keyin" shartiga qat'iy
    rioya qilinadi."""
    if not papka.parent_id:
        return  # faqat 2-darajali (ichki) papkalarga tegishli
    bolim_testlari = _papka_bolim_testlari(papka)
    toliqmi = set(bolim_testlari) == _TOLIQ_BOLIMLAR
    mock_bor = hasattr(papka, "mock")
    if toliqmi or mock_bor:
        _papkadan_mock_tayyorla(papka, foydalanuvchi)


class PapkadanMockYaratishView(APIView):
    """Owner/admin uchun — 2-darajali (ichki) papkadagi testlardan Mock
    imtihon yaratish yoki mavjudini qayta ishlatish (2026-08-11 kech,
    foydalanuvchi talabi: "mock test rejimida aynan shu 4 likni beramiz").

    2026-08-11 (yana kech): admin panelidagi "Mock sifatida boshlash"
    TUGMASI OLIB TASHLANDI — endi `MockPapkalarView` 4/4 to'liq
    papkalarni O'ZI avtomatik aniqlab, shu funksiyani (`_papkadan_mock_
    tayyorla`) chaqiradi, qo'lda bosish shart emas. Bu endpoint API
    darajasida SAQLANDI (dasturiy/qo'lda chaqiruv uchun), lekin
    frontend UI'da endi hech qayerdan chaqirilmaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        papka = get_object_or_404(TestPapkasi, pk=pk)
        if not papka.parent_id:
            return Response(
                {"detail": "Mock faqat ichki (2-darajali) papkadan yig'iladi — bu 1-darajali papka."},
                status=400,
            )
        if not papka.testlar.exists():
            return Response({"detail": "Bu papkada test yo'q"}, status=400)

        mavjud_edimi = hasattr(papka, "mock")
        mock, _bolim_testlari = _papkadan_mock_tayyorla(papka, request.user)
        if mock is None:
            return Response({"detail": "Markaz topilmadi"}, status=400)
        return Response(_mock_admin_dict(mock), status=200 if mavjud_edimi else 201)


class ImtihonBoshqaruvDetailView(APIView):
    """Owner/admin uchun — to'liq testni o'chirish yoki papkaga ko'chirish."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Bitta testni TO'LIQ (qismlari, savollari bilan) olish
        (2026-08-11, "Javobsiz savollar hisoboti" uchun) — avval bunday
        yo'l yo'q edi, ro'yxat sahifasi test obyektini `royxat`dan
        (allaqachon yuklangan) olardi. Hisobot sahifasi esa ro'yxatni
        yuklamaydi, faqat topilgan savol qatorini ko'rsatadi — shuning
        uchun "Mashq nomi"ga bosilganda tahrirlash oynasini ochish
        uchun testni ALOHIDA so'rash kerak."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        return Response(_test_admin_dict(test))

    def patch(self, request, pk):
        """Testni papkaga ko'chirish va/yoki nomini o'zgartirish
        (2026-08-01/2). `papka`: papka id yoki null (papkadan chiqarish).
        `name`: yangi nom (ixtiyoriy, berilmasa o'zgarmaydi)."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        maydonlar = []

        if "name" in request.data:
            nom = (request.data.get("name") or "").strip()
            if not nom:
                return Response({"detail": "Test nomi bo'sh bo'lishi mumkin emas"}, status=400)
            test.name = nom
            maydonlar.append("name")

        # 2026-08-11 (kech): eski papka ESLAB QOLINADI — testni boshqa
        # papkaga ko'chirish ("olib tashlash + o'rniga boshqasini
        # qo'shish") eski ichki papkani ham 4/4'dan tushirishi mumkin,
        # shu papkaning Mock holati ham moslashtirilishi kerak.
        eski_papka = test.papka

        if "papka" in request.data:
            papka_id = request.data.get("papka")
            if papka_id in (None, "", "null"):
                test.papka = None
            else:
                # 2026-08-11: bo'lim tekshiruvi olib tashlandi — papka endi
                # bir nechta bo'lim testini birga saqlaydi (`TestPapkasi`
                # izohiga qarang), shuning uchun bu yerda rad etish kerak
                # emas.
                papka = get_object_or_404(TestPapkasi, pk=papka_id)
                # 2026-08-11 kech: 2-DARAJALI (ichki, parent bor) papka —
                # Mock yig'ish uchun mo'ljallangan, shuning uchun har
                # bo'limdan FAQAT BITTADAN test bo'lishi mumkin (foydalanuvchi
                # talabi). 1-darajali papkalarda bu cheklov yo'q.
                if papka.parent_id:
                    band_test = (
                        ImtihonTest.objects.filter(papka=papka, bolim=test.bolim)
                        .exclude(pk=test.pk)
                        .first()
                    )
                    if band_test:
                        return Response(
                            {
                                "detail": (
                                    f"Bu ichki papkada allaqachon '{test.get_bolim_display()}' "
                                    f"bo'limidan test bor ({band_test.name}) — har bo'limdan "
                                    "faqat bittadan test qo'shish mumkin."
                                )
                            },
                            status=400,
                        )
                test.papka = papka
            maydonlar.append("papka")

        if not maydonlar:
            return Response({"detail": "name yoki papka maydoni kerak"}, status=400)
        test.save(update_fields=maydonlar)

        # 2026-08-11 (kech): papka o'zgargan bo'lsa — YANGI papka (agar
        # shu bilan 4/4 to'lgan bo'lsa yaratadi/yangilaydi) VA eski papka
        # (agar mock'i bor bo'lsa, endi bo'shagan bo'limni aks ettirib
        # yangilanadi) ikkalasi ham moslashtiriladi.
        if "papka" in maydonlar:
            if eski_papka and eski_papka.pk != test.papka_id:
                _papka_mock_moslashtir(eski_papka, request.user)
            if test.papka:
                _papka_mock_moslashtir(test.papka, request.user)

        return Response(_test_admin_dict(test))

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        test = get_object_or_404(ImtihonTest, pk=pk)
        test_id, nomi, bolim = test.id, test.name, test.bolim
        papka = test.papka  # o'chirishdan OLDIN — pastda Mock moslashtiriladi
        test.delete()
        if papka:
            _papka_mock_moslashtir(papka, request.user)
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
    rasm (Map/Diagram Labelling, Writing Task 1 grafigi) biriktirish,
    shuningdek MATNINI tahrirlash (2026-08-05, foydalanuvchi talabi:
    "mavjud testlar qismida mashq ustiga bosganda ... matnni qo'lda
    tahrirlash imkoni bo'lsin" — avval faqat fayl almashtirish bor edi).

    `JSONParser` qo'shildi (fayl bo'lmagan, faqat matn/savol tahriri
    uchun) — `MultiPartParser` bilan bir qatorda, DRF ikkalasini ham
    Content-Type'ga qarab avtomatik tanlaydi."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # request.data'dan to'g'ridan-to'g'ri (o'zgartirmasdan) o'tkaziladigan
    # matn maydonlari — fayl EMAS, shuning uchun oddiy qiymat solishtirish
    # bilan "o'zgardimi" tekshiriladi (audit-log uchun eski/yangi qiymat).
    _MATN_MAYDONLARI = ("sarlavha", "yoriqnoma", "matn", "savollar", "maxsus_format")

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
        for maydon in self._MATN_MAYDONLARI:
            if maydon not in request.data:
                continue
            yangi = request.data[maydon]
            eski = getattr(qism, maydon)
            if yangi == eski:
                continue
            setattr(qism, maydon, yangi)
            ozgarishlar[maydon] = {
                "eski": eski if maydon in ("sarlavha", "yoriqnoma", "matn") else "—",
                "yangi": yangi if maydon in ("sarlavha", "yoriqnoma", "matn") else "yangilandi",
            }
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

    def delete(self, request, pk):
        """2026-08-10, foydalanuvchi talabi: audio yoki rasmni O'CHIRISH
        (masalan noto'g'ri fayl yuklangan bo'lsa, qayta yuklashdan oldin
        tozalash). `?maydon=audio_fayl` yoki `?maydon=rasm`."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qism = get_object_or_404(TestQismi, pk=pk)
        maydon = request.query_params.get("maydon")
        if maydon not in ("audio_fayl", "rasm"):
            return Response({"detail": "'maydon' 'audio_fayl' yoki 'rasm' bo'lishi kerak"}, status=400)
        fayl = getattr(qism, maydon)
        if fayl:
            fayl.delete(save=False)
            qism.save(update_fields=[maydon])
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=qism.test,
                obyekt_turi="ImtihonTest",
                obyekt_nomi=f"{qism.test.name} — {qism.sarlavha or qism.tartib}-qism",
                ozgarishlar={maydon: {"eski": "yangilandi", "yangi": "—"}},
            )
        return Response(_qism_admin_dict(qism))


class QismPozitsiyaAniqlashView(APIView):
    """Owner/admin uchun — B-BOSQICH (2026-08-05): shu qismda ALLAQACHON
    saqlangan rasmdan (Map/Diagram Labelling) savol pozitsiyalarini AI
    orqali QAYTA aniqlash. Natija DARHOL saqlanmaydi — faqat TAKLIF
    qaytaradi, admin `TestQismiFayllarBoshqaruvView.patch` orqali
    (savollar[].pozitsiya bilan) tasdiqlab saqlaydi — xuddi Kurslar
    blok-tasdiqlash tamoyili: AI taxmin qiladi, odam tasdiqlaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        qism = get_object_or_404(TestQismi, pk=pk)
        if not qism.rasm:
            return Response({"detail": "Bu qismda rasm yo'q"}, status=400)
        if not qism.savollar:
            return Response({"detail": "Bu qismda savol yo'q"}, status=400)

        from .pdf_generatsiya import pdf_provider_olish
        from .pozitsiya_generatsiya import pozitsiyalarni_aniqla

        savollar = [
            {"raqam": i + 1, "savol": s.get("savol") or ""}
            for i, s in enumerate(qism.savollar)
        ]
        try:
            provider = pdf_provider_olish()
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)
        rasm_bytes = qism.rasm.read()
        pozitsiyalar, xato = pozitsiyalarni_aniqla(provider, rasm_bytes, savollar)
        if xato:
            return Response({"detail": xato}, status=502)
        # JSON kalitlar doim string bo'ladi — frontend ham shunga qarab o'qiydi.
        return Response({"pozitsiyalar": {str(k): v for k, v in pozitsiyalar.items()}})


class ImtihonListView(APIView):
    """Talabaga ko'rinadigan to'liq testlar ro'yxati (nomi, bo'limi).

    2026-08-01: har test qaysi papkada ekani ham qaytadi (`papka` — id,
    `papka_nomi`) — talaba tomonida papkalar accordion bo'lib ko'rsatiladi.
    Papkasiz testlar `papka: null` bilan keladi."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 2026-07-27: `manba` bilan "IELTS testlari" (admin) va "AI mashqlari"
        # (ai) bo'limlari bir xil endpointdan, lekin alohida ro'yxat oladi.
        qs = korinadigan_testlar(request.user, manba=request.query_params.get("manba"))
        bolim = request.query_params.get("bolim")
        if bolim:
            qs = qs.filter(bolim=bolim)
        qs = qs.select_related("papka")
        return Response([
            {
                "id": t.id,
                "name": t.name,
                "bolim": t.bolim,
                "papka": t.papka_id,
                "papka_nomi": t.papka.nomi if t.papka_id else None,
            }
            for t in qs
        ])


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


def _mock_yechimni_yangila(user, mock_yechim_id, bolim, malumot):
    """Mock imtihon sessiyasi davomida (agar `mock_yechim_id` yuborilgan
    bo'lsa) shu bo'limning natijasini `MockYechim`ga yozadi, barcha kerakli
    bo'limlar tugagan bo'lsa Overall Band'ni hisoblab, `tugallandi_at`ni
    belgilaydi. `mock_yechim_id` bo'lmasa (mockdan tashqari, mustaqil test)
    hech narsa qilmaydi, None qaytaradi."""
    if not mock_yechim_id:
        return None
    yechim = MockYechim.objects.filter(pk=mock_yechim_id, talaba=user).select_related("mock").first()
    if not yechim:
        return None

    if bolim == Bolim.LISTENING:
        yechim.listening_yechim = malumot["yechim"]
    elif bolim == Bolim.READING:
        yechim.reading_yechim = malumot["yechim"]
    elif bolim == Bolim.WRITING:
        yechim.writing_band = malumot["band"]
    elif bolim == Bolim.SPEAKING:
        yechim.speaking_band = malumot["band"]

    if yechim.hammasi_tugadimi(yechim.mock):
        from django.utils import timezone

        bandlar = yechim.band_royxati()
        yechim.overall_band = round(sum(bandlar) / len(bandlar) * 2) / 2 if bandlar else None
        yechim.tugallandi_at = timezone.now()

    yechim.save()
    return {
        "id": yechim.id,
        "tugadimi": yechim.tugallandi_at is not None,
        "overall_band": float(yechim.overall_band) if yechim.overall_band is not None else None,
    }


def _yechilayotgan_testni_ol(user, pk):
    """Yechilayotgan testni oladi; yo'q bo'lsa TUSHUNARLI xato qaytaradi.

    2026-07-31 (foydalanuvchi xabar berdi): "Testni yakunlash" bosilganda
    xom Django xabari chiqardi — "No ImtihonTest matches the given query."
    Bu talabaga hech narsa tushuntirmaydi. Sabab esa deyarli doim bitta:
    test OCHIQ turganda o'chirilgan yoki qayta yuklangan (admin paneli va
    test yechish oynasi BITTA sahifada — `ImtihonBoshqarish.jsx`).

    `kod` — frontend uchun mashina o'qiy oladigan belgi: shu kod kelsa
    test oynasi yopilib, ro'yxat yangilanadi.

    Qaytaradi: (test, None) yoki (None, Response)."""
    test = korinadigan_testlar(user).filter(pk=pk).first()
    if test is None:
        return None, Response(
            {
                "detail": (
                    "Bu test topilmadi — u o'chirilgan yoki qayta yuklangan "
                    "bo'lishi mumkin. Testni ro'yxatdan qaytadan oching."
                ),
                "kod": "test_topilmadi",
            },
            status=404,
        )
    return test, None


class ImtihonYechishView(APIView):
    """Butun testga javob yuborish — flat ro'yxat, barcha qismlar bo'yicha
    uzluksiz tartibda. Kunlik limitga bog'liq emas (mustaqil, cheklovsiz)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        test, xato = _yechilayotgan_testni_ol(request.user, pk)
        if xato:
            return xato
        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, list):
            return Response({"detail": "javoblar ro'yxati majburiy"}, status=400)

        barcha_savollar = []
        for qism in test.qismlar.all():
            barcha_savollar.extend(qism.savollar)

        natija = javoblarni_tekshir(barcha_savollar, javoblar)
        band = band_hisobla(natija["ball"], natija["jami"], test.bolim)
        yechim = TestYechim.objects.create(
            talaba=request.user,
            test=test,
            javoblar=javoblar,
            ball=natija["ball"],
            jami=natija["jami"],
            natijalar=natija["natijalar"],
            band=band,
        )

        mock_natija = _mock_yechimni_yangila(
            request.user, request.data.get("mock_yechim_id"), test.bolim, {"yechim": yechim}
        )

        return Response(
            {
                "ball": natija["ball"],
                "jami": natija["jami"],
                "natijalar": natija["natijalar"],
                "band": band,
                "mock": mock_natija,
            }
        )


# Writing/Speaking qismlarining BAHOLASH NAVBATI (2026-07-26 talabi):
# Writing — avval Task 1, keyin Task 2; Speaking — Part 1, keyin 2, keyin 3.
# `TestQismi.Meta.ordering = ["tartib"]` odatda shu tartibni beradi, lekin
# `tartib` yuklashda noto'g'ri qo'yilgan bo'lsa navbat buzilardi — shuning
# uchun tur bo'yicha ANIQ tartib majburlanadi, `tartib` esa faqat teng
# hollarda (yoki tur bo'sh bo'lsa) ishlatiladi.
_YOZGAP_NAVBATI = {"task1": 0, "task2": 1, "part1": 0, "part2": 1, "part3": 2}


def _yozgap_qism_tartibi(qism):
    return (_YOZGAP_NAVBATI.get(qism.tur, 99), qism.tartib)


class ImtihonYozGapTekshirishView(APIView):
    """Writing/Speaking to'liq testga javob — har bir qism (Task1+Task2 yoki
    Part1/2/3) uchun AI orqali baholanadi (assessment.providers — Writing/
    Speaking AI-tekshiruv paneli bilan bir xil mexanizm, mavzuga moslik
    tekshiruvi bilan birga).

    Har bir qism uchun alohida `WritingTekshiruv`/`SpeakingTekshiruv` yozuvi
    yaratiladi — shunda mavjud XP/tarix/statistika infratuzilmasi (signal
    orqali) avtomatik ishlaydi, alohida "natija" modeli kerak emas. Paket
    (agar aktiv bo'lsa) BUTUN test uchun bir marta yechiladi (real IELTS'da
    Writing/Speaking — bitta yaxlit sessiya, har qism uchun alohida emas).

    2026-07-26 — qismlar NAVBATMA-NAVBAT baholanadi (ataylab, parallel emas).
    Parallel variant sinab ko'rilgan va kutishni ~2-3 barobar qisqartirardi,
    lekin rad etildi: Gemini bepul tarifining DAQIQALIK so'rov limiti bor
    (sinovda `GenerateRequestsPerMinutePerProjectPerModel-FreeTier` 429
    xatosi kuzatilgan) va bir necha talaba bir vaqtda topshirsa, parallel
    rejim limitga tezroq urib, hech kimga baho bermay qolishi mumkin.

    Buning narxi: bitta so'rov ichida 2 (Writing) yoki 3 (Speaking) ta
    ketma-ket AI chaqiruvi. Shuning uchun gunicorn `--timeout` ni oshirish
    SHART — default 30 sekundda prod'da worker o'ldirilardi (Render logida
    `handle_abort -> SystemExit`), talaba esa generik "Xatolik yuz berdi"
    xabarini olardi. Kutishni qisqartirish asosan Gemma'ni olib tashlash
    bilan hal qilindi (6 chaqiruv -> 2, qarang: assessment/providers.py).

    Rasm o'qish AI chaqiruvidan OLDIN, alohida bajariladi — shunda R2'dagi
    yo'q fayl butun topshiriqni yo'qotmaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from assessment.models import SpeakingTekshiruv, WritingTekshiruv
        from assessment.providers import ProviderXatosi, provider_tanla
        from assessment.views import ai_xatosi_javobi
        from packages.models import paketdan_ishlat

        test, topilmadi = _yechilayotgan_testni_ol(request.user, pk)
        if topilmadi:
            return topilmadi
        if test.bolim not in (Bolim.WRITING, Bolim.SPEAKING):
            return Response({"detail": "Bu endpoint faqat Writing/Speaking testlar uchun"}, status=400)

        # 2026-07-30 (Speaking), 2026-08-02 (Writing ham) talabi: har
        # qism ALOHIDA topshirilishi mumkin (Mock/AI mashqlari/IELTS
        # testlari — bir xil komponent). Shuning uchun Mock'dagi umumiy
        # bandni FAQAT hamma qism alohida tekshirilib bo'lgach (frontend
        # hisoblab) yakunlash uchun alohida yo'l — qayta AI bahosi
        # olinmaydi, faqat MockYechim yangilanadi.
        yakunlovchi_bandlar = request.data.get("mock_yakunlovchi_bandlar")
        if yakunlovchi_bandlar is not None:
            if not isinstance(yakunlovchi_bandlar, list):
                return Response({"detail": "Noto'g'ri so'rov"}, status=400)
            bandlar = [b for b in yakunlovchi_bandlar if b is not None]
            umumiy_band = round(sum(bandlar) / len(bandlar) * 2) / 2 if bandlar else None
            mock_natija = _mock_yechimni_yangila(
                request.user, request.data.get("mock_yechim_id"), test.bolim, {"band": umumiy_band}
            )
            return Response({"umumiy_band": umumiy_band, "mock": mock_natija})

        javoblar = request.data.get("javoblar")
        if not isinstance(javoblar, dict):
            return Response({"detail": "javoblar {qism_id: matn} lug'ati majburiy"}, status=400)

        qismlar_hammasi = sorted(test.qismlar.all(), key=_yozgap_qism_tartibi)
        # Writing (Task1/Task2) va Speaking (Part1/2/3) — ikkisi ham
        # `javoblar`da kelgan qism(lar)i bilan cheklanadi, shunda har
        # qism ALOHIDA "Tekshirish" bilan yuborilishi mumkin (2026-08-02:
        # avval Writing majburiy IKKISINI BIRGA talab qilardi — Task 1'ni
        # alohida tekshirsa "Task 2 uchun matn kiritilmagan" xatosi
        # berardi, foydalanuvchi buni Speaking bilan bir xil qilishni
        # so'radi). 20 so'z sharti pastda Writing uchun saqlanadi.
        qismlar = [q for q in qismlar_hammasi if str(q.id) in javoblar]
        if not qismlar:
            return Response({"detail": "javoblar bo'sh"}, status=400)

        for qism in qismlar:
            matn = (javoblar.get(str(qism.id)) or "").strip()
            if not matn:
                return Response(
                    {"detail": f"\"{qism.sarlavha or qism.tur}\" uchun matn kiritilmagan"},
                    status=400,
                )
            if test.bolim == Bolim.WRITING and len(matn.split()) < 20:
                return Response(
                    {"detail": f"\"{qism.sarlavha or qism.tur}\" uchun matn juda qisqa — kamida 20 so'z"},
                    status=400,
                )

        try:
            provider = provider_tanla(request.user)
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)

        # 1-qadam (asosiy oqim): AI chaqiruvi uchun hamma narsani tayyorlaymiz
        # — rasm baytlari ham shu yerda o'qiladi, threadda emas.
        ishlar = []
        for qism in qismlar:
            matn = javoblar[str(qism.id)].strip()
            rasm_bytes, rasm_mime = None, None
            if test.bolim == Bolim.WRITING and qism.rasm:
                try:
                    # `with` — fayl deskriptori yopilishi uchun. Yopilmasa
                    # Windows'da fayl band bo'lib qoladi, R2'da esa ulanish
                    # oqadi (2026-07-26 sinovida aniqlangan).
                    with qism.rasm.open("rb") as f:
                        rasm_bytes, rasm_mime = f.read(), "image/png"
                except Exception:
                    # Rasm yo'q/o'qilmadi (masalan R2'da fayl topilmadi) —
                    # butun topshiriqni yo'qotgandan ko'ra rasmsiz baholaymiz.
                    # ESLATMA: bu holatda AI Task 1 grafigidagi ma'lumotlarga
                    # mosligini tekshira olmaydi, ya'ni ball yuqori chiqishi
                    # mumkin — shuning uchun logga ALBATTA yozamiz.
                    logger.exception(
                        "TestQismi rasmini o'qib bo'lmadi (qism id=%s) — rasmsiz baholanadi",
                        qism.id,
                    )
            ishlar.append((qism, matn, rasm_bytes, rasm_mime))

        def bahoni_ol(ish):
            qism, matn, rb, rm = ish
            if test.bolim == Bolim.WRITING:
                return provider.writing_baholash(
                    matn, savol_matni=qism.matn, tur=qism.tur, rasm_bytes=rb, rasm_mime=rm
                )
            return provider.speaking_matn_baholash(matn, savol_matni=qism.matn, tur=qism.tur)

        # 2-qadam: AI chaqiruvlari NAVBATMA-NAVBAT (daqiqalik limitni
        # urmaslik uchun — yuqoridagi izohga qarang).
        try:
            baholar = [bahoni_ol(ish) for ish in ishlar]
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=502)
        except Exception as e:
            return ai_xatosi_javobi(
                e, f"Imtihon {test.bolim} tekshiruvi (test id={test.id}, talaba id={request.user.id})"
            )

        # 3-qadam (asosiy oqim): DB yozuvlari, qismlar tartibida.
        natijalar = []
        bandlar = []
        for (qism, matn, _, _), baho in zip(ishlar, baholar):
            natija = baho["natija"]
            if test.bolim == Bolim.WRITING:
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

        bandlar = [b for b in bandlar if b is not None]
        umumiy_band = round(sum(bandlar) / len(bandlar) * 2) / 2 if bandlar else None

        xizmat = "w" if test.bolim == Bolim.WRITING else "s"
        paket = paketdan_ishlat(request.user, xizmat)

        # Speaking endi part-part topshirilishi mumkin — bu yerdagi
        # `umumiy_band` faqat SHU so'rovda kelgan part(lar)niki, butun
        # Speaking bo'liminiki emas. Shuning uchun MockYechim'ni bu yerda
        # yangilash faqat Writing uchun to'g'ri (u hamon yaxlit topshiriladi);
        # Speaking uchun yakunlash yuqoridagi `mock_yakunlovchi_bandlar`
        # yo'li orqali, frontend hamma part tekshirilgach, alohida qiladi.
        mock_natija = None
        if test.bolim == Bolim.WRITING:
            mock_natija = _mock_yechimni_yangila(
                request.user, request.data.get("mock_yechim_id"), test.bolim, {"band": umumiy_band}
            )

        return Response(
            {
                "natijalar": natijalar,
                "umumiy_band": umumiy_band,
                "paketdan": paket is not None,
                "mock": mock_natija,
            }
        )


def _mock_admin_dict(m):
    return {
        "id": m.id,
        "name": m.name,
        "korinish": m.korinish,
        "bolimlar": {b: {"id": t.id, "name": t.name} for b, t in m.bolimlar()},
        "created_at": m.created_at,
    }


def _mock_talaba_dict(m):
    return {
        "id": m.id,
        "name": m.name,
        "bolimlar": [b for b, _ in m.bolimlar()],
    }


class ImtihonMockYaratishView(APIView):
    """Admin/owner uchun — mavjud (allaqachon yuklangan) testlardan qo'lda
    mock yaratish, ZIP qayta yuklamasdan (2026-07-26). Har bo'lim ixtiyoriy —
    kamida bittasi tanlanishi kerak, lekin to'liq mock uchun 4 tasi ham
    berilishi tavsiya etiladi."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        markaz = Markaz.objects.first()
        if not markaz:
            return Response({"detail": "Markaz topilmadi"}, status=400)

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "name majburiy"}, status=400)

        bolim_testlari = {}
        for b in Bolim.values:
            tid = request.data.get(b)
            if not tid:
                continue
            test = ImtihonTest.objects.filter(pk=tid, bolim=b).first()
            if not test:
                return Response({"detail": f"'{b}' uchun test topilmadi"}, status=400)
            bolim_testlari[b] = test

        if not bolim_testlari:
            return Response({"detail": "Kamida bitta bo'lim tanlanishi kerak"}, status=400)

        mock = ImtihonMock.objects.create(
            name=name,
            markaz=markaz,
            korinish="private",
            yaratuvchi=request.user,
            manba=_manba_ol(request),
            listening=bolim_testlari.get(Bolim.LISTENING),
            reading=bolim_testlari.get(Bolim.READING),
            writing=bolim_testlari.get(Bolim.WRITING),
            speaking=bolim_testlari.get(Bolim.SPEAKING),
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=mock,
            obyekt_turi="ImtihonMock",
            snapshot={"name": mock.name, "bolimlar": list(bolim_testlari)},
        )
        return Response(_mock_admin_dict(mock), status=201)


class ImtihonMockRoyxatiView(APIView):
    """Mock imtihonlar ro'yxati — hammaga (oddiy foydalanuvchidan boshqa)
    ko'rinadi, xuddi `korinadigan_testlar` bilan bir xil qoida."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = korinadigan_moklar(
            request.user, manba=request.query_params.get("manba")
        ).order_by("-created_at")
        dict_fn = _mock_admin_dict if _mashq_admin_mi(request.user) else _mock_talaba_dict
        return Response([dict_fn(m) for m in qs])


_TOLIQ_BOLIMLAR = frozenset({Bolim.READING, Bolim.LISTENING, Bolim.WRITING, Bolim.SPEAKING})


class MockPapkalarView(APIView):
    """Talaba/admin — Mock'larni PAPKA orqali ko'rish (2026-08-11,
    foydalanuvchi talabi: "mock qismida mavjud papkalar hammasi ko'rinadi,
    talaba papkani tanlaydi, ichidan yana bitta papkani tanlasa shuni
    mock sifatida ishlaydi" — R/L/W/S bo'limlari esa O'ZGARMAYDI, ular
    hamon o'z alohida mashqini ishlaydi).

    2026-08-11 (yana kech), foydalanuvchi talabi: "Mock sifatida
    boshlash" tugmasi OLIB TASHLANDI, va Mock yozuvi endi bu sahifa
    ochilishini KUTMAYDI — u YOZISH vaqtida (`ImtihonBoshqaruvDetailView.
    patch`/`.delete` orqali `_papka_mock_moslashtir`) allaqachon
    tayyorlangan bo'ladi: "bitta papkaga 4 ta mashqning hammasi
    qo'shilgandan keyin avtomatik mock yaratilsin". Shuning uchun bu
    GET — SOF O'QISH, yon ta'siri YO'Q: faqat 4/4 to'liq VA mock'i
    ALLAQACHON tayyor bo'lgan ichki papkalarni qaytaradi (ikkinchi shart
    amalda birinchisidan kelib chiqadi — `_papka_mock_moslashtir` har
    to'liqlanganda mock yaratadi — lekin ikkalasini ham tekshirib
    ehtiyot chorasi ko'ramiz, masalan eski ma'lumot yozish yo'lidan
    o'tmasdan boshqa yo'l bilan o'zgargan bo'lsa).

    Tashqi (1-darajali) papka faqat shunday to'liq ichki papkasi
    bo'lsagina qaytariladi. Eski, papka-siz (qo'lda
    `ImtihonMockYaratishView` orqali yaratilgan) mocklar alohida
    `papkasiz_moklar` ro'yxatida — orqaga moslik uchun, ular yo'qolib
    qolmasin."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        manba = request.query_params.get("manba")
        oddiy_mi = request.user.role == "oddiy"

        papka_qs = TestPapkasi.objects.filter(parent__isnull=True)
        if manba:
            papka_qs = papka_qs.filter(manba=manba)
        if oddiy_mi:
            papka_qs = papka_qs.filter(manba=Manba.AI)

        papkalar = []
        for top in papka_qs.order_by("tartib", "nomi"):
            ichkilar = []
            for ich in top.ichki_papkalar.order_by("tartib", "nomi"):
                bolim_testlari = _papka_bolim_testlari(ich)
                if set(bolim_testlari) != _TOLIQ_BOLIMLAR:
                    continue  # 4/4 emas — ro'yxatda chiqmasin

                # `OneToOneField` teskari bog'lanishi — mock yo'q bo'lsa
                # `RelatedObjectDoesNotExist` (AttributeError avlodi)
                # ko'taradi, shuning uchun `getattr(..., None)` xavfsiz.
                mock = getattr(ich, "mock", None)
                if not mock:
                    continue  # yozish yo'lidan hali o'tmagan (kutilmagan)
                ichkilar.append({"id": ich.id, "nomi": ich.nomi, "mock_id": mock.id})
            if ichkilar:
                papkalar.append({"id": top.id, "nomi": top.nomi, "ichki": ichkilar})

        papkasiz_qs = korinadigan_moklar(request.user, manba=manba).filter(papka__isnull=True)
        papkasiz_moklar = [{"id": m.id, "name": m.name} for m in papkasiz_qs.order_by("-created_at")]

        return Response({"papkalar": papkalar, "papkasiz_moklar": papkasiz_moklar})


class ImtihonMockDetailView(APIView):
    """Bitta mock imtihon — 4 bo'lim testining asosiy ma'lumoti (qismlari
    emas, ular alohida `/api/imtihon/testlar/<id>/` orqali yuklanadi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        m = get_object_or_404(korinadigan_moklar(request.user), pk=pk)
        return Response(_mock_admin_dict(m))

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        m = get_object_or_404(ImtihonMock, pk=pk)
        nomi = m.name
        m.delete()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="ImtihonMock",
            obyekt_nomi=nomi,
        )
        return Response(status=204)


class ImtihonMockBoshlashView(APIView):
    """Talaba mock imtihonni boshlaydi — tugallanmagan urinishi bo'lsa
    o'shani davom ettiradi (qayta boshlamaydi), bo'lmasa yangi yaratadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        mock = get_object_or_404(korinadigan_moklar(request.user), pk=pk)
        if request.user.role != User.Role.STUDENT:
            return Response({"detail": "Faqat talaba uchun"}, status=403)

        yechim = (
            MockYechim.objects.filter(talaba=request.user, mock=mock, tugallandi_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not yechim:
            yechim = MockYechim.objects.create(talaba=request.user, mock=mock)

        return Response(_mock_yechim_dict(yechim))


class ImtihonMockYechimView(APIView):
    """Mock urinishining joriy holati — bosqichma-bosqich davom ettirish
    yoki yakuniy Overall Band'ni ko'rish uchun."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        yechim = get_object_or_404(MockYechim, pk=pk, talaba=request.user)
        return Response(_mock_yechim_dict(yechim))


def _mock_yechim_dict(yechim):
    return {
        "id": yechim.id,
        "mock": {
            "id": yechim.mock_id,
            "name": yechim.mock.name,
            "bolim_testlari": {b: t.id for b, t in yechim.mock.bolimlar()},
        },
        "listening_tugadimi": yechim.listening_yechim_id is not None,
        "reading_tugadimi": yechim.reading_yechim_id is not None,
        "writing_tugadimi": yechim.writing_band is not None,
        "speaking_tugadimi": yechim.speaking_band is not None,
        "listening_band": float(yechim.listening_yechim.band) if yechim.listening_yechim_id and yechim.listening_yechim.band is not None else None,
        "reading_band": float(yechim.reading_yechim.band) if yechim.reading_yechim_id and yechim.reading_yechim.band is not None else None,
        "writing_band": yechim.writing_band,
        "speaking_band": yechim.speaking_band,
        "tugadimi": yechim.tugallandi_at is not None,
        "overall_band": float(yechim.overall_band) if yechim.overall_band is not None else None,
    }
