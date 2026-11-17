"""Intermediate > Unit 1-10, 12 > Tests bo'limlariga Unit testlarini kiritadi
(2026-10-15, foydalanuvchi talabi). Manba — `Headway/Intermediate/Intermediate.zip`;
ajratilgan savollar `courses/fixtures/intermediate_testlari.json`da.

Har testda 50 savol: Grammar 1-25, Vocabulary & Everyday English 26-50.

Manba kamchiliklari: fayl nomi va sarlavhalari xato "Pre-Intermediate" (mazmuni
Intermediate Wordlist'iga mos); Unit 11 testi yo'q; Unit 2 ikki xil — Wordlist'ga
mos kelgani ("50Q") olindi. Ikki to'g'ri javobli 16 savol (4 ta 2026-10-15,
12 ta 2026-11-17 tekshiruvida — noto'g'ri variant almashtirilgan) va bitta imlo
tuzatilgan; hammasi "A" bo'lgan qismlarda variantlar aralashtirilgan.

Mantiq `elementary_testlari` bilan bir xil (idempotent, `--qayta`)."""

from pathlib import Path

from .elementary_testlari import Command as ElementaryCommand


class Command(ElementaryCommand):
    help = "Intermediate Unit testlarini Tests bo'limlariga kiritadi"
    DARAJA = "intermediate"
    FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "intermediate_testlari.json"
    GRAMMAR_SONI = 25
