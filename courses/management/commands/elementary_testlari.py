"""Elementary > Unit 1-12 > Tests bo'limlariga Unit testlarini kiritadi
(2026-10-14, foydalanuvchi talabi).

Manba — `Headway/Elementary tests/Elementary.zip` (har Unit uchun PDF/DOCX
test, 30 savol: Grammar 15 + Vocabulary & Everyday English 15, javob
kaliti bilan). Ajratilgan savollar `courses/fixtures/elementary_testlari.json`da.

Idempotent: Tests tugunida mashq allaqachon bo'lsa — tegilmaydi
(`--qayta` bilan eskisi o'chirilib qayta yoziladi)."""

import json
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import KursMashq, KursTugun

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "elementary_testlari.json"
QISMLAR = [
    ("PART 1: GRAMMAR (15 Questions)", slice(0, 15)),
    ("PART 2: VOCABULARY & EVERYDAY ENGLISH (15 Questions)", slice(15, 30)),
]


class Command(BaseCommand):
    help = "Elementary Unit 1-12 Tests bo'limlariga test savollarini kiritadi"

    def add_arguments(self, parser):
        parser.add_argument("--qayta", action="store_true", help="Mavjud mashqlarni o'chirib qayta yozish")

    def handle(self, *args, qayta=False, **options):
        call_command("tests_tugun_qoshish", stdout=self.stdout)
        malumot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with transaction.atomic():
            for raqam, savollar in sorted(malumot.items(), key=lambda x: int(x[0])):
                for tests in KursTugun.objects.filter(
                    kalit="tests", parent__kalit=f"elementary_unit_{raqam}"
                ):
                    if tests.mashqlar.exists():
                        if not qayta:
                            self.stdout.write(f"Unit {raqam} > Tests: mashqlar bor — tegilmadi")
                            continue
                        tests.mashqlar.all().delete()
                    for i, (matn, qism) in enumerate(QISMLAR, start=1):
                        KursMashq.objects.create(
                            tugun=tests, tartib=i, matn=matn, savollar=savollar[qism]
                        )
                    self.stdout.write(f"Unit {raqam} > Tests: {len(savollar)} savol kiritildi")
