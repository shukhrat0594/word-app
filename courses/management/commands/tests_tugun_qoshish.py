"""Bir martalik migratsiya (2026-10-11, Matn-TZ 246): allaqachon mavjud
Unit'larga "Tests" tugunini qo'shadi (`games_tugun_qoshish` bilan bir xil
naqsh).

Idempotent: Unit'da "tests" kalitli farzand allaqachon bo'lsa — tegilmaydi.
2026-10-14: Tests Games'dan oldinga o'tkaziladi (pastga qarang)."""

from django.core.management.base import BaseCommand

from courses.models import KursTugun


class Command(BaseCommand):
    help = "Mavjud Unit'larga Tests tugunini qo'shadi (agar hali yo'q bo'lsa)"

    def handle(self, *args, **options):
        qoshildi = 0
        for unit in KursTugun.objects.filter(unit_darsi=True):
            if KursTugun.objects.filter(parent=unit, kalit="tests").exists():
                continue
            oxirgi_tartib = (
                KursTugun.objects.filter(parent=unit)
                .order_by("-tartib")
                .values_list("tartib", flat=True)
                .first()
                or 0
            )
            KursTugun.objects.create(
                kalit="tests", nomi="Tests", parent=unit,
                markaz=unit.markaz, tartib=oxirgi_tartib + 1,
            )
            qoshildi += 1
            self.stdout.write(f"{unit.nomi}: Tests qo'shildi")

        self.stdout.write(self.style.SUCCESS(f"Tayyor: {qoshildi} ta Unit'ga Tests qo'shildi"))

        # 2026-10-14, foydalanuvchi talabi: Tests Games'dan OLDIN turishi
        # kerak. Games Tests'dan oldin turgan Unit'larda tartiblar
        # almashtiriladi (idempotent — to'g'ri tartibdagilarga tegilmaydi).
        almashdi = 0
        for unit in KursTugun.objects.filter(unit_darsi=True):
            tests = KursTugun.objects.filter(parent=unit, kalit="tests").first()
            games = KursTugun.objects.filter(parent=unit, kalit="games").first()
            if tests and games and games.tartib < tests.tartib:
                tests.tartib, games.tartib = games.tartib, tests.tartib
                tests.save(update_fields=["tartib"])
                games.save(update_fields=["tartib"])
                almashdi += 1
        self.stdout.write(self.style.SUCCESS(f"Tests/Games o'rni almashdi: {almashdi} ta Unit"))
