"""CDI Listening HTML + audio -> "IELTS testlari"ga yuklanadigan ZIP (2026-10-22).

    python manage.py cdi_listening_zip "Full Listening CDI.html" audio.mp3 --chiqish test.zip
    python manage.py cdi_listening_zip ... --bazaga   # lokal bazada darhol yaratadi

ZIP admin panelida "IELTS testlari -> ZIP yuklash" orqali yuklanadi (deploy shart
emas): ichida test.json va bitta audio — u testning hamma qismlariga ulanadi
(`_test_yarat`). Test "private" yaratiladi — admin tekshirib, keyin ochadi.
O'girish qoidalari: `exercises/cdi_html.py`."""

import json
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from exercises.cdi_html import HtmlXatosi, html_dan_test


class Command(BaseCommand):
    help = "CDI Listening HTML + audio'dan IELTS testi ZIP'ini yasaydi (javob kaliti serverda qoladi)"

    def add_arguments(self, parser):
        parser.add_argument("html")
        parser.add_argument("audio")
        parser.add_argument("--nom", help="Test nomi (standart: 1-qism sarlavhasidan)")
        parser.add_argument("--chiqish", help="ZIP fayl yo'li (standart: HTML yonida, .zip)")
        parser.add_argument("--bazaga", action="store_true", help="ZIP o'rniga lokal bazada yaratish")

    def handle(self, *args, html, audio, nom=None, chiqish=None, bazaga=False, **kw):
        html_yol, audio_yol = Path(html), Path(audio)
        for yol in (html_yol, audio_yol):
            if not yol.is_file():
                raise CommandError(f"Fayl topilmadi: {yol}")
        try:
            test = html_dan_test(html_yol.read_text(encoding="utf-8"), nom=nom)
        except HtmlXatosi as e:
            raise CommandError(f"{html_yol.name}: {e}") from e
        jami = sum(len(q["savollar"]) for q in test["qismlar"])

        if bazaga:
            from accounts.models import Markaz
            from exercises.views import _test_yarat

            markaz = Markaz.objects.first()
            if markaz is None:
                raise CommandError("Bazada markaz yo'q")
            yaratilgan, xato = _test_yarat(test, markaz, audio_fayllar={audio_yol.name: audio_yol.read_bytes()})
            if xato:
                raise CommandError(xato["detail"])
            self.stdout.write(self.style.SUCCESS(f"Yaratildi: #{yaratilgan.pk} «{yaratilgan.name}», {jami} savol"))
            return

        zip_yol = Path(chiqish) if chiqish else html_yol.with_suffix(".zip")
        with zipfile.ZipFile(zip_yol, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.json", json.dumps(test, ensure_ascii=False, indent=1))
            zf.write(audio_yol, audio_yol.name)
        self.stdout.write(self.style.SUCCESS(f"ZIP: {zip_yol} — «{test['name']}», {jami} savol"))
