import logging

from django.test import SimpleTestCase

from parentsbot import telegram  # noqa: F401 — import log sozlamasini o'rnatadi
from parentsbot.telegram import Tg, TgXato


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


class BuyruqlarMenyusiTest(SimpleTestCase):
    def test_buyruqlar_ornatiladi(self):
        from parentsbot.matnlar import BUYRUQLAR

        class Yozuvchi:
            def __init__(self):
                self.chaqiruvlar = []

            def post(self, url, json=None):
                self.chaqiruvlar.append((url.rsplit("/", 1)[-1], json))

                class R:
                    def json(self_):
                        return {"ok": True, "result": True}
                return R()

        y = Yozuvchi()
        Tg("123456:ABC", klient=y).buyruqlarni_ornat(BUYRUQLAR)
        self.assertTrue(all(m == "setMyCommands" for m, _ in y.chaqiruvlar))
        # uz: tilsiz + "uz"; ru: "ru"
        tillar = [j.get("language_code") for _, j in y.chaqiruvlar]
        self.assertEqual(tillar, [None, "uz", "ru"])
        nomlar = [c["command"] for c in y.chaqiruvlar[0][1]["commands"]]
        self.assertEqual(nomlar, ["start", "farzandlarim", "til", "yordam"])

    def test_har_buyruq_botda_bor(self):
        from parentsbot.matnlar import BUYRUQLAR

        # menyudagi har buyruq botda ishlaydi (tushunmadim bermaydi)
        kodda = {"/start", "/farzandlarim", "/til", "/yordam"}
        for til, royxat in BUYRUQLAR.items():
            self.assertEqual({"/" + b for b, _ in royxat}, kodda, til)
            for _, tavsif in royxat:
                self.assertLessEqual(len(tavsif), 256)
