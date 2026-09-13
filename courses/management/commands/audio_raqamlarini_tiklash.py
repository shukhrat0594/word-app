"""Bloklardagi yo'qolgan `audio_raqam` belgisini matndan tiklash
(2026-09-14, Shuhrat: "Kurslar bo'limida Intermediate audio yuklab
bo'lmayabdi").

MUAMMO: Kurslar bo'limida mashqqa audio yuklash tugmasi FAQAT blokda
`audio_raqam` to'ldirilgan bo'lsa (yoki `audio_kerak=True` bo'lsa)
chiqadi — `frontend/src/pages/Kurslar.jsx: mashqAudioRaqamlari`.
Intermediate darajasining 7, 8, 9, 10, 12-unitlarida import paytida bu
belgi AJRATILMAY qolgan: trek raqami blok matnining boshida oddiy matn
bo'lib qolib ketgan ("7.1 Read and listen to three people ...").
Natijada o'sha unitlarda audio yuklash tugmasi UMUMAN ko'rinmasdi.

YECHIM: matni `<raqam>.<raqam>` bilan BOSHLANADIGAN va ichida "listen"
so'zi bor bloklarda — o'sha raqam `audio_raqam`ga ko'chiriladi, matn
boshidan esa olib tashlanadi (ishlaydigan unitlardagi konvensiya aynan
shunday: raqam matnda emas, alohida maydonda).

NEGA "listen" SHARTI BOR: raqam bilan boshlanadigan har qanday matnni
olsak, audio bo'lmagan bloklar ham "audio" deb belgilanib qolardi.
Bazada sinab ko'rilgan — shu shartsiz ikkita notog'ri nomzod chiqdi:
"4.3 to'liq gaplar: ..." (javob kaliti) va "10.00 p.m.-12.00 a.m."
(soat vaqti). "listen" sharti ikkalasini ham to'g'ri chetlab o'tadi.

BU BUYRUQ HAMMASINI HAL QILMAYDI: audio belgisi matnda umuman
yo'q bo'lgan mashqlar qolib ketadi. Shuning uchun interfeys tomonida
ham zaxira yo'l bor — admin uchun audio yuklash tugmasi endi belgidan
QAT'I NAZAR ko'rsatiladi (`Kurslar.jsx`). Bu buyruq esa belgini
tiklab, tugmani TO'G'RI trek raqami bilan chiqaradi.

Qayta ishga tushirish xavfsiz: `audio_raqam` allaqachon to'ldirilgan
bloklarga tegilmaydi.

Ishlatish:
    python manage.py audio_raqamlarini_tiklash --sinov   # faqat ko'rsatadi
    python manage.py audio_raqamlarini_tiklash           # yozadi
"""

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import KursMashq

# Matn boshidagi trek raqami: "7.1 ", "12.10 " va h.k.
NAQSH = re.compile(r"^(\d{1,2}\.\d{1,2})\s+(.*)", re.S)


def tiklanadigan_raqam(blok):
    """Blokdan tiklanadigan (raqam, tozalangan_matn) juftligi yoki None."""
    if blok.get("audio_raqam"):
        return None
    matn = (blok.get("matn") or "").strip()
    moslik = NAQSH.match(matn)
    if not moslik:
        return None
    if "listen" not in matn.lower():
        return None
    return moslik.group(1), moslik.group(2).strip()


class Command(BaseCommand):
    help = "Blok matnining boshidagi trek raqamini `audio_raqam` maydoniga tiklaydi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sinov",
            action="store_true",
            help="Hech narsa yozmaydi, faqat nima o'zgarishini ko'rsatadi",
        )

    def handle(self, *args, **sozlamalar):
        sinov = sozlamalar["sinov"]
        ozgargan_mashqlar = 0
        ozgargan_bloklar = 0

        with transaction.atomic():
            for mashq in KursMashq.objects.exclude(bloklar=[]).iterator():
                bloklar = mashq.bloklar or []
                tegildi = False
                for blok in bloklar:
                    natija = tiklanadigan_raqam(blok)
                    if not natija:
                        continue
                    raqam, toza_matn = natija
                    blok["audio_raqam"] = raqam
                    blok["matn"] = toza_matn
                    tegildi = True
                    ozgargan_bloklar += 1
                    if sinov:
                        self.stdout.write(
                            f"  mashq {mashq.id}: {raqam} <- {toza_matn[:60]!r}"
                        )
                if tegildi:
                    ozgargan_mashqlar += 1
                    if not sinov:
                        mashq.save(update_fields=["bloklar"])

            if sinov:
                transaction.set_rollback(True)

        xabar = (
            f"{ozgargan_bloklar} ta blok, {ozgargan_mashqlar} ta mashq "
            f"{'o`zgarardi (SINOV — yozilmadi)' if sinov else 'yangilandi'}"
        )
        self.stdout.write(self.style.SUCCESS(xabar))
