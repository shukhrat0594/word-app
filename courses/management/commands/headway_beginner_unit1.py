"""Headway Beginner 5th edition — Unit 1 "Hello!" kontentini to'g'ridan-
to'g'ri bazaga yozadi (2026-08-16, foydalanuvchi talabi: "push qilinganda
chiqadigan qilib" — ya'ni admin panelidan qo'lda JSON/rasm yuklashning
o'rniga, shu buyruq orqali tayyor holda).

2026-08-16 (2-marta): rasm-ustiga-pozitsiya usulidan BUTUNLAY voz kechildi
(foydalanuvchi talabi — "Gemini'ga yuborib emas, o'zing mashqlar ishlash
oynasini yasab bergin"). Endi sahifa BLOK formatida ("bloklar" maydoni,
`courses/blok_generatsiya.py`da AI-generatsiya uchun ishlatiladigan format,
bu yerda qo'lda yozilgan): matn haqiqiy HTML matni (dialog/grammar_spot/
mashq bloklari), suratlar sahifadan ALOHIDA kesib olingan (`KursMashqRasmi`),
bo'sh joylar esa `mashq`/`grammar_spot` bloklari ichidagi haqiqiy <input>
maydonlari — rasm ustidan pozitsiya bo'yicha EMAS.

Har KITOB SAHIFASI — bitta alohida `KursMashq` (kitobdagi kabi ketma-ket
sahifalar). Faqat chinakam BAHOLANADIGAN bo'sh joylar `savollar`ga kiradi;
nutqiy/roleplay/mingle mashqlar "erkin" (baholanmaydigan) input sifatida
ko'rsatiladi yoki umuman kiritilmaydi.

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
from courses.models import KursMashq, KursMashqRasmi, KursSoz, KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat

RASM_PAPKA = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "headway", "unit1")


def _erkin(matn_oldin, matn_keyin=""):
    """Baholanmaydigan (talaba o'zi to'ldiradigan, masalan o'z ismi)
    bo'sh joyli bolak — mingle/speaking mashqlari uchun."""
    bolaklar = [{"matn": matn_oldin}, {"bosh_joy": True, "erkin": True}]
    if matn_keyin:
        bolaklar.append({"matn": matn_keyin})
    return bolaklar


# ---------------------------------------------------------------------
# SAHIFA 2 (Student's Book p8) — Starter + Grammar am/is, my/your.
# Rasmlar: 0=Mara, 1=Leo, 2=Nari, 3=Tom&Serena.
# Baholanadigan savol YO'Q (faqat nutqiy/mingle) — savollar=[].
# ---------------------------------------------------------------------
SAHIFA2_RASMLAR = ["p0_cover.png", "p1_mara.png", "p1_leo.png", "p1_nari.png", "p1_tomserena.png"]
SAHIFA2_BLOKLAR = [
    {"tur": "rasm", "rasm_idx": 0, "katta": True},
    {"tur": "korsatma", "raqam": "STARTER", "audio_raqam": "1.1", "matn": "Read and listen. Say your name."},
    {"tur": "rasm_qatori", "qator": [
        {"rasm_idx": 1, "izoh": "Mara", "matn": "Hello, I'm Mara."},
        {"rasm_idx": 2, "izoh": "Leo", "matn": "Hello, I'm Leo."},
        {"rasm_idx": 3, "izoh": "Nari", "matn": "Hello, I'm Nari."},
    ]},
    {"tur": "mashq", "bulut": True, "bolaklar": _erkin("Hello, I'm ", ". What's your name?")},
    {"tur": "bolim_sarlavha", "matn": "Grammar — am/is, my/your"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "1.2", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 4, "tomon": "ong"},
    {"tur": "dialog", "audio_raqam": "1.2", "qatorlar": [
        {"kim": "Serena", "gap": "Hello. I'm Serena. What's your name?"},
        {"kim": "Tom", "gap": "My name's Tom."},
        {"kim": "Serena", "gap": "Hello, Tom."},
    ]},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "1.2", "matn": "Listen again and repeat."},
    {"tur": "grammar_spot", "sarlavha": "GRAMMAR SPOT", "qatorlar": [
        "I'm = I am", "What's = What is", "name's = name is",
    ]},
    {"tur": "korsatma", "raqam": "3", "matn": "Stand up and practise."},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": _erkin("Hello, I'm ", ". What's your name?")},
    {"tur": "mashq", "bulut": True, "kim": "B", "bolaklar": _erkin("My name's ", ".")},
]

# ---------------------------------------------------------------------
# SAHIFA 3 (Student's Book p9) — Introductions (This is.../Nice to meet you).
# Rasmlar: 0=Serena/Tom/Carlos, 1=Paul/Sarah.
# Baholanadigan savol YO'Q.
# ---------------------------------------------------------------------
SAHIFA3_RASMLAR = ["p2_group3.png", "p2_paulsarah.png", "p2_elvis_cleopatra.png"]
SAHIFA3_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Introductions — This is..."},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "1.3", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 0, "tomon": "ong"},
    {"tur": "dialog", "audio_raqam": "1.3", "qatorlar": [
        {"kim": "Serena", "gap": "Tom, this is Carlos. Carlos, this is Tom."},
        {"kim": "Tom", "gap": "Hello, Carlos."},
        {"kim": "Carlos", "gap": "Hello, Tom."},
    ]},
    {"tur": "korsatma", "raqam": "2", "matn": "Practise in groups of three."},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": [
        {"bosh_joy": True, "erkin": True}, {"matn": ", this is "}, {"bosh_joy": True, "erkin": True}, {"matn": "."},
    ]},
    {"tur": "mashq", "bulut": True, "kim": "B", "bolaklar": [
        {"bosh_joy": True, "erkin": True}, {"matn": ", this is "}, {"bosh_joy": True, "erkin": True}, {"matn": "."},
    ]},
    {"tur": "mashq", "bulut": True, "kim": "C", "bolaklar": _erkin("Hello, ", ".")},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": _erkin("Hello, ", ".")},
    {"tur": "bolim_sarlavha", "matn": "Nice to meet you"},
    {"tur": "korsatma", "raqam": "3", "audio_raqam": "1.4", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 1, "tomon": "ong"},
    {"tur": "dialog", "audio_raqam": "1.4", "qatorlar": [
        {"kim": "Paul", "gap": "Hello. My name's Paul Bartosz."},
        {"kim": "Sarah", "gap": "Hello. I'm Sarah Taylor. Nice to meet you."},
        {"kim": "Paul", "gap": "Nice to meet you, too."},
    ]},
    {"tur": "korsatma", "raqam": "4", "matn": "Practise in pairs. Say your first name and your surname."},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": _erkin("Hello. My name's ", ".")},
    {"tur": "mashq", "bulut": True, "kim": "B", "bolaklar": _erkin("Hello. I'm ", ". Nice to meet you.")},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": [{"matn": "Nice to meet you, too."}]},
    {"tur": "korsatma", "raqam": "5", "matn": "Choose a name. Stand up and say hello."},
    {"tur": "rasm", "rasm_idx": 2, "tomon": "ong"},
    {"tur": "mashq", "bulut": True, "bolaklar": [{"matn": "Hello. My name's Elvis Presley."}]},
    {"tur": "mashq", "bulut": True, "bolaklar": [{"matn": "Hello. I'm Cleopatra."}]},
    {"tur": "mashq", "bulut": True, "bolaklar": [{"matn": "Nice to meet you."}]},
    {"tur": "mashq", "bulut": True, "bolaklar": [{"matn": "Nice to meet you, too!"}]},
]

# ---------------------------------------------------------------------
# SAHIFA 4 (Student's Book p10) — How are you? + Check it.
# Rasmlar: 0=Artur/Dinos, 1=Linda/May, 2=Check1, 3=Check2, 4=Check3.
# GRADED savol_idx 0-9.
# ---------------------------------------------------------------------
SAHIFA4_RASMLAR = [
    "p3_arturdinos.png", "p3_lindamay.png", "p3_check1.png", "p3_check2.png", "p3_check3.png",
]
SAHIFA4_SAVOLLAR = [
    {"savol": "I ____ Helen.", "togri": "'m", "variantlar": ["'m", "is", "are"]},
    {"savol": "How ____ you?", "togri": "are", "variantlar": ["'m", "is", "are"]},
    {"savol": "This ____ Tom.", "togri": "is", "variantlar": ["'m", "is", "are"]},
    {"savol": "Hello. My name's Usha. ____ your name?", "togri": "What's"},
    {"savol": "____ Ben.", "togri": "My name's"},
    {"savol": "Shi, ____ is Huan.", "togri": "this"},
    {"savol": "Hello, Shi. ____ to meet you.", "togri": "Nice"},
    {"savol": "Hi, Sophie. How ____ you?", "togri": "are"},
    {"savol": "Fine, thanks, Amy. And ____?", "togri": "you"},
    {"savol": "____ well, thanks.", "togri": "Very"},
]
SAHIFA4_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "How are you?"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "1.5", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 0, "tomon": "ong"},
    {"tur": "dialog", "qatorlar": [
        {"kim": "Artur", "gap": "Hi, Dinos. How are you?"},
        {"kim": "Dinos", "gap": "Fine, thanks, Artur. And you?"},
        {"kim": "Artur", "gap": "I'm OK, thanks."},
    ]},
    {"tur": "rasm", "rasm_idx": 1, "tomon": "ong"},
    {"tur": "dialog", "qatorlar": [
        {"kim": "Linda", "gap": "Hello, May. How are you?"},
        {"kim": "May", "gap": "Very well, thank you. How are you?"},
        {"kim": "Linda", "gap": "Fine."},
    ]},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "1.5", "matn": "Listen again and repeat."},
    {"tur": "grammar_spot", "sarlavha": "GRAMMAR SPOT — Write 'm, is, or are.", "qatorlar": [
        {"bolaklar": [{"matn": "I "}, {"bosh_joy": True, "savol_idx": 0}, {"matn": " Helen."}]},
        {"bolaklar": [{"matn": "How "}, {"bosh_joy": True, "savol_idx": 1}, {"matn": " you?"}]},
        {"bolaklar": [{"matn": "This "}, {"bosh_joy": True, "savol_idx": 2}, {"matn": " Tom."}]},
    ]},
    {"tur": "korsatma", "raqam": "4", "matn": "Check it — Complete the conversations."},
    {"tur": "rasm", "rasm_idx": 2, "tomon": "ong"},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: Hello. My name's Usha. "}, {"bosh_joy": True, "savol_idx": 3}, {"matn": " your name?"}]},
        {"bolaklar": [{"matn": "B: "}, {"bosh_joy": True, "savol_idx": 4}, {"matn": " Ben."}]},
    ]},
    {"tur": "rasm", "rasm_idx": 3, "tomon": "ong"},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: Shi, "}, {"bosh_joy": True, "savol_idx": 5}, {"matn": " is Huan."}]},
        {"bolaklar": [{"matn": "B: Hello, Huan."}]},
        {"bolaklar": [{"matn": "C: Hello, Shi. "}, {"bosh_joy": True, "savol_idx": 6}, {"matn": " to meet you."}]},
    ]},
    {"tur": "rasm", "rasm_idx": 4, "tomon": "ong"},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: Hi, Sophie. How "}, {"bosh_joy": True, "savol_idx": 7}, {"matn": " you?"}]},
        {"bolaklar": [{"matn": "B: Fine, thanks, Amy. And "}, {"bosh_joy": True, "savol_idx": 8}, {"matn": "?"}]},
        {"bolaklar": [{"matn": "A: "}, {"bosh_joy": True, "savol_idx": 9}, {"matn": " well, thanks."}]},
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 5 (Student's Book p11) — Everyday English: Good morning!
# Rasmlar: 0=morning, 1=afternoon, 2=goodbye, 3=goodnight.
# GRADED savol_idx 0-7.
# ---------------------------------------------------------------------
SAHIFA5_RASMLAR = ["p4_morning.png", "p4_afternoon.png", "p4_goodbye.png", "p4_goodnight.png"]
SAHIFA5_SAVOLLAR = [
    {"savol": "A: ____ / B: Hello. A cup of tea, please.", "togri": "Good afternoon!",
     "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"]},
    {"savol": "A: ____. Have a nice day! / B: Bye! See you later, Mum!", "togri": "Goodbye!",
     "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"]},
    {"savol": "A: ____! Sleep well. / B: Night night, Daddy.", "togri": "Goodnight!",
     "variantlar": ["Goodbye!", "Goodnight!", "Good afternoon!"]},
    {"savol": "2-suhbat, B: (please / coffee, / A)", "togri": "A coffee, please."},
    {"savol": "3-suhbat, A: (nice / Have / day / a)", "togri": "Have a nice day."},
    {"savol": "3-suhbat, B: (you / later / See)", "togri": "See you later."},
    {"savol": "4-suhbat, A: (well / Sleep)", "togri": "Sleep well."},
    {"savol": "4-suhbat, B: (you / And)", "togri": "And you."},
]
SAHIFA5_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Everyday English — Good morning!"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "1.6", "matn": "Complete the conversations."},
    {"tur": "soz_banki", "qatorlar": [
        "Goodbye!", "Goodnight!", {"matn": "Good morning!", "ishlatilgan": True}, "Good afternoon!",
    ]},
    {"tur": "dialog", "qatorlar": [
        {"kim": "A", "gap": "Good morning!", "namuna": True},
        {"kim": "B", "gap": "Good morning! What a lovely day!"},
    ]},
    {"tur": "rasm", "rasm_idx": 0},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: "}, {"bosh_joy": True, "savol_idx": 0}]},
        {"bolaklar": [{"matn": "B: Hello. A cup of tea, please."}]},
    ]},
    {"tur": "rasm", "rasm_idx": 1},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: "}, {"bosh_joy": True, "savol_idx": 1}, {"matn": " Have a nice day!"}]},
        {"bolaklar": [{"matn": "B: Bye! See you later, Mum!"}]},
    ]},
    {"tur": "rasm", "rasm_idx": 2},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "A: "}, {"bosh_joy": True, "savol_idx": 2}, {"matn": "! Sleep well."}]},
        {"bolaklar": [{"matn": "B: Night night, Daddy."}]},
    ]},
    {"tur": "rasm", "rasm_idx": 3},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "1.7", "matn": "Put the words in the correct order."},
    {"tur": "matn", "matn": "1) A: Good morning!"},
    {"tur": "soz_banki", "qatorlar": ["are", "you", "How", "today"]},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "How are you today?", "namuna": True},
        {"kim": "B", "gap": "Fine, thanks. And you?"},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "2) A: Good afternoon!"}]},
        {"bolaklar": [{"matn": "B: Good afternoon! "}, {"bosh_joy": True, "savol_idx": 3}, {"matn": " (please / coffee, / A)"}]},
        {"bolaklar": [{"matn": "A: Sugar?  B: Yes, please."}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "3) A: Goodbye! "}, {"bosh_joy": True, "savol_idx": 4}, {"matn": " (nice / Have / day / a)"}]},
        {"bolaklar": [{"matn": "B: Thank you. And you. "}, {"bosh_joy": True, "savol_idx": 5}, {"matn": " (you / later / See)"}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "4) A: Goodnight! "}, {"bosh_joy": True, "savol_idx": 6}, {"matn": " (well / Sleep)"}]},
        {"bolaklar": [{"matn": "B: Thank you. "}, {"bosh_joy": True, "savol_idx": 7}, {"matn": " (you / And)"}]},
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 6 (Student's Book p12) — Vocabulary: What's this in English?
# Rasmlar: 0-11 = v1_book..v12_umbrella.
# GRADED savol_idx 0-11.
# ---------------------------------------------------------------------
SAHIFA6_RASMLAR = [
    "v1_book.png", "v2_phone.png", "v3_photo.png", "v4_bike.png", "v5_sandwich.png", "v6_house.png",
    "v7_laptop.png", "v8_bag.png", "v9_watch.png", "v10_bus.png", "v11_apple.png", "v12_umbrella.png",
]
SAHIFA6_SAVOLLAR_TOGRI = [
    "a book", "a phone", "a photo", "a bike", "a sandwich", "a house",
    "a laptop", "a bag", "a watch", "a bus", "an apple", "an umbrella",
]
SAHIFA6_SAVOLLAR = [{"savol": f"{i}-rasm", "togri": t} for i, t in enumerate(SAHIFA6_SAVOLLAR_TOGRI, start=1)]
SAHIFA6_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Vocabulary — What's this in English?"},
    {"tur": "korsatma", "raqam": "1", "matn": "Write the words."},
    {"tur": "soz_banki", "qatorlar": [
        "a bus", "a phone", "an apple", "a laptop", "an umbrella", "a bike",
        "a house", "a bag", "a watch", "a book", "a sandwich", "a photo",
    ]},
    {"tur": "rasm_javobli_grid", "itemlar": [
        {"rasm_idx": i, "raqam": str(i + 1), "savol_idx": i} for i in range(12)
    ]},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "1.8", "matn": "Listen and repeat the words."},
    {"tur": "korsatma", "raqam": "3", "audio_raqam": "1.9", "matn": "Listen and repeat."},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "What's this in English?"},
        {"kim": "", "gap": "It's a photo."},
    ]},
    {"tur": "korsatma", "raqam": "4", "matn": "Work with a partner. Point to a photo. Ask and answer questions."},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "What's this in English?"},
        {"kim": "", "gap": "It's a watch."},
    ]},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "What's this in English?"},
        {"kim": "", "gap": "It's an apple."},
    ]},
    {"tur": "korsatma", "raqam": "5", "matn": "Point to things in the room. Ask your teacher."},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "What's this in English?"},
        {"kim": "", "gap": "It's a/an ..."},
    ]},
    {"tur": "grammar_spot", "sarlavha": "GRAMMAR SPOT", "qatorlar": [
        "It's = It is",
        "a book — an apple",
        "a watch — an umbrella",
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 7 (Student's Book p13) — Numbers 1-10 and plurals.
# Rasmlar: 0-8 = n1_books..n9_sandwiches.
# GRADED savol_idx 0-8.
# ---------------------------------------------------------------------
SAHIFA7_RASMLAR = [
    "n1_books.png", "n2_bikes.png", "n3_houses.png", "n4_umbrellas.png", "n5_photos.png",
    "n6_laptops.png", "n7_watches.png", "n8_apples.png", "n9_sandwiches.png",
]
SAHIFA7_SAVOLLAR_TOGRI = ["five", "three", "eight", "six", "nine", "four", "seven", "ten", "two"]
SAHIFA7_BIRLIKLAR = ["books", "bikes", "houses", "umbrellas", "photos", "laptops", "watches", "apples", "sandwiches"]
SAHIFA7_SAVOLLAR = [{"savol": f"{i}-band", "togri": t} for i, t in enumerate(SAHIFA7_SAVOLLAR_TOGRI, start=1)]
SAHIFA7_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Numbers 1-10 and plurals"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "1.10", "matn": "Read and listen. Practise the numbers."},
    {"tur": "matn", "matn": "one, two, three, four, five, six, seven, eight, nine, ten"},
    {"tur": "korsatma", "raqam": "2", "matn": "Say the numbers round the class."},
    {"tur": "korsatma", "raqam": "3", "audio_raqam": "1.11", "matn": "Write the numbers."},
    {"tur": "rasm_javobli_grid", "qator_boyicha": True, "itemlar": [
        {"rasm_idx": i, "raqam": str(i + 1), "savol_idx": i, "birlik": SAHIFA7_BIRLIKLAR[i]} for i in range(9)
    ]},
    {"tur": "korsatma", "audio_raqam": "1.11", "matn": "Listen and check."},
    {"tur": "korsatma", "raqam": "4", "audio_raqam": "1.12", "matn": "Listen and repeat."},
    {"tur": "jadval", "sarlavhalar": ["/s/", "/z/", "/ɪz/"], "qatorlar": [
        ["books", "apples", "buses"],
        ["bikes", "bags", "houses"],
        ["laptops", "phones", "watches"],
        ["", "photos", "sandwiches"],
        ["", "umbrellas", ""],
    ]},
    {"tur": "korsatma", "raqam": "5", "matn": "Ask and answer questions."},
    {"tur": "dialog", "qatorlar": [
        {"kim": "", "gap": "What's in 3?"},
        {"kim": "", "gap": "Eight houses."},
    ]},
    {"tur": "bolim_sarlavha", "matn": "GRAMMAR SPOT"},
    {"tur": "jadval", "sarlavhalar": ["Singular", "Plural"], "qatorlar": [
        ["one book", "two books"],
        ["one bus", "two buses"],
    ]},
]

SAHIFALAR = [
    (2, SAHIFA2_RASMLAR, SAHIFA2_BLOKLAR, []),
    (3, SAHIFA3_RASMLAR, SAHIFA3_BLOKLAR, []),
    (4, SAHIFA4_RASMLAR, SAHIFA4_BLOKLAR, SAHIFA4_SAVOLLAR),
    (5, SAHIFA5_RASMLAR, SAHIFA5_BLOKLAR, SAHIFA5_SAVOLLAR),
    (6, SAHIFA6_RASMLAR, SAHIFA6_BLOKLAR, SAHIFA6_SAVOLLAR),
    (7, SAHIFA7_RASMLAR, SAHIFA7_BLOKLAR, SAHIFA7_SAVOLLAR),
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
    help = "Headway Beginner Unit 1 (\"Hello!\") kontentini yaratadi (idempotent, blok format)"

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
            # 2026-08-17: tartib qat'iy 1 (mavjud Unitlar soniga qarab
            # HISOBLANMAYDI) — aks holda Unit 1 biror sababga ko'ra
            # (masalan qayta yaratilganda) Unit 2'dan KEYIN ishga
            # tushsa, ikkalasi ham bir xil tartibga ega bo'lib, ro'yxatda
            # adashib qolar edi (haqiqiy production xatosi, 2026-08-17).
            unit = KursTugun.objects.create(
                kalit="beginner_unit_1", nomi="Unit 1 — Hello!", parent=beginner,
                markaz=markaz, tartib=1, unit_darsi=True,
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

        for tartib, rasmlar, bloklar, savollar in SAHIFALAR:
            mashq = KursMashq(tugun=mashq_tugun, tartib=tartib, bloklar=bloklar, savollar=savollar)
            mashq.save()
            for idx, rasm_nomi in enumerate(rasmlar):
                rasm_yoli = os.path.join(RASM_PAPKA, rasm_nomi)
                if not os.path.exists(rasm_yoli):
                    self.stdout.write(self.style.WARNING(f"Rasm topilmadi: {rasm_yoli}"))
                    continue
                r = KursMashqRasmi(mashq=mashq, tartib=idx)
                with open(rasm_yoli, "rb") as fh:
                    r.rasm.save(rasm_nomi, File(fh), save=False)
                r.save()
            self.stdout.write(f"Sahifa {tartib} tayyor: {len(bloklar)} blok, {len(rasmlar)} rasm")

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
            f"Unit 1 tayyor: {len(SAHIFALAR)} sahifa, {len(WORDLIST)} so'z"
        ))
