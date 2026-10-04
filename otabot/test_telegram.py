import logging

from django.test import SimpleTestCase

from otabot import telegram  # noqa: F401 — import log sozlamasini o'rnatadi
from otabot.telegram import Tg, TgXato


class TokenLogdaYoqTest(SimpleTestCase):
    def test_httpx_loglari_ogohlantirishdan_boshlanadi(self):
        # INFO darajasida httpx URL (ya'ni TOKEN) yozardi
        self.assertGreaterEqual(logging.getLogger("httpx").getEffectiveLevel(), logging.WARNING)
        self.assertGreaterEqual(logging.getLogger("httpcore").getEffectiveLevel(), logging.WARNING)

    def test_xato_matnida_token_yoq(self):
        import httpx

        class Buzuq:
            def post(self, *a, **k):
                raise httpx.ConnectError("https://api.telegram.org/botSIRLI:TOKEN/getMe ulanmadi")

        with self.assertRaises(TgXato) as ctx:
            Tg("SIRLI:TOKEN", klient=Buzuq()).chaqir("getMe")
        self.assertNotIn("SIRLI", str(ctx.exception))
        self.assertNotIn("TOKEN", str(ctx.exception))
