import json
from pathlib import Path

from django.core.management.base import BaseCommand

from games.models import GrammatikaSavoli

MANBA = (
    Path(__file__).resolve().parents[4]
    / "word-app-backup"
    / "content"
    / "word-app"
    / "data"
    / "grammar"
    / "questions.json"
)


class Command(BaseCommand):
    help = "Eski StudyCards grammatika savollarini (JSON) bazaga import qiladi."

    def handle(self, *args, **options):
        if GrammatikaSavoli.objects.exists():
            self.stdout.write("Grammatika savollari allaqachon import qilingan — o'tkazib yuborildi.")
            return

        if not MANBA.exists():
            self.stderr.write(f"Topilmadi: {MANBA}")
            return

        with open(MANBA, encoding="utf-8") as f:
            savollar = json.load(f)

        GrammatikaSavoli.objects.bulk_create(
            [
                GrammatikaSavoli(
                    mavzu=s["topic"],
                    savol=s["question"],
                    variantlar=s["options"],
                    togri=s["correct"],
                )
                for s in savollar
            ]
        )
        self.stdout.write(self.style.SUCCESS(f"Jami: {len(savollar)} savol import qilindi"))
