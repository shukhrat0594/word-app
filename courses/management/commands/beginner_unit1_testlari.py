"""Beginner > Unit 1 > Tests bo'limiga "Unit 1 Practice Test" (A1) PDF'idagi
30 ta savolni kiritadi (2026-10-11, Matn-TZ 246). Ikki mashq: Part 1
Grammar (15) va Part 2 Vocabulary & Everyday English (15), javoblar
PDF'dagi ANSWER KEY bo'yicha.

Idempotent: Tests tugunida mashq allaqachon bo'lsa — tegilmaydi."""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from courses.models import KursTugun
from courses.test_mashqi import test_mashqini_yarat

# (savol, variantlar A-D, to'g'ri harf)
GRAMMAR = [
    ("Hello, I _____ Anna.", ["am", "is", "are", "be"], "A"),
    ("What is _____ name?", ["you", "your", "I", "he"], "B"),
    ("My name _____ John.", ["am", "are", "is", "be"], "C"),
    ("How _____ you?", ["is", "am", "are", "do"], "C"),
    ("Max, _____ is David.", ["this", "that's", "it", "here"], "A"),
    ("This is _____ apple.", ["a", "an", "two", "the"], "B"),
    ("What's this _____ English?", ["at", "on", "in", "to"], "C"),
    ("It's _____ book.", ["an", "a", "three", "two"], "B"),
    ("Two _____.", ["book", "books", "bookes", "a book"], "B"),
    ("Five _____.", ["sandwich", "sandwichs", "sandwiches", "a sandwich"], "C"),
    ("A: How are you? B: Fine, _____ you.", ["thank", "thanks", "pleased", "good"], "A"),
    ("_____ name is Sarah. She is a student.", ["My", "Your", "Her", "His"], "C"),
    ("Three _____.", ["bus", "buses", "buss", "bussed"], "B"),
    ("What _____ it? It's a computer.", ["am", "are", "is", "be"], "C"),
    ("A: Nice to meet you. B: Nice to meet you, _____.", ["two", "to", "too", "also"], "C"),
]
VOCABULARY = [
    ('What number is this? "7"', ["six", "seven", "eight", "nine"], "B"),
    ('"1, 2, 3, 4, _____"', ["five", "six", "four", "ten"], "A"),
    ('What number is this? "9"', ["eight", "ten", "nine", "five"], "C"),
    ("Which word means a drink?", ["house", "tea", "book", "bag"], "B"),
    ("You take photos with a _____.", ["camera", "car", "book", "house"], "A"),
    ("What do you say in the morning?", ["Good night", "Good morning", "Good afternoon", "Goodbye"], "B"),
    ("What do you say before going to sleep?", ["Good morning", "Hello", "Good night", "How are you?"], "C"),
    ("A: Have a nice day! B: _____.", ["You too!", "Fine, thanks.", "Good night.", "Hello."], "A"),
    ("Which item is used for transport?", ["apple", "taxi", "book", "cup"], "B"),
    ("You call your friends using a _____.", ["computer", "phone", "television", "bag"], "B"),
    ('How do you spell the number "8"?', ["eigt", "eight", "eigth", "aight"], "B"),
    ("Which word is NOT a greeting?", ["Hello", "Hi", "Goodbye", "Sandwich"], "D"),
    ("A: Cup of tea, please. B: _____.", ["Goodbye", "Here you are.", "Fine, thanks.", "Nice to meet you."], "B"),
    ("People live in a _____.", ["house", "bus", "phone", "sandwich"], "A"),
    ("A: Bye! B: _____!", ["See you later", "Good morning", "Hello", "Nice to meet you"], "A"),
]


def savollar(qatorlar):
    return [
        {"savol": s, "variantlar": v, "togri": v["ABCD".index(h)]}
        for s, v, h in qatorlar
    ]


class Command(BaseCommand):
    help = "Beginner Unit 1 Tests bo'limiga Practice Test savollarini kiritadi"

    def handle(self, *args, **options):
        call_command("tests_tugun_qoshish", stdout=self.stdout)
        beginner = KursTugun.objects.filter(kalit="beginner", parent__kalit="ingliz_tili").first()
        unit = beginner and KursTugun.objects.filter(
            parent=beginner, unit_darsi=True).order_by("tartib", "id").first()
        if not unit:
            self.stdout.write(self.style.WARNING("Beginner Unit 1 topilmadi — o'tkazib yuborildi"))
            return
        tests = KursTugun.objects.get(parent=unit, kalit="tests")
        if tests.mashqlar.exists():
            self.stdout.write(f"{unit.nomi} > Tests: mashqlar allaqachon bor — tegilmadi")
            return
        test_mashqini_yarat(tests, savollar(GRAMMAR), savollar(VOCABULARY))
        self.stdout.write(self.style.SUCCESS(
            f"{unit.nomi} > Tests: 1 mashq, {len(GRAMMAR) + len(VOCABULARY)} savol kiritildi"))
