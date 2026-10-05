"""Suhbat mantiqi. Tarmoqsiz sinash mumkin: `Tg` o'rniga `yubor()` va `callback_javob()` bor
istalgan obyekt beriladi.

Faqat shaxsiy chat (private) qayta ishlanadi; guruh va kanal xabarlari e'tiborsiz.

Qaysi xabarlar borishini MARKAZ hal qiladi (CRM sozlamasi) — ota-onada o'chirish/to'xtatish yo'q.
Ota-ona botni bloklasa — markazga bildirishnoma (`xizmat.bloklandi`).
"""

import logging
from datetime import timedelta

from django.utils import timezone

from . import matnlar, moslash, tugmalar, xizmat
from .matnlar import t
from .models import Abonent, Boglanish
from .telegram import TgXato

log = logging.getLogger("parentsbot")

URINISH_CHEGARASI = 3  # bitta Telegram hisobi 24 soatda ko'pi bilan shuncha marta ism bilan urinadi
TIL_TUGMALARI = {"inline_keyboard": [[
    {"text": "🇺🇿 O'zbekcha", "callback_data": "til:uz"},
    {"text": "🇷🇺 Русский", "callback_data": "til:ru"},
]]}
KLAVIATURA_YOP = {"remove_keyboard": True}


def telefon_tugmasi(til):
    return {
        "keyboard": [[{"text": t(til, "telefon_tugma"), "request_contact": True}]],
        "resize_keyboard": True, "one_time_keyboard": True,
    }


class Bot:
    def __init__(self, tg):
        self.tg = tg

    # ── kirish nuqtasi ──────────────────────────────────────────────
    def qayta_ishla(self, update):
        try:
            self._ishla(update)
        except TgXato as xato:
            log.warning("Telegram xatosi: %s", xato)
        except Exception:  # noqa: BLE001 — bitta yangilanish botni to'xtatmasin
            log.exception("Yangilanishni qayta ishlashda xato")

    def _ishla(self, update):
        azolik = update.get("my_chat_member")
        if azolik:
            return self._azolik(azolik)
        cb = update.get("callback_query")
        if cb:
            return self._callback(cb)
        xabar = update.get("message")
        if not xabar or (xabar.get("chat") or {}).get("type") != "private":
            return
        kim = xabar.get("from") or {}
        if kim.get("is_bot") or not kim.get("id"):
            return
        ab = self._abonent(kim)
        if xabar.get("contact"):
            return self._kontakt(ab, xabar["contact"], kim)
        matn = (xabar.get("text") or "").strip()
        if not matn:
            return
        if matn.startswith("/"):
            return self._buyruq(ab, matn.split()[0].split("@")[0].lower())
        buyruq = tugmalar.tugma_buyrugi(matn)
        if buyruq:
            return self._buyruq(ab, buyruq)
        self._matn(ab, matn)

    def _abonent(self, kim):
        ism = " ".join(x for x in (kim.get("first_name"), kim.get("last_name")) if x)[:200]
        ab, yaratildi = Abonent.objects.get_or_create(
            telegram_id=kim["id"], defaults={"ism": ism, "username": (kim.get("username") or "")[:100]})
        if not yaratildi and (ab.ism != ism or ab.username != (kim.get("username") or "")[:100]):
            ab.ism, ab.username = ism, (kim.get("username") or "")[:100]
            ab.save(update_fields=["ism", "username"])
        xizmat.blokdan_chiqdi(ab)  # botga yozyapti — demak bloklamagan
        return ab

    def _azolik(self, m):
        """`my_chat_member`: ota-ona botni blokladi ("kicked") yoki blokdan chiqardi ("member").
        Telegram buni darhol yuboradi — markaz navbatdagi xabarni kutmasdan biladi."""
        if (m.get("chat") or {}).get("type") != "private":
            return
        ab = Abonent.objects.filter(telegram_id=(m.get("from") or {}).get("id")).first()
        if ab is None:
            return
        holat = (m.get("new_chat_member") or {}).get("status")
        if holat == "kicked":
            xizmat.bloklandi(ab)
        elif holat == "member":
            xizmat.blokdan_chiqdi(ab)

    def _yubor(self, ab, kalit, tugmalar=None, **q):
        self.tg.yubor(ab.telegram_id, t(ab.til, kalit, **q), tugmalar)

    def _menyu(self, ab):
        """Doimiy tugmalar: ulangan ota-onaga; hali ulanmaganga — yo'q."""
        return tugmalar.menyu(ab.til) if xizmat.faol_farzandlar(ab) else None

    # ── buyruqlar ───────────────────────────────────────────────────
    def _buyruq(self, ab, buyruq):
        if buyruq == "/start":
            if ab.holat == Abonent.Holat.TIL:
                return self._yubor(ab, "til_tanlang", TIL_TUGMALARI)
            if xizmat.faol_farzandlar(ab):
                return self._farzandlar(ab)
            ab.holat = Abonent.Holat.TELEFON
            ab.save(update_fields=["holat"])
            return self._yubor(ab, "salom_telefon", telefon_tugmasi(ab.til))
        if buyruq == "/farzandlarim":
            return self._farzandlar(ab)
        if buyruq == "/til":
            return self._yubor(ab, "til_tanlang", TIL_TUGMALARI)
        if buyruq == "/yordam":
            return self._yubor(ab, "yordam", self._menyu(ab))
        self._tushunmadim(ab)

    def _tushunmadim(self, ab):
        # Joriy menyu bilan: telefonda eski tugmalar ("Sozlamalar", "To'xtatish") qolgan bo'lsa,
        # bosilganda shu javob ularni yangisiga almashtiradi.
        self._yubor(ab, "tushunmadim", self._menyu(ab))

    def _farzandlar(self, ab):
        bolalar = xizmat.faol_farzandlar(ab)
        if not bolalar:
            return self._yubor(ab, "farzand_yoq")
        royxat = "\n".join(f"• {moslash.talaba_ismi(b)}" for b in bolalar)
        self._yubor(ab, "farzandlar", self._menyu(ab), royxat=royxat)

    def _callback(self, cb):
        kim = cb.get("from") or {}
        data = cb.get("data") or ""
        if kim.get("is_bot") or not kim.get("id"):
            return
        til = data[4:] if data.startswith("til:") else None
        if til not in matnlar.TILLAR:
            # eski xabardagi tugma (masalan olib tashlangan "Sozlamalar") — "soat" osilib qolmasin
            return self.tg.callback_javob(cb.get("id"))
        ab = self._abonent(kim)
        self.tg.callback_javob(cb.get("id"))
        ab.til = til
        if ab.holat == Abonent.Holat.TIL:
            ab.holat = Abonent.Holat.TELEFON
            ab.save(update_fields=["til", "holat"])
            return self._yubor(ab, "salom_telefon", telefon_tugmasi(til))
        ab.save(update_fields=["til"])
        # Ulanish jarayonining o'rtasida til almashsa — joriy savol yangi tilda qayta beriladi
        # (aks holda telefon tugmasi yo'qolib, ota-ona nima qilishini bilmay qolardi).
        if ab.holat == Abonent.Holat.TELEFON:
            return self._yubor(ab, "salom_telefon", telefon_tugmasi(til))
        if ab.holat == Abonent.Holat.FARZAND_ISM:
            return self._yubor(ab, "farzand_ism_so")
        if ab.holat == Abonent.Holat.FARZAND_SANA:
            return self._yubor(ab, "farzand_sana_so")
        self._yubor(ab, "til_ozgardi", self._menyu(ab))

    # ── telefon ─────────────────────────────────────────────────────
    def _kontakt(self, ab, kontakt, kim):
        # Faqat O'Z raqami: boshqaning kontaktini yuborib farzandini ochib bo'lmaydi.
        if kontakt.get("user_id") != kim["id"]:
            return self._yubor(ab, "begona_kontakt", telefon_tugmasi(ab.til))
        ab.telefon = (kontakt.get("phone_number") or "")[:20]
        topildi = moslash.telefon_boyicha(ab.telefon)
        if topildi:
            xizmat.ulash(ab, topildi, Boglanish.Usul.TELEFON)
            ab.holat = Abonent.Holat.TAYYOR
            ab.save(update_fields=["telefon", "holat"])
            return self._yubor(ab, "ulandi", self._menyu(ab), ismlar=xizmat.ismlar_matni(topildi))
        ab.holat = Abonent.Holat.FARZAND_ISM
        ab.save(update_fields=["telefon", "holat"])
        self._yubor(ab, "farzand_ism_so", KLAVIATURA_YOP)

    # ── ism va tug'ilgan sana ───────────────────────────────────────
    def _matn(self, ab, matn):
        h = ab.holat
        if h == Abonent.Holat.FARZAND_ISM:
            if sum(c.isalpha() for c in matn) < 3:
                return self._yubor(ab, "ism_xato")
            ab.kontekst = {"ism": matn[:100]}
            ab.holat = Abonent.Holat.FARZAND_SANA
            ab.save(update_fields=["kontekst", "holat"])
            return self._yubor(ab, "farzand_sana_so")
        if h == Abonent.Holat.FARZAND_SANA:
            return self._sana(ab, matn)
        if h == Abonent.Holat.TIL:
            return self._yubor(ab, "til_tanlang", TIL_TUGMALARI)
        if h == Abonent.Holat.TELEFON:
            return self._yubor(ab, "salom_telefon", telefon_tugmasi(ab.til))
        self._tushunmadim(ab)

    def _sana(self, ab, matn):
        sana = moslash.sana_tahlil(matn)
        if sana is None:
            return self._yubor(ab, "sana_xato")
        hozir = timezone.now()
        chegara = hozir - timedelta(hours=24)
        songgilari = [x for x in ab.urinishlar if x > chegara.isoformat()]
        if len(songgilari) >= URINISH_CHEGARASI:
            return self._yubor(ab, "urinish_kop")
        ab.urinishlar = songgilari + [hozir.isoformat()]
        ism = (ab.kontekst or {}).get("ism", "")
        mos = moslash.aniq_moslik(ism, sana)
        ab.kontekst = {}
        ab.holat = Abonent.Holat.TAYYOR
        ab.save(update_fields=["urinishlar", "kontekst", "holat"])
        if len(mos) == 1:
            xizmat.ulash(ab, mos, Boglanish.Usul.ISM_SANA)
            return self._yubor(ab, "ulandi", self._menyu(ab), ismlar=xizmat.ismlar_matni(mos))
        # Topilmadi yoki bir nechta mos keldi: ota-onaga ATAYLAB bir xil javob; adminlar hal qiladi.
        xizmat.sorov_yarat(ab, ism, matn.strip()[:30], moslash.nomzodlar(ism, sana))
        self._yubor(ab, "sorov_yuborildi")
