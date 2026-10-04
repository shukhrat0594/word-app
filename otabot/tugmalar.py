"""Ota-ona uchun doimiy tugmalar menyusi (ekran pastida). Buyruq yozish shart emas.

Tugma bosilganda Telegram uning MATNINI xabar sifatida yuboradi — bot shu matnni
tugma deb taniydi (`tugma_buyrugi`).
"""

from .matnlar import t

# kalit -> (tugma kaliti, mos buyruq)
_TUGMALAR = {
    "farzandlar": "/farzandlarim",
    "til": "/til",
    "yordam": "/yordam",
    "stop": "/stop",
    "start": "/start",  # to'xtatilgan bo'lsa — qayta yoqish
}
TILLAR = ("uz", "ru")


def menyu(til, faol=True):
    """ReplyKeyboardMarkup: faol bo'lsa [Farzandlarim] [Til | Yordam] [To'xtatish]; to'xtatilgan bo'lsa — [Qayta yoqish]."""
    if faol:
        qatorlar = [
            [t(til, "tugma_farzandlar")],
            [t(til, "tugma_til"), t(til, "tugma_yordam")],
            [t(til, "tugma_stop")],
        ]
    else:
        qatorlar = [[t(til, "tugma_start")]]
    return {
        "keyboard": [[{"text": x} for x in qator] for qator in qatorlar],
        "resize_keyboard": True, "is_persistent": True,
    }


def tugma_buyrugi(matn):
    """Tugma matni (istalgan tilda) -> mos buyruq ('/farzandlarim'...); tugma bo'lmasa — None."""
    matn = (matn or "").strip()
    for til in TILLAR:
        for kalit, buyruq in _TUGMALAR.items():
            if matn == t(til, f"tugma_{kalit}"):
                return buyruq
    return None
