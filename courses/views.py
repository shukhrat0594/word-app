import io
import json
import uuid
import zipfile

from django.core.files.base import ContentFile
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import asl_owner_mi
from accounts.models import User
from accounts.permissions import owner_mi
from assessment.providers import ProviderXatosi
from audit.models import FaoliyatYozuvi
from audit.utils import logla
from exercises.models import javoblarni_tekshir

from .excel_import import javob_qatorlarini_oqi, javoblarni_yangila
from .kontent_generatsiya import (
    AUDIO_EXTS,
    IMAGE_EXTS,
    audio_raqamini_ajrat,
    javob_kaliti_indeksla,
    javob_kaliti_sahifasini_tahlil_qil,
    kengaytma_turi,
    raqam_kaliti,
    sahifa_provider_olish,
    sahifani_tahlil_qil,
    savollarga_javob_kaliti_qoll,
    tabiiy_tartib_kaliti,
)
from .models import (
    KursMashq,
    KursMashqAudio,
    KursMashqRasmGuruhi,
    KursMashqRasmi,
    KursMashqYechim,
    KursProgress,
    KursSoz,
    KursTugun,
)
from .unit_qurish import unit_ichki_tuzilmasini_yarat

OTISH_FOIZ = 0.6

# 2026-08-15: fayl yuklashda validatsiya — avval bu uchta endpoint
# (`KursTugunFaylBoshqaruvView`, `KursMashqRasmBoshqaruvView`,
# `KursMashqAudioBoshqaruvView`) hech qanday tur/hajm tekshiruvisiz
# istalgan faylni to'g'ridan-to'g'ri R2'ga yozardi (2026-08-14 audit'da
# aniqlangan). Namuna — `accounts/views.py: FoydalanuvchiRasmView`.
RASM_MAKS_HAJM = 8 * 1024 * 1024  # 8 MB — darslik skanerlari kattaroq bo'lishi mumkin
AUDIO_MAKS_HAJM = 50 * 1024 * 1024  # 50 MB — mavjud izohda ("_audio_xeshi") ko'rsatilgan chegara
FAYL_MAKS_HAJM = 20 * 1024 * 1024  # 20 MB — Unit fayli (PDF/hujjat)
FAYL_RUXSAT_KENGAYTMALARI = {".pdf", ".doc", ".docx", ".ppt", ".pptx"} | IMAGE_EXTS | AUDIO_EXTS


def _rasm_tekshir(fayl, maks_hajm=RASM_MAKS_HAJM):
    """Hajm + mazmun tekshiruvi (kengaytmaga ishonib bo'lmaydi — ".png"
    deb nomlangan istalgan fayl yuborilishi mumkin). Xato bo'lsa xabar
    qatorini, hammasi joyida bo'lsa `None` qaytaradi."""
    if fayl.size > maks_hajm:
        return f"Rasm hajmi {maks_hajm // (1024 * 1024)} MB dan oshmasin"
    from PIL import Image, UnidentifiedImageError

    try:
        Image.open(fayl).verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return "Fayl rasm emas yoki buzuq"
    fayl.seek(0)  # `verify()` faylni oxirigacha o'qiydi
    return None


def _audio_tekshir(fayl, maks_hajm=AUDIO_MAKS_HAJM):
    """Hajm + kengaytma tekshiruvi. Audio mazmunini rasm kabi to'liq
    dekodlab tekshirish qimmatga tushadi (butun faylni o'qish kerak) —
    kengaytma + hajm yetarli himoya darajasi hisoblanadi."""
    if fayl.size > maks_hajm:
        return f"Audio hajmi {maks_hajm // (1024 * 1024)} MB dan oshmasin"
    import os

    _, ext = os.path.splitext(fayl.name.lower())
    if ext not in AUDIO_EXTS:
        return f"Ruxsat etilgan audio formatlari: {', '.join(sorted(AUDIO_EXTS))}"
    return None


def _fayl_tekshir(fayl, maks_hajm=FAYL_MAKS_HAJM):
    """Unit fayli uchun — kengaytma oq ro'yxati + hajm. Bu maydon
    umumiy (PDF/hujjat/rasm/audio bo'lishi mumkin), shuning uchun
    mazmun tekshiruvi emas, faqat xavfli fayllarni (masalan .exe/.sh)
    chiqarib tashlaydigan kengaytma cheklovi."""
    if fayl.size > maks_hajm:
        return f"Fayl hajmi {maks_hajm // (1024 * 1024)} MB dan oshmasin"
    import os

    _, ext = os.path.splitext(fayl.name.lower())
    if ext not in FAYL_RUXSAT_KENGAYTMALARI:
        return f"Ruxsat etilgan formatlar: {', '.join(sorted(FAYL_RUXSAT_KENGAYTMALARI))}"
    return None


def _kurslar_korinadimi(user):
    """Kurslar bo'limi — "oddiy foydalanuvchi"dan boshqa hamma
    (talaba/o'qituvchi/admin/owner) ko'radi (IELTS testlari bilan bir xil qoida)."""
    return user.role != User.Role.ODDIY


def _mashq_admin_mi(user):
    return owner_mi(user) or user.role == User.Role.ADMIN


def _shox_idlari(tugun):
    """Tugun va uning BUTUN avlodining id'lari (rekursiv).

    2026-07-28: Unit tuzilmasi chuqurlashdi (Unit > Student's Book /
    Workbook > Mashqlar), shuning uchun mashqlarni bitta qatlam bo'yicha
    (`tugun__parent_id=unit.id`) qidirish endi ISHLAMAYDI — mashq Unit'ning
    nevarasi. Bu e'tibordan chetda qolsa, hech bir mashq topilmay,
    `_unit_otildimi` doim False qaytarardi va BARCHA Unit'lar talabaga
    qulflangan bo'lib qolardi."""
    idlar = [tugun.id]
    joriy = [tugun.id]
    while joriy:
        joriy = list(
            KursTugun.objects.filter(parent_id__in=joriy).values_list("id", flat=True))
        idlar.extend(joriy)
    return idlar


def _unit_otildimi(user, unit_tugun, yechim_map):
    """Talaba shu Unit'ning BARCHA bo'limlaridagi mashqlaridan jami
    OTISH_FOIZ (60%) dan ko'p ball olganmi — Unit ichidagi har bir
    mashqqa javob yuborgan va o'rtacha ball yetarli bo'lishi shart.

    Unit ostidagi butun shox hisobga olinadi (Student's Book va Workbook
    ikkalasi ham) — 2026-07-28 tuzilma o'zgarishidan keyin.

    2026-08-14: `yechim_map` ({mashq_id: (ball, jami)}) chaqiruvchi
    tomonidan BITTA so'rovda oldindan tayyorlanadi — avval har mashq
    uchun alohida `KursMashqYechim` so'rovi berilardi (N+1), endi
    xotiradan o'qiladi."""
    mashqlar = list(KursMashq.objects.filter(tugun_id__in=_shox_idlari(unit_tugun)))
    if not mashqlar:
        return False
    jami_ball = 0
    jami_savol = 0
    for m in mashqlar:
        yechim = yechim_map.get(m.id)
        if not yechim:
            return False
        ball, jami = yechim
        jami_ball += ball
        jami_savol += jami
    return jami_savol > 0 and (jami_ball / jami_savol) >= OTISH_FOIZ


def _boshlanish_unitdan_oldinmi(user, unit_tugun):
    """Talaba biriktirilgan guruh(lar)dan birida shu Unit joylashgan daraja
    uchun `boshlanish_unit` belgilangan bo'lsa va bu Unit shundan OLDIN
    (yoki teng) bo'lsa — talaba uchun QULFSIZ (lekin "o'tilgan" emas,
    _unit_otildimi'ga ta'sir qilmaydi). 2026-08-02, Guruh.talabalar
    `through=GuruhAzoligi`ga o'tkazilgandan keyin qo'shilgan."""
    from academics.models import GuruhAzoligi

    azolik = (
        GuruhAzoligi.objects.filter(
            talaba=user,
            guruh__daraja_id=unit_tugun.parent_id,
            boshlanish_unit__isnull=False,
        )
        .select_related("boshlanish_unit")
        .first()
    )
    if not azolik:
        return False
    return unit_tugun.tartib <= azolik.boshlanish_unit.tartib


def _unit_qulflanganmi(user, unit_tugun, yechim_map):
    """Faqat talaba uchun: shu Unit'dan oldingi (bir xil ota-tugun ostidagi,
    tartibi kichikroq) Unit hali o'tilmagan bo'lsa — qulflangan. Guruhda
    belgilangan `boshlanish_unit`gacha (unga qo'shilgan holda) — har doim
    qulfsiz, oldingi Unit'lar o'tilganligiga qaramay.

    2026-08-16, foydalanuvchi talabi: owner "Ko'rish rejimi" orqali
    Talaba sifatida ko'rayotganda ham (`asl_owner_mi` — simulyatsiyadan
    MUSTAQIL, haqiqiy owner ekanligini bildiradi) BARCHA Unit'lar ochiq
    ko'rinsin — owner sinab ko'rish uchun, haqiqiy talaba progressiga
    bog'lanmasdan."""
    if asl_owner_mi(user):
        return False
    if user.role != User.Role.STUDENT:
        return False
    if _boshlanish_unitdan_oldinmi(user, unit_tugun):
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
    return not _unit_otildimi(user, oldingi, yechim_map)


def _eng_yaqin_unit(tugun):
    """Berilgan tugunning eng yaqin unit_darsi=True ota-tuguni (o'zi hisobga
    olinmaydi) — yo'q bo'lsa None."""
    node = tugun.parent
    while node:
        if node.unit_darsi:
            return node
        node = node.parent
    return None


def _yechim_map_ol(user):
    """Talabaning BARCHA KursMashq yechimlaridan {mashq_id: (ball, jami)}
    xaritasi — bitta so'rovda (2026-08-14, N+1 tuzatish). `KursMashqYechim`
    Meta'sida `ordering = ["-created_at"]` bo'lgani uchun har mashq
    bo'yicha BIRINCHI uchraganini saqlash — eng yangi yechim demakdir."""
    yechim_map = {}
    qs = KursMashqYechim.objects.filter(talaba=user).values_list("mashq_id", "ball", "jami")
    for mashq_id, ball, jami in qs:
        yechim_map.setdefault(mashq_id, (ball, jami))
    return yechim_map


def _talaba_tugun_qulflanganmi(user, tugun):
    """Himoya qatlami: talaba uchun shu tugun (yoki uning eng yaqin Unit
    ota-tuguni) hali qulflanganmi — fayl/mashq amallarini to'g'ridan-to'g'ri
    ID orqali chaqirishga urinishdan himoyalaydi."""
    if user.role != User.Role.STUDENT:
        return False
    unit = tugun if tugun.unit_darsi else _eng_yaqin_unit(tugun)
    if not unit:
        return False
    return _unit_qulflanganmi(user, unit, _yechim_map_ol(user))


def _mashqlar_sonini_hisobla(tugun):
    """Unit ro'yxatida ko'rsatiladigan "Mashqlar (N)" soni (2026-07-29).

    Avval bu — `KursMashq.objects.filter(tugun=tugun).count()`, ya'ni har
    SAHIFA (rasm) uchun bitta yozuv — blok formatida bitta sahifada
    bir nechta haqiqiy mashq (Exercise 2, 3, 4...) bo'lishi mumkin, lekin
    ularning HAMMASI bitta KursMashq qatoriga yig'iladi. Natijada son
    "nechta sahifa" degani edi, "nechta mashq" emas — foydalanuvchi buni
    noto'g'ri deb topdi ("rasmlar soniga qarab emas, umumiy mashqlar
    soniga qarasin").

    Endi: blok formatidagi (`bloklar` to'ldirilgan) yozuvlar uchun ichidagi
    "mashq" turidagi bloklar soni sanaladi (har biri BlokMashqi'da alohida
    Tekshirish tugmasiga ega — demak "mashq" degani shu). Eski (bloklar
    bo'sh) yozuvlar uchun avvalgidek 1 ta deb hisoblanadi (orqaga
    moslik — ular bitta yaxlit mashq edi)."""
    jami = 0
    for m in KursMashq.objects.filter(tugun=tugun).only("bloklar"):
        if m.bloklar:
            jami += sum(1 for b in m.bloklar if b.get("tur") == "mashq")
        else:
            jami += 1
    return jami


def _tugun_dict(tugun, user, bolalar_keshi, tugatgan_idlar, sozlar_soni_map, yechim_map, qulflangan=False):
    bolalar = bolalar_keshi.get(tugun.id, [])
    oxirgi_qatlammi = len(bolalar) == 0
    natija = {
        "id": tugun.id,
        "nomi": tugun.nomi,
        # 2026-07-28: frontend nomni SHU KALIT bo'yicha tarjima qiladi
        # (i18n), `nomi` esa kaliti yo'q tugunlar uchun zaxira.
        "kalit": tugun.kalit,
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
        mashqlar_soni = _mashqlar_sonini_hisobla(tugun)
        if mashqlar_soni:
            natija["mashqlar_soni"] = mashqlar_soni
        # 2026-07-27: "Grammar reference" (matn) va "Wordlist" (so'zlar
        # soni) — Unit'ning boshqa 2 bo'limi, mashq emas.
        if tugun.matn:
            natija["matn"] = tugun.matn
        sozlar_soni = sozlar_soni_map.get(tugun.id, 0)
        if sozlar_soni:
            natija["sozlar_soni"] = sozlar_soni
        if user.role == User.Role.STUDENT:
            natija["tugallandimi"] = tugun.id in tugatgan_idlar
    else:
        children = []
        for b in bolalar:
            b_qulflangan = _unit_qulflanganmi(user, b, yechim_map) if b.unit_darsi else False
            children.append(
                _tugun_dict(b, user, bolalar_keshi, tugatgan_idlar, sozlar_soni_map, yechim_map, b_qulflangan)
            )
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
        yechim_map = {}
        if request.user.role == User.Role.STUDENT:
            tugatgan_idlar = set(
                KursProgress.objects.filter(talaba=request.user).values_list("tugun_id", flat=True)
            )
            # 2026-08-14: avval har mashq uchun `_unit_otildimi` ichida
            # alohida so'rov berilardi (N+1) — endi bitta so'rovda.
            yechim_map = _yechim_map_ol(request.user)

        # 2026-08-14: "Wordlist" so'zlar soni — avval har oxirgi qatlam
        # tuguni uchun alohida `.count()` so'rovi berilardi (N+1), endi
        # bitta guruhlangan so'rovda.
        sozlar_soni_map = dict(
            KursSoz.objects.values("tugun_id").annotate(soni=Count("id")).values_list("tugun_id", "soni")
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
                    _tugun_dict(b, request.user, bolalar_keshi, tugatgan_idlar, sozlar_soni_map, yechim_map)
                    for b in bolalar
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
        xato = _fayl_tekshir(fayl)
        if xato:
            return Response({"detail": xato}, status=400)

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


def _unit_bolimlari(tugun):
    """Kontent yuklanadigan bo'limlarni (`mashqlar`, `vocabulary`) KALIT
    bo'yicha qaytaradi — nomi bo'yicha emas (2026-07-28: nomlar 3 tilda
    ko'rsatiladi, shuning uchun ular kalit bo'la olmaydi).

    2026-07-28 tuzilma o'zgarishi: bo'limlar endi Unit ostida EMAS,
    kitob (Student's Book / Workbook) ostida turadi. Shuning uchun bu
    endpointlar KITOB tugunini kutadi.

    Unit tuguni berilsa — Student's Book'ga tushamiz. Sabab: eski kontent
    aynan o'sha yerga ko'chirilgan va brauzerda keshlangan eski JS hali
    Unit id bilan so'rov yuborishi mumkin — bunday so'rov xato bermay,
    to'g'ri joyga tushsin."""
    bolalar = list(KursTugun.objects.filter(parent=tugun))
    bolimlar = {b.kalit: b for b in bolalar if b.kalit in ("mashqlar", "vocabulary")}
    if bolimlar:
        return bolimlar
    kitob = next((b for b in bolalar if b.kalit == "students_book"), None)
    if kitob:
        return {b.kalit: b for b in KursTugun.objects.filter(parent=kitob)
                if b.kalit in ("mashqlar", "vocabulary")}
    return {}


def _unit_boshmi(unit):
    """Unit BUTUNLAY bo'shmi (o'chirish xavfsizmi).

    `_unit_bolimlari` faqat BITTA kitobni tekshiradi (u Unit berilsa
    Student's Book'ga tushadi) — bu yerda esa Unit'ning IKKALA kitobi
    (Student's Book VA Workbook) ko'riladi, aks holda Workbook'dagi
    kontent payqalmay o'chirilib ketishi mumkin edi."""
    for kitob in KursTugun.objects.filter(parent=unit):
        bolalar = _unit_bolimlari(kitob)
        mashq_tugun = bolalar.get("mashqlar")
        vocab_tugun = bolalar.get("vocabulary")
        if mashq_tugun and mashq_tugun.mashqlar.exists():
            return False
        if vocab_tugun and (vocab_tugun.sozlar.exists() or vocab_tugun.matn):
            return False
    return True


def _kurs_mashq_audiolar_royxati(m):
    """Bitta mashqqa biriktirilgan BIR NECHTA audio (2026-07-27) — yon
    panelda ro'yxat sifatida ko'rsatiladi, talaba keraklisini play qiladi."""
    return [
        {"id": a.id, "url": f"/api/kurslar/mashq-audio/{a.id}/", "raqam": a.raqam}
        for a in m.audiolar.all()
    ]


def _kurs_blok_rasmlari(m):
    """Blok formatidagi sahifadan kesilgan suratlar (2026-07-28) —
    blok JSON ichida faqat `rasm_idx` turadi, manzil shu ro'yxatdan
    olinadi."""
    return [
        {"idx": r.tartib, "url": f"/api/kurslar/blok-rasm/{r.id}/", "izoh": r.izoh}
        for r in m.rasmlar.all()
    ]


# 2026-08-10: bu yerda "unit_raqami" (Unit tartibi × ketma-ketlik, masalan
# "1.4") hisoblanardi — OLIB TASHLANDI. Sabab: u kitobdagi AUDIO TREK
# raqamiga (1.1, 1.2 — dinamik belgisi yonida bosilgan) o'xshab ketib,
# chalkashtirardi. Mashqning kitobda BOSILGAN raqami (`blok.raqam`) va
# audio trek raqami (`blok.audio_raqam`) allaqachon AI tomonidan o'qib
# olinadi va o'z joyida ko'rsatiladi — qo'shimcha hisoblangan raqam
# kerak emas.


def _kurs_mashq_admin_dict(m):
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.effektiv_rasm else None,
        "rasm_guruhi_id": m.rasm_guruhi_id,
        "rasm_guruhi_tomoni": m.rasm_guruhi.tomon if m.rasm_guruhi_id else None,
        "audio_url": f"/api/kurslar/mashq/{m.id}/audio/" if m.audio else None,
        "audiolar": _kurs_mashq_audiolar_royxati(m),
        "savollar": m.savollar,
        "bloklar": m.bloklar,
        "blok_rasmlari": _kurs_blok_rasmlari(m),
        # 2026-08-07: admin ro'yxatidagi "Audio yuklash" tugmasi shu
        # bo'yicha ham chiqadi. Blok rejimida tugma `bloklar[].audio_raqam`
        # bo'yicha chiqardi, rasm-fon rejimida esa `bloklar` BO'SH —
        # tugma umuman ko'rinmay qolardi, holbuki AI sahifada audio
        # belgisini ko'rgan bo'lsa admin faylni biriktirishi kerak.
        "audio_kerak": m.audio_kerak,
    }


def _kurs_mashq_talaba_dict(m):
    """MUHIM: `togri` maydoni talabaga YUBORILMAYDI.

    Blok formatida ham xavfsiz: bo'sh joylar bloklarda faqat `savol_idx`
    bilan turadi (javob emas), javoblarning o'zi `savollar` ichida va u
    shu yerda tozalanadi. Ya'ni talaba F12 bosib javobni ko'ra olmaydi."""
    return {
        "id": m.id,
        "tartib": m.tartib,
        "matn": m.matn,
        "rasm_url": f"/api/kurslar/mashq/{m.id}/rasm/" if m.effektiv_rasm else None,
        "rasm_guruhi_id": m.rasm_guruhi_id,
        "rasm_guruhi_tomoni": m.rasm_guruhi.tomon if m.rasm_guruhi_id else None,
        "audio_url": f"/api/kurslar/mashq/{m.id}/audio/" if m.audio else None,
        "audiolar": _kurs_mashq_audiolar_royxati(m),
        "savollar": [{k: v for k, v in s.items() if k != "togri"} for s in m.savollar],
        "bloklar": m.bloklar,
        "blok_rasmlari": _kurs_blok_rasmlari(m),
    }


def _kurs_mashq_oqituvchi_dict(m):
    """O'qituvchi uchun — talaba ko'rinishining AYNAN o'zi, lekin to'g'ri
    javoblar OCHIQ (2026-08-18, foydalanuvchi talabi: o'qituvchi kurslardagi
    mashqlarni o'quvchi kabi ko'rsin, mashq qo'shish/tahrirlash esa kerak
    emas). Boshqaruv maydonlari (`audio_kerak` va h.k.) bu yerda YO'Q —
    o'qituvchi kontentni o'zgartira olmaydi, faqat ko'radi."""
    d = _kurs_mashq_talaba_dict(m)
    d["savollar"] = m.savollar
    return d


class KursMashqBoshqaruvView(APIView):
    """Admin/owner uchun — bitta tugunning mashqlari ro'yxati va yangi
    mashq(lar) qo'shish (JSON, bir nechtasi birga — "mashqlar" ro'yxati)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        return Response(
            [_kurs_mashq_admin_dict(m) for m in tugun.mashqlar.prefetch_related("audiolar", "rasmlar")]
        )

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


def _tugun_eksport_qil(tugun, zf, fayllar_indeksi):
    """`tugun` va uning BUTUN farzandlar daraxtini rekursiv JSON'ga
    o'giradi. Har bir haqiqiy fayl (rasm/audio) ZIP ichiga `files/<uuid>`
    nomi bilan qo'shiladi, JSON esa faqat shu nomga ishora qiladi —
    fayllar bir necha joyda ishlatilsa ham (masalan ulashilgan rasm
    guruhi) ikki marta yozilmaydi (`fayllar_indeksi` shu uchun keshlaydi)."""

    def fayl_qosh(fayl_maydoni):
        if not fayl_maydoni:
            return None
        nomi = fayl_maydoni.name
        if nomi not in fayllar_indeksi:
            kalit = f"files/{uuid.uuid4().hex}_{nomi.rsplit('/', 1)[-1]}"
            with fayl_maydoni.open("rb") as fh:
                zf.writestr(kalit, fh.read())
            fayllar_indeksi[nomi] = kalit
        return fayllar_indeksi[nomi]

    natija = {
        "kalit": tugun.kalit,
        "nomi": tugun.nomi,
        "ikonka": tugun.ikonka,
        "tartib": tugun.tartib,
        "tez_kunda": tugun.tez_kunda,
        "unit_darsi": tugun.unit_darsi,
        "matn": tugun.matn,
        "fayl": fayl_qosh(tugun.fayl) if tugun.fayl else None,
        "children": [
            _tugun_eksport_qil(bola, zf, fayllar_indeksi)
            for bola in tugun.children.order_by("tartib", "id")
        ],
        "mashqlar": [
            {
                "tartib": m.tartib,
                "matn": m.matn,
                "savollar": m.savollar,
                "bloklar": m.bloklar,
                "rasm": fayl_qosh(m.rasm) if m.rasm else None,
                "audio": fayl_qosh(m.audio) if m.audio else None,
                "rasmlar": [
                    {"tartib": r.tartib, "izoh": r.izoh, "rasm": fayl_qosh(r.rasm)}
                    for r in m.rasmlar.all()
                ],
                "audiolar": [
                    {"tartib": a.tartib, "raqam": a.raqam, "audio": fayl_qosh(a.audio)}
                    for a in m.audiolar.all()
                ],
            }
            for m in tugun.mashqlar.order_by("tartib", "id")
        ],
        "sozlar": [
            {"tartib": s.tartib, "en": s.en, "uz": s.uz, "turkum": s.turkum, "misol": s.misol}
            for s in tugun.sozlar.order_by("tartib", "id")
        ],
    }
    return natija


class KursEksportView(APIView):
    """Owner/admin uchun — bitta tugun (masalan bitta Unit) va uning
    BUTUN ichidagi daraxtini (kichik tugunlar, mashqlar, so'zlar,
    rasm/audio fayllari bilan birga) BITTA ZIP faylga yig'ib beradi
    (2026-08-16, foydalanuvchi talabi: "backup qilgandek yuklab olib,
    boshqa bazaga yuklash"). Bu faylni `KursImportView` orqali istalgan
    boshqa muhitga (masalan prod<->local) aynan bir xil holda ko'chirish
    mumkin — versiyalar farqidan mustaqil, chunki BAZA HOLATINING O'ZI
    ko'chiriladi, kod emas."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)

        bufer = io.BytesIO()
        fayllar_indeksi = {}
        with zipfile.ZipFile(bufer, "w", zipfile.ZIP_DEFLATED) as zf:
            daraxt = _tugun_eksport_qil(tugun, zf, fayllar_indeksi)
            zf.writestr("data.json", json.dumps(daraxt, ensure_ascii=False, indent=1))
        bufer.seek(0)

        # 2026-08-19, foydalanuvchi talabi: "Saqlash" bosilganda barcha
        # Unitlar bir xil nom bilan (masalan "kurslar_students_book_
        # eksport.zip") saqlanardi -- chunki Saqlash endi Unit darajasida
        # ham, Student's Book/Workbook darajasida ham ishlaydi, va
        # "students_book"/"workbook" kaliti barcha Unitlarda BIR XIL.
        # Endi fayl nomi tugundan ILDIZGACHA bo'lgan BUTUN yo'lni o'z
        # ichiga oladi (masalan "beginner_unit_3-students_book"), shuning
        # uchun qaysi Unit ekani fayl nomining o'zidan ko'rinadi.
        # "kurslar-ingliz_tili-beginner-" kabi umumiy old qismni cho'zib
        # o'tirmaslik uchun — eng yaqin Unit tugunidan (unit_darsi=True)
        # boshlab yo'l quramiz, topilmasa (masalan IELTS bo'limlarida
        # unit_darsi belgisi yo'q) BUTUN yo'lga qaytamiz.
        zanjir = []
        node = tugun
        while node:
            zanjir.append(node)
            node = node.parent
        zanjir.reverse()
        boshlanish = next((i for i, n in enumerate(zanjir) if n.unit_darsi), 0)
        yol_qismlari = [n.kalit for n in zanjir[boshlanish:] if n.kalit]
        yol = "-".join(yol_qismlari) or str(tugun.id)
        fayl_nomi = f"kurslar_{yol}_eksport.zip"
        javob = HttpResponse(bufer.read(), content_type="application/zip")
        javob["Content-Disposition"] = f'attachment; filename="{fayl_nomi}"'
        return javob


def _tugun_import_qil(daraxt, ota, markaz, zf):
    """`_tugun_eksport_qil`ning teskarisi — JSON tugun tavsifidan haqiqiy
    `KursTugun` (+ mashq/so'z/fayl) yaratadi. `kalit+ota` bo'yicha MAVJUD
    tugun topilsa o'shanga YOZILADI (import ikki marta bajarilsa
    dublikat yaratilmaydi) — boshqa joylardagi idempotent naqsh bilan
    bir xil (`kurslar_urugla.py`)."""

    def fayl_ol(kalit):
        if not kalit:
            return None
        nomi = kalit.rsplit("/", 1)[-1]
        return nomi, ContentFile(zf.read(kalit))

    tugun = KursTugun.objects.filter(
        kalit=daraxt["kalit"], parent=ota, markaz=markaz
    ).first() if daraxt["kalit"] else None
    if not tugun:
        tugun = KursTugun(parent=ota, markaz=markaz, kalit=daraxt["kalit"])
    tugun.nomi = daraxt["nomi"]
    tugun.ikonka = daraxt["ikonka"]
    tugun.tartib = daraxt["tartib"]
    tugun.tez_kunda = daraxt["tez_kunda"]
    tugun.unit_darsi = daraxt["unit_darsi"]
    tugun.matn = daraxt["matn"]
    if daraxt["fayl"]:
        nomi, tarkib = fayl_ol(daraxt["fayl"])
        tugun.fayl.save(nomi, tarkib, save=False)
    tugun.save()

    # 2026-08-18, HAQIQIY XATO: tugun o'zi kalit+ota bo'yicha idempotent
    # topilar edi, lekin ICHIDAGI mashq/so'z yozuvlari HECH QACHON
    # o'chirilmasdi — shu sababli BIR XIL ZIP ikki marta import qilinsa
    # yoki maqsad tugunda avvaldan (masalan eski/tugallanmagan) kontent
    # bo'lsa, eski va yangi yozuvlar ARALASHIB dublikat hosil qilardi
    # (savollar soni ikki barobar, rasm-mashq mos kelmay qolardi).
    # Import "zaxiradan tiklash" degani — shu tugunning eski
    # mashq/so'zlarini tozalab, ZIPdagi holatga TO'LIQ almashtiramiz.
    tugun.mashqlar.all().delete()
    tugun.sozlar.all().delete()

    for m in daraxt["mashqlar"]:
        mashq = KursMashq(
            tugun=tugun, tartib=m["tartib"], matn=m["matn"],
            savollar=m["savollar"], bloklar=m["bloklar"],
        )
        if m["rasm"]:
            nomi, tarkib = fayl_ol(m["rasm"])
            mashq.rasm.save(nomi, tarkib, save=False)
        if m["audio"]:
            nomi, tarkib = fayl_ol(m["audio"])
            mashq.audio.save(nomi, tarkib, save=False)
        mashq.save()
        for r in m["rasmlar"]:
            rasm = KursMashqRasmi(mashq=mashq, tartib=r["tartib"], izoh=r["izoh"])
            nomi, tarkib = fayl_ol(r["rasm"])
            rasm.rasm.save(nomi, tarkib, save=False)
            rasm.save()
        for a in m["audiolar"]:
            audio = KursMashqAudio(mashq=mashq, tartib=a["tartib"], raqam=a["raqam"])
            nomi, tarkib = fayl_ol(a["audio"])
            audio.audio.save(nomi, tarkib, save=False)
            audio.save()

    KursSoz.objects.bulk_create([
        KursSoz(
            tugun=tugun, tartib=s["tartib"], en=s["en"], uz=s["uz"],
            turkum=s["turkum"], misol=s["misol"],
        )
        for s in daraxt["sozlar"]
    ])

    for bola in daraxt["children"]:
        _tugun_import_qil(bola, tugun, markaz, zf)

    return tugun


class KursImportView(APIView):
    """Owner/admin uchun — `KursEksportView` yaratgan ZIP faylni
    ko'rsatilgan ota-tugun ICHIGA import qiladi. Idempotent: bir xil
    kalitli tugun/mashqlar mavjud bo'lsa ustiga yozadi (dublikat
    yaratmaydi) — shuning uchun xavfsiz qayta-qayta ishga tushiriladi."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        ota = get_object_or_404(KursTugun, pk=pk)
        fayl = request.FILES.get("fayl")
        if not fayl:
            return Response({"detail": "fayl majburiy"}, status=400)

        try:
            with zipfile.ZipFile(fayl) as zf:
                daraxt = json.loads(zf.read("data.json").decode("utf-8"))
                # 2026-08-17, HAQIQIY XATO: admin odatda Import tugmasini
                # AYNAN O'SHA Unit'ning o'zida bosadi ("shu Unit'ni
                # yangilash" niyatida) — lekin ZIP'ning tepa tuguni ham
                # O'SHA Unit (bir xil kalit). Agar shu holatda `ota`ni
                # o'zgartirmasdan import qilsak, dastur "ota ichida shu
                # kalitli BOLA"ni qidiradi, topmaydi (chunki bu kalit
                # ota'NING O'ZIDA, farzandida emas) va uni ICHIGA
                # DUBLIKAT qilib yaratadi. Shuning uchun: agar ZIP tepa
                # tuguni aynan `ota`ning o'zi bilan bir xil kalitga ega
                # bo'lsa — qidiruv `ota.parent` ichida (ya'ni ota bilan
                # BIR DARAJADA, uning o'rniga) olib boriladi.
                qidiruv_ota = ota
                if ota.kalit and daraxt.get("kalit") == ota.kalit and ota.parent_id:
                    qidiruv_ota = ota.parent
                yangi_tugun = _tugun_import_qil(daraxt, qidiruv_ota, ota.markaz, zf)
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
            return Response({"detail": f"ZIP fayl noto'g'ri: {exc}"}, status=400)

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=yangi_tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"Import: {yangi_tugun.nomi}",
            snapshot={"ota": ota.nomi},
        )
        return Response({"id": yangi_tugun.id, "nomi": yangi_tugun.nomi}, status=201)


class KursUnitTozalashView(APIView):
    """Admin/owner uchun — bitta Unit'ning BARCHA kontentini (Mashqlar +
    Vocabulary so'zlari + matni) BITTA harakatda o'chirish (2026-07-28,
    foydalanuvchi talabi — qayta yuklashdan oldin eskisini tozalash uchun).
    Tugunlarning O'ZI (Mashqlar/Vocabulary bo'lim tugunlari) qolади, faqat
    ichidagi kontent tozalanadi — Unit tuzilmasi buzilmaydi.

    2026-07-30: ATAYLAB tugallanmagan blok-ZIP jarayoniga TEGMAYDI — bu
    ikkita MUSTAQIL amal (foydalanuvchi aniq ajratdi): "Tozalash" faqat
    mashq/so'z kontentini o'chiradi, tiqilib qolgan jarayonni bekor
    qilish uchun alohida "Bekor qilish" tugmasi bor (Davom ettirish
    yonida, `KursBlokJarayonHolatiView.delete`)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        unit = get_object_or_404(KursTugun, pk=pk)
        bolalar = _unit_bolimlari(unit)

        mashqlar_soni = 0
        sozlar_soni = 0

        mashq_tugun = bolalar.get("mashqlar")
        if mashq_tugun:
            mashqlar_soni = mashq_tugun.mashqlar.count()
            mashq_tugun.mashqlar.all().delete()

        vocab_tugun = bolalar.get("vocabulary")
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


# 2026-07-29: "Elementary...Upper-Intermediate uchun Unit sonini admin
# belgilashi" talabi. Beginner ham 2026-07-29(2)da shu ro'yxatga
# qo'shildi — qattiq kodlangan 14 ta Headway Unit'i bekor qilindi,
# Beginner ham boshqa darajalar bilan BIR XIL admin-mexanizmga o'tdi
# (IELTS/CEFR bundan mustasno — ular butunlay boshqa tuzilma).
UNIT_YARATISH_MUMKIN_DARAJALAR = {
    "beginner", "elementary", "pre_intermediate", "intermediate", "upper_intermediate",
}


class KursDarajaUnitYaratishView(APIView):
    """Admin/owner uchun — Ingliz tili darajasida (Beginner yoki
    Elementary...Upper-Intermediate) Unit'lar (har biri Student's
    Book/Workbook > Mashqlar/Vocabulary tuzilmasi bilan, generic "Unit N"
    nomi bilan) yaratadi.

    Bu daraja hozircha FLAT (Grammar/Vocabulary/Reading/... to'g'ridan-to'g'ri
    daraja ostida, kontentsiz) — birinchi marta Unit yaratilganda bu bo'sh
    flat bo'limlar O'CHIRILADI (ular hali hech qanday kontentga ega emas,
    o'chirish xavfsiz).

    2026-07-30 talabi: dastlab bu FAQAT bir martalik edi (qayta chaqirilsa
    xato), lekin admin keyinroq ko'proq Unit qo'shishi kerak bo'lib qoldi —
    endi Unit ALLAQACHON bo'lsa ham ishlaydi, YANGI Unitlarni MAVJUDLARNING
    OXIRIGA (eng katta `tartib`dan keyin) qo'shadi.

    `delete()` — faqat ENG OXIRGI Unitni, va FAQAT u BO'SH (mashq/so'z
    yo'q) bo'lsa o'chiradi (2026-07-30 talabi) — o'rtadagi yoki
    to'ldirilgan Unitni o'chirish qo'llab-quvvatlanmaydi, tasodifan
    kontentli Unitni yo'qotib qo'yishning oldini olish uchun."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        daraja = get_object_or_404(KursTugun, pk=pk)
        if daraja.kalit not in UNIT_YARATISH_MUMKIN_DARAJALAR:
            return Response(
                {"detail": "Bu tugun uchun Unit yaratib bo'lmaydi"}, status=400
            )

        try:
            unit_soni = int(request.data.get("unit_soni"))
        except (TypeError, ValueError):
            return Response({"detail": "unit_soni butun son bo'lishi kerak"}, status=400)
        if not 1 <= unit_soni <= 50:
            return Response({"detail": "unit_soni 1 dan 50 gacha bo'lishi kerak"}, status=400)

        mavjud_unitlar = KursTugun.objects.filter(parent=daraja, unit_darsi=True)
        boshlangich = mavjud_unitlar.count()
        if boshlangich == 0:
            # Eski (hali bo'sh) flat bo'limlarni tozalaymiz — Unit
            # tuzilmasiga o'tishda ular endi kerak emas. Unit allaqachon
            # bor bo'lsa bu qadam KERAK EMAS (flat bo'limlar bir marta
            # o'chirilgach qayta paydo bo'lmaydi).
            KursTugun.objects.filter(parent=daraja, unit_darsi=False).delete()

        for j in range(boshlangich + 1, boshlangich + unit_soni + 1):
            # `kalit` GLOBAL unikal emas (faqat bir ota-tugun ichida), lekin
            # frontend nomlarni KALIT bo'yicha (parentga qaramay) tarjima
            # qiladi (i18n.jsx, `tugun_<kalit>`) — shuning uchun oddiy
            # "unit_N" ishlatilsa, Beginner'ning "unit_1"="Unit 1 — Hello!"
            # kabi haqiqiy sarlavhalari bilan TO'QNASHIB, noto'g'ri nom
            # ko'rsatilardi (2026-07-29, sinovda aniqlandi). Daraja kaliti
            # bilan prefikslash bu to'qnashuvni oldini oladi.
            unit = KursTugun.objects.create(
                kalit=f"{daraja.kalit}_unit_{j}", nomi=f"Unit {j}", parent=daraja,
                markaz=daraja.markaz, tartib=j, unit_darsi=True,
            )
            unit_ichki_tuzilmasini_yarat(unit)

        natija = {"yaratilgan_unit_soni": unit_soni}
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=daraja,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{daraja.nomi} ({unit_soni} ta Unit)",
            snapshot=natija,
        )
        return Response(natija, status=201)

    def delete(self, request, pk):
        """Oxiridan `soni` ta Unitni o'chiradi (2026-08-10 talabi: "unit
        qo'shish maydonida nechi bo'lsa, oxiridan shuncha o'chirsin").
        `soni` berilmasa — 1 ta (eski xatti-harakat).

        HAMMASI-YOKI-HECH NARSA: avval o'chiriladigan BARCHA Unit bo'sh
        ekani tekshiriladi, biror-birida kontent bo'lsa HECH NARSA
        o'chirilmaydi. Aks holda admin "3 ta o'chir" deganda 1 tasi
        o'chib, qolgani qolib ketardi — bu chalkash va xavfli."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        daraja = get_object_or_404(KursTugun, pk=pk)

        try:
            soni = int(request.query_params.get("soni", 1))
        except (TypeError, ValueError):
            return Response({"detail": "'soni' butun son bo'lishi kerak"}, status=400)
        if not 1 <= soni <= 50:
            return Response({"detail": "'soni' 1 dan 50 gacha bo'lishi kerak"}, status=400)

        unitlar = list(
            KursTugun.objects.filter(parent=daraja, unit_darsi=True).order_by("-tartib")[:soni]
        )
        if not unitlar:
            return Response({"detail": "Bu darajada Unit yo'q"}, status=400)
        if len(unitlar) < soni:
            return Response(
                {"detail": f"Bu darajada atigi {len(unitlar)} ta Unit bor"}, status=400
            )

        band = [u.nomi for u in unitlar if not _unit_boshmi(u)]
        if band:
            return Response(
                {
                    "detail": (
                        f"Bo'sh emas (mashq/so'z bor): {', '.join(reversed(band))} — "
                        'avval "Tozalash" bilan bo\'shating'
                    )
                },
                status=400,
            )

        nomlar = [u.nomi for u in reversed(unitlar)]
        for u in unitlar:
            u.delete()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt=daraja,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{daraja.nomi} — {', '.join(nomlar)} o'chirildi",
            snapshot={"ochirilgan_unit_soni": len(nomlar)},
        )
        return Response({"ochirildi": nomlar, "soni": len(nomlar)})


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
        bolalar = _unit_bolimlari(unit)
        kerakli = {"mashqlar", "vocabulary"}
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
            mashq_tugun = bolalar["mashqlar"]
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
            vocab_tugun = bolalar["vocabulary"]
            vocab_tugun.matn = vocabulary_matn
            vocab_tugun.save(update_fields=["matn"])
            natija["vocabulary_matn_qoshildi"] = True

        if wordlist:
            if not isinstance(wordlist, list):
                return Response({"detail": "'wordlist' massiv bo'lishi kerak"}, status=400)
            vocab_tugun = bolalar["vocabulary"]
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
        bolalar = _unit_bolimlari(unit)
        kerakli = {"mashqlar", "vocabulary"}
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
            provider = sahifa_provider_olish()
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=400)

        mashq_tugun = bolalar["mashqlar"]
        vocab_tugun = bolalar["vocabulary"]

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


def _pozitsiyani_tozala(xom):
    """Foydalanuvchidan kelgan `pozitsiya`ni tekshirib, faqat kutilgan
    maydonlarni qaytaradi (yaroqsiz bo'lsa None — savol oddiy ro'yxat
    ko'rinishida chiqadi, bu xavfsiz zaxira)."""
    if not isinstance(xom, dict):
        return None
    try:
        x, y = float(xom["x"]), float(xom["y"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0 <= x <= 100 and 0 <= y <= 100):
        return None
    natija = {"x": round(x, 1), "y": round(y, 1)}
    try:
        kenglik = float(xom.get("kenglik"))
    except (TypeError, ValueError):
        return natija
    if 0 < kenglik <= 100:
        natija["kenglik"] = round(kenglik, 1)
    return natija


class KursMashqDetailBoshqaruvView(APIView):
    """Admin/owner uchun — bitta mashqni o'chirish yoki (2026-07-29)
    savollarining to'g'ri javoblarini QO'LDA tahrirlash."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        mashq.delete()
        return Response(status=204)

    def _savollarni_almashtir(self, mashq, xom):
        """RASM-FON rejimi uchun (2026-08-08): admin bo'sh joylarning
        JOYLASHUVINI ham tahrirlaydi, shuning uchun butun `savollar`
        ro'yxati qayta yuboriladi (qo'shish/o'chirish ham shu orqali).

        DIQQAT: savollar soni o'zgarsa, shu mashq bo'yicha ALLAQACHON
        topshirilgan natijalardagi javob indekslari mos kelmay qoladi.
        Tahrirlash mashq talabalarga berilishidan OLDIN qilinishi
        ko'zda tutilgan (rasm-fonda tasdiqlash bosqichi yo'q — shu
        UI uning o'rnini bosadi)."""
        if not isinstance(xom, list):
            return Response({"detail": "'savollar' ro'yxat bo'lishi kerak"}, status=400)
        if len(xom) > 200:
            return Response({"detail": "Savollar soni juda ko'p"}, status=400)

        savollar = []
        for s in xom:
            if not isinstance(s, dict):
                return Response({"detail": "Har bir savol obyekt bo'lishi kerak"}, status=400)
            yangi = {
                "savol": str(s.get("savol") or "").strip()[:500] or "___",
                "togri": str(s.get("togri") or "").strip()[:200],
            }
            if s.get("erkin"):
                yangi["erkin"] = True
            pozitsiya = _pozitsiyani_tozala(s.get("pozitsiya"))
            if pozitsiya:
                yangi["pozitsiya"] = pozitsiya
            savollar.append(yangi)

        mashq.savollar = savollar
        mashq.save(update_fields=["savollar"])
        return Response({"yangilandi": len(savollar), "xatolar": [],
                         "mashq": _kurs_mashq_admin_dict(mashq)})

    def patch(self, request, pk):
        """So'rov tanasi: {"javoblar": [{"raqam": 1, "togri": "..."}, ...]}
        — "raqam" shu mashq ICHIDAGI savol tartib raqami (1 dan boshlab,
        `savollar` ro'yxatidagi pozitsiyaga mos).

        Yoki {"savollar": [...]} — butun ro'yxatni almashtirish
        (`_savollarni_almashtir`ga qarang)."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        if "savollar" in request.data:
            return self._savollarni_almashtir(mashq, request.data["savollar"])
        yangilash = request.data.get("javoblar")
        if not isinstance(yangilash, list) or not yangilash:
            return Response({"detail": "'javoblar' ro'yxati majburiy"}, status=400)

        savollar = mashq.savollar
        xatolar = []
        yangilandi = 0
        for y in yangilash:
            raqam = y.get("raqam")
            if not isinstance(raqam, int) or not 1 <= raqam <= len(savollar):
                xatolar.append({"raqam": raqam, "xato": "savol raqami noto'g'ri"})
                continue
            savollar[raqam - 1]["togri"] = y.get("togri")
            # 2026-08-10: "erkin" — to'g'ri javob YO'Q, talaba nima yozsa
            # ham (bo'sh qoldirmasa) to'g'ri hisoblanadi (qarang
            # `exercises.models.javoblarni_tekshir`).
            if "erkin" in y:
                savollar[raqam - 1]["erkin"] = bool(y["erkin"])
            yangilandi += 1
        mashq.savollar = savollar
        mashq.save(update_fields=["savollar"])
        return Response({
            "yangilandi": yangilandi, "xatolar": xatolar, "mashq": _kurs_mashq_admin_dict(mashq),
        })


class KursMashqJavobExcelView(APIView):
    """Admin/owner uchun — bitta mashqning to'g'ri javoblarini Excel
    (.xlsx) orqali ommaviy yangilash (2026-07-29 talabi). Format:
    1-ustun — savol raqami (shu mashq ICHIDA, 1 dan boshlab), 2-ustun —
    to'g'ri javob. Bitta qatorda xato bo'lsa (masalan mavjud bo'lmagan
    raqam) — o'sha qator o'tkazib yuboriladi, qolganlari davom etadi
    (`accounts/excel_import.py` bilan bir xil naqsh)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        fayl = request.FILES.get("fayl")
        if not fayl:
            return Response({"detail": "fayl majburiy"}, status=400)
        try:
            qatorlar = javob_qatorlarini_oqi(fayl)
        except Exception:
            return Response({"detail": "Fayl yaroqli Excel (.xlsx) emas"}, status=400)
        if not qatorlar:
            return Response({"detail": "Faylda qator topilmadi"}, status=400)

        yangilandi, xatolar = javoblarni_yangila(mashq, qatorlar)
        return Response({
            "yangilandi": yangilandi, "xatolar": xatolar, "mashq": _kurs_mashq_admin_dict(mashq),
        })


class KursMashqRasmBoshqaruvView(APIView):
    """Admin/owner uchun — mashqqa rasm biriktirish/o'chirish."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        rasm = request.FILES.get("rasm")
        if not rasm:
            return Response({"detail": "rasm majburiy"}, status=400)
        xato = _rasm_tekshir(rasm)
        if xato:
            return Response({"detail": xato}, status=400)
        # Yangi, MUSTAQIL rasm yuklanmoqda — agar mashq ilgari boshqa
        # mashq(lar) bilan rasm ulashgan bo'lsa (`rasm_guruhi`), shu
        # ulanish uziladi (guruhning o'zi, ya'ni undagi BOSHQA mashqlar
        # tegilmaydi — faqat shu mashq endi o'z alohida rasmiga ega).
        mashq.rasm_guruhi = None
        mashq.rasm = rasm
        mashq.save(update_fields=["rasm", "rasm_guruhi"])
        return Response(_kurs_mashq_admin_dict(mashq))

    def delete(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        if mashq.rasm_guruhi_id:
            # Ulashilgan rasm — faylning o'zi O'CHIRILMAYDI (guruhdagi
            # boshqa mashq(lar) hali undan foydalanishi mumkin), shu
            # mashq FAQAT guruhdan uziladi.
            mashq.rasm_guruhi = None
            mashq.save(update_fields=["rasm_guruhi"])
        elif mashq.rasm:
            mashq.rasm.delete(save=False)
            mashq.save(update_fields=["rasm"])
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
        xato = _audio_tekshir(audio)
        if xato:
            return Response({"detail": xato}, status=400)
        mashq.audio = audio
        mashq.save()
        return Response(_kurs_mashq_admin_dict(mashq))


def _audio_xeshi(fayl):
    """Yuklangan faylning SHA-256 yig'indisi. Bo'laklab o'qiladi —
    audio 50 MB bo'lishi mumkin, uni butunlay xotiraga olish shart
    emas. O'qigandan keyin ko'rsatkich boshiga qaytariladi, chunki
    chaqiruvchi faylni saqlashi mumkin."""
    import hashlib

    xesh = hashlib.sha256()
    fayl.seek(0)
    for bolak in iter(lambda: fayl.read(1024 * 256), b""):
        xesh.update(bolak)
    fayl.seek(0)
    return xesh.hexdigest()


def _mavjud_audioni_top(mashq, xesh):
    """SHU MARKAZDA xuddi shu fayl allaqachon yuklanganmi (2026-08-08).

    Markaz bilan chegaralangan: boshqa o'quv markazining fayliga ishora
    qilish ma'lumot chegarasini buzardi."""
    return (
        KursMashqAudio.objects
        .filter(fayl_xesh=xesh, mashq__tugun__markaz_id=mashq.tugun.markaz_id)
        .exclude(audio="")
        .order_by("id")
        .first()
    )


def _audio_faylini_xavfsiz_ochir(yozuv):
    """Yozuvning faylini o'chiradi — LEKIN faqat unga BOSHQA yozuv
    ishora qilmayotgan bo'lsa. Takrorni qayta ishlatish tufayli bitta
    fayl bir nechta yozuvga tegishli bo'lishi mumkin; tekshirmasdan
    o'chirilsa, qolgan mashqlarning audiosi jimgina yo'qolardi."""
    if not yozuv.audio:
        return
    nom = yozuv.audio.name
    boshqasi_ishlatyaptimi = (
        KursMashqAudio.objects.filter(audio=nom).exclude(pk=yozuv.pk).exists()
    )
    if boshqasi_ishlatyaptimi:
        yozuv.audio = ""  # faqat bog'lanishni uzamiz, fayl qoladi
    else:
        yozuv.audio.delete(save=False)


def _mashq_blok_audio_raqamlari(mashq):
    """Mashqning blok formatidagi audio BELGILARI (audio_raqam) —
    ketma-ketlikni saqlab, takrorsiz ro'yxat."""
    raqamlar = []
    for b in mashq.bloklar or []:
        raqam = b.get("audio_raqam")
        if raqam and raqam not in raqamlar:
            raqamlar.append(raqam)
    return raqamlar


class KursMashqBlokAudioBoshqaruvView(APIView):
    """2026-07-31 talabi: blok formatidagi mashq yaratilgach, admin
    darslikdagi audio faylni AYNAN o'sha mashqdagi audio belgisiga
    (`audio_raqam`) biriktirishi kerak — "Qayta yuklash" tugmasi
    yonida. Mashqda bitta audio belgisi bo'lsa avtomatik shunga
    biriktiriladi; bir nechta bo'lsa `raqam` majburiy (frontend
    tanlov ko'rsatadi)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        audio = request.FILES.get("audio")
        if not audio:
            return Response({"detail": "audio majburiy"}, status=400)

        raqamlar = _mashq_blok_audio_raqamlari(mashq)
        if raqamlar:
            raqam = request.data.get("raqam") or raqamlar[0]
            if raqam not in raqamlar:
                return Response({"detail": "Noto'g'ri audio raqami"}, status=400)
        elif mashq.audio_kerak:
            # 2026-08-07, RASM-FON rejimi: u yerda `bloklar` bo'sh, ya'ni
            # trek raqami (`audio_raqam`) umuman yo'q — AI faqat sahifada
            # audio BELGISI borligini aytadi (`audio_kerak`). Shunday
            # mashqqa audio RAQAMSIZ biriktiriladi; `KursMashqAudio.raqam`
            # `blank=True`, talaba panelida raqamsiz ko'rinadi.
            raqam = ""
        else:
            return Response({"detail": "Bu mashqda audio belgisi yo'q"}, status=400)

        xesh = _audio_xeshi(audio)
        yozuv, yaratildi = KursMashqAudio.objects.get_or_create(mashq=mashq, raqam=raqam)
        if not yaratildi:
            _audio_faylini_xavfsiz_ochir(yozuv)  # eski fayl diskda "yetim" qolmasin

        # 2026-08-08, foydalanuvchi talabi: "2 ta mashq uchun bir xil
        # audio yuklansa qayta yuklamasin, oldin yuklangan fayl adresini
        # ko'rsatib qo'ysin". Shu markazda xuddi shu fayl bo'lsa — diskka
        # YANGI nusxa yozilmaydi, yozuv mavjud faylga ishora qiladi.
        mavjud = _mavjud_audioni_top(mashq, xesh)
        if mavjud:
            yozuv.audio.name = mavjud.audio.name
        else:
            yozuv.audio.save(f"{mashq.id}_{raqam or 'audio'}.mp3", audio, save=False)
        yozuv.fayl_xesh = xesh
        yozuv.save()

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=mashq.tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=(
                f"{mashq.tugun.nomi} (#{mashq.tartib} mashqqa audio {raqam} "
                f"{'qayta ishlatildi' if mavjud else 'biriktirildi'})"
            ),
        )
        javob = _kurs_mashq_admin_dict(mashq)
        if mavjud:
            javob["audio_qayta_ishlatildi"] = {
                "mashq_id": mavjud.mashq_id,
                "mashq_tartib": mavjud.mashq.tartib,
                "raqam": mavjud.raqam,
                "url": f"/api/kurslar/mashq-audio/{mavjud.id}/",
            }
        return Response(javob)


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
        rasm = mashq.effektiv_rasm
        if not rasm:
            raise Http404
        javob = FileResponse(rasm.open("rb"))
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


class KursBlokRasmView(APIView):
    """Blok formatidagi sahifadan kesilgan surat — autentifikatsiyalangan
    stream (B3.2 qoidasi: xom /media/ orqali berilmaydi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        from .models import KursMashqRasmi

        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        yozuv = get_object_or_404(KursMashqRasmi, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, yozuv.mashq.tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        if not yozuv.rasm:
            raise Http404
        javob = FileResponse(yozuv.rasm.open("rb"))
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
        return Response(
            [_kurs_mashq_admin_dict(m) for m in tugun.mashqlar.prefetch_related("audiolar", "rasmlar")]
        )


class KursMashqRoyxatiView(APIView):
    """Talaba uchun — bitta tugunning mashqlari ro'yxati (savollar 'togri'siz)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _kurslar_korinadimi(request.user):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if _talaba_tugun_qulflanganmi(request.user, tugun):
            return Response({"detail": "Bu qism hali qulflangan"}, status=403)
        # Talabaga javoblar YUBORILMAYDI, o'qituvchi/admin/owner esa
        # darsda tushuntirishi uchun to'g'ri javoblarni ko'radi.
        tayyorla = (
            _kurs_mashq_talaba_dict
            if request.user.role == User.Role.STUDENT
            else _kurs_mashq_oqituvchi_dict
        )
        return Response(
            [tayyorla(m) for m in tugun.mashqlar.prefetch_related("audiolar", "rasmlar")]
        )


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
