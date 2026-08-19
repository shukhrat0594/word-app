"""Bir martalik migratsiya (2026-08-19): eski tuzilmadan
(Unit > Student's Book/Workbook > Mashqlar/Vocabulary, har kitobda O'Z
Vocabulary'si) yangisiga (Unit > Student's Book/Workbook (bevosita
mashqlar) + Unit > Vocabulary (ikkalasiga umumiy)) o'tkazadi.

Idempotent: eski tugunlar (kalit="mashqlar"/kitob ichidagi "vocabulary")
topilmasa hech narsa qilmaydi — xavfsiz qayta-qayta ishga tushiriladi
(local va prod'da bir marta qo'lda chaqiriladi, `prod_boshlangich`ga
ULANMAYDI — bu faqat MAVJUD noto'g'ri tuzilmani tuzatish uchun, yangi
Unit'lar allaqachon to'g'ri tuzilmada yaratiladi)."""

from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import KursMashq, KursSoz, KursTugun

KITOB_KALITLARI = ("students_book", "workbook")


class Command(BaseCommand):
    help = "Unit'lardagi Student's Book/Workbook Vocabulary'sini Unit darajasidagi umumiy Vocabulary'ga birlashtiradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Hech narsa o'zgartirmasdan, nima qilinishini ko'rsatadi",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            self._migratsiya(options)

    def _migratsiya(self, options):
        dry_run = options["dry_run"]
        units = KursTugun.objects.filter(unit_darsi=True).order_by("id")
        jami_kochirilgan_mashq = 0
        jami_kochirilgan_soz = 0
        jami_tozalangan_tugun = 0

        for unit in units:
            kitoblar = list(KursTugun.objects.filter(parent=unit, kalit__in=KITOB_KALITLARI))
            if not kitoblar:
                continue

            vocab = KursTugun.objects.filter(parent=unit, kalit="vocabulary").first()
            if not vocab and not dry_run:
                vocab = KursTugun.objects.create(
                    kalit="vocabulary", nomi="Vocabulary", parent=unit,
                    markaz=unit.markaz, tartib=len(kitoblar) + 1,
                )

            for kitob in kitoblar:
                manba = kitob.kalit
                matn_maydoni = "matn" if manba == "students_book" else "matn_workbook"

                eski_vocab = KursTugun.objects.filter(parent=kitob, kalit="vocabulary").first()
                eski_mashqlar_tugun = KursTugun.objects.filter(parent=kitob, kalit="mashqlar").first()

                if eski_vocab:
                    soz_soni = eski_vocab.sozlar.count()
                    matn_bormi = bool(eski_vocab.matn)
                    self.stdout.write(
                        f"{unit.nomi} > {kitob.nomi}: {soz_soni} so'z, "
                        f"matn={'bor' if matn_bormi else 'yoq'} -> Unit-darajasidagi Vocabulary ({manba})"
                    )
                    jami_kochirilgan_soz += soz_soni
                    if not dry_run:
                        if eski_vocab.matn:
                            mavjud = getattr(vocab, matn_maydoni)
                            setattr(
                                vocab, matn_maydoni,
                                f"{mavjud}\n\n{eski_vocab.matn}".strip() if mavjud else eski_vocab.matn,
                            )
                            vocab.save(update_fields=[matn_maydoni])
                        KursSoz.objects.filter(tugun=eski_vocab).update(tugun=vocab, manba=manba)
                        eski_vocab.delete()
                        jami_tozalangan_tugun += 1

                if eski_mashqlar_tugun:
                    mashq_soni = eski_mashqlar_tugun.mashqlar.count()
                    self.stdout.write(
                        f"{unit.nomi} > {kitob.nomi}: {mashq_soni} mashq -> bevosita '{kitob.nomi}'ga"
                    )
                    jami_kochirilgan_mashq += mashq_soni
                    if not dry_run:
                        KursMashq.objects.filter(tugun=eski_mashqlar_tugun).update(tugun=kitob)
                        eski_mashqlar_tugun.delete()
                        jami_tozalangan_tugun += 1

                qolganlar = list(KursTugun.objects.filter(parent=kitob))
                for qolgan in qolganlar:
                    self.stdout.write(self.style.WARNING(
                        f"  Kutilmagan qoldiq tugun: {unit.nomi} > {kitob.nomi} > {qolgan.nomi} "
                        f"(kalit={qolgan.kalit!r}) — qo'lda tekshiring"
                    ))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] Ko'chiriladi: {jami_kochirilgan_mashq} mashq, {jami_kochirilgan_soz} so'z"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Tayyor: {jami_kochirilgan_mashq} mashq, {jami_kochirilgan_soz} so'z ko'chirildi, "
                f"{jami_tozalangan_tugun} eski tugun tozalandi"
            ))
