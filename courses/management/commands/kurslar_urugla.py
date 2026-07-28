"""Kurslar bo'limining qattiq (fixed) boshlang'ich tuzilmasini yaratadi —
Texnik Topshiriq (2026-07-21) sxemasi bo'yicha. Idempotent: mavjud
tugunlarni (kalit+parent bo'yicha) qayta yaratmaydi, faqat yetishmaganini
qo'shadi — xavfsiz qayta-qayta ishga tushiriladi (prod_boshlangich'ga
ulash uchun).

2026-07-22: Beginner endi "Unit" asosida (Headway Beginner 5th edition
kitobi bo'yicha, 14 ta unit) — har bir Unit o'zining bo'limiga ega va
ketma-ket ochiladi (`unit_darsi=True`).

2026-07-27: Unit ichidagi bo'limlar qayta qurildi — avvalgi 6 bo'lim
o'rniga Mashqlar/Grammar reference/Wordlist, so'ng (shu kuni, ikkinchi
marta) Grammar reference va Wordlist BIRLASHTIRILDI ("Vocabulary"), Unit
2 bo'limga tushdi.

2026-07-28 — IKKI KATTA O'ZGARISH:

1) `kalit` (slug) maydoni. Avval tugunlar NOMI bo'yicha topilardi
   (`bolalar["Mashqlar"]`, frontendda `nomi === "Vocabulary"`). Nomlar
   3 tilda ko'rsatiladigan bo'lgach bu yo'l sinadi, shuning uchun kod
   endi HAR DOIM `kalit`ka tayanadi. Bazadagi `nomi` o'zgarmaydi (zaxira
   sifatida qoladi), tarjima frontendda i18n orqali qilinadi.

2) Unit ichida yangi qatlam — Student's Book va Workbook, HAR IKKALASIDA
   Mashqlar+Vocabulary:

       Unit 1 — Hello!
       ├── Student's Book
       │   ├── Mashqlar
       │   └── Vocabulary
       └── Workbook
           ├── Mashqlar
           └── Vocabulary

   MAVJUD kontent yo'qolmaydi: Unit ostida to'g'ridan-to'g'ri turgan eski
   Mashqlar/Vocabulary tugunlari (ichidagi KursMashq, KursSoz,
   KursMashqAudio bilan birga) Student's Book ostiga KO'CHIRILADI —
   faqat `parent` o'zgaradi, o'chirib-qayta yaratish YO'Q.

Bu faqat Beginner'ning Unit tuzilmasiga tegishli. Boshqa darajalar
(Elementary...Upper-Intermediate) hali flat va eski bo'lim to'plamida
qoladi (ular hali bo'sh, real kitob berilmagan).
"""

from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursMashq, KursTugun

# Har bo'lim (kalit, nomi) juftligi bilan beriladi — `nomi` bazadagi
# zaxira ko'rinish, foydalanuvchi ko'radigan matn frontendda `kalit`
# bo'yicha tarjima qilinadi.
INGLIZ_DARAJA_BOLIMLARI = [
    ("grammar", "Grammar"),
    ("vocabulary", "Vocabulary"),
    ("reading", "Reading"),
    ("listening", "Listening"),
    ("speaking_writing", "Speaking/Writing"),
    ("everyday_english", "Everyday English"),
]

# Unit ichidagi kitob turlari (2026-07-28) va ularning har biridagi bo'limlar.
UNIT_KITOBLARI = [("students_book", "Student's Book"), ("workbook", "Workbook")]
UNIT_BOLIMLARI = [("mashqlar", "Mashqlar"), ("vocabulary", "Vocabulary")]

INGLIZ_DARAJALAR = [
    ("beginner", "Beginner"),
    ("elementary", "Elementary"),
    ("pre_intermediate", "Pre-Intermediate"),
    ("intermediate", "Intermediate"),
    ("upper_intermediate", "Upper-Intermediate"),
]
IELTS_TEXTBOOKS_QISMLARI = [
    ("reading", "Reading"),
    ("writing", "Writing"),
    ("listening", "Listening"),
    ("speaking", "Speaking"),
    ("vocabulary", "Vocabulary"),
    ("grammar", "Grammar"),
]
# 2026-07-27: "Cambridge" va "Vocabulary" bo'limlari IELTS ostidan olib
# tashlandi (foydalanuvchi talabi). ESLATMA: IELTS > Textbooks > Vocabulary
# BOSHQA tugun — u `IELTS_TEXTBOOKS_QISMLARI` ichida va o'z joyida qoladi.
IELTS_BOLIMLARI = [
    ("textbooks", "Textbooks"),
    ("practice_tests", "Practice tests"),
    ("mock_exam", "Mock exam"),
]

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

# Eski (kalitsiz) tugunlarni bir martalik kalitlash uchun nom -> kalit
# jadvali. Faqat `kalit` bo'sh bo'lgan tugunlarga qo'llanadi.
NOM_KALIT = {
    "Kurslar": "kurslar",
    "Rus tili": "rus_tili",
    "Matematika": "matematika",
    "Ingliz tili": "ingliz_tili",
    "IELTS": "ielts",
    "CEFR": "cefr",
    "Student's Book": "students_book",
    "Workbook": "workbook",
    "Mashqlar": "mashqlar",
    "Practice tests": "practice_tests",
    "Mock exam": "mock_exam",
    "Textbooks": "textbooks",
    "Speaking/Writing": "speaking_writing",
    "Everyday English": "everyday_english",
    "Grammar": "grammar",
    "Vocabulary": "vocabulary",
    "Reading": "reading",
    "Writing": "writing",
    "Listening": "listening",
    "Speaking": "speaking",
    **{nomi: f"unit_{i}" for i, nomi in enumerate(HEADWAY_BEGINNER_UNITLAR, start=1)},
    **{nomi: kalit for kalit, nomi in INGLIZ_DARAJALAR},
}


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

        self._kalitlarni_toldir()

        def bor_yoki_yarat(kalit, nomi, parent=None, tartib=0, ikonka="",
                           tez_kunda=False, unit_darsi=False):
            """Kalit+parent bo'yicha topadi (nomi bo'yicha EMAS — nom
            o'zgarishi mumkin, kalit esa barqaror)."""
            tugun = KursTugun.objects.filter(
                kalit=kalit, parent=parent, markaz=markaz).first()
            if tugun:
                return tugun
            return KursTugun.objects.create(
                kalit=kalit, nomi=nomi, parent=parent, markaz=markaz,
                tartib=tartib, ikonka=ikonka, tez_kunda=tez_kunda,
                unit_darsi=unit_darsi,
            )

        def eski_bolimlarni_tozala(ota_tugun, mos_kalitlar):
            """Ota tugun ostidagi, endi ro'yxatda yo'q bo'lim tugunlarini
            KASKAD o'chiradi — bo'lim sxemasi o'zgarganda eskisi qolib
            ketmasligi uchun. Nima o'chirilgani (tugun+mashq soni) deploy
            logiga yoziladi, sezilmay qolmasligi uchun."""
            ortiqcha = list(
                KursTugun.objects.filter(parent=ota_tugun).exclude(kalit__in=mos_kalitlar))
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

        kurslar = bor_yoki_yarat("kurslar", "Kurslar", tartib=0)

        bor_yoki_yarat("rus_tili", "Rus tili", parent=kurslar, tartib=1,
                       ikonka="🌐", tez_kunda=True)
        bor_yoki_yarat("matematika", "Matematika", parent=kurslar, tartib=2,
                       ikonka="📐", tez_kunda=True)

        ingliz = bor_yoki_yarat("ingliz_tili", "Ingliz tili", parent=kurslar,
                                tartib=3, ikonka="🇬🇧")

        for i, (daraja_kalit, daraja_nomi) in enumerate(INGLIZ_DARAJALAR, start=1):
            daraja = bor_yoki_yarat(daraja_kalit, daraja_nomi, parent=ingliz, tartib=i)

            if daraja_kalit == "beginner":
                # Eski (Unit'siz, flat) bo'limlar bo'lsa — Unit tuzilmasiga
                # o'tishda tozalanadi (2026-07-22, hali real kontent yo'q edi).
                KursTugun.objects.filter(parent=daraja, unit_darsi=False).delete()
                for j, unit_nomi in enumerate(HEADWAY_BEGINNER_UNITLAR, start=1):
                    unit = bor_yoki_yarat(f"unit_{j}", unit_nomi, parent=daraja,
                                          tartib=j, unit_darsi=True)
                    self._unitni_kitoblarga_bol(unit, bor_yoki_yarat)
                    eski_bolimlarni_tozala(unit, [k for k, _ in UNIT_KITOBLARI])
            else:
                eski_bolimlarni_tozala(daraja, [k for k, _ in INGLIZ_DARAJA_BOLIMLARI])
                for j, (kalit, nomi) in enumerate(INGLIZ_DARAJA_BOLIMLARI, start=1):
                    bor_yoki_yarat(kalit, nomi, parent=daraja, tartib=j)

        ielts = bor_yoki_yarat("ielts", "IELTS", parent=ingliz,
                               tartib=len(INGLIZ_DARAJALAR) + 1)
        for i, (kalit, nomi) in enumerate(IELTS_BOLIMLARI, start=1):
            bolim = bor_yoki_yarat(kalit, nomi, parent=ielts, tartib=i)
            if kalit == "textbooks":
                for j, (q_kalit, q_nomi) in enumerate(IELTS_TEXTBOOKS_QISMLARI, start=1):
                    bor_yoki_yarat(q_kalit, q_nomi, parent=bolim, tartib=j)

        # IELTS ostidan olib tashlangan bo'limlar ("Cambridge", "Vocabulary",
        # 2026-07-27) — bir xil naqsh, endi umumiy funksiya orqali.
        eski_bolimlarni_tozala(ielts, [k for k, _ in IELTS_BOLIMLARI])

        bor_yoki_yarat("cefr", "CEFR", parent=ingliz,
                       tartib=len(INGLIZ_DARAJALAR) + 2, tez_kunda=True)

        self.stdout.write(
            self.style.SUCCESS(f"Kurslar tuzilmasi tayyor (jami {KursTugun.objects.count()} tugun)"))

    # ------------------------------------------------------------------

    def _kalitlarni_toldir(self):
        """Kaliti bo'sh mavjud tugunlarga NOM_KALIT jadvali bo'yicha kalit
        beradi (bir martalik, keyingi ishga tushirishlarda hech narsa
        qilmaydi). Buni tuzilma qurishdan OLDIN bajarish shart — chunki
        `bor_yoki_yarat` endi kalit bo'yicha qidiradi va kalitsiz eski
        tugunni topa olmay, DUBLIKAT yaratib yuborardi."""
        yangilandi = 0
        for nomi, kalit in NOM_KALIT.items():
            yangilandi += KursTugun.objects.filter(
                nomi=nomi, kalit="").update(kalit=kalit)
        if yangilandi:
            self.stdout.write(f"Kalit berildi: {yangilandi} ta eski tugun")

    def _unitni_kitoblarga_bol(self, unit, bor_yoki_yarat):
        """Unit ostida Student's Book / Workbook qatlamini quradi va
        MAVJUD bo'limlarni Student's Book ostiga KO'CHIRADI (2026-07-28).

        Ko'chirish `parent` ni o'zgartirish orqali bo'ladi — tugunlar
        o'chirilmaydi, shuning uchun ichidagi KursMashq / KursSoz /
        KursMashqAudio va talabalarning KursMashqYechim yozuvlari
        BUTUNLIGICHA saqlanib qoladi."""
        kitoblar = {}
        for i, (kalit, nomi) in enumerate(UNIT_KITOBLARI, start=1):
            kitoblar[kalit] = bor_yoki_yarat(kalit, nomi, parent=unit, tartib=i)

        # Eski tuzilma: Mashqlar/Vocabulary to'g'ridan-to'g'ri Unit ostida
        # turardi -> Student's Book ostiga ko'chiramiz.
        kochirildi = KursTugun.objects.filter(
            parent=unit, kalit__in=[k for k, _ in UNIT_BOLIMLARI]
        ).update(parent=kitoblar["students_book"])
        if kochirildi:
            self.stdout.write(
                f"\"{unit.nomi}\": {kochirildi} ta bo'lim Student's Book ostiga ko'chirildi")

        for kitob in kitoblar.values():
            for j, (kalit, nomi) in enumerate(UNIT_BOLIMLARI, start=1):
                bor_yoki_yarat(kalit, nomi, parent=kitob, tartib=j)
