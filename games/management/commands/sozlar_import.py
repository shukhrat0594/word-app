import json
from pathlib import Path

from django.core.management.base import BaseCommand

from games.models import Soz

# Eski StudyCards loyihasidagi lug'at fayllari (word-app-backup).
MANBA_DIR = (
    Path(__file__).resolve().parents[4]
    / "word-app-backup"
    / "content"
    / "word-app"
    / "data"
    / "dictionary"
)

FAYLLAR = {
    "a1.json": Soz.Daraja.A1,
    "a2.json": Soz.Daraja.A2,
    "b1.json": Soz.Daraja.B1,
    "b2.json": Soz.Daraja.B2,
    "c1.json": Soz.Daraja.C1,
    "idioms.json": Soz.Daraja.IDIOM,
}


class Command(BaseCommand):
    help = "Eski StudyCards lug'at fayllaridan (JSON) so'zlarni bazaga import qiladi."

    def handle(self, *args, **options):
        if Soz.objects.exists():
            self.stdout.write("So'zlar allaqachon import qilingan — o'tkazib yuborildi.")
            return

        jami = 0
        for fayl_nomi, daraja in FAYLLAR.items():
            yol = MANBA_DIR / fayl_nomi
            if not yol.exists():
                self.stderr.write(f"Topilmadi: {yol}")
                continue

            with open(yol, encoding="utf-8") as f:
                sozlar = json.load(f)

            Soz.objects.bulk_create(
                [
                    Soz(
                        en=s["en"],
                        uz=s["uz"],
                        daraja=daraja,
                        turkum=s.get("type", ""),
                        misol=s.get("example", ""),
                    )
                    for s in sozlar
                ]
            )
            jami += len(sozlar)
            self.stdout.write(f"{fayl_nomi}: {len(sozlar)} so'z import qilindi")

        self.stdout.write(self.style.SUCCESS(f"Jami: {jami} so'z"))
