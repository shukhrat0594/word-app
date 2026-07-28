import zipfile

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import owner_mi
from assessment.providers import ProviderXatosi
from audit.models import FaoliyatYozuvi
from audit.utils import logla
from exercises.models import javoblarni_tekshir

from .kontent_generatsiya import (
    audio_raqamini_ajrat,
    gemini_provider_olish,
    javob_kaliti_indeksla,
    javob_kaliti_sahifasini_tahlil_qil,
    kengaytma_turi,
    raqam_kaliti,
    sahifani_tahlil_qil,
    savollarga_javob_kaliti_qoll,
    tabiiy_tartib_kaliti,
)
from .models import (
    KursMashq,
    KursMashqAudio,
    KursMashqYechim,
    KursProgress,
    KursSoz,
    KursTugun,
)

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
        # 2026-07-27: "Grammar reference" (matn) va "Wordlist" (so'zlar
        # soni) — Unit'ning boshqa 2 bo'limi, mashq emas.
        if tugun.matn:
            natija["matn"] = tugun.matn
        sozlar_soni = tugun.sozlar.count()
        if sozlar_soni:
            natija["sozlar_soni"] = sozlar_soni
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


def _kurs_mashq_audiolar_royxati(m):
    """Bitta mashqqa biriktirilgan BIR NECHTA audio (2026-07-27) — yon
    panelda ro'yxat sifatida ko'rsatiladi, talaba keraklisini play qiladi."""
    return [
        {"id": a.id, "url": f"/api/kurslar/mashq-audio/{a.id}/", "raqam": a.raqam}
        for a in m.audiolar.all()
    ]


def _kurs_mashq_admin_dict(m):
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.rasm else None,
        "audio_url": f"/api/kurslar/mashq/{m.id}/audio/" if m.audio else None,
        "audiolar": _kurs_mashq_audiolar_royxati(m),
        "savollar": m.savollar,
    }


def _kurs_mashq_talaba_dict(m):
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.rasm else None,
        "audio_url": f"/api/kurslar/mashq/{m.id}/audio/" if m.audio else None,
        "audiolar": _kurs_mashq_audiolar_royxati(m),
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


class KursUnitTozalashView(APIView):
    """Admin/owner uchun — bitta Unit'ning BARCHA kontentini (Mashqlar +
    Vocabulary so'zlari + matni) BITTA harakatda o'chirish (2026-07-28,
    foydalanuvchi talabi — qayta yuklashdan oldin eskisini tozalash uchun).
    Tugunlarning O'ZI (Mashqlar/Vocabulary bo'lim tugunlari) qolади, faqat
    ichidagi kontent tozalanadi — Unit tuzilmasi buzilmaydi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        unit = get_object_or_404(KursTugun, pk=pk)
        bolalar = {b.nomi: b for b in KursTugun.objects.filter(parent=unit)}

        mashqlar_soni = 0
        sozlar_soni = 0

        mashq_tugun = bolalar.get("Mashqlar")
        if mashq_tugun:
            mashqlar_soni = mashq_tugun.mashqlar.count()
            mashq_tugun.mashqlar.all().delete()

        vocab_tugun = bolalar.get("Vocabulary")
        if vocab_tugun:
            sozlar_soni = vocab_tugun.sozlar.count()
            vocab_tugun.sozlar.all().delete()
            if vocab_tugun.matn:
                vocab_tugun.matn = ""
                vocab_tugun.save(update_fields=["matn"])

        natija = {"mashqlar_ochirildi": mashqlar_soni, "sozlar_ochirildi": sozlar_soni}
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt=unit,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{unit.nomi} (tozalandi)",
            snapshot=natija,
        )
        return Response(natija)


class KursUnitYuklashView(APIView):
    """Admin/owner uchun — bitta Unit'ning IKKALA bo'limini (Mashqlar,
    Vocabulary) BITTA so'rovda to'ldirish (2026-07-27, foydalanuvchi
    talabi — avval har bo'lim o'z alohida JSON/fayl tugmasiga ega edi,
    endi Unit uchun yagona "Yuklash" harakati).

    2026-07-27 (2): Unit endi 3 EMAS, 2 bo'lim — "Grammar reference" va
    "Wordlist" bir xil sahifada bo'lgani uchun BIRLASHTIRILDI ("Vocabulary"
    nomi bilan). `KursTugun.matn` endi Vocabulary tuguni uchun ishlatiladi
    (grammatika qisqa xulosasi, ixtiyoriy).

    So'rov tanasi — ikkisi ham ixtiyoriy, kamida bittasi kerak:
      {"mashqlar": [...], "vocabulary_matn": "matn", "wordlist": [...]}

    "mashqlar" va "wordlist" — mavjudlarga QO'SHILADI (append), "Mashq(lar)
    qo'shish" bilan bir xil mantiq. "vocabulary_matn" — mavjudini
    ALMASHTIRADI (bir butun matn, qo'shib borish ma'nosiz)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        unit = get_object_or_404(KursTugun, pk=pk)
        bolalar = {b.nomi: b for b in KursTugun.objects.filter(parent=unit)}
        kerakli = {"Mashqlar", "Vocabulary"}
        if not kerakli.issubset(bolalar):
            return Response(
                {"detail": "Bu tugunda Mashqlar/Vocabulary bo'limlari topilmadi"},
                status=400,
            )

        mashqlar = request.data.get("mashqlar")
        vocabulary_matn = request.data.get("vocabulary_matn")
        wordlist = request.data.get("wordlist")
        if not mashqlar and not vocabulary_matn and not wordlist:
            return Response(
                {"detail": "Hech narsa yuborilmadi ('mashqlar'/'vocabulary_matn'/'wordlist')"},
                status=400,
            )

        natija = {}

        if mashqlar:
            if not isinstance(mashqlar, list):
                return Response({"detail": "'mashqlar' massiv bo'lishi kerak"}, status=400)
            mashq_tugun = bolalar["Mashqlar"]
            boshlangich = mashq_tugun.mashqlar.count()
            yangi_mashqlar = []
            for i, q in enumerate(mashqlar, start=1):
                savollar = q.get("savollar") or []
                if not isinstance(savollar, list) or not savollar:
                    return Response({"detail": f"{i}-mashqda savollar bo'sh"}, status=400)
                yangi_mashqlar.append(
                    KursMashq(
                        tugun=mashq_tugun,
                        tartib=q.get("tartib") or boshlangich + i,
                        matn=q.get("matn", ""),
                        savollar=savollar,
                    )
                )
            KursMashq.objects.bulk_create(yangi_mashqlar)
            natija["mashqlar_soni"] = len(yangi_mashqlar)

        if vocabulary_matn:
            if not isinstance(vocabulary_matn, str):
                return Response({"detail": "'vocabulary_matn' matn bo'lishi kerak"}, status=400)
            vocab_tugun = bolalar["Vocabulary"]
            vocab_tugun.matn = vocabulary_matn
            vocab_tugun.save(update_fields=["matn"])
            natija["vocabulary_matn_qoshildi"] = True

        if wordlist:
            if not isinstance(wordlist, list):
                return Response({"detail": "'wordlist' massiv bo'lishi kerak"}, status=400)
            vocab_tugun = bolalar["Vocabulary"]
            boshlangich = vocab_tugun.sozlar.count()
            yangi_sozlar = []
            for i, s in enumerate(wordlist, start=1):
                if not s.get("en") or not s.get("uz"):
                    return Response({"detail": f"{i}-so'zda 'en'/'uz' to'ldirilmagan"}, status=400)
                yangi_sozlar.append(
                    KursSoz(
                        tugun=vocab_tugun,
                        tartib=boshlangich + i,
                        en=s["en"],
                        uz=s["uz"],
                        turkum=s.get("turkum", ""),
                        misol=s.get("misol", ""),
                    )
                )
            KursSoz.objects.bulk_create(yangi_sozlar)
            natija["wordlist_soni"] = len(yangi_sozlar)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=unit,
            obyekt_turi="KursTugun",
            obyekt_nomi=unit.nomi,
            snapshot=natija,
        )
        return Response(natija, status=201)


class KursZipYuklashView(APIView):
    """Admin/owner uchun — bitta Unit uchun ZIP yuklab, kontentni Gemini
    orqali AVTOMATIK generatsiya qilish (2026-07-27, foydalanuvchi talabi).

    ZIP ichida ikkita "papka" (nomi muhim emas — fayl KENGAYTMASIGA qarab
    aniqlanadi): rasm fayllari (sahifalar, nom bo'yicha "1.jpg", "2.jpg"...
    tartibda) va audio fayllar (nomi oxirida mashq/track raqami, masalan
    "..._1.01.mp3"). Har SAHIFA (rasm) alohida Gemini'ga yuboriladi —
    "sahifa = mashq" qoidasi: bitta sahifadagi barcha savollar BITTA
    `KursMashq`ga joylanadi.

    IKKI BOSQICHLI ishlaydi (2026-07-27, foydalanuvchi talabi — darslik
    oxiridagi "Answer key" sahifalari ham rasm papkasida bo'ladi):
    1) BARCHA sahifalar Gemini'ga yuboriladi, natijalar xotirada yig'iladi
       (hali bazaga yozilmaydi) — chunki javob kaliti odatda oxirgi
       sahifalarda, mashq sahifalaridan KEYIN keladi.
    2) Javob kaliti sahifalaridan (mashq_raqami, band_raqami) -> javob
       indeksi tuziladi, mashq sahifalarining savollariga QO'LLANILADI
       (Gemini taxminidan ustun), SO'NGRA bazaga yoziladi.

    Bitta sahifa xato bo'lsa, jarayon TO'XTAMAYDI — yakunda to'liq hisobot
    qaytariladi."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        unit = get_object_or_404(KursTugun, pk=pk)
        bolalar = {b.nomi: b for b in KursTugun.objects.filter(parent=unit)}
        kerakli = {"Mashqlar", "Vocabulary"}
        if not kerakli.issubset(bolalar):
            return Response(
                {"detail": "Bu tugunda Mashqlar/Vocabulary bo'limlari topilmadi"},
                status=400,
            )

        zip_fayl = request.FILES.get("zip_fayl")
        if not zip_fayl:
            return Response({"detail": "zip_fayl majburiy"}, status=400)

        try:
            arxiv = zipfile.ZipFile(zip_fayl)
        except zipfile.BadZipFile:
            return Response({"detail": "Fayl yaroqli ZIP emas"}, status=400)

        rasm_fayllari = []
        javob_kaliti_fayllari = []
        audio_fayllari = []
        for nom in arxiv.namelist():
            if nom.endswith("/"):
                continue
            asos_nom = nom.rsplit("/", 1)[-1]
            turi = kengaytma_turi(asos_nom)
            if turi == "rasm":
                # "answers" (yoki nomida "answer" bo'lgan) papkadagi rasm —
                # ANIQ javob kaliti sahifasi (2026-07-27, foydalanuvchi
                # talabi — papka nomidan ma'lum, Gemini'ga klassifikatsiya
                # qildirish shart emas, xato xavfini kamaytiradi).
                if "answer" in nom.lower():
                    javob_kaliti_fayllari.append(nom)
                else:
                    rasm_fayllari.append(nom)
            elif turi == "audio":
                audio_fayllari.append(nom)
        rasm_fayllari.sort(key=lambda n: tabiiy_tartib_kaliti(n.rsplit("/", 1)[-1]))
        javob_kaliti_fayllari.sort(key=lambda n: tabiiy_tartib_kaliti(n.rsplit("/", 1)[-1]))

        if not rasm_fayllari:
            return Response({"detail": "ZIP ichida rasm fayli topilmadi"}, status=400)

        try:
            provider = gemini_provider_olish()
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=400)

        mashq_tugun = bolalar["Mashqlar"]
        vocab_tugun = bolalar["Vocabulary"]

        # === 1-BOSQICH: barcha sahifani tahlil qilish (hali bazaga yozmasdan) ===
        xato_sahifalar = []
        sahifa_natijalari = []  # (nom, rasm_bytes, natija)
        for i, nom in enumerate(rasm_fayllari, start=1):
            rasm_bytes = arxiv.read(nom)
            _, ext = nom.rsplit(".", 1)
            rasm_mime = f"image/{'jpeg' if ext.lower() in ('jpg', 'jpeg') else ext.lower()}"

            natija, xato = sahifani_tahlil_qil(provider, rasm_bytes, rasm_mime)
            if xato:
                xato_sahifalar.append({"sahifa": i, "fayl": nom, "xato": xato})
                continue
            sahifa_natijalari.append((nom, rasm_bytes, natija))

        for i, nom in enumerate(javob_kaliti_fayllari, start=1):
            rasm_bytes = arxiv.read(nom)
            _, ext = nom.rsplit(".", 1)
            rasm_mime = f"image/{'jpeg' if ext.lower() in ('jpg', 'jpeg') else ext.lower()}"

            natija, xato = javob_kaliti_sahifasini_tahlil_qil(provider, rasm_bytes, rasm_mime)
            if xato:
                xato_sahifalar.append({"sahifa": f"javob kaliti #{i}", "fayl": nom, "xato": xato})
                continue
            sahifa_natijalari.append((nom, rasm_bytes, natija))

        # === 2-BOSQICH: javob kaliti indeksi + bazaga yozish ===
        javob_kaliti_indeksi = javob_kaliti_indeksla([n for _, _, n in sahifa_natijalari])

        mashqlar_boshlangich = mashq_tugun.mashqlar.count()
        sozlar_boshlangich = vocab_tugun.sozlar.count()

        grammar_matnlari = []
        yangi_sozlar = []
        yaratilgan_mashqlar = []  # (KursMashq, audio_raqamlar) — audio moslashtirish uchun

        for nom, rasm_bytes, natija in sahifa_natijalari:
            asos_nom = nom.rsplit("/", 1)[-1]
            if natija["turi"] == "mashq":
                savollar = savollarga_javob_kaliti_qoll(natija["savollar"], javob_kaliti_indeksi)
                mashq = KursMashq.objects.create(
                    tugun=mashq_tugun,
                    tartib=mashqlar_boshlangich + len(yaratilgan_mashqlar) + 1,
                    matn=natija.get("matn", ""),
                    savollar=savollar,
                )
                mashq.rasm.save(asos_nom, ContentFile(rasm_bytes), save=True)
                yaratilgan_mashqlar.append((mashq, natija.get("audio_raqamlar") or []))
            elif natija["turi"] == "vocabulary":
                if natija.get("grammar_matn"):
                    grammar_matnlari.append(natija["grammar_matn"])
                for s in natija.get("wordlist", []):
                    if not s.get("en") or not s.get("uz"):
                        continue
                    yangi_sozlar.append(
                        KursSoz(
                            tugun=vocab_tugun,
                            tartib=sozlar_boshlangich + len(yangi_sozlar) + 1,
                            en=s["en"],
                            uz=s["uz"],
                            turkum=s.get("turkum", ""),
                            misol=s.get("misol", ""),
                        )
                    )
            # "javob_kaliti" turi — bazaga alohida yozilmaydi, faqat yuqorida
            # savollarga qo'llanildi.

        if grammar_matnlari:
            vocab_tugun.matn = "\n\n".join(grammar_matnlari)
            vocab_tugun.save(update_fields=["matn"])
        if yangi_sozlar:
            KursSoz.objects.bulk_create(yangi_sozlar)

        # Audio fayllarni raqami bo'yicha mos mashq(lar)ga biriktirish —
        # bitta mashqda BIR NECHTA audio bo'lishi mumkin (2026-07-27,
        # foydalanuvchi talabi — "hammasi turishi kerak, keraklisini play
        # bosib ishlayveradi").
        # Kalit — NORMALLASHTIRILGAN raqam (`raqam_kaliti`), satr emas:
        # Gemini "1.1" deb qaytarishi mumkin, fayl nomi esa "1.01" (nolli)
        # bo'ladi — satr solishtirilsa mos kelmaydi (2026-07-28, haqiqiy
        # ZIP bilan sinovda 12 audiodan 9tasi shu sabab mos kelmagan edi).
        audio_indeks = {}
        for nom in audio_fayllari:
            asos_nom = nom.rsplit("/", 1)[-1]
            raqam = audio_raqamini_ajrat(asos_nom)
            kalit = raqam_kaliti(raqam)
            if kalit is not None:
                audio_indeks.setdefault(kalit, []).append(nom)

        moslangan_audio_soni = 0
        ishlatilgan_audio = set()
        for mashq, audio_raqamlar in yaratilgan_mashqlar:
            for tartib, raqam in enumerate(audio_raqamlar, start=1):
                kalit = raqam_kaliti(raqam)
                if kalit is None or kalit not in audio_indeks:
                    continue
                audio_nomi = audio_indeks[kalit][0]
                audio_bytes = arxiv.read(audio_nomi)
                asos_nom = audio_nomi.rsplit("/", 1)[-1]
                audio_yozuvi = KursMashqAudio(mashq=mashq, raqam=raqam, tartib=tartib)
                audio_yozuvi.audio.save(asos_nom, ContentFile(audio_bytes), save=True)
                ishlatilgan_audio.add(audio_nomi)
                moslangan_audio_soni += 1

        moslanmagan_audio = [
            nom.rsplit("/", 1)[-1] for nom in audio_fayllari if nom not in ishlatilgan_audio
        ]

        natija = {
            "jami_sahifa": len(rasm_fayllari) + len(javob_kaliti_fayllari),
            "muvaffaqiyatli_sahifalar": len(sahifa_natijalari),
            "xato_sahifalar": xato_sahifalar,
            "yaratilgan_mashqlar": len(yaratilgan_mashqlar),
            "wordlist_soni": len(yangi_sozlar),
            "vocabulary_matn_qoshildi": len(grammar_matnlari) > 0,
            "javob_kaliti_qollanganlar_soni": len(javob_kaliti_indeksi),
            "moslangan_audio_soni": moslangan_audio_soni,
            "moslanmagan_audio": moslanmagan_audio,
        }

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=unit,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{unit.nomi} (ZIP orqali)",
            snapshot=natija,
        )
        return Response(natija, status=201)


class KursSozlarView(APIView):
    """Bitta "Wordlist" tuguniga tegishli so'zlar ro'yxati — talaba uchun
    o'yinlarda ishlatiladi, admin uchun ro'yxatni ko'rish (2026-07-27)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        return Response(
            [
                {"id": s.id, "en": s.en, "uz": s.uz, "turkum": s.turkum, "misol": s.misol}
                for s in tugun.sozlar.all()
            ]
        )


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


class KursMashqAudioBoshqaruvView(APIView):
    """Admin/owner uchun — bitta mashqqa audio biriktirish (yakka fayl,
    ZIP orqali guruh biriktirish shart bo'lmagan holatlar uchun)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        audio = request.FILES.get("audio")
        if not audio:
            return Response({"detail": "audio majburiy"}, status=400)
        mashq.audio = audio
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


class KursMashqAudioView(APIView):
    """Mashq audiosi — autentifikatsiyalangan stream (B3.2 qoidasiga mos)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, mashq.tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        if not mashq.audio:
            raise Http404
        javob = FileResponse(mashq.audio.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class KursMashqAudioKopView(APIView):
    """Bitta mashqning KO'P audiosidan (2026-07-27) BITTASI — autentifikatsiyalangan
    stream, xuddi `KursMashqAudioView` bilan bir xil qoida (B3.2)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        audio_yozuvi = get_object_or_404(KursMashqAudio, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, audio_yozuvi.mashq.tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        javob = FileResponse(audio_yozuvi.audio.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob


class KursMashqAudioZipBoshqaruvView(APIView):
    """Admin/owner uchun — bitta tugunning mashqlariga ZIP arxiv orqali
    audio fayllarni birdaniga biriktirish (IELTS Listening ZIP yuklashdagi
    bilan bir xil moslashtirish mantig'i — `_fayllarni_taqsimla`: fayl
    nomidagi raqam mashqning "tartib"i bilan solishtiriladi, mos kelmasa
    tabiiy tartibda ketma-ket biriktiriladi). Faqat audiosi hali yo'q
    mashqlarga tegadi (2026-07-24)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response(
                {"detail": "Faqat oxirgi qatlam (farzandsiz) tugunga audio biriktiriladi"}, status=400
            )

        fayl = request.FILES.get("zip_fayl")
        if not fayl:
            return Response({"detail": "zip_fayl majburiy"}, status=400)

        import io
        import zipfile

        from exercises.views import _audio_fayllarni_ol, _fayllarni_taqsimla

        try:
            arxiv = zipfile.ZipFile(io.BytesIO(fayl.read()))
        except zipfile.BadZipFile:
            return Response({"detail": "Fayl to'g'ri ZIP arxiv emas"}, status=400)

        fayl_nomlari = [n for n in arxiv.namelist() if not n.endswith("/")]
        audio_fayllar = _audio_fayllarni_ol(arxiv, fayl_nomlari)
        if not audio_fayllar:
            return Response({"detail": "Arxivda audio fayl topilmadi"}, status=400)

        mashqlar = list(tugun.mashqlar.all())
        _fayllarni_taqsimla(mashqlar, audio_fayllar, "audio")

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
            ozgarishlar={"audio_zip": {"eski": "—", "yangi": f"{len(audio_fayllar)} fayl"}},
        )
        return Response([_kurs_mashq_admin_dict(m) for m in tugun.mashqlar.all()])


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
