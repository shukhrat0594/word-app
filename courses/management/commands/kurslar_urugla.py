"""Kurslar bo'limining qattiq (fixed) boshlang'ich tuzilmasini yaratadi —
Texnik Topshiriq (2026-07-21) sxemasi bo'yicha. Idempotent: mavjud
tugunlarni (kalit+parent bo'yicha) qayta yaratmaydi, faqat yetishmaganini
qo'shadi — xavfsiz qayta-qayta ishga tushiriladi (prod_boshlangich'ga
ulash uchun).

2026-07-22...2026-07-28: Beginner "Unit" asosida (Headway Beginner 5th
edition kitobi bo'yicha, 14 ta qattiq kodlangan unit nomi bilan) qurilgan
edi — har Unit Student's Book/Workbook > Mashqlar/Vocabulary tuzilmasiga
ega, ketma-ket ochiladigan (`unit_darsi=True`).

2026-07-29: Bu qattiq kodlash BEKOR QILINDI (foydalanuvchi talabi —
"Beginnerni ham keyingi bo'limlar bilan bir xil qilamiz"). Beginner endi
BOSHQA barcha Ingliz tili darajalari (Elementary...Upper-Intermediate)
bilan BIR XIL yo'ldan o'tadi: Unit yaratilmaguncha daraja BO'SH turadi
(hech qanday flat bo'lim yaratilmaydi — 2026-07-29(3), foydalanuvchi:
"ortiqcha narsani olib tashla"), admin panelidan (`KursDarajaUnitYaratishView`,
courses/views.py) Unit sonini o'zi belgilab, Unit-asosli tuzilmaga (soni
ixtiyoriy, nomlari generic "Unit N") o'tkazadi. Eski 3 ta to'ldirilgan
Unit (talaba javoblari bilan birga) `prod_boshlangich.py`da BIR MARTALIK
o'chirildi — qarang `_beginner_eski_unitlarni_tozala`.

Har bir daraja uchun: agar darajada ALLAQACHON Unit (`unit_darsi=True`)
mavjud bo'lsa (admin panel orqali yaratilgan), bu buyruq UNGA TEGMAYDI —
aks holda bu buyruq HAR DEPLOY'DA ishga tushgani uchun (prod_boshlangich),
admin yaratgan Unitlar keyingi deploy'da o'chirilib ketardi."""

from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursMashq, KursTugun

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
    **{nomi: kalit for kalit, nomi in INGLIZ_DARAJALAR},
}


def _shoxni_yig(tugun, idlar):
    """Tugun va uning butun avlodini (rekursiv) `idlar` ro'yxatiga yig'adi
    — kaskad o'chirishdan oldin nima yo'qolayotganini hisoblash uchun."""
    idlar.append(tugun.id)
    for bola in KursTugun.objects.filter(parent=tugun):
        _shoxni_yig(bola, idlar)


class Command(BaseCommand):
    help = "Kurslar bo'limi boshlang'ich tuzilmasini yaratadi (Ingliz tili darajalari — Unit yaratilmaguncha flat)"

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

            if KursTugun.objects.filter(parent=daraja, unit_darsi=True).exists():
                # Admin bu darajada `KursDarajaUnitYaratishView` orqali
                # Unit-asosli tuzilma yaratgan (courses/views.py) — bu
                # buyruq HAR DEPLOY'DA ishga tushgani uchun, UNGA TEGMAYMIZ.
                continue

            # 2026-07-29(3): Unit hali yaratilmagan bo'lsa daraja BO'SH
            # turadi — admin panelida faqat "Unit soni" input+tugma
            # ko'rinishi uchun (ortiqcha flat bo'lim ko'rsatilmasin).
            # Eski versiyada qolgan flat bo'limlar bo'lsa — tozalanadi.
            eski_bolimlarni_tozala(daraja, [])

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
