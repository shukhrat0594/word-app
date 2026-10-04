"""Ota-ona botini ishga tushiradi (Railway'da alohida service): `python manage.py otabot`.

Long polling: Telegram'dan yangilanishlarni oladi va `otabot.bot.Bot`ga beradi. Oxirgi ko'rilgan
yangilanish bazada saqlanadi — qayta ishga tushganda xabarlar takrorlanmaydi.
"""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from otabot.bot import Bot
from otabot.models import OtaBotKuzatuv
from otabot.telegram import Tg, TgXato

log = logging.getLogger("otabot")


class Command(BaseCommand):
    help = "Ota-ona nazorati botini (Telegram, long polling) ishga tushiradi"

    def add_arguments(self, parser):
        parser.add_argument("--bir", action="store_true", help="Bitta partiyani qayta ishlab chiqib ketadi (sinov)")

    def handle(self, *args, **opts):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        tg = Tg(settings.UTMOSTPARENTSBOT_TOKEN)
        tg.chaqir("deleteWebhook")  # polling bilan webhook to'qnashmasin
        bot = Bot(tg)
        offset = OtaBotKuzatuv.ol().oxirgi_update_id + 1
        log.info("Ota-ona boti ishga tushdi (offset %s)", offset)
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
                OtaBotKuzatuv.objects.filter(pk=1).update(oxirgi_update_id=u["update_id"])
            close_old_connections()
            if opts["bir"]:
                return
