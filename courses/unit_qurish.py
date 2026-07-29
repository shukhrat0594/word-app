"""Bitta Unit tugunining ICHKI tuzilmasini quradi — Student's Book /
Workbook, har birida Mashqlar/Vocabulary (2026-07-28 sxemasi bo'yicha,
`kurslar_urugla.py`da joriy qilingan).

Alohida modulga chiqarilgan (2026-07-29) — endi bu tuzilma FAQAT
Beginner uchun emas: admin Elementary...Upper-Intermediate darajalari
uchun ham xuddi shu ichki tuzilmali Unitlarni "Unit soni" orqali
yaratishi mumkin (`courses/views.py`, `KursDarajaUnitYaratishView`)."""

from .models import KursTugun

UNIT_KITOBLARI = [("students_book", "Student's Book"), ("workbook", "Workbook")]
UNIT_BOLIMLARI = [("mashqlar", "Mashqlar"), ("vocabulary", "Vocabulary")]


def unit_ichki_tuzilmasini_yarat(unit):
    """Berilgan (bo'sh) Unit tuguni ostida standart 2x2 tuzilmani quradi:
    Student's Book/Workbook, har birida Mashqlar/Vocabulary."""
    for i, (kitob_kalit, kitob_nomi) in enumerate(UNIT_KITOBLARI, start=1):
        kitob = KursTugun.objects.create(
            kalit=kitob_kalit, nomi=kitob_nomi, parent=unit,
            markaz=unit.markaz, tartib=i,
        )
        for j, (b_kalit, b_nomi) in enumerate(UNIT_BOLIMLARI, start=1):
            KursTugun.objects.create(
                kalit=b_kalit, nomi=b_nomi, parent=kitob,
                markaz=unit.markaz, tartib=j,
            )
