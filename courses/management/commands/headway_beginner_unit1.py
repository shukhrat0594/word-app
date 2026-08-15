"""Headway Beginner 5th edition — Unit 1 "Hello!" kontentini to'g'ridan-
to'g'ri bazaga yozadi (2026-08-16, foydalanuvchi talabi: "push qilinganda
chiqadigan qilib" — ya'ni admin panelidan qo'lda JSON/rasm yuklashning
o'rniga, shu buyruq orqali tayyor holda).

Manba: Student's Book 5th edition (Teacher's Guide bilan tasdiqlangan
javoblar). Rasmlar shu fayl bilan bir papkada, `courses/fixtures/headway/
unit1/*.png` — repo bilan birga push qilinadi, shuning uchun prod'da ham
ishlaydi.

Idempotent: Beginner darajasida "Unit 1" allaqachon mavjud bo'lsa (mashq/
so'z bilan to'ldirilgan) — hech narsa qilmaydi, xato ham bermaydi."""

import os

from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursMashq, KursSoz, KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat

RASM_PAPKA = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "headway", "unit1")

MASHQLAR = [
    {
        "rasm": "grammar_spot.png",
        "matn": "GRAMMAR SPOT — Write 'm, is, or are.",
        "savollar": [
            {"savol": "I ____ Helen.", "variantlar": ["'m", "is", "are"], "togri": "'m", "pozitsiya": {"x": 25, "y": 64, "kenglik": 12}},
            {"savol": "How ____ you?", "variantlar": ["'m", "is", "are"], "togri": "are", "pozitsiya": {"x": 30, "y": 66, "kenglik": 12}},
            {"savol": "This ____ Tom.", "variantlar": ["'m", "is", "are"], "togri": "is", "pozitsiya": {"x": 30, "y": 68, "kenglik": 12}},
        ],
    },
    {
        "rasm": "check_it.png",
        "matn": "Check it — Complete the conversations.",
        "savollar": [
            {"savol": "1. Hello. My name's Usha. ____ your name?", "togri": "What's", "pozitsiya": {"x": 62, "y": 30, "kenglik": 12}},
            {"savol": "1. ____ Ben.", "togri": "My name's", "pozitsiya": {"x": 25, "y": 32, "kenglik": 15}},
            {"savol": "2. Shi, ____ is Huan.", "togri": "this", "pozitsiya": {"x": 19, "y": 55, "kenglik": 12}},
            {"savol": "2. Hello, Shi. ____ to meet you.", "togri": "Nice", "pozitsiya": {"x": 28, "y": 59, "kenglik": 12}},
            {"savol": "3. Hi, Sophie. How ____ you?", "togri": "are", "pozitsiya": {"x": 43, "y": 79, "kenglik": 12}},
            {"savol": "3. Fine, thanks, Amy. And ____?", "togri": "you", "pozitsiya": {"x": 50, "y": 81, "kenglik": 12}},
            {"savol": "3. ____ well, thanks.", "togri": "Very", "pozitsiya": {"x": 19, "y": 83, "kenglik": 12}},
        ],
    },
    {
        "rasm": "everyday1.png",
        "matn": "Everyday English 1 — Complete the conversations (Goodbye! / Goodnight! / Good afternoon!).",
        "savollar": [
            {"savol": "A: ____ / B: Hello. A cup of tea, please.", "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"], "togri": "Good afternoon!", "pozitsiya": {"x": 30, "y": 38, "kenglik": 20}},
            {"savol": "A: ____. Have a nice day! / B: Bye! See you later, Mum!", "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"], "togri": "Goodbye!", "pozitsiya": {"x": 34, "y": 57, "kenglik": 20}},
            {"savol": "A: ____! Sleep well. / B: Night night, Daddy.", "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"], "togri": "Goodnight!", "pozitsiya": {"x": 34, "y": 75, "kenglik": 20}},
        ],
    },
    {
        "rasm": "everyday2.png",
        "matn": "Everyday English 2 — Put the words in the correct order.",
        "savollar": [
            {"savol": "2-suhbat, B: please / coffee, / A", "togri": "A coffee, please.", "pozitsiya": {"x": 57, "y": 38, "kenglik": 25}},
            {"savol": "3-suhbat, A: nice / Have / day / a", "togri": "Have a nice day.", "pozitsiya": {"x": 57, "y": 54, "kenglik": 25}},
            {"savol": "3-suhbat, B: you / later / See", "togri": "See you later.", "pozitsiya": {"x": 57, "y": 61, "kenglik": 25}},
            {"savol": "4-suhbat, A: well / Sleep", "togri": "Sleep well.", "pozitsiya": {"x": 57, "y": 74, "kenglik": 25}},
            {"savol": "4-suhbat, B: you / And", "togri": "And you.", "pozitsiya": {"x": 57, "y": 81, "kenglik": 25}},
        ],
    },
    {
        "rasm": "vocabulary.png",
        "matn": "Vocabulary — What's this in English? Write the words.",
        "savollar": [
            {"savol": "1-rasm", "togri": "a book", "pozitsiya": {"x": 14, "y": 26, "kenglik": 12}},
            {"savol": "2-rasm", "togri": "a phone", "pozitsiya": {"x": 38, "y": 26, "kenglik": 12}},
            {"savol": "3-rasm", "togri": "a photo", "pozitsiya": {"x": 59, "y": 26, "kenglik": 12}},
            {"savol": "4-rasm", "togri": "a bike", "pozitsiya": {"x": 84, "y": 26, "kenglik": 12}},
            {"savol": "5-rasm", "togri": "a sandwich", "pozitsiya": {"x": 21, "y": 40, "kenglik": 12}},
            {"savol": "6-rasm", "togri": "a house", "pozitsiya": {"x": 84, "y": 40, "kenglik": 12}},
            {"savol": "7-rasm", "togri": "a laptop", "pozitsiya": {"x": 14, "y": 56, "kenglik": 12}},
            {"savol": "8-rasm", "togri": "a bag", "pozitsiya": {"x": 84, "y": 56, "kenglik": 12}},
            {"savol": "9-rasm", "togri": "a watch", "pozitsiya": {"x": 21, "y": 70, "kenglik": 12}},
            {"savol": "10-rasm", "togri": "a bus", "pozitsiya": {"x": 38, "y": 70, "kenglik": 12}},
            {"savol": "11-rasm", "togri": "an apple", "pozitsiya": {"x": 59, "y": 70, "kenglik": 12}},
            {"savol": "12-rasm", "togri": "an umbrella", "pozitsiya": {"x": 84, "y": 70, "kenglik": 12}},
        ],
    },
    {
        "rasm": "numbers.png",
        "matn": "Numbers 1-10 and plurals — Write the numbers.",
        "savollar": [
            {"savol": "1-band (books)", "togri": "five books", "pozitsiya": {"x": 43, "y": 15, "kenglik": 14}},
            {"savol": "2-band (bikes)", "togri": "three bikes", "pozitsiya": {"x": 38, "y": 21, "kenglik": 14}},
            {"savol": "3-band (houses)", "togri": "eight houses", "pozitsiya": {"x": 46, "y": 27, "kenglik": 14}},
            {"savol": "4-band (umbrellas)", "togri": "six umbrellas", "pozitsiya": {"x": 43, "y": 34, "kenglik": 14}},
            {"savol": "5-band (photos)", "togri": "nine photos", "pozitsiya": {"x": 41, "y": 44, "kenglik": 14}},
            {"savol": "6-band (laptops)", "togri": "four laptops", "pozitsiya": {"x": 41, "y": 47, "kenglik": 14}},
            {"savol": "7-band (watches)", "togri": "seven watches", "pozitsiya": {"x": 46, "y": 53, "kenglik": 14}},
            {"savol": "8-band (apples)", "togri": "ten apples", "pozitsiya": {"x": 46, "y": 65, "kenglik": 14}},
            {"savol": "9-band (sandwiches)", "togri": "two sandwiches", "pozitsiya": {"x": 40, "y": 67, "kenglik": 14}},
        ],
    },
]

VOCABULARY_MATN = (
    "GRAMMAR REFERENCE — Unit 1: Hello!\n\n"
    "1.1 am/are/is\n"
    "I 'm/am ... (masalan: I'm Serena.)\n"
    "You 're/are ... (masalan: You're Tom.)\n"
    "My name 's/is ... (masalan: My name's James Bond.)\n"
    "This is ... (masalan: This is Paul Bartosz.)\n\n"
    "1.2 Savol so'zlari bilan savollar\n"
    "What's your name? / What's this in English? (what's = what is)\n"
    "How are you?\n\n"
    "1.3 Egalik olmoshlari (Possessive adjectives)\n"
    "My name's John. / What's your name?\n\n"
    "1.4 a/an\n"
    "Unli tovush bilan boshlanadigan (a, e, i, o, u) so'zlardan oldin \"an\" ishlatiladi: "
    "an apple, an umbrella, an English book.\n"
    "Boshqa hollarda \"a\": a bike, a phone, a house.\n\n"
    "1.5 Ko'plik qo'shimchalari (Plural nouns)\n"
    "1) Ko'p so'zlarga -s qo'shiladi: book -> books, phone -> phones, laptop -> laptops.\n"
    "2) Ba'zilariga -es qo'shiladi (sh/ch/s/x/z tovushidan keyin): sandwich -> sandwiches, "
    "bus -> buses, watch -> watches.\n"
    "Talaffuz: /s/ (books), /z/ (apples), /ɪz/ (buses, houses, watches, sandwiches)."
)

WORDLIST = [
    {"en": "a cup of tea", "uz": "bir chashka choy"},
    {"en": "and", "uz": "va", "turkum": "conj"},
    {"en": "apple", "uz": "olma", "turkum": "n"},
    {"en": "bag", "uz": "sumka", "turkum": "n"},
    {"en": "bike", "uz": "velosiped", "turkum": "n"},
    {"en": "book", "uz": "kitob", "turkum": "n"},
    {"en": "bus", "uz": "avtobus", "turkum": "n"},
    {"en": "Bye!", "uz": "Xayr!", "turkum": "excl"},
    {"en": "coffee", "uz": "kofe", "turkum": "n"},
    {"en": "Daddy", "uz": "Dada", "turkum": "n"},
    {"en": "day", "uz": "kun", "turkum": "n"},
    {"en": "English", "uz": "ingliz tili", "turkum": "n"},
    {"en": "fine", "uz": "yaxshi", "turkum": "adj"},
    {"en": "first name", "uz": "ism (familiya emas)", "turkum": "n"},
    {"en": "Good afternoon!", "uz": "Xayrli kun! (tushdan keyin)", "turkum": "excl"},
    {"en": "Good morning!", "uz": "Xayrli tong!", "turkum": "excl"},
    {"en": "Good night!", "uz": "Xayrli tun!", "turkum": "excl"},
    {"en": "Goodbye!", "uz": "Xayr, ko'rishguncha!", "turkum": "excl"},
    {"en": "Have a nice day!", "uz": "Kuningiz xayrli o'tsin!"},
    {"en": "Hello!", "uz": "Salom!", "turkum": "excl"},
    {"en": "house", "uz": "uy", "turkum": "n"},
    {"en": "How are you?", "uz": "Qalaysiz? / Yaxshimisiz?"},
    {"en": "laptop", "uz": "noutbuk", "turkum": "n"},
    {"en": "lovely", "uz": "ajoyib, chiroyli", "turkum": "adj"},
    {"en": "Mum", "uz": "Ona", "turkum": "n"},
    {"en": "name", "uz": "ism", "turkum": "n"},
    {"en": "Nice to meet you.", "uz": "Tanishganimdan xursandman."},
    {"en": "OK", "uz": "yaxshi, yaxshimisan", "turkum": "adj"},
    {"en": "phone", "uz": "telefon", "turkum": "n"},
    {"en": "photo", "uz": "surat", "turkum": "n"},
    {"en": "please", "uz": "iltimos", "turkum": "excl"},
    {"en": "sandwich", "uz": "sendvich", "turkum": "n"},
    {"en": "See you later!", "uz": "Ko'rishguncha!", "turkum": "excl"},
    {"en": "Sleep well!", "uz": "Yaxshi uxlang!", "turkum": "excl"},
    {"en": "sugar", "uz": "shakar", "turkum": "n"},
    {"en": "surname", "uz": "familiya", "turkum": "n"},
    {"en": "Thank you", "uz": "Rahmat", "turkum": "excl"},
    {"en": "Thanks", "uz": "Rahmat", "turkum": "excl"},
    {"en": "this", "uz": "bu", "turkum": "pron"},
    {"en": "today", "uz": "bugun", "turkum": "adv"},
    {"en": "umbrella", "uz": "soyabon", "turkum": "n"},
    {"en": "very well", "uz": "juda yaxshi"},
    {"en": "watch", "uz": "soat (qo'l soati)", "turkum": "n"},
    {"en": "What?", "uz": "Nima?", "turkum": "pron"},
    {"en": "with", "uz": "bilan", "turkum": "prep"},
    {"en": "your", "uz": "sizning/sening", "turkum": "det"},
    {"en": "one", "uz": "bir"},
    {"en": "two", "uz": "ikki"},
    {"en": "three", "uz": "uch"},
    {"en": "four", "uz": "to'rt"},
    {"en": "five", "uz": "besh"},
    {"en": "six", "uz": "olti"},
    {"en": "seven", "uz": "yetti"},
    {"en": "eight", "uz": "sakkiz"},
    {"en": "nine", "uz": "to'qqiz"},
    {"en": "ten", "uz": "o'n"},
]


class Command(BaseCommand):
    help = "Headway Beginner Unit 1 (\"Hello!\") kontentini yaratadi (idempotent)"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.WARNING("Markaz topilmadi — o'tkazib yuborildi"))
            return

        ingliz = KursTugun.objects.filter(kalit="ingliz_tili", markaz=markaz).first()
        if not ingliz:
            self.stdout.write(self.style.ERROR("\"Ingliz tili\" tuguni topilmadi — avval kurslar_urugla ishga tushirilishi kerak"))
            return
        beginner = KursTugun.objects.filter(kalit="beginner", parent=ingliz).first()
        if not beginner:
            self.stdout.write(self.style.ERROR("\"Beginner\" tuguni topilmadi"))
            return

        unit = KursTugun.objects.filter(kalit="beginner_unit_1", parent=beginner).first()
        if not unit:
            mavjud = KursTugun.objects.filter(parent=beginner, unit_darsi=True).count()
            unit = KursTugun.objects.create(
                kalit="beginner_unit_1", nomi="Unit 1 — Hello!", parent=beginner,
                markaz=markaz, tartib=mavjud + 1, unit_darsi=True,
            )
            unit_ichki_tuzilmasini_yarat(unit)
            self.stdout.write("Unit 1 tuguni yaratildi")

        students_book = KursTugun.objects.filter(kalit="students_book", parent=unit).first()
        if not students_book:
            self.stdout.write(self.style.ERROR("Unit 1 ostida \"Student's Book\" tuguni topilmadi"))
            return
        mashq_tugun = KursTugun.objects.filter(kalit="mashqlar", parent=students_book).first()
        vocab_tugun = KursTugun.objects.filter(kalit="vocabulary", parent=students_book).first()
        if not mashq_tugun or not vocab_tugun:
            self.stdout.write(self.style.ERROR("Mashqlar/Vocabulary tugunlari topilmadi"))
            return

        if mashq_tugun.mashqlar.exists() or vocab_tugun.sozlar.exists() or vocab_tugun.matn:
            self.stdout.write(self.style.WARNING("Unit 1 allaqachon to'ldirilgan — o'tkazib yuborildi"))
            return

        for i, m in enumerate(MASHQLAR, start=1):
            mashq = KursMashq(
                tugun=mashq_tugun, tartib=i, matn=m["matn"], savollar=m["savollar"],
            )
            rasm_yoli = os.path.join(RASM_PAPKA, m["rasm"])
            if os.path.exists(rasm_yoli):
                with open(rasm_yoli, "rb") as fh:
                    mashq.rasm.save(m["rasm"], File(fh), save=False)
            else:
                self.stdout.write(self.style.WARNING(f"Rasm topilmadi: {rasm_yoli}"))
            mashq.save()

        vocab_tugun.matn = VOCABULARY_MATN
        vocab_tugun.save(update_fields=["matn"])

        KursSoz.objects.bulk_create([
            KursSoz(
                tugun=vocab_tugun, tartib=i, en=s["en"], uz=s["uz"],
                turkum=s.get("turkum", ""), misol=s.get("misol", ""),
            )
            for i, s in enumerate(WORDLIST, start=1)
        ])

        self.stdout.write(self.style.SUCCESS(
            f"Unit 1 tayyor: {len(MASHQLAR)} mashq, {len(WORDLIST)} so'z"
        ))
