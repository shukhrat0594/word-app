"""Bir martalik tozalash (2026-08-11): `TestPapkasi.bolim` maydoni olib
tashlangandan keyin, avval har bo'lim uchun alohida yaratilgan bir xil
nomli papkalarni (masalan "Band 6.5-7.5" — reading/listening/writing/
speaking uchun 4 ta alohida qator) BITTAGA birlashtiradi.

Guruhlash (nomi, manba, markaz) bo'yicha — eng kichik id'li qator asosiy
qilib qoldiriladi, qolganlarining testlari o'sha asosiyga ko'chiriladi,
bo'sh qolgan takroriy qatorlar o'chiriladi.

IDEMPOTENT — qayta ishga tushirish xavfsiz (takror qolmasa, hech narsa
qilmaydi). `--dry-run` bilan faqat nima qilinishini ko'rsatadi, o'zgartirmaydi.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from exercises.models import ImtihonTest, TestPapkasi


class Command(BaseCommand):
    help = "Nomi/manba/markaz bo'yicha bir xil TestPapkasi qatorlarini birlashtiradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Faqat nima qilinishini ko'rsatadi, bazani o'zgartirmaydi",
        )

    def handle(self, *args, dry_run=False, **options):
        guruhlar = defaultdict(list)
        for p in TestPapkasi.objects.order_by("id"):
            guruhlar[(p.nomi, p.manba, p.markaz_id)].append(p)

        takrorlar = {kalit: royxat for kalit, royxat in guruhlar.items() if len(royxat) > 1}
        if not takrorlar:
            self.stdout.write(self.style.SUCCESS("Takroriy papka topilmadi — hammasi toza."))
            return

        for (nomi, manba, markaz_id), royxat in takrorlar.items():
            asosiy, *ortiqchalar = royxat
            ortiqcha_idlar = [p.id for p in ortiqchalar]
            testlar_soni = ImtihonTest.objects.filter(papka_id__in=ortiqcha_idlar).count()

            self.stdout.write(
                f"{nomi!r} (manba={manba}, markaz={markaz_id}): "
                f"asosiy #{asosiy.id} qoladi, {len(ortiqchalar)} ta takror "
                f"(#{ortiqcha_idlar}) birlashtiriladi, {testlar_soni} test ko'chadi"
            )
            if dry_run:
                continue

            ImtihonTest.objects.filter(papka_id__in=ortiqcha_idlar).update(papka=asosiy)
            TestPapkasi.objects.filter(id__in=ortiqcha_idlar).delete()

        if dry_run:
            self.stdout.write(self.style.WARNING("--dry-run: hech narsa o'zgartirilmadi."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{len(takrorlar)} guruh birlashtirildi."))
