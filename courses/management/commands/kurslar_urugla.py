"""Kurslar bo'limining qattiq (fixed) boshlang'ich tuzilmasini yaratadi —
Texnik Topshiriq (2026-07-21) sxemasi bo'yicha. Idempotent: mavjud
tugunlarni (nomi+parent bo'yicha) qayta yaratmaydi, faqat yetishmaganini
qo'shadi — xavfsiz qayta-qayta ishga tushiriladi (prod_boshlangich'ga
ulash uchun).

2026-07-22: Beginner endi "Unit" asosida (Headway Beginner 5th edition
kitobi bo'yicha, 14 ta unit) — har bir Unit o'zining bo'limiga ega va
ketma-ket ochiladi (`unit_darsi=True`).

2026-07-22 (2): Unit ichidagi bo'limlar darslik ("Headway") uslubiga
moslashtirildi — Students Book/Workbook/Test-Exam o'rniga haqiqiy darslik
bo'limlari: Grammar/Vocabulary/Reading/Listening/Speaking-Writing/Everyday
English. Har biri — oxirgi qatlam (fayl + mashq biriktiriladigan tugun).
"Grammar reference" (Grammar oxiridagi xulosa beti) va "Wordlist"
(Vocabulary oxiridagi so'zlar ro'yxati) alohida tugun sifatida
modellanmaydi — shu bo'limning umumiy fayliga (masalan darslik sahifalari
skani) kiritiladi. Bu bo'lim to'plami Beginner'dan Upper-Intermediate'gacha
BARCHA darajalarda bir xil (Elementary...Upper-Intermediate hali kitob
berilmagani uchun bo'sh/flat holatda qoladi, faqat bo'lim nomlari mos).
"""

from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursTugun

INGLIZ_DARAJA_BOLIMLARI = [
    "Grammar",
    "Vocabulary",
    "Reading",
    "Listening",
    "Speaking/Writing",
    "Everyday English",
]
INGLIZ_DARAJALAR = ["Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate"]
IELTS_TEXTBOOKS_QISMLARI = ["Reading", "Writing", "Listening", "Speaking", "Vocabulary", "Grammar"]
IELTS_BOLIMLARI = ["Textbooks", "Practice tests", "Cambridge", "Vocabulary", "Mock exam"]

HEADWAY_BEGINNER_UNITLAR = [
    "Unit 1 — Hello!",
    "Unit 2 — Your world",
    "Unit 3 — All about you",
    "Unit 4 — Family and friends",
    "Unit 5 — Things I like!",
    "Unit 6 — Every day",
    "Unit 7 — Favourite things",
    "Unit 8 — Home sweet home",
    "Unit 9 — Past times",
    "Unit 10 — We had a good time!",
    "Unit 11 — We can do it!",
    "Unit 12 — Thank you very much!",
    "Unit 13 — What's happening now?",
    "Unit 14 — Let's go!",
]


class Command(BaseCommand):
    help = "Kurslar bo'limi boshlang'ich tuzilmasini yaratadi (Ingliz tili — Beginner Unit'lar bilan, boshqa darajalar flat)"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.WARNING("Markaz topilmadi — o'tkazib yuborildi"))
            return

        def bor_yoki_yarat(nomi, parent=None, tartib=0, ikonka="", tez_kunda=False, unit_darsi=False):
            tugun, yaratildi = KursTugun.objects.get_or_create(
                nomi=nomi, parent=parent, markaz=markaz,
                defaults={"tartib": tartib, "ikonka": ikonka, "tez_kunda": tez_kunda, "unit_darsi": unit_darsi},
            )
            return tugun

        def eski_bolimlarni_tozala(ota_tugun):
            """Ota tugun ostidagi, endi ro'yxatda yo'q (eski nomdagi)
            bo'lim tugunlarini o'chiradi — bo'lim sxemasi o'zgarganda
            (masalan Students Book/Workbook -> Grammar/Vocabulary/...)
            eskisi qolib ketmasligi uchun."""
            KursTugun.objects.filter(parent=ota_tugun).exclude(nomi__in=INGLIZ_DARAJA_BOLIMLARI).delete()

        kurslar = bor_yoki_yarat("Kurslar", tartib=0)

        bor_yoki_yarat("Rus tili", parent=kurslar, tartib=1, ikonka="🌐", tez_kunda=True)
        bor_yoki_yarat("Matematika", parent=kurslar, tartib=2, ikonka="📐", tez_kunda=True)

        ingliz = bor_yoki_yarat("Ingliz tili", parent=kurslar, tartib=3, ikonka="🇬🇧")

        for i, daraja_nomi in enumerate(INGLIZ_DARAJALAR, start=1):
            daraja = bor_yoki_yarat(daraja_nomi, parent=ingliz, tartib=i)

            if daraja_nomi == "Beginner":
                # Eski (Unit'siz, flat) bo'limlar bo'lsa — Unit tuzilmasiga
                # o'tishda tozalanadi (2026-07-22, hali real kontent yo'q edi).
                KursTugun.objects.filter(parent=daraja, unit_darsi=False).delete()
                for j, unit_nomi in enumerate(HEADWAY_BEGINNER_UNITLAR, start=1):
                    unit = bor_yoki_yarat(unit_nomi, parent=daraja, tartib=j, unit_darsi=True)
                    eski_bolimlarni_tozala(unit)
                    for k, bolim_nomi in enumerate(INGLIZ_DARAJA_BOLIMLARI, start=1):
                        bor_yoki_yarat(bolim_nomi, parent=unit, tartib=k)
            else:
                eski_bolimlarni_tozala(daraja)
                for j, bolim_nomi in enumerate(INGLIZ_DARAJA_BOLIMLARI, start=1):
                    bor_yoki_yarat(bolim_nomi, parent=daraja, tartib=j)

        ielts = bor_yoki_yarat("IELTS", parent=ingliz, tartib=len(INGLIZ_DARAJALAR) + 1)
        for i, bolim_nomi in enumerate(IELTS_BOLIMLARI, start=1):
            bolim = bor_yoki_yarat(bolim_nomi, parent=ielts, tartib=i)
            if bolim_nomi == "Textbooks":
                for j, qism_nomi in enumerate(IELTS_TEXTBOOKS_QISMLARI, start=1):
                    bor_yoki_yarat(qism_nomi, parent=bolim, tartib=j)

        bor_yoki_yarat("CEFR", parent=ingliz, tartib=len(INGLIZ_DARAJALAR) + 2, tez_kunda=True)

        self.stdout.write(self.style.SUCCESS(f"Kurslar tuzilmasi tayyor (jami {KursTugun.objects.count()} tugun)"))
