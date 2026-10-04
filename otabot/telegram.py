"""Telegram Bot API uchun kichik klient (httpx — loyihada allaqachon bor, yangi bog'liqlik yo'q)."""

import logging

import httpx

log = logging.getLogger("otabot")


class TgXato(Exception):
    pass


class Tg:
    def __init__(self, token, klient=None):
        if not token:
            raise TgXato("UTMOSTPARENTSBOT_TOKEN sozlanmagan")
        self._url = f"https://api.telegram.org/bot{token}"
        self._klient = klient or httpx.Client(timeout=45)

    def chaqir(self, metod, **parametrlar):
        try:
            r = self._klient.post(f"{self._url}/{metod}", json=parametrlar)
            data = r.json()
        except (httpx.HTTPError, ValueError) as xato:
            # Xato matnida URL (ya'ni TOKEN) bo'lishi mumkin — faqat turini yozamiz.
            raise TgXato(f"{metod}: {type(xato).__name__}") from None
        if not data.get("ok"):
            raise TgXato(f"{metod}: {data.get('error_code')} {data.get('description')}")
        return data["result"]

    def yangilanishlar(self, offset, kutish=30):
        return self.chaqir(
            "getUpdates", offset=offset, timeout=kutish,
            allowed_updates=["message", "callback_query"],
        )

    def yubor(self, chat_id, matn, tugmalar=None):
        parametrlar = {"chat_id": chat_id, "text": matn}
        if tugmalar:
            parametrlar["reply_markup"] = tugmalar
        return self.chaqir("sendMessage", **parametrlar)

    def callback_javob(self, callback_id):
        try:
            self.chaqir("answerCallbackQuery", callback_query_id=callback_id)
        except TgXato:
            pass  # bosilgan tugma "soat" belgisi qolib ketmasin — xato bo'lsa ahamiyatsiz
