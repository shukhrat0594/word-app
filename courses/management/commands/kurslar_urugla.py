"""Kurslar bo'limining qattiq (fixed) boshlang'ich tuzilmasini yaratadi —
Texnik Topshiriq (2026-07-21) sxemasi bo'yicha. Idempotent: mavjud
tugunlarni (nomi+parent bo'yicha) qayta yaratmaydi, faqat yetishmaganini
qo'shadi — xavfsiz qayta-qayta ishga tushiriladi (prod_boshlangich'ga
ulash uchun).

2026-07-22: Beginner endi "Unit" asosida (Headway Beginner 5th edition
kitobi bo'yicha, 14 ta unit) — har bir Unit o'zining bo'limiga ega va
ketma-ket ochiladi (`unit_darsi=True`).

2026-07-27: Unit ichidagi bo'limlar QAYTA QURILDI (foydalanuvchi talabi) —
avvalgi 6 bo'lim (Grammar/Vocabulary/Reading/Listening/Speaking-Writing/
Everyday English) o'rniga har Unit endi 3 bo'limdan iborat:
  * "Mashqlar"          — darslikdagi barcha mashqlar shu yerga kiradi
                           (Reading/Listening/Grammar/Vocabulary va h.k.
                           endi alohida bo'lim emas, hammasi "Mashqlar"
                           ichida KursMashq sifatida). Qaysi mashqda
                           darslikda audio belgisi bo'lsa, shu mashqqa
                           audio biriktiriladi (har bo'lak alohida, audio
                           umumiy emas). Rasm ustida javob kiritish
                           (masalan "nechta narsa bor" turidagi mashqlar)
                           `savol.pozitsiya` orqali qo'llab-quvvatlanadi
                           (Kurslar.jsx: TalabaMashqi, IELTS testlaridagi
                           mexanizm bilan bir xil, model o'zgarishi kerak
                           emas — `KursMashq.savollar` erkin JSON).
  * "Grammar reference"  — darslik Unit oxiridagi grammatika xulosa beti
                            (fayl-only, mashq yo'q).
  * "Wordlist"            — darslik Unit oxiridagi so'zlar ro'yxati
                             (fayl-only, mashq yo'q).
Bu faqat Beginner'ning Unit tuzilmasiga tegishli. Boshqa darajalar
(Elementary...Upper-Intermediate) hali flat va eski bo'lim to'plamida
qoladi (ular hali bo'sh, real kitob berilmagan).
"""

from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursMashq, KursTugun

# Flat (Unit'siz) darajalarda ishlatiladigan bo'lim to'plami — hali
# o'zgartirilmagan (Elementary...Upper-Intermediate hali bo'sh).
INGLIZ_DARAJA_BOLIMLARI = [
    "Grammar",
    "Vocabulary",
    "Reading",
    "Listening",
    "Speaking/Writing",
    "Everyday English",
]
# Beginner Unit'lari ichidagi bo'lim to'plami (2026-07-27 qayta qurish).
UNIT_BOLIMLARI = ["Mashqlar", "Grammar reference", "Wordlist"]

INGLIZ_DARAJALAR = ["Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate"]
IELTS_TEXTBOOKS_QISMLARI = ["Reading", "Writing", "Listening", "Speaking", "Vocabulary", "Grammar"]
# 2026-07-27: "Cambridge" va "Vocabulary" bo'limlari IELTS ostidan olib
# tashlandi (foydalanuvchi talabi). ESLATMA: IELTS > Textbooks > Vocabulary
# BOSHQA tugun — u `IELTS_TEXTBOOKS_QISMLARI` ichida va o'z joyida qoladi.
IELTS_BOLIMLARI = ["Textbooks", "Practice tests", "Mock exam"]

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


def _shoxni_yig(tugun, idlar):
    """Tugun va uning butun avlodini (rekursiv) `idlar` ro'yxatiga yig'adi
    — kaskad o'chirishdan oldin nima yo'qolayotganini hisoblash uchun."""
    idlar.append(tugun.id)
    for bola in KursTugun.objects.filter(parent=tugun):
        _shoxni_yig(bola, idlar)


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

        def eski_bolimlarni_tozala(ota_tugun, mos_nomlar):
            """Ota tugun ostidagi, endi ro'yxatda yo'q (eski nomdagi)
            bo'lim tugunlarini KASKAD o'chiradi — bo'lim sxemasi
            o'zgarganda (masalan 6 bo'lim -> 3 bo'lim) eskisi qolib
            ketmasligi uchun. Nima o'chirilgani (tugun+mashq soni) deploy
            logiga yoziladi, sezilmay qolmasligi uchun."""
            ortiqcha = list(KursTugun.objects.filter(parent=ota_tugun).exclude(nomi__in=mos_nomlar))
            if not ortiqcha:
                return
            idlar = []
            for t in ortiqcha:
                _shoxni_yig(t, idlar)
            mashq_soni = KursMashq.objects.filter(tugun_id__in=idlar).count()
            nomlar = ", ".join(t.nomi for t in ortiqcha)
            KursTugun.objects.filter(id__in=idlar).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"\"{ota_tugun.nomi}\" ostidan olib tashlandi: {nomlar} "
                    f"({len(idlar)} tugun, {mashq_soni} mashq bilan birga)"
                )
            )

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
                    eski_bolimlarni_tozala(unit, UNIT_BOLIMLARI)
                    for k, bolim_nomi in enumerate(UNIT_BOLIMLARI, start=1):
                        bor_yoki_yarat(bolim_nomi, parent=unit, tartib=k)
            else:
                eski_bolimlarni_tozala(daraja, INGLIZ_DARAJA_BOLIMLARI)
                for j, bolim_nomi in enumerate(INGLIZ_DARAJA_BOLIMLARI, start=1):
                    bor_yoki_yarat(bolim_nomi, parent=daraja, tartib=j)

        ielts = bor_yoki_yarat("IELTS", parent=ingliz, tartib=len(INGLIZ_DARAJALAR) + 1)
        for i, bolim_nomi in enumerate(IELTS_BOLIMLARI, start=1):
            bolim = bor_yoki_yarat(bolim_nomi, parent=ielts, tartib=i)
            if bolim_nomi == "Textbooks":
                for j, qism_nomi in enumerate(IELTS_TEXTBOOKS_QISMLARI, start=1):
                    bor_yoki_yarat(qism_nomi, parent=bolim, tartib=j)

        # IELTS ostidan olib tashlangan bo'limlar ("Cambridge", "Vocabulary",
        # 2026-07-27) — bir xil naqsh, endi umumiy funksiya orqali.
        eski_bolimlarni_tozala(ielts, IELTS_BOLIMLARI)

        bor_yoki_yarat("CEFR", parent=ingliz, tartib=len(INGLIZ_DARAJALAR) + 2, tez_kunda=True)

        self.stdout.write(self.style.SUCCESS(f"Kurslar tuzilmasi tayyor (jami {KursTugun.objects.count()} tugun)"))
