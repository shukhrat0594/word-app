"""Qurilma limiti (2026-10-20, Shuhrat qarori — "B variant").

Qurilma IKKI narsa bilan taniladi:
  1. Brauzer ID'si — frontend uni birinchi ochilishda o'zi yasaydi, brauzer
     xotirasiga (localStorage) yozadi va har login bilan yuboradi. Brauzer
     tarixi / sayt ma'lumotlari tozalansa — o'chadi.
  2. Brauzer belgilari — har login'da qurilmaning O'ZIDAN o'qiladi (Android
     modeli, ekran, video karta, yadrolar, xotira, vaqt mintaqasi), shuning
     uchun tozalash ularga ta'sir qilmaydi. ID ro'yxatda yo'q va limit to'lgan
     bo'lsa — belgilar ro'yxatdagi qurilmalardan AYNAN BITTASIGA mos kelsa, bu
     o'sha qurilma deb hisoblanadi: jim kiritiladi, eski brauzer seansi yopiladi.

Cheklov (Shuhrat bilib turib qabul qilgan): bir xil modeldagi ikki telefon
belgilarda deyarli farqlanmaydi — do'sti xuddi shunday telefondan kirsa,
o'quvchining o'zi chiqib ketadi (bir vaqtda ikkalasi emas). Bu jurnalda
"avtomatik tanildi" bo'lib ko'rinadi.

Server cookie (2026-10-02, 737d127) OLIB TASHLANDI: prodda sayt va API ikki
xil saytda (`up.railway.app` umumiy suffiks), brauzer cookie'ni hech qachon
saqlamagan.

Ishga tushishi (Shuhrat, 2026-10-22): mavjud qurilmalar HAMMASI o'chiriladi
(migratsiya 0029), limitlar o'z holicha qoladi; qurilma belgisi (`qid`) yo'q
eski kalitlar qabul qilinmaydi — hamma bir marta qayta kiradi va birinchi
kirgan qurilmasi 1-qurilma bo'ladi.

Kelajak (Shuhrat, 2026-10-20): mobil ilova bo'lganda — qurilmaning o'z ID'si;
Telegram mini-ilova bo'lganda — Telegram DeviceStorage.
"""

import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Bildirishnoma, QurilmaSorovi, User

# Shuncha kun kirilmagan qurilma ro'yxatdan o'zi chiqadi — yo'qolgan/sotilgan
# telefon joyni band qilib turmasin.
ESKIRISH_KUNI = 60
# Rad etilgan qurilma shuncha vaqtdan keyin yana so'rov yubora oladi.
RAD_AMAL_QILADI = timedelta(hours=24)
# Refresh paytida qurilmaning "oxirgi" vaqti shundan tez-tez yozilmaydi.
FAOLLIK_ORALIGI = timedelta(hours=1)

_ID_NAMUNA = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def id_tozala(xom):
    """Kelgan brauzer ID'si: faqat harf/raqam/chiziqcha, 1-64 belgi. Yaroqsiz — ''."""
    xom = xom.strip() if isinstance(xom, str) else ""
    return xom if _ID_NAMUNA.match(xom) else ""


# ── Belgilar ──────────────────────────────────────────────────────────

_MATN_KALITLAR = {"model": 60, "gpu": 200, "vaqt": 60}
_SON_KALITLAR = ("yadro", "xotira", "teginish", "dpr")

_BRAUZERLAR = (
    ("Telegram", re.compile(r"Telegram")),
    ("Instagram", re.compile(r"Instagram")),
    ("Yandex", re.compile(r"YaBrowser|YaApp")),
    ("Samsung Internet", re.compile(r"SamsungBrowser")),
    ("Opera", re.compile(r"OPR/|Opera")),
    ("Edge", re.compile(r"Edg/|EdgA/|EdgiOS/")),
    ("Firefox", re.compile(r"Firefox/|FxiOS/")),
    ("Chrome", re.compile(r"CriOS/|Chrome/")),
    ("Safari", re.compile(r"Safari/")),
)
# "Linux; Android 13; SM-A525F Build/TP1A...; wv)" yoki "Android 14; SAMSUNG SM-S918B)"
_ANDROID_MODEL = re.compile(r"Android [\d.]+; (?:[a-z]{2}[-_][A-Za-z]{2}; )?([^;)]+?)(?: Build/[^;)]+)?[;)]")
# Chrome 110+ modelni yashiradi ("Android 10; K") — haqiqiy model frontend'dan keladi.
_SOXTA_MODELLAR = {"K", "Mobile", "Tablet"}


def ua_tahlil(ua):
    """User-Agent'dan (tizim, brauzer, model). Topilmagani — ''."""
    ua = ua or ""
    if "Windows" in ua:
        tizim = "Windows"
    elif "iPhone" in ua:
        tizim = "iOS"
    elif "iPad" in ua:
        tizim = "iPadOS"
    elif "Android" in ua:
        tizim = "Android"
    elif "Macintosh" in ua or "Mac OS X" in ua:
        tizim = "macOS"
    elif "CrOS" in ua:
        tizim = "ChromeOS"
    elif "Linux" in ua:
        tizim = "Linux"
    else:
        tizim = ""
    brauzer = next((nom for nom, naqsh in _BRAUZERLAR if naqsh.search(ua)), "")
    if tizim == "Android" and "; wv)" in ua and brauzer in ("Chrome", "Safari"):
        brauzer = "Ilova ichidagi brauzer"
    model = ""
    if tizim == "Android" and (m := _ANDROID_MODEL.search(ua)):
        model = re.sub(r"^(?:SAMSUNG|samsung) ", "", m.group(1).strip())
        if model in _SOXTA_MODELLAR:
            model = ""
    return tizim, brauzer, model[:60]


def belgilarni_tozala(xom, ua=""):
    """Frontend yuborgan belgilardan faqat ma'lum kalitlarni, cheklangan
    uzunlikda oladi (begona narsa bazaga tushmasin) va User-Agent'dan
    tizim/brauzer/modelni qo'shadi."""
    xom = xom if isinstance(xom, dict) else {}
    b = {}
    for kalit, uzunlik in _MATN_KALITLAR.items():
        v = xom.get(kalit)
        if isinstance(v, str) and v.strip():
            b[kalit] = v.strip()[:uzunlik]
    for kalit in _SON_KALITLAR:
        v = xom.get(kalit)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 100000:
            b[kalit] = round(float(v), 2)
    ekran = xom.get("ekran")
    if (isinstance(ekran, list) and len(ekran) == 2
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) and 0 < x < 100000 for x in ekran)):
        b["ekran"] = sorted(int(x) for x in ekran)  # telefon burilsa ham bir xil
    tizim, brauzer, ua_model = ua_tahlil(ua)
    if tizim == "macOS" and b.get("teginish", 0) > 1:
        tizim = "iPadOS"  # iPad "kompyuter rejimida" o'zini Mac deb ko'rsatadi
    if tizim:
        b["tizim"] = tizim
    if brauzer:
        b["brauzer"] = brauzer
    if ua_model and "model" not in b:
        b["model"] = ua_model
    return b


def qurilma_nomi(belgilar):
    """Admin ko'radigan nom: "Android · Chrome · SM-A515F"."""
    qismlar = [(belgilar or {}).get(k) for k in ("tizim", "brauzer", "model")]
    return " · ".join(q for q in qismlar if q) or "Noma'lum qurilma"


# Ikkala tomonda BO'LISHI va teng bo'lishi shart.
_ASOSIY = ("tizim", "yadro", "vaqt")
# Ikkala tomonda bo'lsa — teng bo'lishi shart.
_AGAR_BOR = ("gpu", "model", "xotira", "teginish")


def _fizik_ekran(b):
    """Haqiqiy piksellar (CSS o'lcham × piksel zichligi). Kompyuterda brauzer
    masshtabi (zoom) ekran o'lchamini ham, zichlikni ham o'zgartiradi, ko'paytmasi esa o'zgarmaydi."""
    ekran, dpr = b.get("ekran"), b.get("dpr")
    if not ekran or not dpr:
        return None
    return sorted(round(x * dpr) for x in ekran)


def mos_keladimi(a, b):
    """Ikki belgilar to'plami bitta qurilmanikimi. Brauzer nomi ATAYLAB
    solishtirilmaydi: bitta telefondagi Chrome va Telegram ichidagi brauzer
    bitta qurilma. Kamida video karta yoki model ikkala tomonda bo'lishi
    kerak — faqat ekran va yadrolar bilan tanib bo'lmaydi."""
    if not a or not b:
        return False
    if any(k not in a or k not in b or a[k] != b[k] for k in _ASOSIY):
        return False
    fa, fb = _fizik_ekran(a), _fizik_ekran(b)
    if not fa or not fb or any(abs(x - y) > 2 for x, y in zip(fa, fb)):  # 2 px — yaxlitlash farqi
        return False
    # Telefonda masshtab zichlikni o'zgartirmaydi — u model belgisi sifatida ham solishtiriladi.
    if a.get("teginish", 0) > 0 and a.get("dpr") != b.get("dpr"):
        return False
    if any(k in a and k in b and a[k] != b[k] for k in _AGAR_BOR):
        return False
    return any(k in a and k in b for k in ("gpu", "model"))


# ── Ro'yxat (User.qurilmalar) ─────────────────────────────────────────

def _vaqt(hozir):
    return hozir.isoformat()


def yangi_yozuv(qid, belgilar, hozir):
    return {
        "id": qid,
        "k": secrets.token_hex(6),  # tashqariga beriladigan kalit — ID'ning o'zi emas
        "nom": qurilma_nomi(belgilar),
        "belgilar": belgilar,
        "qoshilgan": _vaqt(hozir),
        "oxirgi": _vaqt(hozir),
    }


def royxat(user):
    """`User.qurilmalar` — yozuvlar ro'yxati (eski ID qatorlari migratsiya 0029'da o'chirilgan)."""
    return [d for d in user.qurilmalar or [] if isinstance(d, dict) and d.get("id")]


def idlar(user):
    return {d["id"] for d in royxat(user)}


def _eski_mi(d, hozir):
    oxirgi = d.get("oxirgi")
    if not oxirgi:
        return False
    try:
        from datetime import datetime
        return datetime.fromisoformat(oxirgi) < hozir - timedelta(days=ESKIRISH_KUNI)
    except ValueError:
        return False


def _saqla(user, yozuvlar):
    user.qurilmalar = yozuvlar
    user.save(update_fields=["qurilmalar"])


def qurilma_kalitlarini_bekor_qil(user_id, qid):
    """Shu qurilmaning refresh kalitlarini qora ro'yxatga qo'yadi (o'qib
    bo'lmaganlarini ham). Kirish kaliti esa har so'rovda tekshiriladi
    (`authentication.py`) — qurilma o'chirilishi bilan darhol chiqarib yuboriladi."""
    from rest_framework_simplejwt.settings import api_settings
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    from .seans_views import amaldagi_kalitlar

    sanoq = 0
    for kalit in amaldagi_kalitlar(user_id):
        try:
            qurilma = api_settings.TOKEN_BACKEND.decode(kalit.token, verify=False).get("qid")
        except Exception:  # noqa: BLE001 — o'qib bo'lmagan kalit ham bekor qilinadi
            qurilma = None
        if qurilma in (None, qid):
            BlacklistedToken.objects.get_or_create(token=kalit)
            sanoq += 1
    return sanoq


def _bildirishnoma_kaliti(sorov):
    return f"qurilma-sorov:{sorov.pk}"


def _adminlarga_xabar(sorov, user, ruxsat_soni):
    adminlar = User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True), is_active=True).distinct()
    ism = (user.get_full_name() or user.username).strip()
    for admin in adminlar:
        Bildirishnoma.objects.get_or_create(
            foydalanuvchi=admin,
            kalit=_bildirishnoma_kaliti(sorov),
            defaults={
                "turi": Bildirishnoma.Turi.OGOHLANTIRISH,
                "sarlavha": "Yangi qurilmadan kirishga urinish",
                "matn": (
                    f"{ism} ({user.username}) yangi qurilmadan kirishga urindi: {sorov.nom}. "
                    f"Ruxsat etilgan qurilmalar: {ruxsat_soni}/{user.qurilma_limiti}."
                ),
                "havola": "/qurilma-sorovlari",
            },
        )


def sorov_yopildi(sorov):
    """Hal qilingan so'rov haqidagi admin xabarlari "o'qilgan" bo'ladi."""
    Bildirishnoma.objects.filter(kalit=_bildirishnoma_kaliti(sorov)).update(oqilgan=True)


def kirishni_tekshir(user, qid, belgilar, hozir=None):
    """Login paytidagi qurilma tekshiruvi. Qaytaradi: (True, None) — kiradi;
    (False, {"ruxsat_etilgan": [...nomlar], "sorov": "kutilmoqda"|"rad"}) — rad.

    Tartib: tanish ID -> limitda joy bor -> belgilar AYNAN BITTA qurilmaga mos
    -> aks holda adminga so'rov (bitta; takroriy urinish shu so'rovga yoziladi).
    `select_for_update` — bir vaqtdagi ikki login limitni chetlab o'tmasin."""
    hozir = hozir or timezone.now()
    nom = qurilma_nomi(belgilar)
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        hammasi = royxat(user)
        yozuvlar = [d for d in hammasi if not _eski_mi(d, hozir)]
        eskilar_ochdi = len(yozuvlar) != len(hammasi)

        tanish = next((d for d in yozuvlar if d["id"] == qid), None)
        if tanish:
            # Belgilar USTIGA qo'shiladi: bu safar o'qilmagan belgi (masalan video
            # karta) eski qiymatini yo'qotmasin — aks holda keyingi safar tanib bo'lmaydi.
            yangi = {**(tanish.get("belgilar") or {}), **belgilar}
            tanish.update(nom=qurilma_nomi(yangi), belgilar=yangi, oxirgi=_vaqt(hozir))
            _saqla(user, yozuvlar)
            return True, None

        if len(yozuvlar) < user.qurilma_limiti:
            yozuvlar.append(yangi_yozuv(qid, belgilar, hozir))
            _saqla(user, yozuvlar)
            for sorov in QurilmaSorovi.objects.filter(foydalanuvchi=user, qid=qid, holat=QurilmaSorovi.Holat.KUTILMOQDA):
                sorov.holat, sorov.hal_vaqti = QurilmaSorovi.Holat.RUXSAT, hozir
                sorov.save(update_fields=["holat", "hal_vaqti"])
                sorov_yopildi(sorov)
            return True, None

        moslar = [d for d in yozuvlar if mos_keladimi(belgilar, d.get("belgilar"))]
        if len(moslar) == 1:
            eski = moslar[0]
            eski_id, eski_nom = eski["id"], eski["nom"]
            yangi = {**(eski.get("belgilar") or {}), **belgilar}
            eski.update(id=qid, nom=qurilma_nomi(yangi), belgilar=yangi, oxirgi=_vaqt(hozir))
            _saqla(user, yozuvlar)
            QurilmaSorovi.objects.create(
                foydalanuvchi=user, qid=qid, nom=nom, belgilar=belgilar,
                holat=QurilmaSorovi.Holat.AVTO, almashtirilgan_nom=eski_nom, hal_vaqti=hozir,
            )
            user_id = user.pk
            transaction.on_commit(lambda: qurilma_kalitlarini_bekor_qil(user_id, eski_id))
            return True, None

        if eskilar_ochdi:
            _saqla(user, yozuvlar)

        oxirgi = QurilmaSorovi.objects.filter(foydalanuvchi=user, qid=qid).exclude(
            holat=QurilmaSorovi.Holat.AVTO).order_by("-yaratilgan", "-id").first()
        if oxirgi and oxirgi.holat == QurilmaSorovi.Holat.RAD and oxirgi.hal_vaqti and hozir - oxirgi.hal_vaqti < RAD_AMAL_QILADI:
            holat = "rad"
        elif oxirgi and oxirgi.holat == QurilmaSorovi.Holat.KUTILMOQDA:
            oxirgi.urinishlar += 1
            oxirgi.oxirgi_urinish = hozir
            oxirgi.nom, oxirgi.belgilar = nom, belgilar
            oxirgi.save(update_fields=["urinishlar", "oxirgi_urinish", "nom", "belgilar"])
            holat = "kutilmoqda"
        else:
            sorov = QurilmaSorovi.objects.create(
                foydalanuvchi=user, qid=qid, nom=nom, belgilar=belgilar, oxirgi_urinish=hozir,
            )
            _adminlarga_xabar(sorov, user, len(yozuvlar))
            holat = "kutilmoqda"
    return False, {"ruxsat_etilgan": [d["nom"] for d in yozuvlar], "sorov": holat}


def faollikni_yoz(user_id, qid, hozir=None):
    """Refresh paytida qurilmaning "oxirgi" vaqti (soatda bir martadan ko'p emas).
    Usiz faol, lekin qayta login qilmaydigan qurilma 60 kunda "eskirgan" bo'lib qolardi."""
    hozir = hozir or timezone.now()
    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=user_id).first()
        if user is None:
            return
        yozuvlar = royxat(user)
        d = next((x for x in yozuvlar if x["id"] == qid), None)
        if d is None:
            return
        try:
            from datetime import datetime
            if d.get("oxirgi") and hozir - datetime.fromisoformat(d["oxirgi"]) < FAOLLIK_ORALIGI:
                return
        except ValueError:
            pass
        d["oxirgi"] = _vaqt(hozir)
        _saqla(user, yozuvlar)


def qurilmani_ochir(user, kalit):
    """Bitta qurilmani (tashqi kalit `k` bo'yicha) o'chiradi va uning seanslarini
    darhol yopadi. Qaytaradi: o'chirilgan yozuv yoki None."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        yozuvlar = royxat(user)
        d = next((x for x in yozuvlar if x.get("k") == kalit), None)
        if d is None:
            return None
        _saqla(user, [x for x in yozuvlar if x is not d])
        user_id, qid = user.pk, d["id"]
        transaction.on_commit(lambda: qurilma_kalitlarini_bekor_qil(user_id, qid))
    return d


class QarorXatosi(ValueError):
    """Admin qarorini bajarib bo'lmaydi — matni foydalanuvchiga ko'rsatiladi."""


def sorovni_hal_qil(sorov, amal, kim, kalit=None, hozir=None):
    """Admin qarori: "almashtir" (`kalit` — qaysi qurilma o'rniga; u darhol
    chiqarib yuboriladi), "limit" (limit bittaga oshadi, hech kim chiqmaydi),
    "rad". Qaytaradi: yangilangan so'rov."""
    hozir = hozir or timezone.now()
    if amal not in ("almashtir", "limit", "rad"):
        raise QarorXatosi("Noma'lum amal")
    with transaction.atomic():
        sorov = QurilmaSorovi.objects.select_for_update().get(pk=sorov.pk)
        if sorov.holat != QurilmaSorovi.Holat.KUTILMOQDA:
            raise QarorXatosi("Bu so'rov allaqachon hal qilingan")
        user = User.objects.select_for_update().get(pk=sorov.foydalanuvchi_id)
        yozuvlar = royxat(user)
        if amal == "rad":
            sorov.holat = QurilmaSorovi.Holat.RAD
        elif amal == "almashtir":
            eski = next((d for d in yozuvlar if d.get("k") == kalit), None)
            if eski is None:
                raise QarorXatosi("Bu qurilma ro'yxatda yo'q — sahifani yangilang")
            yozuvlar[yozuvlar.index(eski)] = yangi_yozuv(sorov.qid, sorov.belgilar, hozir)
            _saqla(user, yozuvlar)
            sorov.holat, sorov.almashtirilgan_nom = QurilmaSorovi.Holat.RUXSAT, eski["nom"]
            user_id, eski_id = user.pk, eski["id"]
            transaction.on_commit(lambda: qurilma_kalitlarini_bekor_qil(user_id, eski_id))
        else:
            if all(d["id"] != sorov.qid for d in yozuvlar):
                yozuvlar.append(yangi_yozuv(sorov.qid, sorov.belgilar, hozir))
            user.qurilmalar = yozuvlar
            user.qurilma_limiti = max(user.qurilma_limiti, len(yozuvlar))
            user.save(update_fields=["qurilmalar", "qurilma_limiti"])
            sorov.holat = QurilmaSorovi.Holat.RUXSAT
        sorov.hal_qildi, sorov.hal_vaqti = kim, hozir
        sorov.save(update_fields=["holat", "almashtirilgan_nom", "hal_qildi", "hal_vaqti"])
        sorov_yopildi(sorov)
    return sorov


def kutayotganlar():
    """Kutilayotgan qurilma so'rovi bor foydalanuvchilar ID'lari — ro'yxatlardagi
    belgi uchun, hamma uchun bitta so'rov."""
    return set(QurilmaSorovi.objects.filter(holat=QurilmaSorovi.Holat.KUTILMOQDA)
               .values_list("foydalanuvchi_id", flat=True))


def oy_almashtirishlari(user, hozir=None):
    """Shu oyda nechta qurilma almashtirilgan (admin ruxsati bilan yoki avtomatik)."""
    hozir = hozir or timezone.now()
    oy_boshi = hozir.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return QurilmaSorovi.objects.filter(foydalanuvchi=user, hal_vaqti__gte=oy_boshi).filter(
        Q(holat=QurilmaSorovi.Holat.AVTO) | (Q(holat=QurilmaSorovi.Holat.RUXSAT) & ~Q(almashtirilgan_nom=""))
    ).count()
