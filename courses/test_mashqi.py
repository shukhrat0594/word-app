"""Unit Tests bo'limidagi test — BITTA mashq (2026-10-14, foydalanuvchi
talabi: avval Grammar va Vocabulary ikki alohida mashq edi, savollar esa
raqamsiz). Endi barcha savollar bitta mashqda ketma-ket (1–30), qismlar
faqat sarlavhada ko'rsatiladi; raqamlar frontendda qo'yiladi."""

from .models import KursMashq

GRAMMAR = "PART 1: GRAMMAR"
VOCABULARY = "PART 2: VOCABULARY & EVERYDAY ENGLISH"


def sarlavha(grammar_soni, jami):
    if grammar_soni >= jami:
        return f"{GRAMMAR} (1–{jami})"
    return f"{GRAMMAR} (1–{grammar_soni}) · {VOCABULARY} ({grammar_soni + 1}–{jami})"


def test_mashqini_yarat(tests_tugun, grammar, vocabulary):
    """Grammar + Vocabulary savollaridan bitta mashq yaratadi."""
    savollar = list(grammar) + list(vocabulary)
    return KursMashq.objects.create(
        tugun=tests_tugun, tartib=1, savollar=savollar,
        matn=sarlavha(len(grammar), len(savollar)),
    )


def test_mashqlarini_birlashtir(tests_tugun):
    """Ikki qismga bo'lingan eski testni bitta mashqqa birlashtiradi.
    Idempotent: bitta (yoki nol) mashq bo'lsa — tegilmaydi. Qismlar
    "PART 1"/"PART 2" sarlavhali bo'lsagina birlashtiriladi, admin qo'lda
    qo'shgan boshqa mashqlarga tegilmaydi."""
    mashqlar = list(tests_tugun.mashqlar.order_by("tartib", "id"))
    if len(mashqlar) != 2 or not all(
        m.matn.upper().startswith(("PART 1", "PART 2")) for m in mashqlar
    ):
        return False
    birinchi, ikkinchi = mashqlar
    grammar_soni = len(birinchi.savollar)
    birinchi.savollar = birinchi.savollar + ikkinchi.savollar
    birinchi.matn = sarlavha(grammar_soni, len(birinchi.savollar))
    birinchi.tartib = 1
    birinchi.save(update_fields=["savollar", "matn", "tartib"])
    ikkinchi.delete()
    return True
