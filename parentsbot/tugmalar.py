"""Ota-ona uchun doimiy tugmalar menyusi (ekran pastida). Buyruq yozish shart emas.

Tugma bosilganda Telegram uning MATNINI xabar sifatida yuboradi — bot shu matnni
tugma deb taniydi (`tugma_buyrugi`).
"""

import re

from .matnlar import t

# kalit -> (tugma kaliti, mos buyruq)
_TUGMALAR = {
    "farzandlar": "/farzandlarim",
    "til": "/til",
    "yordam": "/yordam",
}
TILLAR = ("uz", "ru")


def menyu(til):
    """ReplyKeyboardMarkup: [Farzandlarim] [Til | Yordam]. Xabarlarni o'chirish/to'xtatish tugmasi
    yo'q — qaysi xabarlar borishini markaz hal qiladi."""
    qatorlar = [
        [t(til, "tugma_farzandlar")],
        [t(til, "tugma_til"), t(til, "tugma_yordam")],
    ]
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
