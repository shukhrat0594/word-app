"""Ota-ona botini ishga tushiradi: `python manage.py parentsbot`. Railway'da sayt bilan bitta
konteynerda, fonda ishlaydi (`railway.json` -> startCommand). Bir vaqtda faqat BITTA nusxa
ishlashi kerak (Telegram 409) — lokalda prod bilan birga ishga tushirilmasin.

Long polling: Telegram'dan yangilanishlarni oladi va `parentsbot.bot.Bot`ga beradi. Oxirgi ko'rilgan
yangilanish bazada saqlanadi — qayta ishga tushganda xabarlar takrorlanmaydi.
"""

import logging
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from parentsbot.bot import Bot
from parentsbot.matnlar import BUYRUQLAR
from parentsbot.models import ParentsBotKuzatuv
from parentsbot.telegram import Tg, TgXato
from parentsbot.xabarlar import skanerla_hammasi, yubor_navbat

log = logging.getLogger("parentsbot")

TEKSHIRUV_SEK = 30  # yangi davomat/to'lov/qarz/natija va navbat shuncha sekundda bir tekshiriladi


def xabar_bir_marta(tg):
    skanerla_hammasi()
    yubor_navbat(tg)


def xabar_oqimi(tg):
    """Ota-onaga xabar yuborish oqimi (suhbat oqimi bilan parallel). Xato bo'lsa to'xtamaydi."""
    while True:
        try:
            xabar_bir_marta(tg)
        except Exception:  # noqa: BLE001
            log.exception("Xabar oqimi xatosi")
        finally:
            close_old_connections()
        time.sleep(TEKSHIRUV_SEK)


class Command(BaseCommand):
    help = "Ota-ona nazorati botini (Telegram, long polling) ishga tushiradi"

    def add_arguments(self, parser):
        parser.add_argument("--bir", action="store_true", help="Bitta partiyani qayta ishlab chiqib ketadi (sinov)")

    def handle(self, *args, **opts):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        # basicConfig'dan KEYIN: httpx URL'i (ya'ni bot tokeni) log'ga tushmasin.
        for nom in ("httpx", "httpcore"):
            logging.getLogger(nom).setLevel(logging.WARNING)
        if not getattr(settings, "UTMOSTPARENTSBOT_TOKEN", ""):
            # Railway'da sayt bilan bitta konteynerda ishga tushadi (railway.json): token hali
            # qo'shilmagan bo'lsa — jimgina chiqadi, sayt bundan ta'sirlanmaydi.
            log.warning("UTMOSTPARENTSBOT_TOKEN sozlanmagan — ota-ona boti ishga tushmadi")
            return
        tg = Tg(settings.UTMOSTPARENTSBOT_TOKEN)
        tg.chaqir("deleteWebhook")  # polling bilan webhook to'qnashmasin
        try:
            tg.buyruqlarni_ornat(BUYRUQLAR)  # "/" bosilganda buyruqlar menyusi
        except TgXato as xato:
            log.warning("Buyruqlar menyusi o'rnatilmadi: %s", xato)
        bot = Bot(tg)
        offset = ParentsBotKuzatuv.ol().oxirgi_update_id + 1
        log.info("Ota-ona boti ishga tushdi (offset %s)", offset)
        if opts["bir"]:
            xabar_bir_marta(tg)
        else:
            threading.Thread(target=xabar_oqimi, args=(tg,), name="parentsbot-xabar", daemon=True).start()
        while True:
            try:
                yangilar = tg.yangilanishlar(offset, kutish=1 if opts["bir"] else 30)
            except TgXato as xato:
                log.warning("getUpdates xatosi: %s", xato)
                time.sleep(5)
                continue
            for u in yangilar:
                bot.qayta_ishla(u)
                offset = u["update_id"] + 1
                ParentsBotKuzatuv.objects.filter(pk=1).update(oxirgi_update_id=u["update_id"])
            close_old_connections()
            if opts["bir"]:
                return
