"""Beginner > Unit 2–14 > Tests bo'limlariga "Headway/Beginner Tests" PDF'laridagi
savollarni kiritadi (2026-10-12, Matn-TZ Shuxrat_26). Har Unit'ga ikki mashq:
Part 1 Grammar va Part 2 Vocabulary & Everyday English, javoblar PDF'dagi
ANSWER KEY bo'yicha (savollar beginner_testlari.json'da).

PDF kamchiliklari: Unit 3'da 20-savol yo'q (29 savol); Unit 7 kalitida
5, 10, 15, 20, 25, 30 kesilgan — javoblar savol mazmunidan qo'yilgan.

Unit N — Beginner ichidagi N-chi unit_darsi tugun (tartib bo'yicha).
Idempotent: Tests tugunida mashq allaqachon bo'lsa — tegilmaydi."""

import json
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from courses.models import KursMashq, KursTugun

from .beginner_unit1_testlari import savollar

MALUMOT = Path(__file__).with_name("beginner_testlari.json")
QISM_NOMLARI = ["PART 1: GRAMMAR", "PART 2: VOCABULARY & EVERYDAY ENGLISH"]


class Command(BaseCommand):
    help = "Beginner Unit 2–14 Tests bo'limlariga PDF test savollarini kiritadi"

    def handle(self, *args, **options):
        call_command("tests_tugun_qoshish", stdout=self.stdout)
        beginner = KursTugun.objects.filter(kalit="beginner", parent__kalit="ingliz_tili").first()
        unitlar = list(KursTugun.objects.filter(
            parent=beginner, unit_darsi=True).order_by("tartib", "id")) if beginner else []
        for n, qismlar in json.loads(MALUMOT.read_text(encoding="utf-8")).items():
            n = int(n)
            if n > len(unitlar):
                self.stdout.write(self.style.WARNING(f"Beginner Unit {n} topilmadi — o'tkazib yuborildi"))
                continue
            unit = unitlar[n - 1]
            tests = KursTugun.objects.get(parent=unit, kalit="tests")
            if tests.mashqlar.exists():
                self.stdout.write(f"{unit.nomi} > Tests: mashqlar allaqachon bor — tegilmadi")
                continue
            for i, (nom, qatorlar) in enumerate(zip(QISM_NOMLARI, qismlar), start=1):
                KursMashq.objects.create(tugun=tests, tartib=i, matn=f"{nom} ({len(qatorlar)} Questions)",
                                         savollar=savollar(qatorlar))
            self.stdout.write(self.style.SUCCESS(
                f"{unit.nomi} > Tests: {len(qismlar)} mashq, {sum(len(q) for q in qismlar)} savol kiritildi"))
