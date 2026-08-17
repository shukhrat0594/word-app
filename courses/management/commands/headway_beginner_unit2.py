"""Headway Beginner 5th edition — Unit 2 "Your world" kontentini
to'g'ridan-to'g'ri bazaga yozadi (2026-08-16, `headway_beginner_unit1.py`
bilan bir xil naqsh — blok/HTML format, rasm-ustiga-pozitsiya EMAS).

Manba: Student's Book 5th edition (Teacher's Guide bilan tasdiqlangan
javoblar). Rasmlar `courses/fixtures/headway/unit2/*.png`.

Idempotent: Beginner darajasida "Unit 2" allaqachon mavjud bo'lsa (mashq/
so'z bilan to'ldirilgan) — hech narsa qilmaydi, xato ham bermaydi."""

import os

from django.core.files import File
from django.core.management.base import BaseCommand

from accounts.models import Markaz
from courses.models import KursMashq, KursMashqRasmi, KursSoz, KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat

RASM_PAPKA = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "headway", "unit2")


def _erkin(matn_oldin, matn_keyin=""):
    bolaklar = [{"matn": matn_oldin}, {"bosh_joy": True, "erkin": True}]
    if matn_keyin:
        bolaklar.append({"matn": matn_keyin})
    return bolaklar


# ---------------------------------------------------------------------
# SAHIFA 2 (Student's Book p15) — Unit opener + flags matching.
# ---------------------------------------------------------------------
SAHIFA2_RASMLAR = ["p0_cover.png", "flags_grid.png"]
SAHIFA2_SAVOLLAR = [
    {"savol": "a", "togri": "the UK", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"savol": "b", "togri": "Scotland", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"savol": "c", "togri": "Canada", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"savol": "d", "togri": "England", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"savol": "e", "togri": "Australia", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"savol": "f", "togri": "the US", "variantlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
]
SAHIFA2_BLOKLAR = [
    {"tur": "rasm", "rasm_idx": 0, "katta": True},
    {"tur": "bolim_sarlavha", "matn": "Your world"},
    {"tur": "korsatma", "raqam": "1", "matn": "Match the countries below to the flags."},
    {"tur": "soz_banki", "qatorlar": ["Canada", "Australia", "the US", "the UK", "England", "Scotland"]},
    {"tur": "rasm", "rasm_idx": 1},
    {"tur": "mashq", "bolaklar": [
        {"matn": "a: "}, {"bosh_joy": True, "savol_idx": 0},
    ]},
    {"tur": "mashq", "bolaklar": [
        {"matn": "b: "}, {"bosh_joy": True, "savol_idx": 1},
    ]},
    {"tur": "mashq", "bolaklar": [
        {"matn": "c: "}, {"bosh_joy": True, "savol_idx": 2},
    ]},
    {"tur": "mashq", "bolaklar": [
        {"matn": "d: "}, {"bosh_joy": True, "savol_idx": 3},
    ]},
    {"tur": "mashq", "bolaklar": [
        {"matn": "e: "}, {"bosh_joy": True, "savol_idx": 4},
    ]},
    {"tur": "mashq", "bolaklar": [
        {"matn": "f: "}, {"bosh_joy": True, "savol_idx": 5},
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 3 (Student's Book p16) — She's from China (Starter + Grammar he/she).
# Baholanadigan savol YO'Q (nutqiy/taqdimot).
# ---------------------------------------------------------------------
SAHIFA3_RASMLAR = ["antonio_nuwa.png", "antonio_small.png", "nuwa_small.png"]
SAHIFA3_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "She's from China"},
    {"tur": "korsatma", "raqam": "STARTER", "audio_raqam": "2.1", "matn": "Find your country on the map. Find these countries. Listen and repeat."},
    {"tur": "soz_banki", "qatorlar": [
        "Argentina", "Australia", "Brazil", "Canada", "China", "England", "Egypt",
        "France", "Italy", "Japan", "Spain", "Russia", "Turkey", "the US",
    ]},
    {"tur": "bolim_sarlavha", "matn": "Grammar — he/she, his/her"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "2.2", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 0},
    {"tur": "dialog", "audio_raqam": "2.2", "qatorlar": [
        {"kim": "Antonio", "gap": "Hello, I'm Antonio. What's your name?"},
        {"kim": "Nuwa", "gap": "My name's Nuwa."},
        {"kim": "Antonio", "gap": "Where are you from, Nuwa?"},
        {"kim": "Nuwa", "gap": "I'm from China. Where are you from?"},
        {"kim": "Antonio", "gap": "I'm from Italy. From Milan."},
    ]},
    {"tur": "korsatma", "raqam": "2", "matn": "Where are you from? Stand up and practise."},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": _erkin("Where are you from?")},
    {"tur": "mashq", "bulut": True, "kim": "B", "bolaklar": _erkin("I'm from ", ". Where are you from?")},
    {"tur": "korsatma", "raqam": "3", "audio_raqam": "2.3", "matn": "Read, listen and repeat."},
    {"tur": "rasm_qatori", "qator": [
        {"rasm_idx": 1, "matn": "His name's Antonio. He's from Italy."},
        {"rasm_idx": 2, "matn": "Her name's Nuwa. She's from China."},
    ]},
    {"tur": "grammar_spot", "sarlavha": "GRAMMAR SPOT", "qatorlar": [
        "he's = he is", "she's = she is",
        "Female: she, her", "Male: he, his",
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 4 (Student's Book p17) — Questions: Where's she from? + Practice.
# GRADED savol_idx 0-18 (8 map + 3 grammar spot + 8 cities).
# ---------------------------------------------------------------------
SAHIFA4_RASMLAR = [
    "julie.png", "nadia.png", "anton.png", "geoff.png",
    "paula.png", "amun.png", "lan.png", "oliver.png",
]
SAHIFA4_SAVOLLAR = [
    {"savol": "2-rasm (Nadia)", "togri": "She's from Italy."},
    {"savol": "3-rasm (Anton)", "togri": "He's from Russia."},
    {"savol": "4-rasm (Geoff)", "togri": "He's from Canada."},
    {"savol": "5-rasm (Paula)", "togri": "She's from Brazil."},
    {"savol": "6-rasm (Amun)", "togri": "He's from Egypt."},
    {"savol": "7-rasm (Lan)", "togri": "She's from China."},
    {"savol": "8-rasm (Oliver)", "togri": "He's from Australia."},
    {"savol": "Where ____ she from?", "togri": "is"},
    {"savol": "Where ____ he from?", "togri": "is"},
    {"savol": "Where ____ you from?", "togri": "are"},
    {"savol": "Venice", "togri": "Italy"},
    {"savol": "New York", "togri": "the US"},
    {"savol": "Moscow", "togri": "Russia"},
    {"savol": "Paris", "togri": "France"},
    {"savol": "Beijing", "togri": "China"},
    {"savol": "Sydney", "togri": "Australia"},
    {"savol": "Rio de Janeiro", "togri": "Brazil"},
    {"savol": "Istanbul", "togri": "Turkey"},
]
SAHIFA4_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Questions — Where's she from?"},
    {"tur": "korsatma", "raqam": "1", "matn": "Complete the sentences about the people."},
    {"tur": "rasm_javobli_grid", "itemlar": [
        {"rasm_idx": 1, "raqam": "2", "savol_idx": 0},
        {"rasm_idx": 2, "raqam": "3", "savol_idx": 1},
        {"rasm_idx": 3, "raqam": "4", "savol_idx": 2},
        {"rasm_idx": 4, "raqam": "5", "savol_idx": 3},
        {"rasm_idx": 5, "raqam": "6", "savol_idx": 4},
        {"rasm_idx": 6, "raqam": "7", "savol_idx": 5},
        {"rasm_idx": 7, "raqam": "8", "savol_idx": 6},
    ]},
    {"tur": "matn", "matn": "1 (namuna): Her name's Julie. She's from England."},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "2.5", "matn": "Listen and repeat the questions: What's his/her name? Where's he/she from?"},
    {"tur": "korsatma", "raqam": "3", "matn": "Ask and answer questions about the people in the photos."},
    {"tur": "grammar_spot", "sarlavha": "GRAMMAR SPOT", "qatorlar": [
        {"bolaklar": [{"matn": "Where "}, {"bosh_joy": True, "savol_idx": 7}, {"matn": " she from?"}]},
        {"bolaklar": [{"matn": "Where "}, {"bosh_joy": True, "savol_idx": 8}, {"matn": " he from?"}]},
        {"bolaklar": [{"matn": "Where "}, {"bosh_joy": True, "savol_idx": 9}, {"matn": " you from?"}]},
    ]},
    {"tur": "bolim_sarlavha", "matn": "Practice — Cities and countries"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "2.6", "matn": "Where are the cities? Ask and answer."},
    {"tur": "soz_banki", "qatorlar": ["Australia", "France", "Russia", "the US", "Turkey", "Brazil", "Italy", "China"]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "Venice — "}, {"bosh_joy": True, "savol_idx": 10}]},
        {"bolaklar": [{"matn": "New York — "}, {"bosh_joy": True, "savol_idx": 11}]},
        {"bolaklar": [{"matn": "Moscow — "}, {"bosh_joy": True, "savol_idx": 12}]},
        {"bolaklar": [{"matn": "Paris — "}, {"bosh_joy": True, "savol_idx": 13}]},
        {"bolaklar": [{"matn": "Beijing — "}, {"bosh_joy": True, "savol_idx": 14}]},
        {"bolaklar": [{"matn": "Sydney — "}, {"bosh_joy": True, "savol_idx": 15}]},
        {"bolaklar": [{"matn": "Rio de Janeiro — "}, {"bosh_joy": True, "savol_idx": 16}]},
        {"bolaklar": [{"matn": "Istanbul — "}, {"bosh_joy": True, "savol_idx": 17}]},
    ]},
    {"tur": "korsatma", "raqam": "2", "matn": "Work with a partner — information gap activity (Student A / Student B, roleplay — kitobning p18-19/p141 sahifalarida)."},
    {"tur": "korsatma", "raqam": "3", "matn": "Talking about you — Ask about the students in the class."},
    {"tur": "mashq", "bulut": True, "kim": "A", "bolaklar": _erkin("What's his/her name?")},
    {"tur": "mashq", "bulut": True, "kim": "B", "bolaklar": _erkin("His/Her name's ", ".")},
]

# ---------------------------------------------------------------------
# SAHIFA 5 (Student's Book p18-19) — Questions and answers + Check it.
# GRADED savol_idx 0-22.
# ---------------------------------------------------------------------
SAHIFA5_SAVOLLAR = [
    {"savol": "1. Hello, I'm Blanca. What's ____ name?", "togri": "your"},
    {"savol": "1. ____ name's Rafael.", "togri": "My"},
    {"savol": "1. Hello, Rafael. Where are you ____?", "togri": "from"},
    {"savol": "1. ____ from Spain. Where are you from?", "togri": "I'm"},
    {"savol": "1. Oh, ____ from Spain, too. ____ Barcelona.", "togri": "I'm from"},
    {"savol": "Mateo: Argentina. Akemi: ____", "togri": "Japan"},
    {"savol": "Loretta and Jason: ____", "togri": "Australia"},
    {"savol": "Charles: ____", "togri": "England"},
    {"savol": "Bud: ____", "togri": "the US"},
    {"savol": "1. Where are you from? — I'm from China.", "togri": "h"},
    {"savol": "2. What's her name? — Her name's Sophie.", "togri": "g"},
    {"savol": "3. What's his name? — His name's Edvin.", "togri": "a"},
    {"savol": "4. Where's he from? — He's from France.", "togri": "f"},
    {"savol": "5. What's this in English? — It's a laptop.", "togri": "b"},
    {"savol": "6. How are you? — Fine, thanks. And you?", "togri": "c"},
    {"savol": "7. Where's Liverpool? — It's in England.", "togri": "d"},
    {"savol": "8. What's your name? — My name's Rachna.", "togri": "e"},
    {"savol": "1. My name Goran. / My name's Goran.", "togri": "My name's Goran."},
    {"savol": "2. What's he's name? / What's his name?", "togri": "What's his name?"},
    {"savol": "3. 'What's her name?' 'Rosa.' / 'What's his name?' 'Rosa.'", "togri": "'What's her name?' 'Rosa.'"},
    {"savol": "4. He's from Japan. / His from Japan.", "togri": "He's from Japan."},
    {"savol": "5. Where she from? / Where's she from?", "togri": "Where's she from?"},
    {"savol": "6. What's her name? / What's she name?", "togri": "What's her name?"},
]
SAHIFA5_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Questions and answers"},
    {"tur": "korsatma", "raqam": "4", "audio_raqam": "2.7", "matn": "Listen and complete the conversation. Practise it."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "Blanca: Hello, I'm Blanca. What's "}, {"bosh_joy": True, "savol_idx": 0}, {"matn": " name?"}]},
        {"bolaklar": [{"matn": "Rafael: "}, {"bosh_joy": True, "savol_idx": 1}, {"matn": " name's Rafael."}]},
        {"bolaklar": [{"matn": "Blanca: Hello, Rafael. Where are you "}, {"bosh_joy": True, "savol_idx": 2}, {"matn": "?"}]},
        {"bolaklar": [{"matn": "Rafael: "}, {"bosh_joy": True, "savol_idx": 3}, {"matn": " from Spain. Where are you from?"}]},
        {"bolaklar": [{"matn": "Blanca: Oh, "}, {"bosh_joy": True, "savol_idx": 4}, {"matn": " Barcelona."}]},
        {"bolaklar": [{"matn": "Rafael: Really? I'm from Barcelona, too!"}]},
        {"bolaklar": [{"matn": "Blanca: Oh, nice to meet you, Rafael."}]},
    ]},
    {"tur": "korsatma", "raqam": "5", "audio_raqam": "2.8", "matn": "Listen and write the countries."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "Mateo: Argentina.  Akemi: "}, {"bosh_joy": True, "savol_idx": 5}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "Loretta and Jason: "}, {"bosh_joy": True, "savol_idx": 6}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "Charles: "}, {"bosh_joy": True, "savol_idx": 7}]},
        {"bolaklar": [{"matn": "Bud: "}, {"bosh_joy": True, "savol_idx": 8}]},
    ]},
    {"tur": "korsatma", "raqam": "6", "audio_raqam": "2.9", "matn": "Match the questions and answers."},
    {"tur": "soz_banki", "qatorlar": [
        "a His name's Edvin.", "b It's a laptop.", "c Fine, thanks. And you?", "d It's in England.",
        "e My name's Rachna.", "f He's from France.", "g Her name's Sophie.", "h I'm from China.",
    ]},
    {"tur": "mashq", "bolaklar": [{"matn": "1. Where are you from? "}, {"bosh_joy": True, "savol_idx": 9}]},
    {"tur": "mashq", "bolaklar": [{"matn": "2. What's her name? "}, {"bosh_joy": True, "savol_idx": 10}]},
    {"tur": "mashq", "bolaklar": [{"matn": "3. What's his name? "}, {"bosh_joy": True, "savol_idx": 11}]},
    {"tur": "mashq", "bolaklar": [{"matn": "4. Where's he from? "}, {"bosh_joy": True, "savol_idx": 12}]},
    {"tur": "mashq", "bolaklar": [{"matn": "5. What's this in English? "}, {"bosh_joy": True, "savol_idx": 13}]},
    {"tur": "mashq", "bolaklar": [{"matn": "6. How are you? "}, {"bosh_joy": True, "savol_idx": 14}]},
    {"tur": "mashq", "bolaklar": [{"matn": "7. Where's Liverpool? "}, {"bosh_joy": True, "savol_idx": 15}]},
    {"tur": "mashq", "bolaklar": [{"matn": "8. What's your name? "}, {"bosh_joy": True, "savol_idx": 16}]},
    {"tur": "bolim_sarlavha", "matn": "Check it"},
    {"tur": "korsatma", "raqam": "7", "matn": "Tick (✓) the correct sentence. Type the correct one."},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 17}]},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 18}]},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 19}]},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 20}]},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 21}]},
    {"tur": "mashq", "bolaklar": [{"bosh_joy": True, "savol_idx": 22}]},
]

# ---------------------------------------------------------------------
# SAHIFA 6 (Student's Book p20) — Reading and vocabulary: A holiday in New York.
# GRADED savol_idx 0-18 (7 comprehension + 6 questions + 6 dialogue blanks).
# ---------------------------------------------------------------------
SAHIFA6_RASMLAR = ["nyc_couple.png", "freedom_tower.png"]
SAHIFA6_MATN = (
    "This is a photo of Claude and Holly Duval from Montreal in Canada. "
    "They are on holiday in New York City. Holly is from Canada and Claude "
    "is from France. They are married. Holly is an architect. Her office "
    "is in the centre of Montreal. Claude is a doctor. His hospital is in "
    "the centre of Montreal, too."
)
SAHIFA6_SAVOLLAR = [
    {"savol": "She's an ____.", "togri": "architect"},
    {"savol": "Her ____ is in the centre of Montreal.", "togri": "office"},
    {"savol": "Claude is from ____.", "togri": "France"},
    {"savol": "He's a ____.", "togri": "doctor"},
    {"savol": "His hospital is in the ____ of Montreal, too.", "togri": "centre"},
    {"savol": "They are on ____ in New York.", "togri": "holiday"},
    {"savol": "They ____ married.", "togri": "are"},
    {"savol": "What's his name?", "togri": "What's his name?"},
    {"savol": "What's her name?", "togri": "What's her name?"},
    {"savol": "Where's he from?", "togri": "Where's he from?"},
    {"savol": "Where's she from?", "togri": "Where's she from?"},
    {"savol": "Where's her office?", "togri": "Where's her office?"},
    {"savol": "Where's his hospital?", "togri": "Where's his hospital?"},
    {"savol": "C: Oh no! Look at the weather! H: Ugh! It's ____!", "togri": "awful"},
    {"savol": "C: Mmm. Look at my ____! It looks great!", "togri": "hamburger"},
    {"savol": "H: My pizza is ____, too!", "togri": "really good"},
    {"savol": "H: Yes, you're right. It's ____.", "togri": "amazing"},
    {"savol": "H: Wow! ____ at the view!", "togri": "Look"},
    {"savol": "C: It's ____.", "togri": "beautiful"},
]
SAHIFA6_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Reading and vocabulary — A holiday in New York"},
    {"tur": "korsatma", "raqam": "1", "audio_raqam": "2.10", "matn": "Read and listen."},
    {"tur": "rasm", "rasm_idx": 0},
    {"tur": "matn", "matn": SAHIFA6_MATN},
    {"tur": "korsatma", "raqam": "2", "matn": "Complete the sentences."},
    {"tur": "matn", "matn": "1 (namuna): Holly is from Montreal in Canada."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "2. "}, {"bosh_joy": True, "savol_idx": 0}]},
        {"bolaklar": [{"matn": "3. "}, {"bosh_joy": True, "savol_idx": 1}]},
        {"bolaklar": [{"matn": "4. "}, {"bosh_joy": True, "savol_idx": 2}]},
        {"bolaklar": [{"matn": "5. "}, {"bosh_joy": True, "savol_idx": 3}]},
        {"bolaklar": [{"matn": "6. "}, {"bosh_joy": True, "savol_idx": 4}]},
        {"bolaklar": [{"matn": "7. "}, {"bosh_joy": True, "savol_idx": 5}]},
        {"bolaklar": [{"matn": "8. "}, {"bosh_joy": True, "savol_idx": 6}]},
    ]},
    {"tur": "korsatma", "raqam": "3", "matn": "Complete the questions about Claude and Holly. Ask and answer with a partner."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 7}]},
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 8}]},
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 9}]},
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 10}]},
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 11}]},
        {"bolaklar": [{"bosh_joy": True, "savol_idx": 12}]},
    ]},
    {"tur": "korsatma", "raqam": "4", "audio_raqam": "2.11", "matn": "Listen to Claude and Holly. Complete the conversations."},
    {"tur": "rasm", "rasm_idx": 1},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "1. C: Oh no! Look at the weather!  H: Ugh! It's "}, {"bosh_joy": True, "savol_idx": 13}, {"matn": "."}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "2. H: Mmm. Look at my "}, {"bosh_joy": True, "savol_idx": 14}, {"matn": "! It looks great!"}]},
        {"bolaklar": [{"matn": "C: My pizza is "}, {"bosh_joy": True, "savol_idx": 15}, {"matn": ", too!"}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "3. C: Wow! This building is fantastic!  H: Yes, you're right. It's "}, {"bosh_joy": True, "savol_idx": 16}, {"matn": "."}]},
    ]},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "4. H: Wow! "}, {"bosh_joy": True, "savol_idx": 17}, {"matn": " at the view!"}]},
        {"bolaklar": [{"matn": "C: It's "}, {"bosh_joy": True, "savol_idx": 18}, {"matn": "."}]},
    ]},
]

# ---------------------------------------------------------------------
# SAHIFA 7 (Student's Book p21) — Everyday English: Numbers 11-30.
# GRADED savol_idx 0-19 (10 matching + 5 listen-tick + 5 ages).
# ---------------------------------------------------------------------
SAHIFA7_RASMLAR = ["age1.png", "age2.png", "age3.png", "age4.png", "age5.png"]
SAHIFA7_SAVOLLAR = [
    {"savol": "21", "togri": "twenty-one"},
    {"savol": "22", "togri": "twenty-two"},
    {"savol": "23", "togri": "twenty-three"},
    {"savol": "24", "togri": "twenty-four"},
    {"savol": "25", "togri": "twenty-five"},
    {"savol": "26", "togri": "twenty-six"},
    {"savol": "27", "togri": "twenty-seven"},
    {"savol": "28", "togri": "twenty-eight"},
    {"savol": "29", "togri": "twenty-nine"},
    {"savol": "30", "togri": "thirty"},
    {"savol": "1-band", "togri": "12"},
    {"savol": "2-band", "togri": "16"},
    {"savol": "3-band", "togri": "9"},
    {"savol": "4-band", "togri": "17"},
    {"savol": "5-band", "togri": "23"},
    {"savol": "1-rasm", "togri": "28"},
    {"savol": "2-rasm (Molly)", "togri": "9"},
    {"savol": "3-rasm (Nathan)", "togri": "15"},
    {"savol": "4-rasm (Hua)", "togri": "2"},
    {"savol": "5-rasm (Clare)", "togri": "29"},
]
SAHIFA7_BLOKLAR = [
    {"tur": "bolim_sarlavha", "matn": "Everyday English — Numbers 11-30"},
    {"tur": "korsatma", "raqam": "1", "matn": "Say the numbers 1-10 round the class."},
    {"tur": "korsatma", "raqam": "2", "audio_raqam": "2.12", "matn": "Listen, read and repeat."},
    {"tur": "matn", "matn": "11 eleven, 12 twelve, 13 thirteen, 14 fourteen, 15 fifteen, 16 sixteen, 17 seventeen, 18 eighteen, 19 nineteen, 20 twenty"},
    {"tur": "korsatma", "raqam": "3", "matn": "Say the numbers 1-20 round the class."},
    {"tur": "korsatma", "raqam": "4", "matn": "Write the numbers your teacher says."},
    {"tur": "korsatma", "raqam": "5", "audio_raqam": "2.13", "matn": "Match the numbers. Write the word for each number."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "21 "}, {"bosh_joy": True, "savol_idx": 0}]},
        {"bolaklar": [{"matn": "22 "}, {"bosh_joy": True, "savol_idx": 1}]},
        {"bolaklar": [{"matn": "23 "}, {"bosh_joy": True, "savol_idx": 2}]},
        {"bolaklar": [{"matn": "24 "}, {"bosh_joy": True, "savol_idx": 3}]},
        {"bolaklar": [{"matn": "25 "}, {"bosh_joy": True, "savol_idx": 4}]},
        {"bolaklar": [{"matn": "26 "}, {"bosh_joy": True, "savol_idx": 5}]},
        {"bolaklar": [{"matn": "27 "}, {"bosh_joy": True, "savol_idx": 6}]},
        {"bolaklar": [{"matn": "28 "}, {"bosh_joy": True, "savol_idx": 7}]},
        {"bolaklar": [{"matn": "29 "}, {"bosh_joy": True, "savol_idx": 8}]},
        {"bolaklar": [{"matn": "30 "}, {"bosh_joy": True, "savol_idx": 9}]},
    ]},
    {"tur": "korsatma", "raqam": "6", "audio_raqam": "2.14", "matn": "Listen and write the number you hear."},
    {"tur": "mashq", "qatorlar": [
        {"bolaklar": [{"matn": "1. "}, {"bosh_joy": True, "savol_idx": 10}]},
        {"bolaklar": [{"matn": "2. "}, {"bosh_joy": True, "savol_idx": 11}]},
        {"bolaklar": [{"matn": "3. "}, {"bosh_joy": True, "savol_idx": 12}]},
        {"bolaklar": [{"matn": "4. "}, {"bosh_joy": True, "savol_idx": 13}]},
        {"bolaklar": [{"matn": "5. "}, {"bosh_joy": True, "savol_idx": 14}]},
    ]},
    {"tur": "korsatma", "raqam": "7", "audio_raqam": "2.15", "matn": "Look at the photos. How old is he/she? Listen and find out."},
    {"tur": "rasm_javobli_grid", "qator_boyicha": True, "itemlar": [
        {"rasm_idx": 0, "raqam": "1", "savol_idx": 15},
        {"rasm_idx": 1, "raqam": "2 (Molly)", "savol_idx": 16},
        {"rasm_idx": 2, "raqam": "3 (Nathan)", "savol_idx": 17},
        {"rasm_idx": 3, "raqam": "4 (Hua)", "savol_idx": 18},
        {"rasm_idx": 4, "raqam": "5 (Clare)", "savol_idx": 19},
    ]},
]

SAHIFALAR = [
    (2, SAHIFA2_RASMLAR, SAHIFA2_BLOKLAR, SAHIFA2_SAVOLLAR),
    (3, SAHIFA3_RASMLAR, SAHIFA3_BLOKLAR, []),
    (4, SAHIFA4_RASMLAR, SAHIFA4_BLOKLAR, SAHIFA4_SAVOLLAR),
    (5, [], SAHIFA5_BLOKLAR, SAHIFA5_SAVOLLAR),
    (6, SAHIFA6_RASMLAR, SAHIFA6_BLOKLAR, SAHIFA6_SAVOLLAR),
    (7, SAHIFA7_RASMLAR, SAHIFA7_BLOKLAR, SAHIFA7_SAVOLLAR),
]

VOCABULARY_MATN = (
    "GRAMMAR REFERENCE — Unit 2: Your world\n\n"
    "2.1 Egalik olmoshlari (Possessive adjectives)\n"
    "My name's Serena. What's your name?\n"
    "His name's Antonio. What's her name?\n"
    "his = egalik olmoshi (his name, his bike, his watch)\n"
    "he's = he is (He's Bruno. He's from Brazil. He's fine.)\n\n"
    "2.2 Savol so'zlari bilan savollar\n"
    "Where are you/is she/is he from?\n"
    "What's this (is this) in English?\n"
    "How old are you/is he/is she? — I'm 27. He's 18. She's 12.\n\n"
    "2.3 am/are/is\n"
    "I'm (I am) / You're (You are) / He's, She's (He is, She is) — from England, a student.\n"
    "It's (It is) — a laptop.\n"
    "They're (They are) — in New York, married."
)

WORDLIST = [
    {"en": "amazing", "uz": "ajoyib", "turkum": "adj"},
    {"en": "architect", "uz": "arxitektor", "turkum": "n"},
    {"en": "awful", "uz": "juda yomon", "turkum": "adj"},
    {"en": "beautiful", "uz": "chiroyli", "turkum": "adj"},
    {"en": "building", "uz": "bino", "turkum": "n"},
    {"en": "centre", "uz": "markaz", "turkum": "n"},
    {"en": "city", "uz": "shahar", "turkum": "n"},
    {"en": "country", "uz": "davlat", "turkum": "n"},
    {"en": "doctor", "uz": "shifokor", "turkum": "n"},
    {"en": "fantastic", "uz": "ajoyib", "turkum": "adj"},
    {"en": "favourite", "uz": "sevimli", "turkum": "adj"},
    {"en": "great", "uz": "zo'r", "turkum": "adj"},
    {"en": "hamburger", "uz": "gamburger", "turkum": "n"},
    {"en": "hospital", "uz": "kasalxona", "turkum": "n"},
    {"en": "map", "uz": "xarita", "turkum": "n"},
    {"en": "married", "uz": "turmush qurgan", "turkum": "adj"},
    {"en": "office", "uz": "ofis", "turkum": "n"},
    {"en": "on holiday", "uz": "dam olishda", "turkum": "phr"},
    {"en": "really good", "uz": "juda yaxshi", "turkum": "adj"},
    {"en": "too", "uz": "ham", "turkum": "adv"},
    {"en": "view", "uz": "manzara", "turkum": "n"},
    {"en": "weather", "uz": "ob-havo", "turkum": "n"},
    {"en": "Where?", "uz": "Qayerda?", "turkum": "adv"},
    {"en": "world", "uz": "dunyo", "turkum": "n"},
    {"en": "You're right.", "uz": "Siz haqsiz."},
    {"en": "Argentina", "uz": "Argentina"},
    {"en": "Australia", "uz": "Avstraliya"},
    {"en": "Brazil", "uz": "Braziliya"},
    {"en": "Canada", "uz": "Kanada"},
    {"en": "China", "uz": "Xitoy"},
    {"en": "Egypt", "uz": "Misr"},
    {"en": "England", "uz": "Angliya"},
    {"en": "France", "uz": "Fransiya"},
    {"en": "Italy", "uz": "Italiya"},
    {"en": "Japan", "uz": "Yaponiya"},
    {"en": "Russia", "uz": "Rossiya"},
    {"en": "Scotland", "uz": "Shotlandiya"},
    {"en": "Spain", "uz": "Ispaniya"},
    {"en": "the UK", "uz": "Buyuk Britaniya"},
    {"en": "the US", "uz": "AQSh"},
    {"en": "Turkey", "uz": "Turkiya"},
    {"en": "eleven", "uz": "o'n bir"},
    {"en": "twelve", "uz": "o'n ikki"},
    {"en": "thirteen", "uz": "o'n uch"},
    {"en": "fourteen", "uz": "o'n to'rt"},
    {"en": "fifteen", "uz": "o'n besh"},
    {"en": "sixteen", "uz": "o'n olti"},
    {"en": "seventeen", "uz": "o'n yetti"},
    {"en": "eighteen", "uz": "o'n sakkiz"},
    {"en": "nineteen", "uz": "o'n to'qqiz"},
    {"en": "twenty", "uz": "yigirma"},
    {"en": "twenty-one", "uz": "yigirma bir"},
    {"en": "thirty", "uz": "o'ttiz"},
]


class Command(BaseCommand):
    help = "Headway Beginner Unit 2 (\"Your world\") kontentini yaratadi (idempotent, blok format)"

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

        unit = KursTugun.objects.filter(kalit="beginner_unit_2", parent=beginner).first()
        if not unit:
            # 2026-08-17: tartib qat'iy 2 — sababi headway_beginner_unit1.py
            # dagi izohga qarang (mavjud Unitlar soniga qarab hisoblash
            # qayta yaratishda tartibni buzib qo'ygan edi).
            unit = KursTugun.objects.create(
                kalit="beginner_unit_2", nomi="Unit 2 — Your world", parent=beginner,
                markaz=markaz, tartib=2, unit_darsi=True,
            )
            unit_ichki_tuzilmasini_yarat(unit)
            self.stdout.write("Unit 2 tuguni yaratildi")

        students_book = KursTugun.objects.filter(kalit="students_book", parent=unit).first()
        if not students_book:
            self.stdout.write(self.style.ERROR("Unit 2 ostida \"Student's Book\" tuguni topilmadi"))
            return
        mashq_tugun = KursTugun.objects.filter(kalit="mashqlar", parent=students_book).first()
        vocab_tugun = KursTugun.objects.filter(kalit="vocabulary", parent=students_book).first()
        if not mashq_tugun or not vocab_tugun:
            self.stdout.write(self.style.ERROR("Mashqlar/Vocabulary tugunlari topilmadi"))
            return

        if mashq_tugun.mashqlar.exists() or vocab_tugun.sozlar.exists() or vocab_tugun.matn:
            self.stdout.write(self.style.WARNING("Unit 2 allaqachon to'ldirilgan — o'tkazib yuborildi"))
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
            f"Unit 2 tayyor: {len(SAHIFALAR)} sahifa, {len(WORDLIST)} so'z"
        ))
