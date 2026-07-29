"""Blok formatida ZIP yuklash endpointlari (2026-07-28).

Alohida modulda, chunki `views.py` allaqachon katta va bu — mustaqil
oqim: ZIP bir marta yuklanadi, keyin sahifalar BITTALAB qayta ishlanadi.

Nega ikki bosqich: bitta Unit ZIP'i 7-10 sahifa, har sahifa AI'da ~125
sekund => 15-20 daqiqa. `gunicorn.conf.py` da `timeout = 300`, ya'ni
bitta so'rovda sig'maydi. Celery/worker ATAYLAB ishlatilmadi — Render'da
bu qo'shimcha servis va xarajat, holbuki jarayonni frontend boshqarsa
yetarli (u progress ham ko'rsatadi).
"""

import os
import pathlib
import shutil
import threading
import zipfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assessment.providers import ProviderXatosi
from audit.models import FaoliyatYozuvi
from audit.utils import logla

from .blok_generatsiya import (
    audio_raqamlarini_yig,
    blok_provider_olish,
    bloklarni_tayyorla,
    javob_kaliti_sahifasi,
    rasmni_kes,
    sahifani_bloklarga_ajrat,
)
from .kontent_generatsiya import (
    audio_raqamini_ajrat,
    kengaytma_turi,
    raqam_kaliti,
    tabiiy_tartib_kaliti,
)
from .models import (
    KursMashq,
    KursMashqAudio,
    KursMashqRasmi,
    KursTugun,
    KursZipJarayoni,
)
from .views import _mashq_admin_mi, _unit_bolimlari


def _jarayon_kesh_yoli(jarayon):
    yol = pathlib.Path(settings.MEDIA_ROOT) / "tmp_blok_jarayon"
    yol.mkdir(parents=True, exist_ok=True)
    return yol / f"{jarayon.id}.zip"


def _jarayon_arxivi(jarayon):
    """ZIP faylni ochadi — R2'DAN FAQAT BIR MARTA yuklab, mahalliy diskka
    keshlab qo'yadi (2026-07-28, haqiqiy production xatosidan keyin).

    Muammo: `django-storages`ning S3Storage'i faylni O'QISH uchun
    ochganda uni TO'LIQ QAYTA YUKLAB OLADI (`S3File._get_file` ->
    `download_fileobj`) — bu kutubxonaning o'z ishlash tartibi, bizning
    kod emas. Har sahifa BOSHQA HTTP so'rovda ishlangani uchun, tuzatishsiz
    holatda ZIP R2'dan HAR SAHIFA UCHUN qaytadan yuklanardi: 56 MB'lik
    fayl va 9 sahifalik Unit uchun bu ~500 MB ortiqcha tarmoq trafigi —
    aynan shu sabab bilan (Free tarifda) servis qulab tushgan edi
    (2026-07-29, foydalanuvchi xabar berdi).

    Yechim: birinchi chaqiruvda R2'dan bir marta yuklab, MEDIA_ROOT
    ichidagi vaqtinchalik faylga yoziladi; keyingi sahifalar shu
    mahalliy nusxadan o'qiydi. Konteyner qayta ishga tushsa (disk
    tozalanadi) — keshlangan fayl yo'qoladi va keyingi so'rov R2'dan
    qayta yuklaydi, ya'ni o'z-o'zini tuzatadi, xato bermaydi."""
    kesh = _jarayon_kesh_yoli(jarayon)
    if not kesh.exists():
        # `manba.read()` + `write_bytes()` BUTUN faylni bitta Python
        # `bytes` ob'ekti sifatida xotirada ushlab turardi (56 MB fayl —
        # 56 MB qo'shimcha RAM, `S3File`ning o'zi ham xuddi shuncha
        # ishlatgandan KEYIN). `copyfileobj` kichik bo'laklarda (64 KB)
        # o'qib-yozadi — xotirada faqat bitta bo'lak turadi.
        #
        # Parallel sahifa ishlash qo'shilgandan keyin (2026-07-29) bir
        # nechta so'rov shu yerga BIR VAQTDA kelishi mumkin — ikkalasi
        # ham keshni yo'q deb topib yuklashni boshlashi mumkin. Shuning
        # uchun avval VAQTINCHALIK faylga yozib, keyin ATOMIK ravishda
        # (`os.replace`) asosiy nomga almashtiramiz: yarim yozilgan yoki
        # ikki oqim aralashib ketgan fayl HECH QACHON hosil bo'lmaydi —
        # eng yomon holatda ikkalasi ham bir xil to'liq faylni yuklab,
        # ikkinchisi birinchisining ustidan (zararsiz) yozadi.
        vaqtinchalik = kesh.with_suffix(f".{os.getpid()}-{threading.get_ident()}.tmp")
        with jarayon.zip_fayl.open("rb") as manba, open(vaqtinchalik, "wb") as nishon:
            shutil.copyfileobj(manba, nishon)
        os.replace(vaqtinchalik, kesh)
    return zipfile.ZipFile(kesh)


def _jarayon_keshini_tozala(jarayon):
    _jarayon_kesh_yoli(jarayon).unlink(missing_ok=True)


def _zip_tarkibini_ajrat(nomlar):
    """ZIP ichidagi fayllarni uch guruhga ajratadi — mavjud
    `KursZipYuklashView` bilan BIR XIL qoida bo'yicha (ataylab
    o'zgartirilmadi: admin shu tuzilmaga o'rgangan):

    * tur fayl KENGAYTMASIDAN aniqlanadi (papka nomiga qaralmaydi);
    * nomida "answer" bo'lgan rasm — javob kaliti sahifasi (papka
      nomidan ANIQ ma'lum, AI'ga klassifikatsiya qildirish shart emas);
    * tartib — fayl nomidagi raqam bo'yicha tabiiy ("10" > "2")."""
    sahifalar, javob_kaliti, audiolar = [], [], []
    for nom in nomlar:
        if nom.endswith("/"):
            continue
        asos = nom.rsplit("/", 1)[-1]
        turi = kengaytma_turi(asos)
        if turi == "rasm":
            (javob_kaliti if "answer" in nom.lower() else sahifalar).append(nom)
        elif turi == "audio":
            audiolar.append(nom)

    def kalit(n):
        return tabiiy_tartib_kaliti(n.rsplit("/", 1)[-1])

    sahifalar.sort(key=kalit)
    javob_kaliti.sort(key=kalit)
    return sahifalar, javob_kaliti, audiolar


class KursBlokZipYuklashView(APIView):
    """1-BOSQICH: ZIP'ni qabul qilish va nima borligini sanash.

    `pk` — KITOB tuguni (Student's Book / Workbook)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        kitob = get_object_or_404(KursTugun, pk=pk)
        if not {"mashqlar", "vocabulary"}.issubset(_unit_bolimlari(kitob)):
            return Response(
                {"detail": "Bu tugunda Mashqlar/Vocabulary bo'limlari topilmadi"},
                status=400,
            )

        zip_fayl = request.FILES.get("zip_fayl")
        if not zip_fayl:
            return Response({"detail": "zip_fayl majburiy"}, status=400)

        try:
            nomlar = zipfile.ZipFile(zip_fayl).namelist()
        except zipfile.BadZipFile:
            return Response({"detail": "Fayl yaroqli ZIP emas"}, status=400)

        sahifalar, javob_kaliti, audiolar = _zip_tarkibini_ajrat(nomlar)
        if not sahifalar:
            return Response({"detail": "ZIP ichida rasm fayli topilmadi"}, status=400)

        zip_fayl.seek(0)
        jarayon = KursZipJarayoni.objects.create(
            tugun=kitob,
            zip_fayl=zip_fayl,
            jami_sahifa=len(sahifalar) + len(javob_kaliti),
            natijalar={
                "sahifalar": sahifalar,
                "javob_kaliti_fayllari": javob_kaliti,
                "audiolar": audiolar,
                # Parallel qayta ishlash (2026-07-29): "band_qilingan" —
                # band qilib olingan sahifa indekslari (hali tugamagan
                # bo'lishi ham mumkin); "tugallangan" — indeks(str) -> natija,
                # tugagan sahifalar, tugallanish TARTIBIGA emas, ORIGINAL
                # sahifa TARTIBIGA qarab saqlanadi (parallel so'rovlar har xil
                # tartibda tugashi mumkin, lekin yakuniy mashqlar tartibi
                # HAR DOIM sahifa tartibiga mos bo'lishi kerak).
                "band_qilingan": [],
                "tugallangan": {},
            },
        )
        return Response(
            {
                "jarayon_id": jarayon.id,
                "jami_sahifa": jarayon.jami_sahifa,
                "sahifa_soni": len(sahifalar),
                "javob_kaliti_soni": len(javob_kaliti),
                "audio_soni": len(audiolar),
            },
            status=201,
        )


class KursBlokJarayonHolatiView(APIView):
    """Kitob uchun TUGALLANMAGAN (yarim qolgan) jarayon bor-yo'qligini
    tekshiradi (2026-07-29 talabi: "yuklanmagan qismini qo'lda yuklash
    imkoni kerak").

    Nega kerak: uzoq jarayon davomida brauzer yopilib qolsa yoki
    tarmoq uzilsa, `KursZipJarayoni` bazada "ISHLANMOQDA" holatida
    qolib ketadi (ZIP esa R2'da saqlangan). Admin sahifani qayta
    ochganda buni ko'rib, "Davom ettirish" tugmasi bilan xuddi
    o'sha jarayon_id'dan davom etishi mumkin — boshidan qayta
    yuklash SHART EMAS."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        jarayon = (
            KursZipJarayoni.objects.filter(tugun_id=pk)
            .exclude(holat=KursZipJarayoni.Holat.TUGADI)
            .order_by("-created_at")
            .first()
        )
        if not jarayon:
            return Response({"faol_jarayon": None})
        return Response(
            {
                "faol_jarayon": {
                    "id": jarayon.id,
                    "ishlangan_sahifa": jarayon.ishlangan_sahifa,
                    "jami_sahifa": jarayon.jami_sahifa,
                }
            }
        )


class KursBlokSahifaView(APIView):
    """2-BOSQICH: navbatdagi sahifa(lar)ni qayta ishlash.

    2026-07-29: frontend endi BIR VAQTDA bir nechta (2-3 ta) so'rov
    yuborishi mumkin — har bir HTTP so'rov FAQAT BITTA sahifani oladi,
    lekin bir nechtasi PARALLEL bajarilishi mumkin. Shuning uchun:

    1) Navbatdagi bo'sh sahifa ATOMIK band qilinadi (`select_for_update`
       ichida) — DB darajasidagi qulf tufayli ikkita parallel so'rov
       HECH QACHON bir xil indeksni band qila olmaydi.
    2) Uzoq AI chaqiruvi QULFSIZ bajariladi (~100-125s) — aks holda
       parallel so'rovlar bir-birini navbatda kutib, konkurentlikning
       hech qanday foydasi bo'lmasdi.
    3) Natija yana ATOMIK o'qib-yozib qo'shiladi (`tugallangan[indeks]`)
       — shu orqali boshqa parallel so'rov shu oraliqda yozgan natija
       hech qachon YO'QOLMAYDI ("lost update" muammosi).

    Natijalar SAHIFA INDEKSI bo'yicha saqlanadi (tugallanish tartibida
    emas) — parallel so'rovlar turlicha tartibda tugashi mumkin, lekin
    yakuniy mashqlar tartibi sahifa tartibiga mos bo'lishi SHART."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)

        # 1) Navbatdagi BO'SH sahifani ATOMIK band qilamiz.
        with transaction.atomic():
            jarayon = get_object_or_404(
                KursZipJarayoni.objects.select_for_update(), pk=pk
            )
            if jarayon.holat == KursZipJarayoni.Holat.TUGADI:
                return Response({"detail": "Bu jarayon allaqachon tugagan"}, status=400)

            d = jarayon.natijalar
            oddiy = d["sahifalar"]
            javob_fayllari = d["javob_kaliti_fayllari"]
            jami = len(oddiy) + len(javob_fayllari)
            band = set(d.get("band_qilingan", []))
            indeks = next((i for i in range(jami) if i not in band), None)

            if indeks is None:
                # Boshqa parallel so'rov(lar) allaqachon barcha sahifani
                # band qilib bo'lgan — bu normal holat, xato emas: bu
                # "ishchi" uchun hozircha ish qolmadi.
                return Response(
                    {
                        "band_qilinadigan_sahifa_qolmadi": True,
                        "ishlangan_sahifa": jarayon.ishlangan_sahifa,
                        "jami_sahifa": jarayon.jami_sahifa,
                        "tugadimi": jarayon.ishlangan_sahifa >= jarayon.jami_sahifa,
                    }
                )

            band.add(indeks)
            d["band_qilingan"] = sorted(band)
            jarayon.natijalar = d
            jarayon.holat = KursZipJarayoni.Holat.ISHLANMOQDA
            jarayon.save(update_fields=["natijalar", "holat"])

        # 2) UZOQ AI ishi — DB QULFISIZ (bir necha daqiqagacha cho'zilishi
        #    mumkin; qulf ushlab turilsa boshqa parallel so'rovlar
        #    tiqilib qolardi va konkurentlikdan foyda bo'lmasdi).
        try:
            provider = blok_provider_olish()
        except ProviderXatosi as e:
            return Response({"detail": str(e)}, status=400)

        with _jarayon_arxivi(jarayon) as arxiv:
            if indeks < len(oddiy):
                nom = oddiy[indeks]
                turi = "sahifa"
                natija, xato = sahifani_bloklarga_ajrat(provider, arxiv.read(nom))
            else:
                nom = javob_fayllari[indeks - len(oddiy)]
                turi = "javob_kaliti"
                natija, xato = javob_kaliti_sahifasi(provider, arxiv.read(nom))
                if not xato and not natija.get("javoblar"):
                    # Sahifa "answer" papkasida turibdi, lekin ichida
                    # javob yo'q. Amalda uchragan holat (2026-07-28):
                    # "answers/answer 1.jpg" aslida Teacher's Guide'ning
                    # Unit Overview sahifasi edi. AI to'g'ri ish qilgan,
                    # lekin admin buni BILISHI kerak — aks holda javob
                    # kaliti qo'llandi deb o'ylab qoladi.
                    xato = "Javob topilmadi — bu sahifa javob kaliti emasga o'xshaydi"

        # 3) Natijani ATOMIK qo'shamiz — qayta o'qib-yozamiz, boshqa
        #    parallel so'rov shu oraliqda o'ziniki yozgan bo'lishi mumkin.
        with transaction.atomic():
            jarayon = KursZipJarayoni.objects.select_for_update().get(pk=pk)
            d = jarayon.natijalar
            d.setdefault("tugallangan", {})[str(indeks)] = {
                "turi": turi,
                "fayl": nom,
                "natija": natija,
                "xato": xato,
            }
            jarayon.natijalar = d
            jarayon.ishlangan_sahifa = len(d["tugallangan"])
            jami_sahifa = jarayon.jami_sahifa
            tugadimi = jarayon.ishlangan_sahifa >= jami_sahifa
            if tugadimi:
                # Yakunlashdan OLDIN belgilaymiz — boshqa parallel so'rov
                # shu oraliqda yana bir sahifani band qilib olmasin.
                jarayon.holat = KursZipJarayoni.Holat.TUGADI
            jarayon.save(update_fields=["natijalar", "ishlangan_sahifa", "holat"])

        javob = {
            "ishlangan_sahifa": jarayon.ishlangan_sahifa,
            "jami_sahifa": jami_sahifa,
            "joriy_fayl": nom.rsplit("/", 1)[-1],
            "xato": xato,
            "tugadimi": tugadimi,
        }
        if tugadimi:
            javob["yakun"] = _jarayonni_yakunla(jarayon, request.user)
        return Response(javob)


def _javob_kaliti_indeksi(bandlar):
    """(mashq_raqami, band_raqami) -> javob. Katta-kichik harfga sezmas
    (2026-07-27 da topilgan haqiqiy nomuvofiqlik: "GRAMMAR SPOT" va
    "Grammar Spot" bir xil band edi, lekin mos kelmagan)."""
    indeks = {}
    for b in bandlar:
        kalit = (
            str(b.get("mashq_raqami") or "").strip().lower(),
            str(b.get("band_raqami") or "").strip().lower(),
        )
        if kalit != ("", "") and b.get("javob"):
            indeks[kalit] = b["javob"]
    return indeks


def _jarayonni_yakunla(jarayon, foydalanuvchi):
    """Yig'ilgan tahlillarni BAZAGA yozadi: mashqlar (bloklar+savollar),
    sahifadan kesilgan rasmlar, audio biriktirish.

    2026-07-29: natijalar `tugallangan` lug'atida SAHIFA INDEKSI kaliti
    bilan saqlangan (parallel qayta ishlash tufayli tugallanish tartibi
    original sahifa tartibiga mos kelmasligi mumkin) — shuning uchun bu
    yerda ATAYLAB indeks bo'yicha SARALAB o'qiladi, natijada yakuniy
    mashqlar tartibi har doim sahifa tartibiga mos bo'ladi."""
    d = jarayon.natijalar
    mashq_tugun = _unit_bolimlari(jarayon.tugun)["mashqlar"]

    tugallangan = d.get("tugallangan", {})
    tartiblangan = [tugallangan[k] for k in sorted(tugallangan, key=int)]

    xato_sahifalar = [
        {"fayl": t["fayl"], "xato": t["xato"]} for t in tartiblangan if t["xato"]
    ]
    javob_bandlari = []
    for t in tartiblangan:
        if t["turi"] == "javob_kaliti" and not t["xato"]:
            javob_bandlari.extend(t["natija"].get("javoblar", []))
    javob_indeksi = _javob_kaliti_indeksi(javob_bandlari)

    boshlangich = mashq_tugun.mashqlar.count()
    yaratilgan, rasm_soni, savol_soni, qollangan = [], 0, 0, 0

    with _jarayon_arxivi(jarayon) as arxiv:
        i = 0
        for t in tartiblangan:
            if t["turi"] != "sahifa" or t["xato"]:
                continue
            i += 1
            natija = t["natija"]
            bloklar, savollar, qutilar = bloklarni_tayyorla(natija.get("elementlar", []))

            # Javob kaliti AI taxminidan USTUN — darslikning haqiqiy manbasi.
            for s in savollar:
                kalit = (
                    str(s.get("mashq_raqami") or "").strip().lower(),
                    str(s.get("band_raqami") or "").strip().lower(),
                )
                if kalit in javob_indeksi:
                    s["togri"] = javob_indeksi[kalit]
                    qollangan += 1

            mashq = KursMashq.objects.create(
                tugun=mashq_tugun,
                tartib=boshlangich + i,
                matn=natija.get("sarlavha", ""),
                savollar=savollar,
                bloklar=bloklar,
            )
            savol_soni += len(savollar)

            sahifa_bytes = arxiv.read(t["fayl"])
            for tartib, quti in enumerate(qutilar):
                kesilgan = rasmni_kes(sahifa_bytes, quti)
                if not kesilgan:
                    continue
                yozuv = KursMashqRasmi(mashq=mashq, tartib=tartib)
                yozuv.rasm.save(f"{mashq.id}_{tartib}.jpg", ContentFile(kesilgan), save=True)
                rasm_soni += 1

            yaratilgan.append((mashq, audio_raqamlarini_yig(bloklar)))

        moslangan, ishlatilgan = _audiolarni_biriktir(
            arxiv, d.get("audiolar", []), yaratilgan)

    jarayon.holat = KursZipJarayoni.Holat.TUGADI
    jarayon.save(update_fields=["holat"])
    _jarayon_keshini_tozala(jarayon)  # vaqtinchalik mahalliy nusxa endi kerak emas

    natija = {
        "yaratilgan_mashqlar": len(yaratilgan),
        "kesilgan_rasmlar": rasm_soni,
        "baholanadigan_savollar": savol_soni,
        "javob_kaliti_qollandi": qollangan,
        "moslangan_audio": moslangan,
        "ishlatilmagan_audio": [
            n.rsplit("/", 1)[-1] for n in d.get("audiolar", []) if n not in ishlatilgan
        ],
        "xato_sahifalar": xato_sahifalar,
    }
    logla(
        foydalanuvchi=foydalanuvchi,
        harakat=FaoliyatYozuvi.Harakat.YARATISH,
        obyekt=jarayon.tugun,
        obyekt_turi="KursTugun",
        obyekt_nomi=f"{jarayon.tugun.nomi} (blok ZIP)",
        snapshot=natija,
    )
    return natija


def _audiolarni_biriktir(arxiv, audio_nomlari, yaratilgan):
    """Audio fayllarni raqami bo'yicha mos mashqqa biriktiradi.

    Kalit — NORMALLASHTIRILGAN raqam (`raqam_kaliti`), satr EMAS: AI
    "1.1" deb qaytaradi, fayl nomi esa "1.01" (nolli) bo'ladi — satr
    solishtirilsa mos kelmaydi (2026-07-28 da haqiqiy ZIP bilan sinovda
    12 audiodan 9tasi aynan shu sabab mos kelmagan edi)."""
    indeks = {}
    for nom in audio_nomlari:
        kalit = raqam_kaliti(audio_raqamini_ajrat(nom.rsplit("/", 1)[-1]))
        if kalit is not None:
            indeks.setdefault(kalit, nom)

    moslangan, ishlatilgan = 0, set()
    for mashq, raqamlar in yaratilgan:
        for tartib, raqam in enumerate(raqamlar, start=1):
            nom = indeks.get(raqam_kaliti(raqam))
            if not nom:
                continue
            yozuv = KursMashqAudio(mashq=mashq, raqam=raqam, tartib=tartib)
            yozuv.audio.save(nom.rsplit("/", 1)[-1], ContentFile(arxiv.read(nom)), save=True)
            ishlatilgan.add(nom)
            moslangan += 1
    return moslangan, ishlatilgan
