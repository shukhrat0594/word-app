"""Bitta Unit tugunining ICHKI tuzilmasini quradi.

2026-08-19 qayta qurildi (foydalanuvchi talabi: "students book va work
book da faqat mashqlar bo'ladi... vocabularyni chiqarish kerak"). Avval
Unit > Student's Book/Workbook > Mashqlar/Vocabulary (har kitobda o'z
Vocabulary'si) edi — endi Unit BEVOSITA 3 farzandga ega:

    Unit
     +-- Student's Book   (mashqlar to'g'ridan-to'g'ri shu tugunga —
     |                      "Mashqlar" oraliq qatlami yo'q)
     +-- Workbook          (xuddi shunday)
     +-- Vocabulary        (ikkala kitob uchun UMUMIY — bitta joyda
     |                       ko'rinadi, lekin har so'z/matn qaysi
     |                       kitobdan kelganini `KursSoz.manba` /
     |                       `KursTugun.matn`+`matn_workbook` orqali
     |                       backendda eslab qoladi, `KursUnitTozalashView`
     |                       shu bo'yicha faqat tegishli qismini tozalaydi)
     +-- Games             (2026-08-21, foydalanuvchi talabi — O'yinlar
                             bo'limidagi 4 ta so'z o'yini, FAQAT shu
                             Unit'ning Vocabulary so'zlari bilan. O'z
                             farzandi/kontenti yo'q — so'zlarni birodar
                             Vocabulary tugunidan oladi, frontendda
                             `Kurslar.jsx` shu birodarlikni hisoblaydi)

Alohida modulga chiqarilgan (2026-07-29) — endi bu tuzilma FAQAT
Beginner uchun emas: admin Elementary...Upper-Intermediate darajalari
uchun ham xuddi shu ichki tuzilmali Unitlarni "Unit soni" orqali
yaratishi mumkin (`courses/views.py`, `KursDarajaUnitYaratishView`)."""

from .models import KursTugun

UNIT_KITOBLARI = [("students_book", "Student's Book"), ("workbook", "Workbook")]


def unit_ichki_tuzilmasini_yarat(unit):
    """Berilgan (bo'sh) Unit tuguni ostida Student's Book, Workbook,
    umumiy Vocabulary va Games tugunlarini yaratadi — hech biri
    farzandga ega emas (barchasi "oxirgi qatlam")."""
    for i, (kitob_kalit, kitob_nomi) in enumerate(UNIT_KITOBLARI, start=1):
        KursTugun.objects.create(
            kalit=kitob_kalit, nomi=kitob_nomi, parent=unit,
            markaz=unit.markaz, tartib=i,
        )
    KursTugun.objects.create(
        kalit="vocabulary", nomi="Vocabulary", parent=unit,
        markaz=unit.markaz, tartib=len(UNIT_KITOBLARI) + 1,
    )
    KursTugun.objects.create(
        kalit="games", nomi="Games", parent=unit,
        markaz=unit.markaz, tartib=len(UNIT_KITOBLARI) + 2,
    )
