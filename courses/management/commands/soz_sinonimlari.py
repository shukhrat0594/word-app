"""Vocabulary so'zlariga qo'shimcha to'g'ri tarjimalarni (sinonimlarni)
AI bilan to'ldiradi (2026-10-28, Matn-TZ 674).

Talaba award (v) ga "mukofotlamoq" o'rniga "taqdirlamoq" yoki "mukofot
bermoq" yozsa ham to'g'ri bo'lishi kerak. Har so'z uchun shu turkumdagi
o'zbekcha va ruscha sinonimlar `KursSoz.sinonimlar`ga yoziladi
(`courses.soz_tarjima.sinonimlar_qil`).

FAQAT `sinonimlar` BO'SH so'zlar so'raladi — qayta ishga tushirish
to'xtagan joydan davom etadi va pul qayta sarflanmaydi (`--hammasi` —
hammasini qaytadan). Bir xil so'z (en+turkum+uz+ru) har markaz
daraxtida takrorlanadi — AI'dan bir marta so'raladi, hammasiga yoziladi.

    python manage.py soz_sinonimlari [--daraja beginner] [--hammasi] [--chegara 500]
"""

from django.core.management.base import BaseCommand, CommandError

from courses.models import KursSoz
from courses.soz_tarjima import PARTIYA, ProviderXatosi, sinonimlar_qil

URINISH_SONI = 3


class Command(BaseCommand):
    help = "Vocabulary so'zlariga shu turkumdagi qo'shimcha uz/ru tarjimalarni AI bilan yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--daraja", help="Faqat shu daraja (Unit kaliti boshlanishi, masalan beginner)")
        parser.add_argument("--hammasi", action="store_true", help="To'ldirilganlarni ham qaytadan so'rash")
        parser.add_argument("--chegara", type=int, default=0, help="Ko'pi bilan nechta noyob so'z (0 — cheklovsiz)")

    def handle(self, *args, daraja=None, hammasi=False, chegara=0, **kw):
        qs = KursSoz.objects.all()
        if daraja:
            qs = qs.filter(tugun__parent__kalit__startswith=f"{daraja}_unit_")
        if not hammasi:
            qs = qs.filter(sinonimlar={})

        guruhlar = {}
        for s in qs.order_by("id"):
            guruhlar.setdefault((s.en, s.turkum, s.uz, s.ru), []).append(s)
        vakillar = [ro[0] for ro in guruhlar.values()]
        if chegara:
            vakillar = vakillar[:chegara]
        if not vakillar:
            self.stdout.write("To'ldiriladigan so'z yo'q")
            return

        self.stdout.write(f"{len(vakillar)} ta noyob so'z ({sum(len(guruhlar[_kalit(v)]) for v in vakillar)} yozuv)")
        yozildi = 0
        qoldi = 0
        for i in range(0, len(vakillar), PARTIYA):
            partiya = vakillar[i : i + PARTIYA]
            topildi = {}
            qolgan = partiya
            for _ in range(URINISH_SONI):
                try:
                    javob = sinonimlar_qil(qolgan)
                except ProviderXatosi as e:
                    if not yozildi and not topildi:
                        raise CommandError(f"AI xatosi: {e}")
                    self.stderr.write(f"AI xatosi: {e}")
                    break
                topildi.update(javob)
                keyingi = [s for s in qolgan if s.id not in topildi]
                if len(keyingi) == len(qolgan):
                    break
                qolgan = keyingi
                if not qolgan:
                    break

            yangilar = []
            for v in partiya:
                if v.id not in topildi:
                    qoldi += 1
                    continue
                for s in guruhlar[_kalit(v)]:
                    s.sinonimlar = topildi[v.id]
                    yangilar.append(s)
            KursSoz.objects.bulk_update(yangilar, ["sinonimlar"])
            yozildi += len(yangilar)
            self.stdout.write(f"{min(i + PARTIYA, len(vakillar))}/{len(vakillar)}")

        self.stdout.write(self.style.SUCCESS(
            f"Yozildi: {yozildi} yozuv. AI javob bermagan: {qoldi} so'z (qayta ishga tushiring)"
        ))


def _kalit(s):
    return (s.en, s.turkum, s.uz, s.ru)
