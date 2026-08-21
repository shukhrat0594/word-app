"""Bir martalik migratsiya (2026-08-21): allaqachon mavjud Unit'larga
(struktura o'zgarishidan OLDIN yaratilganlarga) "Games" tugunini qo'shadi.

Idempotent: Unit'da "games" kalitli farzand allaqachon bo'lsa — tegilmaydi."""

from django.core.management.base import BaseCommand

from courses.models import KursTugun


class Command(BaseCommand):
    help = "Mavjud Unit'larga Games tugunini qo'shadi (agar hali yo'q bo'lsa)"

    def handle(self, *args, **options):
        qoshildi = 0
        for unit in KursTugun.objects.filter(unit_darsi=True):
            if KursTugun.objects.filter(parent=unit, kalit="games").exists():
                continue
            oxirgi_tartib = (
                KursTugun.objects.filter(parent=unit)
                .order_by("-tartib")
                .values_list("tartib", flat=True)
                .first()
                or 0
            )
            KursTugun.objects.create(
                kalit="games", nomi="Games", parent=unit,
                markaz=unit.markaz, tartib=oxirgi_tartib + 1,
            )
            qoshildi += 1
            self.stdout.write(f"{unit.nomi}: Games qo'shildi")

        self.stdout.write(self.style.SUCCESS(f"Tayyor: {qoshildi} ta Unit'ga Games qo'shildi"))
