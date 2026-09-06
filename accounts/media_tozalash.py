"""Ishlatilmayotgan (yetim) media fayllarni topish va o'chirish
(2026-09-07, foydalanuvchi talabi: "R2 da turgan medialarning qaysi
biriga hech qanday link bo'lmasa, shu mediani o'chirib tashlash kerak").

Nega kerak: bir xil fayl qayta-qayta import qilinganda Django yangi
nusxa yaratadi (`Test_2_zM6RJZA`, `Test_2_zM6RJZA_73CtjFx`), eskisi esa
bazada havolasiz qoladi. Lokal o'lchovda 4033 MB mediadan 3129 MB
(1430 fayl) aynan shunday yetim fayllar edi.

Django'ning storage API'si orqali ishlaydi — lokal diskda ham, R2'da
ham bir xil kod. `default_storage` qaysi backend bo'lsa, o'shani
ishlatadi.

XAVFSIZLIK — uch qatlam:

1. `HIMOYA_SOAT` — shu vaqtdan yangi fayllarga TEGILMAYDI. Sabab:
   fayl yuklanib bo'lgan, lekin baza yozuvi hali saqlanmagan lahzada u
   "yetim" bo'lib ko'rinadi. 24 soat — foydalanuvchi tanlovi.
2. `CHETLAB_OTILADIGAN` — davom etayotgan jarayonlarning ish papkalari.
3. Ikki bosqich: avval `yetimlarni_top()` ro'yxat beradi, o'chirish
   ALOHIDA chaqiruv bilan bo'ladi (view darajasida GET/POST).
"""

import datetime

from django.apps import apps
from django.core.files.storage import default_storage
from django.db.models import FileField
from django.utils import timezone

# Shu vaqtdan yangi fayllar hech qachon o'chirilmaydi.
HIMOYA_SOAT = 24

# Davom etayotgan yuklash jarayonlarining ish fayllari — ular bazada
# havola qilinmasligi mumkin, lekin jarayon ularga tayanadi.
CHETLAB_OTILADIGAN = ("kurslar/zip_jarayon", "tmp_blok_jarayon")


def _havola_qilingan_nomlar():
    """Bazadagi BARCHA `FileField`/`ImageField` qiymatlari.

    Modellar ro'yxati qattiq kodlanmagan — `apps.get_models()` orqali
    olinadi, ya'ni yangi model qo'shilsa avtomatik hisobga olinadi.
    Bu MUHIM: ro'yxatni qo'lda yuritsak, unutilgan model fayllari
    "yetim" deb o'chib ketardi."""
    nomlar = set()
    for model in apps.get_models():
        maydonlar = [f for f in model._meta.get_fields() if isinstance(f, FileField)]
        if not maydonlar:
            continue
        for qator in model.objects.values_list(*[f.name for f in maydonlar]).iterator():
            nomlar.update(str(x) for x in qator if x)
    return nomlar


def _vaqtni_moslash(vaqt):
    if vaqt is not None and timezone.is_naive(vaqt):
        return timezone.make_aware(vaqt, timezone.get_default_timezone())
    return vaqt


def _s3_royxat():
    """S3/R2 uchun TEZKOR yo'l: nom, hajm va sana BITTA so'rovda.

    Nega kerak: `Storage.listdir()` faqat nomlarni qaytaradi, hajm va
    sana uchun esa har fayl bo'yicha alohida so'rov ketardi — 3356
    faylda ~6700 tarmoq murojaati (sekin va pullik). `list_objects`
    sahifalash esa hammasini birdan beradi.

    Qo'shimcha foyda: ro'yxat BIR LAHZADAGI holat, ya'ni skanerlash
    davomida o'zgargan fayl chalkashtirmaydi.

    S3 emas bo'lsa `None` qaytaradi — chaqiruvchi umumiy yo'lga o'tadi."""
    ombor = getattr(default_storage, "bucket", None)
    if ombor is None:
        return None
    try:
        natija = {}
        for obj in ombor.objects.all():
            # `location` sozlangan bo'lsa kalitlar shu prefiks bilan
            # keladi — uni olib tashlaymiz, chunki bazadagi nomlar
            # prefikssiz saqlanadi.
            kalit = obj.key
            joy = (getattr(default_storage, "location", "") or "").strip("/")
            if joy and kalit.startswith(joy + "/"):
                kalit = kalit[len(joy) + 1:]
            if kalit.endswith("/"):
                continue  # papka belgisi
            natija[kalit] = (obj.size, _vaqtni_moslash(obj.last_modified))
        return natija
    except Exception:
        # Har qanday muammoda (huquq, tarmoq, SDK farqi) umumiy yo'lga
        # tushamiz — sekin, lekin ishlaydi.
        return None


def _saqlangan_fayllar(yol=""):
    """Storage'dagi barcha fayllar (rekursiv, nisbiy nom bilan)."""
    try:
        papkalar, fayllar = default_storage.listdir(yol)
    except (FileNotFoundError, OSError, NotImplementedError):
        return
    for f in fayllar:
        yield f"{yol}/{f}" if yol else f
    for p in papkalar:
        yield from _saqlangan_fayllar(f"{yol}/{p}" if yol else p)


def _malumot(nom):
    """Bitta faylning (hajm, sana) juftligi — sekin yo'l."""
    try:
        hajm = default_storage.size(nom)
    except (FileNotFoundError, OSError):
        hajm = 0
    try:
        vaqt = _vaqtni_moslash(default_storage.get_modified_time(nom))
    except (FileNotFoundError, OSError, NotImplementedError, AttributeError):
        vaqt = None
    return hajm, vaqt


def yetimlarni_top(himoya_soat=HIMOYA_SOAT):
    """Havolasiz fayllar ro'yxati.

    Qaytaradi: `{"fayllar": [...], "jami_hajm": int, "papkalar": {...},
                 "himoyalangan": int, "chetlab_otilgan": int}`
    """
    havolalar = _havola_qilingan_nomlar()
    chegara = timezone.now() - datetime.timedelta(hours=himoya_soat)
    keshlangan = _s3_royxat()  # S3/R2 bo'lsa — bitta so'rovdagi to'liq ro'yxat

    fayllar = []
    jami_hajm = 0
    papkalar = {}
    himoyalangan = chetlab_otilgan = 0

    barchasi = keshlangan.keys() if keshlangan is not None else _saqlangan_fayllar()
    for nom in barchasi:
        if nom in havolalar:
            continue
        if nom.startswith(CHETLAB_OTILADIGAN):
            chetlab_otilgan += 1
            continue
        hajm, vaqt = keshlangan[nom] if keshlangan is not None else _malumot(nom)
        # Vaqt noma'lum bo'lsa fayl YANGI deb hisoblanadi va tegilmaydi.
        # Ehtiyotkorlik ataylab: noaniqlik o'chirish foydasiga hal
        # qilinmasligi kerak.
        if vaqt is None or vaqt > chegara:
            himoyalangan += 1
            continue
        fayllar.append(nom)
        jami_hajm += hajm
        papka = nom.rsplit("/", 1)[0] if "/" in nom else "(ildiz)"
        joriy = papkalar.setdefault(papka, {"soni": 0, "hajm": 0})
        joriy["soni"] += 1
        joriy["hajm"] += hajm

    return {
        "fayllar": fayllar,
        "jami_hajm": jami_hajm,
        "papkalar": papkalar,
        "himoyalangan": himoyalangan,
        "chetlab_otilgan": chetlab_otilgan,
    }


def yetimlarni_ochir(fayllar):
    """Berilgan fayllarni o'chiradi.

    Ro'yxat CHAQIRUVCHIDAN keladi (ya'ni foydalanuvchi ko'rgan
    ro'yxat), qaytadan skanerlanmaydi — skanerlash bilan o'chirish
    o'rtasida yangi fayl paydo bo'lsa, u tasodifan o'chib ketmasin.

    Har fayl o'chirilishidan OLDIN yana bir marta havola tekshiriladi:
    ro'yxat olingandan keyin fayl bazaga biriktirilgan bo'lishi mumkin
    (masalan admin shu orada import qilgan)."""
    havolalar = _havola_qilingan_nomlar()
    ochirildi = 0
    ozod_hajm = 0
    otkazildi = 0
    xatolar = []

    for nom in fayllar:
        if nom in havolalar or nom.startswith(CHETLAB_OTILADIGAN):
            otkazildi += 1
            continue
        try:
            hajm = default_storage.size(nom)
        except (FileNotFoundError, OSError):
            hajm = 0
        try:
            default_storage.delete(nom)
            ochirildi += 1
            ozod_hajm += hajm
        except (OSError, NotImplementedError) as e:
            xatolar.append(f"{nom}: {e}")

    return {
        "ochirildi": ochirildi,
        "ozod_hajm": ozod_hajm,
        "otkazildi": otkazildi,
        "xatolar": xatolar[:20],
    }
