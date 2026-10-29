"""Qurilmalar limiti — 2-tizim (2026-10-29, Shuhrat; reja: tmp/plans/qurilma-v2-reja.md).

Qoidalar:
  1. Limit standart 1 (`User.qurilma_limiti`), owner'dan boshqa hammaga.
  2. Birinchi qurilma avtomatik qo'shiladi; limitda joy bo'lsa yangisi ham.
  3. Limitdan tashqari qurilma — «Kutilmoqda» so'rov, xabar faqat adminga.
  4. Yangi qurilma ruxsat etilganining o'rnini hech qachon egallamaydi.
  5. Talabada bir vaqtda bitta seans: har kirish oldingisini yopadi (`FaolSeans`).
  6. 60 kun ishlatilmagan qurilma ro'yxatdan chiqadi.
  7. Bloklangan qurilma — kaliti va hamma brauzerlari bilan — kira olmaydi.

Brauzer emas, QURILMA tekshiriladi. Qurilmani qurilma kaliti (passkey) taniydi — bitta
telefondagi hamma brauzer bitta kalitni ishlatadi va u brauzer tarixi tozalansa ham
qoladi. Brauzer ID (`BrauzerEslatmasi`) — faqat «bu brauzer shu qurilmada ekani
tasdiqlangan» eslatmasi. Brauzer belgilari qaror uchun ISHLATILMAYDI (1-tizimda bir xil
modeldagi telefonlarni adashtirardi), faqat adminga «o'xshaydi» maslahati.

Eski versiyaga tez qaytish uchun (2-reliz kelguncha) har o'zgarish `User.qurilmalar`,
`User.faol_qurilma` va `QurilmaSorovi` (blok)ga eski formatda ham yoziladi — `eski_formatga_yoz`."""

import logging
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from . import qurilma_kaliti
from .models import (
    Bildirishnoma,
    BrauzerEslatmasi,
    FaolSeans,
    KirishJurnali,
    Qurilma,
    QurilmaKaliti,
    QurilmaSorovi,
    User,
)

logger = logging.getLogger(__name__)

ESKIRISH_KUNI = 60
JURNAL_KUNI = 90
# Kalit yangilashda brauzer va qurilmaning «oxirgi» vaqti shundan tez-tez yozilmaydi.
FAOLLIK_ORALIGI = timedelta(hours=1)

RUXSAT, KUTILMOQDA, BLOK = Qurilma.Holat.RUXSAT, Qurilma.Holat.KUTILMOQDA, Qurilma.Holat.BLOK
KIRDI, RAD, CHIQARILDI, AMAL = (KirishJurnali.Natija.KIRDI, KirishJurnali.Natija.RAD,
                                KirishJurnali.Natija.CHIQARILDI, KirishJurnali.Natija.AMAL)

_RAD_MATNLARI = {
    "bloklangan": "Bu qurilma bloklangan. Administratorga murojaat qiling.",
    "sorov_yuborildi": "Bu yangi qurilma. Administratorga so'rov yuborildi — ruxsat berilgach qayta kiring.",
    "sorov_kutilmoqda": "Bu qurilma uchun so'rov administratorda kutilmoqda — ruxsat berilgach qayta kiring.",
}


# ── Brauzer belgilari (faqat nom va maslahat uchun) ────────────────────

_ID_NAMUNA = re.compile(r"^[A-Za-z0-9-]{1,64}$")
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


def id_tozala(xom):
    """Kelgan brauzer ID'si: faqat harf/raqam/chiziqcha, 1-64 belgi. Yaroqsiz — ''."""
    xom = xom.strip() if isinstance(xom, str) else ""
    return xom if _ID_NAMUNA.match(xom) else ""


def ua_tahlil(ua):
    """User-Agent'dan (tizim, brauzer, model). Topilmagani — ''."""
    ua = ua or ""
    tizim = next((nom for belgi, nom in (
        ("Windows", "Windows"), ("iPhone", "iOS"), ("iPad", "iPadOS"), ("Android", "Android"),
        ("Macintosh", "macOS"), ("Mac OS X", "macOS"), ("CrOS", "ChromeOS"), ("Linux", "Linux"),
    ) if belgi in ua), "")
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
    """Frontend yuborgan belgilardan faqat ma'lum kalitlar, cheklangan uzunlikda
    (begona narsa bazaga tushmasin) + User-Agent'dan tizim/brauzer/model."""
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
        b["ekran"] = sorted(int(x) for x in ekran)
    tizim, brauzer, ua_model = ua_tahlil(ua)
    if tizim == "macOS" and b.get("teginish", 0) > 1:
        tizim = "iPadOS"  # iPad «kompyuter rejimida» o'zini Mac deb ko'rsatadi
    if tizim:
        b["tizim"] = tizim
    if brauzer:
        b["brauzer"] = brauzer
    if ua_model and "model" not in b:
        b["model"] = ua_model
    return b


def umumiy_nom(belgilar):
    """Qurilmaning nomi, brauzersiz: "Android · SM-A515F"."""
    qismlar = [(belgilar or {}).get(k) for k in ("tizim", "model")]
    return " · ".join(q for q in qismlar if q) or "Noma'lum qurilma"


def oxshashi(q, ruxsatlar):
    """Kutilayotgan qurilma ruxsat etilganlardan qaysi biriga o'xshaydi — faqat adminga
    maslahat (bir xil modeldagi boshqa telefon ham «o'xshaydi»). Topilmasa — None."""
    b = q.belgilar or {}
    for r in ruxsatlar:
        a = r.belgilar or {}
        if (a.get("tizim") and a.get("tizim") == b.get("tizim")
                and all(a.get(k) == b.get(k) for k in ("model", "gpu", "ekran", "dpr") if a.get(k) and b.get(k))
                and any(a.get(k) and b.get(k) for k in ("model", "gpu"))):
            return r
    return None


# ── Yordamchilar ───────────────────────────────────────────────────────

@dataclass
class Natija:
    """Kirish natijasi: `javob` bo'sh bo'lsa — kirdi (`qurilma`, `brauzer`); aks holda
    foydalanuvchiga qaytariladigan rad yoki «kalit kerak» javobi va uning holati."""

    qurilma: Qurilma | None = None
    brauzer: str = ""
    javob: dict | None = None
    status: int = 200

    @property
    def kirdi(self):
        return self.javob is None


def bir_vaqtda_bitta(user):
    """«Bir vaqtda bitta seans» — faqat talabalarga (Shuhrat, 2026-10-26/29): xodim CRM'ni
    noutbukda, davomatni telefonda ochadi."""
    return user.role == User.Role.STUDENT


def _jurnal(user, natija, sabab, qurilma=None, kim=None):
    KirishJurnali.objects.create(
        foydalanuvchi=user, qurilma=qurilma, qurilma_nomi=(qurilma.nom if qurilma else "")[:160],
        natija=natija, sabab=sabab, kim=kim,
    )


def _ruxsatlar_soni(user):
    return Qurilma.objects.filter(foydalanuvchi=user, holat=RUXSAT).count()


def _eslatma(user, qid):
    if not qid:
        return None
    return BrauzerEslatmasi.objects.select_related("qurilma").filter(foydalanuvchi=user, qid=qid).first()


def _eslatma_yarat(q, qid, belgilar, hozir):
    return BrauzerEslatmasi.objects.create(
        qurilma=q, foydalanuvchi_id=q.foydalanuvchi_id, qid=qid, brauzer=belgilar.get("brauzer", "")[:40],
        belgilar=belgilar, yaratilgan=hozir, oxirgi=hozir,
    )


def _rad(user, sabab):
    """Login rad javobi. `kod`/`sorov`/`ruxsat_etilgan` — eski frontend bilan mos
    (eski versiyaga yarim qaytilganda ham login ishlasin), `sabab` — yangisi uchun."""
    return {
        "detail": _RAD_MATNLARI[sabab], "kod": "qurilma_mos_emas", "sabab": sabab,
        "sorov": "rad" if sabab == "bloklangan" else "kutilmoqda",
        "ruxsat_etilgan": list(Qurilma.objects.filter(foydalanuvchi=user, holat=RUXSAT).values_list("nom", flat=True)),
    }


def _xabar_kaliti(q):
    return f"qurilma-v2:{q.pk}"


def _adminlarga_xabar(q, user):
    adminlar = User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True), is_active=True).distinct()
    ism = (user.get_full_name() or user.username).strip()
    for admin in adminlar:
        Bildirishnoma.objects.get_or_create(
            foydalanuvchi=admin, kalit=_xabar_kaliti(q),
            defaults={
                "turi": Bildirishnoma.Turi.OGOHLANTIRISH,
                "sarlavha": "Yangi qurilmadan kirishga urinish",
                "matn": (f"{ism} ({user.username}) yangi qurilmadan kirishga urindi: {q.nom}. "
                         f"Ruxsat etilgan qurilmalar: {_ruxsatlar_soni(user)}/{user.qurilma_limiti}."),
                "havola": f"/qurilmalar?holat=kutilmoqda&foydalanuvchi={user.pk}",
            },
        )


def _sorov_xabarini_yop(q):
    Bildirishnoma.objects.filter(kalit=_xabar_kaliti(q)).update(oqilgan=True)


def _eskilarni_tozala(user, hozir):
    for q in Qurilma.objects.filter(foydalanuvchi=user, holat=RUXSAT, oxirgi__lt=hozir - timedelta(days=ESKIRISH_KUNI)):
        _jurnal(user, AMAL, "eskirdi", q)
        q.delete()
    KirishJurnali.objects.filter(foydalanuvchi=user, vaqt__lt=hozir - timedelta(days=JURNAL_KUNI)).delete()


def _bir_xil_telefon(q, belgilar):
    """Kalit talabaning Google/Apple akkaunti orqali boshqa qurilmasiga ham o'tadi —
    shuning uchun kalit bilan tanilganda tizim va model ham mos bo'lishi shart."""
    return all(not (a and b) or a == b for a, b in ((q.tizim, belgilar.get("tizim", "")),
                                                     (q.modeli, belgilar.get("model", ""))))


# ── Kirish ─────────────────────────────────────────────────────────────

def kirish(user, qid, belgilar, origin=None, kalit_qollaydi=False):
    """Parol to'g'ri bo'lgandan keyingi qurilma tekshiruvi. `origin` — kalit ishlatish
    mumkin bo'lgan sayt manzili (`qurilma_kaliti.manzil`), `kalit_qollaydi` — frontend
    shu brauzerda kalit ishlay olishini aytdi (eski frontend aytmaydi)."""
    hozir = timezone.now()
    with transaction.atomic():
        _eskilarni_tozala(user, hozir)
        be = _eslatma(user, qid)
        if be is not None:
            return _eslatma_bilan(user, be, belgilar, hozir)
        kalit_idlar = list(QurilmaKaliti.objects.filter(
            foydalanuvchi=user, qurilma__holat__in=(RUXSAT, BLOK)).values_list("kalit_id", flat=True))
        if kalit_qollaydi and origin and kalit_idlar:
            savol, sozlama = qurilma_kaliti.tasdiqlash_sorovi(origin, kalit_idlar)
            chipta = qurilma_kaliti.chipta_yasa(u=user.pk, q=qid, s=savol, o=origin, b=belgilar)
            return Natija(javob={"detail": "Qurilmangizni tasdiqlang", "kod": "kalit_kerak",
                                 "chipta": chipta, "kalit": sozlama}, status=409)
        return _yangi_qurilma(user, qid, belgilar, hozir)


def kalit_bilan_kirish(chipta, javob=None, kalitsiz=False):
    """«Qurilmangizni tasdiqlang» bosqichi. `kalitsiz` — talaba «Bu yangi qurilma»ni bosdi.
    Qaytaradi: (user, qid, Natija). Kalit yaroqsiz bo'lsa — `qurilma_kaliti.KalitXatosi`."""
    malumot = qurilma_kaliti.chipta_och(chipta)
    user = User.objects.filter(pk=malumot["u"], is_active=True).first()
    if user is None:
        raise qurilma_kaliti.KalitXatosi("Hisob topilmadi — qayta kiring")
    qid, origin, belgilar = malumot["q"], malumot["o"], malumot.get("b") or {}
    hozir = timezone.now()
    with transaction.atomic():
        be = _eslatma(user, qid)
        if be is not None:
            return user, qid, _eslatma_bilan(user, be, belgilar, hozir)
        if kalitsiz:
            return user, qid, _yangi_qurilma(user, qid, belgilar, hozir)
        kalit = QurilmaKaliti.objects.select_related("qurilma").filter(
            foydalanuvchi=user, kalit_id=qurilma_kaliti.javob_kalit_idsi(javob)).first()
        if kalit is None:
            raise qurilma_kaliti.KalitXatosi("Bu qurilmada kalit topilmadi")
        kalit.hisoblagich = qurilma_kaliti.tasdiqni_tekshir(
            javob, malumot["s"], origin, bytes(kalit.ochiq_kalit), kalit.hisoblagich)
        kalit.oxirgi = hozir
        kalit.save(update_fields=["hisoblagich", "oxirgi"])
        q = kalit.qurilma
        if q.holat == BLOK:
            _eslatma_yarat(q, qid, belgilar, hozir)  # keyingi safar ham bloklangan deb taniladi
            _jurnal(user, RAD, "bloklangan", q)
            return user, qid, Natija(javob=_rad(user, "bloklangan"), status=403)
        if q.holat != RUXSAT or not _bir_xil_telefon(q, belgilar):
            return user, qid, _yangi_qurilma(user, qid, belgilar, hozir, sabab="kalit_boshqa_telefon")
        be = _eslatma_yarat(q, qid, belgilar, hozir)
        q.oxirgi = hozir
        q.save(update_fields=["oxirgi"])
        _jurnal(user, KIRDI, "kalit_bilan", q)
        return user, qid, Natija(qurilma=q, brauzer=be.brauzer)


def _eslatma_bilan(user, be, belgilar, hozir):
    q = be.qurilma
    if q.holat == BLOK:
        _jurnal(user, RAD, "bloklangan", q)
        return Natija(javob=_rad(user, "bloklangan"), status=403)
    sabab = "tanish"
    if q.holat == KUTILMOQDA:
        if _ruxsatlar_soni(user) >= user.qurilma_limiti:
            q.urinishlar += 1
            q.oxirgi = hozir
            q.save(update_fields=["urinishlar", "oxirgi"])
            _jurnal(user, RAD, "sorov_kutilmoqda", q)
            return Natija(javob=_rad(user, "sorov_kutilmoqda"), status=403)
        # Admin limitni oshirgan — so'rov o'z-o'zidan hal bo'ladi.
        q.holat, q.hal_vaqti = RUXSAT, hozir
        _sorov_xabarini_yop(q)
        sabab = "joy_ochildi"
    be.belgilar = {**(be.belgilar or {}), **belgilar}
    be.brauzer = belgilar.get("brauzer", "")[:40] or be.brauzer
    be.oxirgi = hozir
    be.save(update_fields=["belgilar", "brauzer", "oxirgi"])
    q.oxirgi = hozir
    q.save(update_fields=["holat", "hal_vaqti", "oxirgi"])
    _jurnal(user, KIRDI, sabab, q)
    return Natija(qurilma=q, brauzer=be.brauzer)


def _yangi_qurilma(user, qid, belgilar, hozir, sabab=None):
    """Hech qaysi qurilmaga bog'lanmagan brauzer: joy bo'lsa — yangi qurilma, aks holda so'rov."""
    joy_bor = _ruxsatlar_soni(user) < user.qurilma_limiti
    q = Qurilma.objects.create(
        foydalanuvchi=user, holat=RUXSAT if joy_bor else KUTILMOQDA, nom=umumiy_nom(belgilar),
        tizim=belgilar.get("tizim", "")[:20], modeli=belgilar.get("model", "")[:60], belgilar=belgilar,
        urinishlar=0 if joy_bor else 1, yaratilgan=hozir, oxirgi=hozir,
    )
    be = _eslatma_yarat(q, qid, belgilar, hozir)
    if joy_bor:
        _jurnal(user, KIRDI, sabab or "yangi_qurilma", q)
        return Natija(qurilma=q, brauzer=be.brauzer)
    _adminlarga_xabar(q, user)
    _jurnal(user, RAD, sabab or "sorov_yuborildi", q)
    return Natija(javob=_rad(user, "sorov_yuborildi"), status=403)


# ── Seans va kalitlar ──────────────────────────────────────────────────

def kalit_ber(user, qid=None, qurilma=None, brauzer=""):
    """Login javobi. Qurilmasi bo'lgan (owner bo'lmagan) foydalanuvchida kalitga brauzer
    (`qid`) va seans (`sid`) belgisi qo'yiladi, oldingi seans yopiladi (talabada)."""
    kalit = RefreshToken.for_user(user)
    if qurilma is not None:
        sid = secrets.token_hex(8)
        kalit["qid"], kalit["sid"] = qid, sid
        jti = kalit[api_settings.JTI_CLAIM]
        # `for_user` kalitni bazaga belgilarsiz yozib bo'ladi — seanslarni yopishda kimniki ekani bilinsin.
        OutstandingToken.objects.filter(jti=jti).update(token=str(kalit))
        _seans_boshla(user, qurilma, brauzer, sid, jti)
    return {"refresh": str(kalit), "access": str(kalit.access_token)}


def _seans_boshla(user, qurilma, brauzer, sid, jti):
    oldingi = FaolSeans.objects.select_related("qurilma").filter(foydalanuvchi=user).first()
    FaolSeans.objects.update_or_create(
        foydalanuvchi=user,
        defaults={"sid": sid, "qurilma": qurilma, "brauzer": brauzer, "boshlangan": timezone.now()},
    )
    if bir_vaqtda_bitta(user):
        transaction.on_commit(lambda: _kalitlarni_bekor_qil(user.pk, saqla_jti=jti))
        if oldingi and oldingi.qurilma and (oldingi.qurilma_id, oldingi.brauzer) != (qurilma.pk, brauzer):
            _jurnal(user, CHIQARILDI, "boshqa_joyda", oldingi.qurilma)
    eski_formatga_yoz(user.pk)


def _kalitlarni_bekor_qil(user_id, qidlar=None, saqla_jti=None):
    """Refresh kalitlarni qora ro'yxatga qo'yadi: `qidlar` berilsa — faqat shu brauzerlarniki
    (belgisiz eski kalitlar ham), aks holda `saqla_jti`dan boshqa hammasi. Kirish kalitlari
    esa har so'rovda tekshiriladi (`kalit_xatosi`) — ular darhol ishlamay qoladi."""
    from rest_framework_simplejwt.state import token_backend

    from .seans_views import amaldagi_kalitlar

    for kalit in amaldagi_kalitlar(user_id):
        if kalit.jti == saqla_jti:
            continue
        if qidlar is not None:
            try:
                qid = token_backend.decode(kalit.token, verify=False).get("qid")
            except Exception:  # noqa: BLE001 — o'qib bo'lmagan kalit ham bekor qilinadi
                qid = None
            if qid is not None and qid not in qidlar:
                continue
        BlacklistedToken.objects.get_or_create(token=kalit)


def _seanslarini_yop(q):
    qidlar = set(q.brauzerlar.values_list("qid", flat=True))
    user_id = q.foydalanuvchi_id
    transaction.on_commit(lambda: _kalitlarni_bekor_qil(user_id, qidlar=qidlar))


def kalit_xatosi(user, kalit):
    """Har so'rovda (`authentication.py`) va kalit yangilashda: kalitdagi brauzer ruxsat
    etilgan qurilmanikimi va (talabada) seans hozirgimi. Qaytaradi: None yoki 401 tanasi."""
    be = _eslatma(user, kalit.get("qid"))
    if be is None or be.qurilma.holat == KUTILMOQDA:
        return {"detail": "Bu qurilmadan kirish yopildi — qayta kiring", "kod": "qurilma_ochirildi"}
    if be.qurilma.holat == BLOK:
        return {"detail": "Bu qurilma bloklangan", "kod": "qurilma_bloklandi"}
    if bir_vaqtda_bitta(user):
        sid = FaolSeans.objects.filter(foydalanuvchi_id=user.pk).values_list("sid", flat=True).first()
        if sid is not None and kalit.get("sid") != sid:
            return {"detail": "Hisobingizga boshqa joydan kirildi — bu yerda davom etish uchun qayta kiring",
                    "kod": "boshqa_qurilmada"}
    return None


def faollikni_yoz(user_id, qid):
    """Kalit yangilanganda brauzer va qurilmaning «oxirgi» vaqti (soatda bir martadan ko'p
    emas) — usiz faol, lekin qayta login qilmaydigan qurilma 60 kunda «eskirib» qolardi."""
    hozir = timezone.now()
    be = BrauzerEslatmasi.objects.filter(
        foydalanuvchi_id=user_id, qid=qid, oxirgi__lt=hozir - FAOLLIK_ORALIGI).first()
    if be is not None:
        BrauzerEslatmasi.objects.filter(pk=be.pk).update(oxirgi=hozir)
        Qurilma.objects.filter(pk=be.qurilma_id).update(oxirgi=hozir)


def qurilma_sanoqlari(user_ids):
    """Ro'yxatlardagi «Qurilmalar n/limit» tugmasi uchun: {user_id: (ruxsat_soni, sorov_bormi)}."""
    natija = {}
    for uid, holat, soni in (Qurilma.objects.filter(foydalanuvchi_id__in=list(user_ids), holat__in=(RUXSAT, KUTILMOQDA))
                             .values_list("foydalanuvchi_id", "holat").annotate(soni=Count("id"))):
        ruxsat, sorov = natija.get(uid, (0, False))
        natija[uid] = (soni, sorov) if holat == RUXSAT else (ruxsat, True)
    return natija


def joriy_qurilma(user, qid):
    be = _eslatma(user, qid)
    return be.qurilma if be is not None and be.qurilma.holat == RUXSAT else None


def joriy_qurilma_malumoti(user, kalit):
    """Profil uchun: shu brauzer qaysi qurilmada va unda kalit bormi («Bu qurilmani
    eslab qolish» taklifi shunga qarab chiqadi). Owner va eski kalitlar — None."""
    if user.is_superuser or kalit is None:
        return None
    q = joriy_qurilma(user, kalit.get("qid"))
    return {"nom": q.nom, "kalit_bor": q.kalitlar.exists()} if q else None


# ── Qurilma kaliti yaratish («Bu qurilmani eslab qolish») ──────────────

def kalit_yaratish_boshla(user, qid, origin):
    q = joriy_qurilma(user, qid)
    if q is None:
        raise qurilma_kaliti.KalitXatosi("Bu qurilma ruxsat etilmagan")
    mavjud = list(QurilmaKaliti.objects.filter(foydalanuvchi=user).values_list("kalit_id", flat=True))
    savol, sozlama = qurilma_kaliti.yaratish_sorovi(origin, user, mavjud)
    return {"chipta": qurilma_kaliti.chipta_yasa(u=user.pk, d=q.pk, s=savol, o=origin), "kalit": sozlama}


def kalit_saqla(user, chipta, javob):
    malumot = qurilma_kaliti.chipta_och(chipta)
    q = Qurilma.objects.filter(pk=malumot.get("d"), foydalanuvchi=user, holat=RUXSAT).first()
    if malumot.get("u") != user.pk or q is None:
        raise qurilma_kaliti.KalitXatosi("Bu qurilma ruxsat etilmagan")
    kalit_id, ochiq_kalit, hisoblagich = qurilma_kaliti.yaratishni_tekshir(javob, malumot["s"], malumot["o"])
    QurilmaKaliti.objects.get_or_create(
        foydalanuvchi=user, kalit_id=kalit_id,
        defaults={"qurilma": q, "ochiq_kalit": ochiq_kalit, "hisoblagich": hisoblagich},
    )
    _jurnal(user, AMAL, "kalit_yaratildi", q, user)
    return q


# ── Admin amallari («Qurilmalar» oynasi) ───────────────────────────────

class AmalXatosi(ValueError):
    """Admin amalini bajarib bo'lmaydi — matni adminga ko'rsatiladi."""


QURILMA_AMALLARI = ("ruxsat", "orniga", "shu_qurilmaga", "blokla", "blokdan_chiqar", "ochir")


def _holat(q, holat, kim, hozir):
    if q.holat == KUTILMOQDA:
        _sorov_xabarini_yop(q)
    q.holat, q.hal_qildi, q.hal_vaqti = holat, kim, hozir
    q.save(update_fields=["holat", "hal_qildi", "hal_vaqti"])


def qurilma_amali(qurilma_id, amal, kim, boshqa_id=None):
    """`ruxsat` (kerak bo'lsa limit +1), `orniga` (`boshqa_id` qurilma o'rniga — u chiqarib
    yuboriladi), `shu_qurilmaga` (kaliti yo'q telefondagi ikkinchi brauzer: `boshqa_id`
    qurilmaga qo'shiladi, yangi joy egallamaydi), `blokla`, `blokdan_chiqar` (joy bo'lsa
    ruxsat, aks holda so'rov), `ochir`. Qaytaradi: qurilma egasi."""
    if amal not in QURILMA_AMALLARI:
        raise AmalXatosi("Noma'lum amal")
    hozir = timezone.now()
    with transaction.atomic():
        q = Qurilma.objects.select_related("foydalanuvchi").filter(pk=qurilma_id).first()
        if q is None:
            raise AmalXatosi("Bu qurilma ro'yxatda yo'q — sahifani yangilang")
        user = q.foydalanuvchi
        boshqa = None
        if amal in ("orniga", "shu_qurilmaga"):
            boshqa = Qurilma.objects.filter(pk=boshqa_id, foydalanuvchi=user, holat=RUXSAT).exclude(pk=q.pk).first()
            if boshqa is None:
                raise AmalXatosi("Tanlangan qurilma ro'yxatda yo'q — sahifani yangilang")
        if amal in ("ruxsat", "orniga", "shu_qurilmaga") and q.holat != KUTILMOQDA:
            raise AmalXatosi("Bu qurilma so'rov kutmayapti — sahifani yangilang")
        if amal == "blokla" and q.holat == BLOK:
            raise AmalXatosi("Bu qurilma allaqachon bloklangan")
        if amal == "blokdan_chiqar" and q.holat != BLOK:
            raise AmalXatosi("Bu qurilma bloklanmagan — sahifani yangilang")

        _jurnal(user, AMAL, amal, boshqa if amal == "orniga" else q, kim)
        if amal == "ruxsat":
            soni = _ruxsatlar_soni(user)
            if soni >= user.qurilma_limiti:
                user.qurilma_limiti = soni + 1
                user.save(update_fields=["qurilma_limiti"])
            _holat(q, RUXSAT, kim, hozir)
        elif amal == "orniga":
            _seanslarini_yop(boshqa)
            boshqa.delete()
            _holat(q, RUXSAT, kim, hozir)
        elif amal == "shu_qurilmaga":
            q.brauzerlar.update(qurilma=boshqa)
            q.kalitlar.update(qurilma=boshqa)
            _sorov_xabarini_yop(q)
            q.delete()
        elif amal == "blokla":
            if q.holat == RUXSAT:
                _seanslarini_yop(q)
            _holat(q, BLOK, kim, hozir)
        elif amal == "blokdan_chiqar":
            _holat(q, RUXSAT if _ruxsatlar_soni(user) < user.qurilma_limiti else KUTILMOQDA, kim, hozir)
        else:  # ochir
            if q.holat == RUXSAT:
                _seanslarini_yop(q)
            if q.holat == KUTILMOQDA:
                _sorov_xabarini_yop(q)
            q.delete()
        eski_formatga_yoz(user.pk)
    return user


def limitni_ozgartir(user, limit, kim):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise AmalXatosi("Limit 1 dan 100 gacha butun son bo'lishi kerak")
    user.qurilma_limiti = limit
    user.save(update_fields=["qurilma_limiti"])
    _jurnal(user, AMAL, "limit", None, kim)


def seansni_yop(user, kim):
    """Foydalanuvchining ochiq seansini yopadi: talaba darhol chiqadi (seans belgisi
    almashadi), qolganlarda yangilash kalitlari bekor qilinadi (≤30 daqiqada chiqadi)."""
    from .seans_views import kalitlarni_bekor_qil

    with transaction.atomic():
        FaolSeans.objects.update_or_create(
            foydalanuvchi=user, defaults={"sid": secrets.token_hex(8), "qurilma": None, "brauzer": ""})
        _jurnal(user, CHIQARILDI, "admin_seans_yopdi", None, kim)
        eski_formatga_yoz(user.pk)
    return kalitlarni_bekor_qil(user.pk)


# ── Eski formatga nusxa (eski versiyaga tez qaytish uchun) ─────────────

def _iso(vaqt):
    return vaqt.isoformat() if vaqt else None


def eski_formatga_yoz(user_id):
    """`User.qurilmalar`, `User.faol_qurilma` va `QurilmaSorovi` (blok) — 1-tizim o'qiydigan
    shaklda. Hech qachon kirishni buzmaydi: xato faqat logga yoziladi. 2-relizda o'chiriladi."""
    try:
        royxat, bloklar = [], {}
        for q in Qurilma.objects.filter(foydalanuvchi_id=user_id).prefetch_related("brauzerlar"):
            brauzerlar = sorted(q.brauzerlar.all(), key=lambda b: b.oxirgi)
            if q.holat == RUXSAT and brauzerlar:
                royxat.append({
                    "k": q.k, "id": brauzerlar[0].qid, "nom": q.nom, "belgilar": q.belgilar,
                    "qoshilgan": _iso(q.yaratilgan), "oxirgi": _iso(q.oxirgi),
                    "brauzerlar": [{"id": b.qid, "brauzer": b.brauzer, "belgilar": b.belgilar,
                                    "qoshilgan": _iso(b.yaratilgan), "oxirgi": _iso(b.oxirgi)} for b in brauzerlar],
                })
            elif q.holat == BLOK:
                bloklar.update({b.qid: (q, b) for b in brauzerlar})
        seans = FaolSeans.objects.select_related("qurilma").filter(foydalanuvchi_id=user_id).first()
        faol = seans.qurilma.k if seans and seans.qurilma and seans.qurilma.holat == RUXSAT else ""
        User.objects.filter(pk=user_id).update(qurilmalar=royxat, faol_qurilma=faol)

        eski_bloklar = {s.qid: s for s in QurilmaSorovi.objects.filter(foydalanuvchi_id=user_id, holat="blok")}
        for qid, s in eski_bloklar.items():
            if qid not in bloklar:
                s.delete()
        hozir = timezone.now()
        for qid, (q, b) in bloklar.items():
            if qid not in eski_bloklar:
                QurilmaSorovi.objects.create(
                    foydalanuvchi_id=user_id, qid=qid, nom=q.nom, belgilar=b.belgilar, holat="blok",
                    hal_qildi_id=q.hal_qildi_id, hal_vaqti=q.hal_vaqti or hozir, oxirgi_urinish=hozir,
                )
    except Exception:  # noqa: BLE001 — nusxa yozish hech qachon kirishni buzmasin
        logger.exception("Qurilmalar eski formatga yozilmadi (user_id=%s)", user_id)
