"""Pre-Intermediate > Unit 1-12 > Tests bo'limlariga Unit testlarini kiritadi
(2026-10-14, foydalanuvchi talabi). Manba — `Headway/Pre-Intemediate tests/
Pre-Intemediate.zip` (12 ta PDF, har birida 30 savol, javob kaliti bilan);
ajratilgan savollar `courses/fixtures/pre_intermediate_testlari.json`da.

Manbadagi kamchiliklar tuzatilgan: U1 q14 ortiqcha so'z, U3 q18 takror
variant, U7 q28 va U9 q9 ikkita to'g'ri javob; hammasi "A" bo'lgan
qismlarda variantlar aralashtirilgan.

Mantiq `elementary_testlari` bilan bir xil (idempotent, `--qayta`)."""

from pathlib import Path

from .elementary_testlari import Command as ElementaryCommand


class Command(ElementaryCommand):
    help = "Pre-Intermediate Unit 1-12 Tests bo'limlariga test savollarini kiritadi"
    DARAJA = "pre_intermediate"
    FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "pre_intermediate_testlari.json"
