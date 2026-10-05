"""Ota-ona uchun doimiy tugmalar menyusi (ekran pastida). Buyruq yozish shart emas.

Tugma bosilganda Telegram uning MATNINI xabar sifatida yuboradi — bot shu matnni
tugma deb taniydi (`tugma_buyrugi`).
"""

import re

from .matnlar import t

# kalit -> (tugma kaliti, mos buyruq)
_TUGMALAR = {
    "farzandlar": "/farzandlarim",
    "sozlamalar": "/sozlamalar",
    "til": "/til",
    "yordam": "/yordam",
    "stop": "/stop",
    "start": "/start",  # to'xtatilgan bo'lsa — qayta yoqish
}
TILLAR = ("uz", "ru")


def menyu(til, faol=True):
    """ReplyKeyboardMarkup: faol bo'lsa [Farzandlarim | Sozlamalar] [Til | Yordam] [To'xtatish];
    to'xtatilgan bo'lsa — [Qayta yoqish]."""
    if faol:
        qatorlar = [
            [t(til, "tugma_farzandlar"), t(til, "tugma_sozlamalar")],
            [t(til, "tugma_til"), t(til, "tugma_yordam")],
            [t(til, "tugma_stop")],
        ]
    else:
        qatorlar = [[t(til, "tugma_start")]]
    return {
        "keyboard": [[{"text": x} for x in qator] for qator in qatorlar],
        "resize_keyboard": True, "is_persistent": True,
    }


def _soz_qismi(matn):
    """Tugma matnining faqat so'zlari: emoji, ko'rinmas belgilar (U+FE0F, ZWJ) va tinish belgilarisiz.
    Telegram tugma matnini qaytarib yuborganda emojini o'zgartirishi mumkin (masalan "⚙️" ->
    "⚙" — U+FE0F tushib qoladi), shuning uchun harfma-harf solishtirib bo'lmaydi."""
    return re.sub(r"[^\w']+", " ", matn or "").strip().casefold()


def tugma_buyrugi(matn):
    """Tugma matni (istalgan tilda) -> mos buyruq ('/farzandlarim'...); tugma bo'lmasa — None."""
    soz = _soz_qismi(matn)
    if not soz:
        return None
    for til in TILLAR:
        for kalit, buyruq in _TUGMALAR.items():
            if soz == _soz_qismi(t(til, f"tugma_{kalit}")):
                return buyruq
    return None
