"""Headway 5th edition Wordlist'ini Vocabulary bo'limlariga yozadi
(2026-10-11, foydalanuvchi talabi).

Manba — `Headway/Wordlist/*.pdf` (Oxford'ning rasmiy so'z ro'yxatlari,
Beginner...Upper-Intermediate). PDF'dan ajratilgan va o'zbekcha/ruscha
tarjima qilingan so'zlar `courses/fixtures/headway_wordlist.json`da.

Foydalanuvchi qarori: Wordlist mavjud Vocabulary so'zlarini (AI
Student's Book/Workbook sahifalaridan olgan) TO'LIQ ALMASHTIRADI. Har
Unit'ning Vocabulary tugunidagi barcha so'zlar o'chirilib, Wordlist
so'zlari `manba=wordlist` bilan yoziladi. Idempotent — qayta ishga
tushirilsa natija o'zgarmaydi.

    python manage.py headway_wordlist_yukla [--daraja beginner] [--quruq]
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import KursSoz, KursTugun

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "headway_wordlist.json"


class Command(BaseCommand):
    help = "Headway Wordlist so'zlarini (uz/ru tarjimasi bilan) Vocabulary bo'limlariga yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--daraja", help="Faqat shu daraja (masalan beginner)")
        parser.add_argument("--quruq", action="store_true", help="Bazaga yozmasdan faqat tekshirish")

    def handle(self, *args, daraja=None, quruq=False, **kw):
        malumot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if daraja:
            if daraja not in malumot:
                raise CommandError(f"'{daraja}' fixture'da yo'q: {', '.join(malumot)}")
            malumot = {daraja: malumot[daraja]}

        # Avval hammasini tekshiramiz — biror Unit/Vocabulary topilmasa
        # yoki tarjima bo'sh bo'lsa, hech narsa yozilmaydi.
        reja = []
        for d, sozlar in malumot.items():
            unitlar = {}
            for s in sozlar:
                if not (s.get("uz") or "").strip() or not (s.get("ru") or "").strip():
                    raise CommandError(f"{d}: '{s['en']}' tarjimasi to'liq emas")
                unitlar.setdefault(s["unit"], []).append(s)
            for raqam, ro in sorted(unitlar.items()):
                # Har markazning o'z daraxti bor — hammasiga yoziladi.
                vocablar = list(KursTugun.objects.filter(
                    parent__kalit=f"{d}_unit_{raqam}", kalit="vocabulary"
                ))
                if not vocablar:
                    raise CommandError(f"{d} Unit {raqam}: Vocabulary tuguni topilmadi")
                reja += [(d, raqam, v, ro) for v in vocablar]

        with transaction.atomic():
            for d, raqam, vocab, ro in reja:
                eski = vocab.sozlar.count()
                if not quruq:
                    vocab.sozlar.all().delete()
                    KursSoz.objects.bulk_create([
                        KursSoz(
                            tugun=vocab, tartib=i, en=s["en"], uz=s["uz"], ru=s["ru"],
                            turkum=s.get("turkum", ""), misol=s.get("misol", ""),
                            manba=KursSoz.Manba.WORDLIST,
                        )
                        for i, s in enumerate(ro, start=1)
                    ])
                self.stdout.write(f"{d} Unit {raqam}: {eski} -> {len(ro)}")
        self.stdout.write(self.style.SUCCESS(
            f"{'Tekshirildi' if quruq else 'Yozildi'}: {sum(len(r[3]) for r in reja)} so'z"
        ))
