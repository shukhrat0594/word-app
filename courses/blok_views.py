"""Blok formatida ZIP yuklash endpointlari (2026-07-28).

Alohida modulda, chunki `views.py` allaqachon katta va bu — mustaqil
oqim: ZIP bir marta yuklanadi, keyin sahifalar BITTALAB qayta ishlanadi.

Nega ikki bosqich: bitta Unit ZIP'i 7-10 sahifa, har sahifa AI'da ~125
sekund => 15-20 daqiqa. `gunicorn.conf.py` da `timeout = 300`, ya'ni
bitta so'rovda sig'maydi. Celery/worker ATAYLAB ishlatilmadi — Render'da
bu qo'shimcha servis va xarajat, holbuki jarayonni frontend boshqarsa
yetarli (u progress ham ko'rsatadi).
"""

import io
import os
import pathlib
import re
import shutil
import threading
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assessment.providers import ProviderXatosi
from audit.models import FaoliyatYozuvi
from audit.utils import logla

from .blok_generatsiya import (
    blok_provider_olish,
    bloklarni_tayyorla,
    rasm_idxlarni_lokallashtir,
    rasmni_kes,
    sahifani_bloklarga_ajrat,
)
from .rasm_fon_generatsiya import sahifani_rasm_fonga_ajrat
from .kontent_generatsiya import kengaytma_turi, tabiiy_tartib_kaliti
from .models import (
    KursMashq,
    KursMashqRasmi,
    KursSoz,
    KursTugun,
    KursZipJarayoni,
)
from .views import _kurs_mashq_admin_dict, _mashq_admin_mi, _unit_bolimlari

# 2026-07-29(6): agar bir sahifa band qilingan-u biror sababdan (masalan
# ESKI, tuzatishdan oldingi versiyada uchragan xato) hech qachon
# `tugallangan`ga yozilmasa, u band holida "muzlab" qolar edi — jarayon
# hech qachon 100%ga yetolmasdi va HECH QANDAY xato ko'rsatmasdi (jim
# "band_qilinadigan_sahifa_qolmadi" javobi bilan abadiy aylanardi).
# Endi shu holat VAQT bo'yicha aniqlanadi: agar band qilingandan beri
# shuncha soniya o'tgan bo'lsa-yu hali tugallanmagan bo'lsa — bu ODDIY
# sekinlik emas, "muzlab qolgan" deb hisoblanadi (SAHIFA_TIMEOUT_MS —
# blok_generatsiya.py'da 240s — va 3 marta qayta urinish + backoff'dan
# ancha katta zaxira bilan).
TIQILIB_QOLISH_CHEGARASI_SONIYA = 360


def _band_vaqtlarini_ol(d):
    """`natijalar["band_qilingan"]`ni {indeks(str): ISO vaqt} shaklida
    qaytaradi. ESKI formatda (2026-07-29(6)dan oldin) bu oddiy ro'yxat
    edi (vaqtsiz) — bunday yozuvlar VAQTI NOMA'LUM, ya'ni har doim
    "juda eski" (darhol tiqilib qolgan) deb hisoblanadi, chunki ular
    haqiqatan ham eski (tuzatishdan oldingi) jarayonlarga tegishli."""
    band_xom = d.get("band_qilingan", [])
    if isinstance(band_xom, dict):
        return dict(band_xom)
    juda_eski = (timezone.now() - timedelta(days=1)).isoformat()
    return {str(i): juda_eski for i in band_xom}


def _jarayon_kesh_yoli(jarayon):
    yol = pathlib.Path(settings.MEDIA_ROOT) / "tmp_blok_jarayon"
    yol.mkdir(parents=True, exist_ok=True)
    return yol / f"{jarayon.id}.zip"


# PDF sahifasi render qilinadigan NISHON kenglik (piksel). 2026-08-03,
# haqiqiy production OOM'idan keyin qo'shilgan edi: qattiq `scale=2.0`
# foydalanuvchining darsligida 3072x3872 (11.9 megapiksel) bergan —
# xom RGB 34 MB, pdfium bitmap yana ~47 MB, bu 512 MB'lik Render
# instansida xotirani tugatgan. Nishon kenglik (qattiq ko'paytuvchi
# emas) tanlangan, chunki turli PDF'larda sahifa o'lchami har xil.
#
# 2026-08-07: PDF yo'li "rasm-fon" rejimi uchun QAYTA tiklandi. Bu
# rejimda sahifa rasmi TALABAGA KO'RSATILADI (blok rejimidagidek faqat
# AI uchun oraliq material emas) — shuning uchun sifat muhimroq, lekin
# 2200 baribir yetarli: `rasmni_kes` kesilgan hududni 900px gacha
# kichraytiradi, undan kattasi hech qayerda ishlatilmaydi.
PDF_NISHON_KENGLIK = 2200


class _PdfManbaWrapper:
    """`zipfile.ZipFile`ning `.read(nom)` interfeysini PDF uchun taqlid
    qiladi — shu tufayli `_jarayon_arxivi`dan foydalanuvchi barcha kod
    (`arxiv.read(nom)`) o'zgarishsiz qoladi, ZIP yoki PDF ekanidan
    qat'i nazar. `nom` — "sahifa-<raqam>.jpg" ko'rinishida, raqam PDF
    sahifa raqami (1 dan boshlanadi)."""

    def __init__(self, pdf_hujjat):
        self._pdf = pdf_hujjat

    def read(self, nom):
        raqam = int(re.search(r"(\d+)", nom).group(1))
        sahifa = self._pdf[raqam - 1]
        # `scale` — nuqtadan pikselga nisbat, NISHON KENGLIKKA qarab
        # hisoblanadi. PDF nuqtasi = 1/72 dyuym, ya'ni A4 (595 nuqta)
        # `scale=1.0`da atigi 595px bo'lardi — matn o'qilmaydi.
        kenglik_nuqta = sahifa.get_width() or 0
        scale = PDF_NISHON_KENGLIK / kenglik_nuqta if kenglik_nuqta else 2.0
        scale = min(max(scale, 0.5), 4.0)
        pil = sahifa.render(scale=scale).to_pil().convert("RGB")
        bufer = io.BytesIO()
        pil.save(bufer, format="JPEG", quality=88)
        return bufer.getvalue()


@contextmanager
def _jarayon_arxivi(jarayon):
    """ZIP yoki PDF faylni ochadi — R2'DAN FAQAT BIR MARTA yuklab,
    mahalliy diskka keshlab qo'yadi (2026-07-28, haqiqiy production
    xatosidan keyin).

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

    if jarayon.manba_turi == KursZipJarayoni.ManbaTuri.PDF:
        import pypdfium2 as pdfium

        pdf_hujjat = pdfium.PdfDocument(str(kesh))
        try:
            yield _PdfManbaWrapper(pdf_hujjat)
        finally:
            pdf_hujjat.close()
    else:
        with zipfile.ZipFile(kesh) as arxiv:
            yield arxiv


def _jarayon_keshini_tozala(jarayon):
    _jarayon_kesh_yoli(jarayon).unlink(missing_ok=True)


def _zip_ichidagi_rasmlarni_ajrat(nomlar):
    """2026-07-30 talabi: ZIP endi FAQAT rasmlar uchun — javob-kaliti
    papkasi, audio, "rejim" tanlovi va h.k. hammasi OLIB TASHLANDI
    (sodda: har rasm — alohida mashq, "🖼️ Rasm orqali mashq qo'shish"
    bilan BIR XIL AI tahlili). Rasmlar fayl nomi bo'yicha TABIIY
    tartibda saralanadi ("10.jpg" "2.jpg"dan keyin keladi)."""
    rasmlar = [
        nom for nom in nomlar
        if not nom.endswith("/") and kengaytma_turi(nom.rsplit("/", 1)[-1]) == "rasm"
    ]
    rasmlar.sort(key=lambda n: tabiiy_tartib_kaliti(n.rsplit("/", 1)[-1]))
    return rasmlar


# RASM_FON tartiblash sxemasi (2026-08-07). `KursMashq.Meta.ordering`
# — ["tartib", "id"], ya'ni ro'yxat tartibi TO'LIQ shu songa bog'liq.
#
# Avvalgi holat (blok rejimidan meros): `tartib` = kitobda BOSILGAN
# raqam. Bitta sahifa uchun bu to'g'ri, lekin butun kitob PDF'ida har
# sahifada "1, 2, 3" takrorlanadi — natijada mashqlar
# 1(s1), 1(s2), 2(s1), 2(s2)... deb ARALASHIB ko'rinardi.
#
# Yangi sxema: tartib = asos + sahifa_indeksi*100 + bosilgan_raqam.
# Shu tufayli (a) sahifalar tartibi buzilmaydi, (b) sahifa ICHIDA
# bosilgan raqam baribir ishlaydi, (c) shu tugunga ilgari qo'shilgan
# mashqlar ustidan yozilmaydi (`asos`).
SAHIFA_QADAMI = 100
# `PositiveSmallIntegerField` chegarasi. Amalda bitta tugun = bitta
# Unit'ning mashqlari, ya'ni ~325 sahifadan oshmaydi; oshib ketsa
# tartib qiymati shu yerda to'xtaydi (mashq YO'QOLMAYDI, faqat oxirgi
# sahifalar bir-biriga qo'shilib ko'rinishi mumkin).
TARTIB_MAKSIMUMI = 32767


def _tartib_asosi(tugun):
    """Tugunda ALLAQACHON bor mashqlardan keyingi "toza" yuzlik."""
    eng_katta = tugun.mashqlar.aggregate(m=Max("tartib"))["m"] or 0
    return (eng_katta // SAHIFA_QADAMI + 1) * SAHIFA_QADAMI if eng_katta else 0


def _rasm_fon_tartibi(sahifa_asosi, raqam, orin):
    """`sahifa_asosi` — asos + sahifa_indeksi*100; `raqam` — kitobda
    bosilgan raqam (bo'lmasa `orin`, sahifa ichidagi ketma-ket o'rin)."""
    try:
        ichki = int(raqam)
    except (TypeError, ValueError):
        ichki = orin
    # Bosilgan raqam yuzlikdan oshsa (masalan sahifa raqamini mashq
    # raqami deb o'qib qo'ysa) qo'shni sahifaga o'tib ketmasin.
    ichki = max(0, min(SAHIFA_QADAMI - 1, ichki))
    return min(TARTIB_MAKSIMUMI, sahifa_asosi + ichki)


class KursBlokZipYuklashView(APIView):
    """1-BOSQICH: ZIP, bitta rasm yoki PDF'ni qabul qilish va nima
    borligini sanash.

    `pk` — MASHQLAR tuguni (oxirgi qatlam).

    2026-08-05: bitta rasm yuklanganda ham xuddi ZIP kabi to'liq oqim
    (jarayon -> AI tahlil -> ...) ishlashi uchun, u xotirada BITTA
    faylli ZIP'ga o'raladi — alohida kod yo'li shart emas.

    2026-08-07: `rejim` parametri qo'shildi (`blok` yoki `rasm_fon`,
    qarang `KursZipJarayoni.Rejim`). PDF esa FAQAT `rasm_fon` rejimida
    qabul qilinadi — sababi: blok rejimida sahifa qayta qurilgani uchun
    manba PDF bo'lishining foydasi yo'q edi (2026-08-05 da shuning
    uchun olib tashlangan), rasm-fon rejimida esa aynan sahifaning
    o'zi talabaga ko'rsatiladi, PDF esa eng sifatli manba."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response(
                {"detail": "Faqat oxirgi qatlam (farzandsiz) tugunga mashq qo'shiladi"}, status=400
            )

        rejim = request.data.get("rejim") or KursZipJarayoni.Rejim.BLOK
        if rejim not in KursZipJarayoni.Rejim.values:
            return Response({"detail": "rejim noto'g'ri"}, status=400)

        fayl = request.FILES.get("zip_fayl")
        if not fayl:
            return Response({"detail": "zip_fayl majburiy"}, status=400)

        pdfmi = fayl.name.lower().endswith(".pdf")
        if pdfmi and rejim != KursZipJarayoni.Rejim.RASM_FON:
            return Response(
                {"detail": "PDF faqat rasm-fon rejimida qabul qilinadi"}, status=400
            )

        if pdfmi:
            import pypdfium2 as pdfium

            try:
                pdf_hujjat = pdfium.PdfDocument(fayl.read())
                jami = len(pdf_hujjat)
                pdf_hujjat.close()
            except Exception:  # noqa: BLE001 — buzuq/parolli PDF
                return Response({"detail": "Fayl yaroqli PDF emas"}, status=400)
            if jami == 0:
                return Response({"detail": "PDF'da sahifa topilmadi"}, status=400)
            sahifalar = [f"sahifa-{i + 1}.jpg" for i in range(jami)]
            manba_turi = KursZipJarayoni.ManbaTuri.PDF
        else:
            if kengaytma_turi(fayl.name) == "rasm":
                bufer = io.BytesIO()
                with zipfile.ZipFile(bufer, "w") as z:
                    _, ext = os.path.splitext(fayl.name.lower())
                    z.writestr(f"sahifa-1{ext}", fayl.read())
                bufer.seek(0)
                fayl = ContentFile(bufer.read(), name="rasm.zip")

            try:
                nomlar = zipfile.ZipFile(fayl).namelist()
            except zipfile.BadZipFile:
                return Response({"detail": "Fayl yaroqli ZIP, rasm yoki PDF emas"}, status=400)
            sahifalar = _zip_ichidagi_rasmlarni_ajrat(nomlar)
            if not sahifalar:
                return Response({"detail": "ZIP ichida rasm fayli topilmadi"}, status=400)
            manba_turi = KursZipJarayoni.ManbaTuri.ZIP

        fayl.seek(0)
        jarayon = KursZipJarayoni.objects.create(
            tugun=tugun,
            zip_fayl=fayl,
            manba_turi=manba_turi,
            rejim=rejim,
            jami_sahifa=len(sahifalar),
            natijalar={
                "sahifalar": sahifalar,
                # 2026-08-07, RASM_FON: mashq `tartib`ining boshlang'ich
                # nuqtasi SHU YERDA, bir marta hisoblanadi. Nega saqlash
                # paytida emas: rasm-fonda sahifalar PARALLEL saqlanadi
                # (blok rejimidagidek oxirida ketma-ket emas), shuning
                # uchun o'sha paytda `mashqlar.count()` o'qish poyga
                # bo'lardi — bir nechta so'rov bir xil sonni ko'rib, bir
                # xil tartib berib yuborardi. Qarang `_tartib_asosi`.
                "tartib_asosi": _tartib_asosi(tugun),
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
                "rejim": jarayon.rejim,
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
                    # 2026-08-07: "Davom ettirish" tugagach frontend nima
                    # qilishini shu belgilaydi — blokda tasdiqlash oynasi,
                    # rasm-fonda esa hech narsa (allaqachon saqlangan).
                    "rejim": jarayon.rejim,
                    # 2026-08-03: True bo'lsa tahlil tugagan, admin
                    # ko'rib-tasdiqlashi kutilmoqda (frontend "Davom
                    # ettirish" o'rniga tasdiqlash oynasini ochishi kerak).
                    "tasdiq_kutilmoqda": jarayon.holat == KursZipJarayoni.Holat.TASDIQ_KUTILMOQDA,
                }
            }
        )

    def delete(self, request, pk):
        """2026-07-30 talabi: "Davom ettirish" yonidagi "Bekor qilish" —
        FAQAT tugallanmagan jarayonni (ZIP holati) o'chiradi, mashqlarga
        ASLO tegmaydi (bu "Tozalash"dan MUSTAQIL, alohida amal — admin
        ikkalasini aniq ajratgan). Shu tufayli allaqachon tugallangan
        sahifalardan yaratilgan mashqlar (agar bo'lsa) saqlanib qoladi."""
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        # 2026-08-03: keshni o'chirishdan OLDIN tozalaymiz — aks holda
        # vaqtinchalik mahalliy nusxa (`_jarayon_kesh_yoli`) doim qoladi
        # (avval faqat MUVAFFAQIYATLI yakunlangandagina tozalanardi).
        # Haqiqiy xavf: SQLite'da (rivojlanish muhitida) o'chirilgan
        # jarayon ID'si keyinroq QAYTA ishlatilishi mumkin — shu holda
        # yangi jarayon eski (butunlay boshqa fayl) keshini "topib",
        # noto'g'ri ma'lumot bilan ishlab ketishi mumkin edi (2026-08-03,
        # xuddi shu xato sinovda amalda kuzatildi).
        jarayonlar = list(
            KursZipJarayoni.objects.filter(tugun_id=pk).exclude(holat=KursZipJarayoni.Holat.TUGADI)
        )
        for j in jarayonlar:
            _jarayon_keshini_tozala(j)
        soni = len(jarayonlar)
        KursZipJarayoni.objects.filter(pk__in=[j.pk for j in jarayonlar]).delete()
        return Response({"bekor_qilindi": soni})


class KursMashqRasmdanQoshishView(APIView):
    """2026-07-30 talabi: ZIP shart emas — admin "Mashq qo'shish" tugmasi
    orqali BITTA rasm tanlaydi, shu rasmdan BITTA mashq yaratiladi (bir
    martalik, sinxron so'rov — ZIP'dagi ko'p-bosqichli jarayon shart
    emas, chunki bitta AI chaqiruvi ~1 daqiqadan oshmaydi).

    Aniq javobli bo'sh joy uchun AI javobni bilmasa ham (bu yerda alohida
    javob-kaliti sahifasi yo'q) savol baribir yaratiladi (`togri` bo'sh)
    — admin keyin mavjud "Javoblarni tahrirlash" panelida to'ldiradi
    (qarang: `blok_generatsiya.bloklarni_tayyorla`)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        tugun = get_object_or_404(KursTugun, pk=pk)
        if tugun.children.exists():
            return Response(
                {"detail": "Faqat oxirgi qatlam (farzandsiz) tugunga mashq qo'shiladi"}, status=400
            )
        rasm = request.FILES.get("rasm")
        if not rasm:
            return Response({"detail": "rasm majburiy"}, status=400)
        rasm_bytes = rasm.read()

        natija_yoki_xato = _rasmni_mashqqa_aylantir(rasm_bytes)
        if isinstance(natija_yoki_xato, Response):
            return natija_yoki_xato
        mashqlar_data, qutilar, sozlar = natija_yoki_xato
        sozlar_soni = _sozlarni_saqla(tugun, sozlar)

        # Sof Wordlist sahifasi (mashq elementi yo'q, faqat so'zlar) — bo'sh
        # KursMashq yaratmaymiz, faqat so'zlar Vocabulary'ga qo'shiladi.
        if not mashqlar_data:
            return Response({"yaratilgan_mashqlar": 0, "wordlist_soni": sozlar_soni}, status=201)

        boshlangich = tugun.mashqlar.count()
        yaratilgan_soni, rasm_soni, savol_soni, javob_talab_soni = 0, 0, 0, 0
        for i, mashq_data in enumerate(mashqlar_data, start=1):
            tartib = _mashq_tartibini_aniqla(mashq_data["raqam"], boshlangich + i)
            mashq, r_soni = _mashqni_saqla(tugun, tartib, mashq_data, rasm_bytes, qutilar)
            yaratilgan_soni += 1
            rasm_soni += r_soni
            savol_soni += len(mashq_data["savollar"])
            javob_talab_soni += sum(1 for s in mashq_data["savollar"] if not s.get("togri"))

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{tugun.nomi} (rasmdan mashq qo'shildi)",
            snapshot={
                "mashqlar_soni": yaratilgan_soni, "savollar_soni": savol_soni,
                "rasm_soni": rasm_soni, "wordlist_soni": sozlar_soni,
            },
        )
        return Response(
            {
                "yaratilgan_mashqlar": yaratilgan_soni,
                "javob_talab_qiluvchi_soni": javob_talab_soni,
                "wordlist_soni": sozlar_soni,
            },
            status=201,
        )


def _sozlarni_saqla(mashq_tugun, sozlar):
    """AI aniqlagan Wordlist so'zlarini (2026-08-03, foydalanuvchi talabi:
    "wordlistdagi so'zlar vocabulary'ga o'tishi kerak") shu Unit'ning
    "vocabulary" bo'limiga qo'shadi — mavjudlarga QO'SHILADI (append),
    `KursUnitYuklashView`dagi qo'lda "wordlist" bilan bir xil qoida.

    `mashq_tugun` — mashqlar (oxirgi qatlam) tuguni, uning ota-tuguni
    (kitob — Student's Book/Workbook) ostida "vocabulary" birodar tugun
    bor deb kutiladi (`unit_qurish.UNIT_BOLIMLARI`). Topilmasa (masalan
    eski/qattiq tuzilmadagi bo'lim) — jimgina o'tkazib yuboriladi, xato
    chiqarilmaydi (Wordlist so'zlari ixtiyoriy qo'shimcha, asosiy mashq
    saqlanishini to'sib qo'ymasligi kerak)."""
    if not sozlar:
        return 0
    bolalar = _unit_bolimlari(mashq_tugun.parent) if mashq_tugun.parent_id else {}
    vocab_tugun = bolalar.get("vocabulary")
    if not vocab_tugun:
        return 0
    boshlangich = vocab_tugun.sozlar.count()
    yangilar = [
        KursSoz(tugun=vocab_tugun, tartib=boshlangich + i, en=s["en"], uz=s["uz"])
        for i, s in enumerate(sozlar, start=1)
        if s.get("en") and s.get("uz")
    ]
    if yangilar:
        KursSoz.objects.bulk_create(yangilar)
    return len(yangilar)


def _rasmni_mashqqa_aylantir(rasm_bytes):
    """`KursMashqRasmdanQoshishView` va `KursMashqQaytaYuklashView`
    ikkalasida ham bir xil AI-chaqiruv+xatolarni ushlash mantig'i —
    muvaffaqiyat bo'lsa (mashqlar, qutilar, sozlar) qaytaradi, xato
    bo'lsa tayyor `Response` obyektini qaytaradi (chaqiruvchi shuni
    to'g'ridan-to'g'ri qaytarishi kifoya).

    2026-08-03: `mashqlar` endi RO'YXAT — bitta sahifada bir nechta
    alohida (kitobda bosilgan raqami bilan) mashq bo'lishi mumkin,
    avvalgi versiyada hammasi bittaga qo'shilib ketardi (foydalanuvchi
    talabi: "har bir sahifada bir nechta mashq bo'lishi mumkin")."""
    try:
        provider = blok_provider_olish()
        natija, xato = sahifani_bloklarga_ajrat(provider, rasm_bytes)
    except ProviderXatosi as e:
        return Response({"detail": str(e)}, status=502)
    except Exception as e:  # noqa: BLE001 — kutilmagan AI/rasm xatosi
        return Response({"detail": f"{type(e).__name__}: {e}"}, status=502)
    if xato:
        return Response({"detail": xato}, status=400)

    elementlar = natija.get("elementlar") or []
    sozlar = natija.get("sozlar") or []
    if not elementlar and not sozlar:
        return Response({"detail": "Rasmdan mashq elementi topilmadi"}, status=400)
    mashqlar, qutilar = bloklarni_tayyorla(elementlar)
    return mashqlar, qutilar, sozlar


def _rasm_fon_sahifasini_saqla(tugun, sahifa_bytes, sahifa_asosi):
    """RASM-FON rejimi (2026-08-07): sahifani AI orqali mashqlarga
    ajratib, HAR BIRINI DARHOL bazaga yozadi (tasdiqlash bosqichi yo'q —
    foydalanuvchi qarori: "darhol saqlasin, lekin tahrirlash imkoni
    bo'lsin").

    Blok rejimidagi `_mashqni_saqla`dan farqi:
      * `bloklar` BO'SH qoldiriladi — frontend (`Kurslar.jsx:931`)
        aynan shu bo'yicha rasm-fon ko'rinishini tanlaydi (mavjud
        mantiq, o'zgartirilmagan);
      * sahifadan TIG'IZ surat qutilari emas, KATTA MASHQ HUDUDI
        kesiladi va `KursMashq.rasm`ga (fon) yoziladi;
      * savollar `pozitsiya` bilan keladi — input'lar shu fon ustiga
        qo'yiladi.

    `sahifa_asosi` — shu sahifaning tartib "yuzligi" (qarang
    `_rasm_fon_tartibi`); chaqiruvchi hisoblaydi, chunki sahifalar
    PARALLEL saqlanadi va bu yerda bazadan sanash poyga bo'lardi.

    Qaytaradi: (yaratilgan_mashqlar, savollar_soni, xato)."""
    try:
        provider = blok_provider_olish()
        mashqlar, xato = sahifani_rasm_fonga_ajrat(provider, sahifa_bytes)
    except ProviderXatosi as e:
        return 0, 0, str(e)
    except Exception as e:  # noqa: BLE001 — kutilmagan AI/rasm xatosi
        return 0, 0, f"{type(e).__name__}: {e}"
    if xato:
        return 0, 0, xato

    yaratilgan, savol_soni = 0, 0
    for i, m in enumerate(mashqlar, start=1):
        kesilgan = rasmni_kes(sahifa_bytes, m["quti"])
        if not kesilgan:
            continue  # hudud juda kichik/buzuq — bu mashq tashlanadi
        mashq = KursMashq.objects.create(
            tugun=tugun,
            tartib=_rasm_fon_tartibi(sahifa_asosi, m["raqam"], i),
            matn=m["sarlavha"] or "",
            savollar=m["savollar"],
            bloklar=[],
            audio_kerak=bool(m.get("audio_kerak")),
        )
        mashq.rasm.save(f"{mashq.id}_fon.jpg", ContentFile(kesilgan), save=True)
        yaratilgan += 1
        savol_soni += len(m["savollar"])
    return yaratilgan, savol_soni, None


def _mashqni_saqla(tugun, tartib, mashq_data, rasm_bytes, qutilar):
    """Bitta mashq guruhini (`bloklarni_tayyorla` natijasidan) haqiqiy
    `KursMashq` + kesilgan `KursMashqRasmi`larga aylantiradi (2026-08-03).

    Rasm indekslari bu guruhda HALI GLOBAL (butun sahifa bo'yicha) —
    `rasm_idxlarni_lokallashtir` ularni shu MASHQGA XOS lokal (0dan
    boshlanadigan) indeksga o'tkazadi, aks holda admin/talaba
    ko'rinishida (`blok.rasm_idx` -> `mashq.rasmlar[idx]`) boshqa
    mashqning surati chiqib qolishi mumkin edi."""
    bloklar = mashq_data["bloklar"]
    global_idxlar = rasm_idxlarni_lokallashtir(bloklar)
    mashq = KursMashq.objects.create(
        tugun=tugun,
        tartib=tartib,
        matn=mashq_data["sarlavha"] or "",
        savollar=mashq_data["savollar"],
        bloklar=bloklar,
        audio_kerak=bool(mashq_data.get("audio_kerak")),
    )
    rasm_soni = 0
    for lokal_idx, global_idx in enumerate(global_idxlar):
        kesilgan = rasmni_kes(rasm_bytes, qutilar[global_idx])
        if not kesilgan:
            continue
        yozuv = KursMashqRasmi(mashq=mashq, tartib=lokal_idx)
        yozuv.rasm.save(f"{mashq.id}_{lokal_idx}.jpg", ContentFile(kesilgan), save=True)
        rasm_soni += 1
    return mashq, rasm_soni


def _mashq_tartibini_aniqla(raqam, boshlangich):
    """Kitobda bosilgan raqamning O'ZI `tartib` sifatida ishlatiladi
    (2026-08-03 talabi: "mashq raqamini mashqning o'zidan olsin") —
    raqam yo'q/parse qilinmasa, ketma-ket (`boshlangich`dan) tushadi."""
    try:
        return int(raqam)
    except (TypeError, ValueError):
        return boshlangich


class KursMashqQaytaYuklashView(APIView):
    """2026-07-30 talabi: mavjud mashqni YANGI rasm bilan ALMASHTIRADI —
    "Rasm orqali mashq qo'shish" bilan bir xil AI tahlili, lekin YANGI
    mashq yaratish o'rniga MAVJUD mashqning bloklari/savollari/kesilgan
    suratlari almashtiriladi (id/tartib — ro'yxatdagi o'rni — o'zgarmaydi).

    2026-08-03: yangi rasm/sahifa BIR NECHTA mashq elementiga ega bo'lsa
    (masalan tuzatilgan rasm avval bittaga qo'shilib ketgan 2 mashqni
    endi to'g'ri ajratsa) — BIRINCHISI mavjud `mashq`ni almashtiradi,
    QOLGANLARI esa yangi alohida `KursMashq` sifatida QO'SHILADI (hech
    narsa yo'qolib qolmasin)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        mashq = get_object_or_404(KursMashq, pk=pk)
        rasm = request.FILES.get("rasm")
        if not rasm:
            return Response({"detail": "rasm majburiy"}, status=400)
        rasm_bytes = rasm.read()

        natija_yoki_xato = _rasmni_mashqqa_aylantir(rasm_bytes)
        if isinstance(natija_yoki_xato, Response):
            return natija_yoki_xato
        mashqlar_data, qutilar, sozlar = natija_yoki_xato
        sozlar_soni = _sozlarni_saqla(mashq.tugun, sozlar)

        if not mashqlar_data:
            return Response({"detail": "Rasmdan mashq elementi topilmadi"}, status=400)

        birinchi, qolganlar = mashqlar_data[0], mashqlar_data[1:]
        bloklar = birinchi["bloklar"]
        global_idxlar = rasm_idxlarni_lokallashtir(bloklar)

        mashq.matn = birinchi["sarlavha"] or ""
        mashq.savollar = birinchi["savollar"]
        mashq.bloklar = bloklar
        mashq.save(update_fields=["matn", "savollar", "bloklar"])

        mashq.rasmlar.all().delete()  # eski kesilgan suratlar — yangi rasmga mos emas
        rasm_soni = 0
        for lokal_idx, global_idx in enumerate(global_idxlar):
            kesilgan = rasmni_kes(rasm_bytes, qutilar[global_idx])
            if not kesilgan:
                continue
            yozuv = KursMashqRasmi(mashq=mashq, tartib=lokal_idx)
            yozuv.rasm.save(f"{mashq.id}_{lokal_idx}.jpg", ContentFile(kesilgan), save=True)
            rasm_soni += 1

        savol_soni = len(birinchi["savollar"])
        qoshimcha_mashqlar = 0
        boshlangich = mashq.tugun.mashqlar.count()
        for i, mashq_data in enumerate(qolganlar, start=1):
            tartib = _mashq_tartibini_aniqla(mashq_data["raqam"], boshlangich + i)
            _, r_soni = _mashqni_saqla(mashq.tugun, tartib, mashq_data, rasm_bytes, qutilar)
            qoshimcha_mashqlar += 1
            rasm_soni += r_soni
            savol_soni += len(mashq_data["savollar"])

        javob_talab_soni = sum(1 for s in birinchi["savollar"] if not s.get("togri"))
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=mashq.tugun,
            obyekt_turi="KursTugun",
            obyekt_nomi=f"{mashq.tugun.nomi} (#{mashq.tartib} mashq qayta yuklandi)",
            snapshot={
                "savollar_soni": savol_soni, "rasm_soni": rasm_soni,
                "wordlist_soni": sozlar_soni, "qoshimcha_mashqlar": qoshimcha_mashqlar,
            },
        )
        return Response(
            {
                **_kurs_mashq_admin_dict(mashq),
                "javob_talab_qiluvchi_soni": javob_talab_soni,
                "wordlist_soni": sozlar_soni,
                "qoshimcha_mashqlar": qoshimcha_mashqlar,
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
            jami = len(oddiy)
            band_vaqtlari = _band_vaqtlarini_ol(d)
            band = {int(k) for k in band_vaqtlari}
            indeks = next((i for i in range(jami) if i not in band), None)

            if indeks is None:
                # Barcha sahifa band qilingan. Lekin hali TUGALLANMAGAN
                # (ishlangan_sahifa < jami_sahifa) bo'lsa — bu ikki xil
                # holat bo'lishi mumkin: (a) boshqa parallel so'rovlar
                # HOZIR ishlab turibdi (normal, tez orada tugaydi), yoki
                # (b) qaysidir sahifa band qilingan-u ABADIY tugallanmay
                # qolgan ("muzlab qolgan"). Ikkinchisini VAQT bo'yicha
                # ajratamiz.
                tugallangan_indekslar = {int(k) for k in d.get("tugallangan", {})}
                hozir = timezone.now()
                tiqilib_qolgan = []
                for idx_str, vaqt_str in band_vaqtlari.items():
                    idx = int(idx_str)
                    if idx in tugallangan_indekslar:
                        continue
                    try:
                        vaqt = datetime.fromisoformat(vaqt_str)
                    except (TypeError, ValueError):
                        vaqt = hozir - timedelta(days=1)
                    if (hozir - vaqt).total_seconds() > TIQILIB_QOLISH_CHEGARASI_SONIYA:
                        tiqilib_qolgan.append(idx)

                if tiqilib_qolgan and jarayon.ishlangan_sahifa < jarayon.jami_sahifa:
                    # Jarayonni O'CHIRAMIZ — aks holda "Davom ettirish"
                    # tugmasi abadiy turib qolardi (Tozalash tugmasi
                    # jarayon holatiga tegmaydi, faqat mashq kontentini
                    # tozalaydi). ZIP faylning o'zi R2'da xavfsiz qoladi,
                    # kerak bo'lsa admin ZIPni qaytadan yuklaydi.
                    tiqilgan_fayllar = [
                        oddiy[idx].rsplit("/", 1)[-1] for idx in sorted(tiqilib_qolgan)
                    ]
                    _jarayon_keshini_tozala(jarayon)  # 2026-08-03: pastdagi izohga qarang
                    jarayon.delete()
                    return Response(
                        {
                            "detail": (
                                f"Yuklash tiqilib qoldi: {len(tiqilib_qolgan)} ta sahifa "
                                f"({', '.join(tiqilgan_fayllar)}) band qilingan edi, lekin "
                                f"{TIQILIB_QOLISH_CHEGARASI_SONIYA} soniyadan ko'proq "
                                "tugallanmadi (server qayta ishga tushishi yoki AI xatosi "
                                "sabab bo'lishi mumkin). Jarayon bekor qilindi — Unit "
                                "kontentini tozalab, ZIPni qaytadan yuklang."
                            ),
                        },
                        status=409,
                    )

                # Boshqa parallel so'rov(lar) HOZIR ishlab turibdi — bu
                # normal holat, xato emas: bu "ishchi" uchun hozircha
                # ish qolmadi.
                return Response(
                    {
                        "band_qilinadigan_sahifa_qolmadi": True,
                        "ishlangan_sahifa": jarayon.ishlangan_sahifa,
                        "jami_sahifa": jarayon.jami_sahifa,
                        "tugadimi": jarayon.ishlangan_sahifa >= jarayon.jami_sahifa,
                    }
                )

            # Eski (bu maydon qo'shilishidan oldingi) jarayonlarda yo'q.
            tartib_asosi = d.get("tartib_asosi") or 0
            band_vaqtlari[str(indeks)] = timezone.now().isoformat()
            d["band_qilingan"] = band_vaqtlari
            jarayon.natijalar = d
            jarayon.holat = KursZipJarayoni.Holat.ISHLANMOQDA
            jarayon.save(update_fields=["natijalar", "holat"])

        # 2) UZOQ AI ishi — DB QULFISIZ (bir necha daqiqagacha cho'zilishi
        #    mumkin; qulf ushlab turilsa boshqa parallel so'rovlar
        #    tiqilib qolardi va konkurentlikdan foyda bo'lmasdi).
        #
        # MUHIM (2026-07-29 tuzatildi): shu blokda ISTALGAN kutilmagan
        # xato (tarmoq, provider, ZIP o'qish va h.k.) ATAYLAB ushlanadi
        # va pastdagi 3-bosqichga "xato" sifatida yetkaziladi. Aks holda
        # bu yerda chiqqan xato TUTILMASA, band qilingan `indeks` HECH
        # QACHON `tugallangan`ga yozilmasdi — u abadiy "band" holatida
        # qolib ketardi (chunki band qilish faqat `band_qilingan`ga
        # qaraydi), va jarayon HECH QACHON 100%ga yetmasdi. Frontend esa
        # xato qaytgan so'rovni qayta urinib, HAR SAFAR YANGI sahifani
        # band qilib, eskisini abadiy tashlab ketardi — production'da
        # aynan shu sabab bilan yuklash sekinlashib/tiqilib qolgan edi
        # (2026-07-29, foydalanuvchi kuzatgan haqiqiy holat).
        nom = oddiy[indeks]
        # 2026-07-30: "🖼️ Rasm orqali mashq qo'shish" bilan BIR XIL
        # tahlil (`_rasmni_mashqqa_aylantir`) — bloklar/savollar/rasm-
        # qutilari shu YERDA (AI chaqiruvi bilan birga) tayyorlanadi;
        # kesish (rasm-qutilarni haqiqiy rasmdan olish) esa yakunlashda
        # (`_jarayonni_yakunla`) amalga oshadi, arxiv bir marta ochilgani
        # uchun.
        rasm_fonmi = jarayon.rejim == KursZipJarayoni.Rejim.RASM_FON
        mashqlar, qutilar, sozlar, xato = None, None, None, None
        yaratilgan, savol_soni = 0, 0
        try:
            with _jarayon_arxivi(jarayon) as arxiv:
                rasm_bytes = arxiv.read(nom)
            if rasm_fonmi:
                # 2026-08-07: rasm-fon rejimida tasdiqlash bosqichi yo'q —
                # mashq DARHOL shu yerda bazaga yoziladi (qarang
                # `_rasm_fon_sahifasini_saqla`), keyinroq faqat tahrirlanadi.
                yaratilgan, savol_soni, xato = _rasm_fon_sahifasini_saqla(
                    jarayon.tugun, rasm_bytes,
                    tartib_asosi + indeks * SAHIFA_QADAMI,
                )
            else:
                natija_yoki_xato = _rasmni_mashqqa_aylantir(rasm_bytes)
                if isinstance(natija_yoki_xato, Response):
                    xato = natija_yoki_xato.data.get("detail", "AI xato qaytardi")
                else:
                    mashqlar, qutilar, sozlar = natija_yoki_xato
        except ProviderXatosi as e:
            xato = str(e)
        except Exception as e:  # noqa: BLE001 — pastdagi izohga qarang
            xato = f"{type(e).__name__}: {e}"

        # 3) Natijani ATOMIK qo'shamiz — qayta o'qib-yozamiz, boshqa
        #    parallel so'rov shu oraliqda o'ziniki yozgan bo'lishi mumkin.
        with transaction.atomic():
            jarayon = KursZipJarayoni.objects.select_for_update().get(pk=pk)
            d = jarayon.natijalar
            if rasm_fonmi:
                # Mashq allaqachon bazaga yozilgan — bu yerda faqat hisobot
                # uchun yig'ma sonlar saqlanadi (`_jarayonni_yakunla` bu
                # rejimda chaqirilmaydi).
                yozuv = {
                    "fayl": nom,
                    "yaratilgan": yaratilgan,
                    "savollar_soni": savol_soni,
                    "xato": xato,
                }
            else:
                # 2026-08-03: "mashqlar" — RO'YXAT (bitta sahifada bir nechta
                # alohida mashq bo'lishi mumkin, `bloklarni_tayyorla`ga qarang).
                yozuv = {
                    "fayl": nom,
                    "mashqlar": mashqlar,
                    "qutilar": qutilar,
                    "sozlar": sozlar,
                    "xato": xato,
                }
            d.setdefault("tugallangan", {})[str(indeks)] = yozuv
            jarayon.natijalar = d
            jarayon.ishlangan_sahifa = len(d["tugallangan"])
            jami_sahifa = jarayon.jami_sahifa
            tugadimi = jarayon.ishlangan_sahifa >= jami_sahifa
            if tugadimi:
                if rasm_fonmi:
                    # Tasdiqlash bosqichi yo'q — mashqlar allaqachon
                    # bazada, jarayon shu zahoti tugallangan hisoblanadi.
                    jarayon.holat = KursZipJarayoni.Holat.TUGADI
                else:
                    # 2026-08-03: avval shu yerda `_jarayonni_yakunla` avtomatik
                    # chaqirilib, bazaga to'g'ridan-to'g'ri yozilardi — AI
                    # xatolari (noto'g'ri kesilgan rasm, joyi surilgan bo'sh
                    # joy) tekshirilmasdan saqlanardi. Endi barcha sahifalar
                    # tahlil qilingach, TASDIQLASH kutiladi — admin
                    # `KursBlokTasdiqView`da ko'rib, kerak bo'lsa tuzatib,
                    # `KursBlokTasdiqlashView`ga yuborgandagina bazaga yoziladi.
                    jarayon.holat = KursZipJarayoni.Holat.TASDIQ_KUTILMOQDA
            jarayon.save(update_fields=["natijalar", "ishlangan_sahifa", "holat"])

        if tugadimi and rasm_fonmi:
            _jarayon_keshini_tozala(jarayon)

        javob = {
            "ishlangan_sahifa": jarayon.ishlangan_sahifa,
            "jami_sahifa": jami_sahifa,
            "joriy_fayl": nom.rsplit("/", 1)[-1],
            "xato": xato,
            "tugadimi": tugadimi,
        }
        return Response(javob)


def _jarayonni_yakunla(jarayon, foydalanuvchi, tahrirlar=None):
    """Yig'ilgan tahlillarni BAZAGA yozadi: har sahifa/rasm — BITTA
    KursMashq (bloklar+savollar allaqachon `KursBlokSahifaView`da AI
    chaqiruvi bilan birga tayyorlangan) + undan kesilgan rasmlar.

    2026-07-30: sodda ZIP oqimi — javob-kaliti, audio moslashtirish
    OLIB TASHLANDI (foydalanuvchi talabi: "ZIP ichida faqat rasmlar").
    Wordlist so'zlari esa 2026-08-03dan buyon HAR sahifadan AVTOMATIK
    (`_sozlarni_saqla`) Vocabulary'ga qo'shiladi — qo'lda
    `/api/kurslar/{pk}/unit-yuklash/` orqali kiritish endi ixtiyoriy
    qo'shimcha (masalan AI o'tkazib yuborgan so'zlar uchun).

    Natijalar `tugallangan` lug'atida SAHIFA INDEKSI kaliti bilan
    saqlangan (parallel qayta ishlash tufayli tugallanish tartibi
    original sahifa tartibiga mos kelmasligi mumkin) — shuning uchun bu
    yerda ATAYLAB indeks bo'yicha SARALAB o'qiladi, natijada yakuniy
    mashqlar tartibi har doim sahifa tartibiga mos bo'ladi.

    `tahrirlar` (2026-08-03, tasdiqlash bosqichi) — ixtiyoriy
    {indeks(str): {"mashqlar","qutilar","sozlar","otkazib_yuborilsin"}}
    — admin AI natijasini ko'rib tuzatgan bo'lsa, shu qiymatlar AI
    natijasi o'RNIGA ishlatiladi (to'liq almashtirish, chunki admin
    butun ro'yxatni qayta yuboradi — masalan bitta mashqni olib tashlash
    uchun "mashqlar"ni shu mashqsiz qayta yuboradi). `otkazib_yuborilsin`
    — sahifa umuman yaroqsiz deb topilsa, mashq yaratilmaydi."""
    tahrirlar = tahrirlar or {}
    d = jarayon.natijalar
    mashq_tugun = jarayon.tugun  # 2026-07-30: jarayon endi to'g'ridan-to'g'ri mashqlar tuguniga bog'lanadi

    tugallangan = d.get("tugallangan", {})
    tartiblangan = []
    for k in sorted(tugallangan, key=int):
        t = dict(tugallangan[k])
        tahrir = tahrirlar.get(k)
        if tahrir:
            if tahrir.get("otkazib_yuborilsin"):
                continue
            for maydon in ("mashqlar", "qutilar", "sozlar"):
                if maydon in tahrir:
                    t[maydon] = tahrir[maydon]
            t["xato"] = None  # admin tuzatib tasdiqlagan — xato bayrog'i olib tashlanadi
        tartiblangan.append(t)

    xato_sahifalar = [
        {"fayl": t["fayl"], "xato": t["xato"]} for t in tartiblangan if t["xato"]
    ]

    boshlangich = mashq_tugun.mashqlar.count()
    yaratilgan_soni, rasm_soni, savol_soni, sozlar_soni = 0, 0, 0, 0

    with _jarayon_arxivi(jarayon) as arxiv:
        for t in tartiblangan:
            if t["xato"]:
                continue
            sozlar_soni += _sozlarni_saqla(mashq_tugun, t.get("sozlar"))
            qutilar = t.get("qutilar") or []
            rasm_bytes = arxiv.read(t["fayl"]) if qutilar else None
            for mashq_data in t.get("mashqlar") or []:
                # Sof Wordlist mashqi (bloklar yo'q) — bo'sh KursMashq
                # yaratilmaydi, faqat yuqoridagi so'zlar saqlanadi.
                if not mashq_data.get("bloklar"):
                    continue
                tartib = _mashq_tartibini_aniqla(
                    mashq_data.get("raqam"), boshlangich + yaratilgan_soni + 1
                )
                mashq, r_soni = _mashqni_saqla(mashq_tugun, tartib, mashq_data, rasm_bytes, qutilar)
                savol_soni += len(mashq_data["savollar"])
                rasm_soni += r_soni
                yaratilgan_soni += 1

    jarayon.holat = KursZipJarayoni.Holat.TUGADI
    jarayon.save(update_fields=["holat"])
    _jarayon_keshini_tozala(jarayon)  # vaqtinchalik mahalliy nusxa endi kerak emas

    natija = {
        "yaratilgan_mashqlar": yaratilgan_soni,
        "kesilgan_rasmlar": rasm_soni,
        "baholanadigan_savollar": savol_soni,
        "wordlist_soni": sozlar_soni,
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


class KursBlokTasdiqView(APIView):
    """3-BOSQICH (2026-08-03): barcha sahifalar tahlil qilingach, admin
    AI natijasini (matn/savollar/rasm-quti koordinatalari) ko'rib chiqishi
    uchun to'liq ma'lumotni qaytaradi — hali bazaga yozilmagan."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        jarayon = get_object_or_404(KursZipJarayoni, pk=pk)
        if jarayon.holat != KursZipJarayoni.Holat.TASDIQ_KUTILMOQDA:
            return Response({"detail": "Jarayon tasdiqlashga tayyor emas"}, status=400)

        d = jarayon.natijalar
        tugallangan = d.get("tugallangan", {})
        sahifalar = [
            {"indeks": int(k), **tugallangan[k]}
            for k in sorted(tugallangan, key=int)
        ]
        return Response({"jarayon_id": jarayon.id, "sahifalar": sahifalar})


class KursBlokSahifaRasmiView(APIView):
    """Bitta sahifaning asl surati — tasdiqlash oynasida rasm-quti
    chegaralarini ko'rish/tuzatish uchun (2026-08-03)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk, indeks):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        jarayon = get_object_or_404(KursZipJarayoni, pk=pk)
        sahifalar = jarayon.natijalar.get("sahifalar", [])
        if indeks < 0 or indeks >= len(sahifalar):
            return Response({"detail": "Sahifa topilmadi"}, status=404)
        with _jarayon_arxivi(jarayon) as arxiv:
            rasm_bytes = arxiv.read(sahifalar[indeks])
        return HttpResponse(rasm_bytes, content_type="image/jpeg")


class KursBlokTasdiqlashView(APIView):
    """4-BOSQICH (2026-08-03): admin ko'rib chiqgan (kerak bo'lsa
    tuzatgan) natijani YAKUNIY deb tasdiqlaydi — shundagina rasm kesish
    va `KursMashq` yaratish (`_jarayonni_yakunla`) amalga oshadi.

    Body: {"tahrirlar": {indeks(str): {mashqlar?, qutilar?, sozlar?,
    otkazib_yuborilsin?}}} — faqat ADMIN o'zgartirgan sahifalar uchun
    kalit yuboriladi, qolganlari AI natijasi bilan ishlatiladi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _mashq_admin_mi(request.user):
            return Response({"detail": "Faqat admin/owner uchun"}, status=403)
        jarayon = get_object_or_404(KursZipJarayoni, pk=pk)
        if jarayon.holat != KursZipJarayoni.Holat.TASDIQ_KUTILMOQDA:
            return Response({"detail": "Jarayon tasdiqlashga tayyor emas"}, status=400)

        tahrirlar = request.data.get("tahrirlar") or {}
        natija = _jarayonni_yakunla(jarayon, request.user, tahrirlar=tahrirlar)
        return Response(natija)
