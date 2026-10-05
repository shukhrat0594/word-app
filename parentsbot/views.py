"""CRM uchun API: ota-ona so'rovlari, ulangan ota-onalar, xabar vaqtlari sozlamasi.

Hamma yo'l `/api/crm/parentsbot/...` ostida, `crm.permissions.CrmView` orqali (CRM yoqilgan bo'lishi,
CRM ruxsati, "parentsbot" bo'limi). Filial xodimi faqat o'z filiali o'quvchilari bilan bog'liq narsani
ko'radi va ulay oladi (`crm.filial.talaba_korinadimi`).
"""

import logging
import re
from datetime import time

from django.conf import settings
from django.db.models import Q
from rest_framework.response import Response

from academics.models import GuruhAzoligi
from accounts.models import User
from audit.models import FaoliyatYozuvi
from audit.utils import logla
from crm.filial import cheklanganmi, ruxsat_filiallari, talaba_korinadimi
from crm.permissions import CrmView
from crm.ruxsatlar import ruxsatlar

from . import xizmat
from .models import Abonent, Boglanish, ParentsBotSozlama, Sorov
from .moslash import talaba_ismi
from .telegram import Tg, TgXato

log = logging.getLogger("parentsbot")


def tg_ol():
    """Telegram klienti (token sozlangan bo'lsa). Testlarda almashtiriladi."""
    token = getattr(settings, "UTMOSTPARENTSBOT_TOKEN", "")
    return Tg(token) if token else None


def _xato(matn, kod=400):
    return Response({"detail": matn}, status=kod)


def _ruxsat(request, kalit):
    return kalit in ruxsatlar(request.user)


def _korinadi(user, talaba_id):
    return talaba_korinadimi(user, talaba_id)


def _talaba_dict(t):
    guruhlar = [
        a.guruh.name for a in GuruhAzoligi.objects.filter(talaba=t).select_related("guruh")[:5]
    ]
    return {
        "id": t.id, "ism": talaba_ismi(t), "tugilgan_sana": t.tugilgan_sana,
        "telefon": t.telefon, "ota_ona_telefon": t.ota_ona_telefon, "guruhlar": guruhlar,
    }


def _abonent_dict(a):
    return {"id": a.id, "ism": a.ism, "username": a.username, "telefon": a.telefon, "til": a.til, "faol": a.faol,
            "bloklangan": a.bloklangan}


def _sorov_dict(s, user):
    nomzodlar = [
        _talaba_dict(t)
        for t in User.objects.filter(pk__in=s.nomzodlar, role=User.Role.STUDENT, is_active=True)
        if _korinadi(user, t.id)
    ]
    return {
        "id": s.id, "abonent": _abonent_dict(s.abonent), "farzand_ismi": s.farzand_ismi,
        "tugilgan_sana": s.tugilgan_sana, "holat": s.holat, "nomzodlar": nomzodlar,
        "talaba": _talaba_dict(s.talaba) if s.talaba_id else None,
        "yaratilgan": s.yaratilgan, "hal_vaqti": s.hal_vaqti,
    }


class SorovlarView(CrmView):
    """Ota-ona so'rovlari. Cheklangan (filial) xodim faqat o'ziga ko'rinadigan nomzodi bor
    so'rovlarni ko'radi; nomzodsiz so'rovlarni cheklanmagan xodim (owner/markaz) hal qiladi."""

    bolim = "parentsbot"

    def get(self, request):
        holat = request.query_params.get("holat") or Sorov.Holat.KUTILMOQDA
        if holat not in dict(Sorov.Holat.choices):
            return _xato("Noma'lum holat")
        natija = []
        for s in Sorov.objects.filter(holat=holat).select_related("abonent", "talaba")[:200]:
            d = _sorov_dict(s, request.user)
            if cheklanganmi(request.user) and not d["nomzodlar"] and not (
                s.talaba_id and _korinadi(request.user, s.talaba_id)
            ):
                continue
            natija.append(d)
        return Response(natija)


class TalabaQidiruvView(CrmView):
    """Qo'lda ulash uchun o'quvchi qidirish (ism bo'yicha, faol, ko'rinadigan filial)."""

    bolim = "parentsbot"

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response([])
        natija = []
        for t in User.objects.filter(role=User.Role.STUDENT, is_active=True).filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
        )[:60]:
            if _korinadi(request.user, t.id):
                natija.append(_talaba_dict(t))
            if len(natija) >= 20:
                break
        return Response(natija)


class SorovHalView(CrmView):
    """Admin qarori: {"amal": "ulash", "talaba_id": 12} yoki {"amal": "rad"}."""

    bolim = "parentsbot"

    def post(self, request, pk):
        if not _ruxsat(request, "parentsbot.ulash"):
            return _xato("Bu amalga ruxsat yo'q", 403)
        try:
            sorov = Sorov.objects.select_related("abonent").get(pk=pk)
        except Sorov.DoesNotExist:
            return _xato("So'rov topilmadi", 404)
        amal = request.data.get("amal")
        talaba = None
        if amal == "ulash":
            talaba = User.objects.filter(pk=request.data.get("talaba_id"), role=User.Role.STUDENT).first()
            if talaba is None or not _korinadi(request.user, talaba.id):
                return _xato("O'quvchi topilmadi", 404)  # boshqa filialniki ham "topilmadi"
        elif cheklanganmi(request.user) and not any(
            _korinadi(request.user, i) for i in sorov.nomzodlar
        ):
            return _xato("So'rov topilmadi", 404)
        try:
            tg = tg_ol()
        except TgXato:
            tg = None
        try:
            xizmat.sorovni_hal_qil(sorov, amal, request.user, tg, talaba=talaba)
        except ValueError as e:
            return _xato(str(e), 400)
        logla(
            foydalanuvchi=request.user, harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH, obyekt=sorov,
            obyekt_turi="Ota-ona so'rovi", obyekt_nomi=f"{sorov.abonent.ism or sorov.abonent.telegram_id}",
            yangi_qiymatlar={"holat": sorov.holat, "talaba": talaba_ismi(talaba) if talaba else ""},
        )
        return Response(_sorov_dict(sorov, request.user))


class AbonentlarView(CrmView):
    """Ulangan ota-onalar (har birida ko'rinadigan farzandlari)."""

    bolim = "parentsbot"

    def get(self, request):
        natija = []
        for a in Abonent.objects.filter(boglanishlar__faol=True).distinct().order_by("-yaratilgan")[:300]:
            bolalar = [
                {"boglanish_id": b.id, "talaba": _talaba_dict(b.talaba), "usul": b.usul,
                 "usul_nomi": b.get_usul_display()}
                for b in a.boglanishlar.filter(faol=True).select_related("talaba")
                if _korinadi(request.user, b.talaba_id)
            ]
            if bolalar:
                natija.append({**_abonent_dict(a), "yaratilgan": a.yaratilgan, "farzandlar": bolalar})
        return Response(natija)


class BoglanishUzishView(CrmView):
    bolim = "parentsbot"

    def post(self, request, pk):
        if not _ruxsat(request, "parentsbot.ulash"):
            return _xato("Bu amalga ruxsat yo'q", 403)
        b = Boglanish.objects.filter(pk=pk, faol=True).select_related("abonent", "talaba").first()
        if b is None or not _korinadi(request.user, b.talaba_id):
            return _xato("Bog'lanish topilmadi", 404)
        b.faol = False
        b.save(update_fields=["faol"])
        logla(
            foydalanuvchi=request.user, harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH, obyekt=b,
            obyekt_turi="Ota-ona bog'lanishi", obyekt_nomi=talaba_ismi(b.talaba),
            yangi_qiymatlar={"faol": "False"},
        )
        return Response(status=204)


# ── Xabar vaqtlari sozlamasi ────────────────────────────────────────

_VAQT = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_BOOL_MAYDONLAR = (
    "davomat_yoqilgan", "davomat_kelmadi", "davomat_kechikdi", "davomat_sababli",
    "tolov_yoqilgan", "qarz_yoqilgan", "natija_yoqilgan",
)
_VAQT_MAYDONLAR = ("qarz_soati", "natija_soati", "tinch_boshi", "tinch_oxiri")
_KUN_MAYDONLAR = ("qarz_kunlari", "natija_kunlari")


def _sozlama_dict(s):
    d = {k: getattr(s, k) for k in _BOOL_MAYDONLAR + _KUN_MAYDONLAR}
    d.update({k: getattr(s, k).strftime("%H:%M") for k in _VAQT_MAYDONLAR})
    return d


class SozlamaView(CrmView):
    """Butun markazga ta'sir qiladi: o'qish — bo'lim egasiga, o'zgartirish — `parentsbot.sozlama`
    (cheklangan filial xodimiga emas)."""

    bolim = "parentsbot"

    def get(self, request):
        return Response(_sozlama_dict(ParentsBotSozlama.ol()))

    def put(self, request):
        if not _ruxsat(request, "parentsbot.sozlama"):
            return _xato("Bu amalga ruxsat yo'q", 403)
        if cheklanganmi(request.user):
            return _xato("Bu sozlama butun markazga ta'sir qiladi — uni faqat owner o'zgartiradi", 403)
        s = ParentsBotSozlama.ol()
        eski = _sozlama_dict(s)
        for k in _BOOL_MAYDONLAR:
            if k in request.data:
                if not isinstance(request.data[k], bool):
                    return _xato(f"{k}: ha/yo'q bo'lsin")
                setattr(s, k, request.data[k])
        for k in _VAQT_MAYDONLAR:
            if k in request.data:
                m = _VAQT.match(str(request.data[k]).strip())
                if not m:
                    return _xato(f"{k}: vaqtni SS:DD ko'rinishida yozing")
                setattr(s, k, time(int(m[1]), int(m[2])))
        for k in _KUN_MAYDONLAR:
            if k in request.data:
                kunlar = request.data[k]
                if not isinstance(kunlar, list) or any(
                    not isinstance(x, int) or isinstance(x, bool) or not 0 <= x <= 6 for x in kunlar
                ):
                    return _xato(f"{k}: kunlar 0 (dushanba) dan 6 (yakshanba) gacha sonlar ro'yxati bo'lsin")
                setattr(s, k, sorted(set(kunlar)))
        s.save()
        yangi = _sozlama_dict(s)
        logla(
            foydalanuvchi=request.user, harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH, obyekt=s,
            obyekt_turi="Ota-ona boti sozlamasi", obyekt_nomi="Xabar vaqtlari",
            eski_qiymatlar={k: str(v) for k, v in eski.items()}, yangi_qiymatlar={k: str(v) for k, v in yangi.items()},
        )
        return Response(yangi)
