"""Intermediate: kitobdagi mashq SHAKLI noto'g'ri qayta yaratilgan 4 ta sahifa.

2026-09-14, Umida tekshiruvi (Intermediate.docx — har muammo skrinshot bilan:
tizimdagi ko'rinish va kitobdagi asl ko'rinish yonma-yon).

Mashqlar ID bo'yicha emas, ko'rsatma MATNI bo'yicha topiladi — prodda id'lar
boshqacha bo'lishi mumkin (kontent eksport/import orqali ko'chiriladi).

Har bir tuzatish IDEMPOTENT: allaqachon qo'llangan bo'lsa hech narsa
qilmaydi, shuning uchun migratsiyani qayta yugurtirish xavfsiz.

Naqsh `courses/pre_intermediate_tuzatish.py` dan olingan — sabab o'sha
fayldagi izohda.

DIQQAT: prodda mashq ID'lari HAM, `savollar` indekslari ham boshqacha
bo'lishi mumkin (kontent u yerga alohida yuklangan). Shuning uchun hech
qayerda `savol_idx` raqami qattiq yozilmaydi — katakchalar JAVOB MATNI
bo'yicha topiladi. Kutilgan javoblar to'plami mos kelmasa, tuzatish
hech narsa qilmay chekinadi (kontentni buzgandan ko'ra tegmagan afzal).
"""

import re

# ─────────────────────────────────────────────────────────────────────────────
# Yordamchilar
# ─────────────────────────────────────────────────────────────────────────────


def _kalit(matn):
    """Solishtirish uchun kalit — tire (— va –), tirnoq va bo'shliq
    farqlariga sezgir emas ("Thanks — but …" va "Thanks – but …" bir xil
    hisoblanadi, chunki AI va kitob turli tire ishlatgan)."""
    return re.sub(r"[^a-z0-9]", "", str(matn).lower())


def _katakcha_indekslari(jadval, savollar):
    """Jadvaldagi bo'sh joylar: {javob kaliti: savol_idx}."""
    natija = {}
    for qator in jadval.get("qatorlar") or []:
        for katak in qator[1:]:
            if not isinstance(katak, dict):
                continue
            for bolak in katak.get("bolaklar") or []:
                idx = bolak.get("savol_idx")
                if idx is not None and idx < len(savollar):
                    natija[_kalit(savollar[idx].get("togri", ""))] = idx
    return natija


def _matnlar(obj):
    """Blok ichidagi barcha `matn` qiymatlari (chuqurlikda)."""
    natija = []
    if isinstance(obj, dict):
        if isinstance(obj.get("matn"), str):
            natija.append(obj["matn"])
        for qiymat in obj.values():
            natija.extend(_matnlar(qiymat))
    elif isinstance(obj, list):
        for qiymat in obj:
            natija.extend(_matnlar(qiymat))
    return natija


def _blok_indeksi(bloklar, boshlanish):
    """Matni `boshlanish` bilan boshlanadigan BIRINCHI blok indeksi."""
    for i, blok in enumerate(bloklar):
        for matn in _matnlar(blok):
            if matn.strip().startswith(boshlanish):
                return i
    return None


def _mashq_top(mashqlar, boshlanish):
    """Ko'rsatma matni bo'yicha mashqni topadi (Intermediate ichida)."""
    for mashq in mashqlar:
        if _blok_indeksi(mashq.bloklar or [], boshlanish) is not None:
            return mashq
    return None


def _saqla(mashq):
    mashq.save(update_fields=["bloklar", "savollar"])


def _bosh_joy(savol_idx):
    return {"bolaklar": [{"bosh_joy": True, "savol_idx": savol_idx}]}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unit 8 SB — "Arranging to meet": kundalik jadvali chala va katakchalar
#    NOTO'G'RI kataklarda turgan edi
# ─────────────────────────────────────────────────────────────────────────────
U8SB_KORSATMA = "Listen to two friends, Jeff and Kevin, arranging to meet over the weekend"

# Teacher's Guide (5th ed., 8.12 kaliti, s.113) bo'yicha JEFF kundaligi.
# "Meet Kevin 10.30" va "Train 11.55" — BITTA katakda (24 Sun, ertalab).
U8SB_JEFF_ERTALAB = ["Meet Kevin 10.30", "Train 11.55"]
U8SB_JEFF_TUSHDAN_KEYIN = ["Conference", "Meet contact"]  # 22 Fri, 23 Sat


def _u8sb_kundaliklar(mashq):
    """Umida: "Mashq jadvali to'liq berilmagan".

    Ikki xato bor edi:

    1. Jadval kitobdagi 3x3 to'r ko'rinishida emas edi — bo'sh kataklar
       chegarasiz `<td>` bo'lgani uchun umuman ko'rinmasdi (ayniqsa JEFF'ning
       butunlay bo'sh "Evening" qatori). Endi ikkala jadval ham `katakli`
       — kitobdagidek to'r chiziqlari bilan chiziladi.

    2. JEFF jadvalida javob katakchalari NOTO'G'RI kataklarda turardi.
       Teacher's Guide (5th ed., 8.12 kaliti, s.113) bo'yicha:
         Morning   — faqat 24 Sun: "Meet Kevin 10.30" va "Train 11.55"
         Afternoon — 22 Fri: "Conference", 23 Sat: "Meet contact"
       Bizda esa "Meet Kevin 10.30" 23 Sat ertalabida, "Meet contact" esa
       24 Sun tushdan keyinida turardi. KEVIN jadvali to'g'ri edi.

    Kalit bo'yicha BO'SH qoladigan kataklarga katakcha QO'YILMAYDI: bo'sh
    javob har doim xato deb hisoblanadi (`exercises.models.javoblarni_tekshir`),
    ya'ni talaba hech qachon to'liq ball ololmasdi.

    "Meet Kevin 10.30" va "Train 11.55" — kitobda BITTA katakda, ikki qator.
    Ikkala savol matni ataylab BIR XIL qilinadi: shunda ular `javoblarni_tekshir`
    uchun bitta tartibsiz guruh bo'ladi va talaba qaysi qatorga qaysi birini
    yozganidan qat'i nazar ball oladi."""
    bloklar = mashq.bloklar
    savollar = mashq.savollar
    jeff = kevin = None
    for blok in bloklar:
        if blok.get("tur") != "jadval":
            continue
        bosh = (blok.get("sarlavhalar") or [""])[0]
        if bosh == "JEFF":
            jeff = blok
        elif bosh == "KEVIN":
            kevin = blok
    if jeff is None or kevin is None or jeff.get("katakli"):
        return False

    # Katakchalarni javob MATNI bo'yicha topamiz (izohga qara). Kutilgan
    # 4 ta javob to'liq chiqmasa — jadval boshqacha qurilgan, tegmaymiz.
    idx = _katakcha_indekslari(jeff, savollar)
    kerak = U8SB_JEFF_ERTALAB + U8SB_JEFF_TUSHDAN_KEYIN
    if set(idx) != {_kalit(j) for j in kerak}:
        return False
    ertalab, tushdan_keyin = (
        [idx[_kalit(j)] for j in U8SB_JEFF_ERTALAB],
        [idx[_kalit(j)] for j in U8SB_JEFF_TUSHDAN_KEYIN],
    )

    jeff["katakli"] = True
    kevin["katakli"] = True
    jeff["qatorlar"] = [
        ["Morning", "", "", {"bolaklar": [
            {"bosh_joy": True, "savol_idx": ertalab[0]},
            {"bosh_joy": True, "savol_idx": ertalab[1]},
        ]}],
        ["Afternoon", _bosh_joy(tushdan_keyin[0]), _bosh_joy(tushdan_keyin[1]), ""],
        ["Evening", "", "", ""],
    ]
    for i in ertalab:
        savollar[i]["savol"] = "JEFF — 24 Sun morning"
    savollar[tushdan_keyin[0]]["savol"] = "JEFF — 22 Fri afternoon"
    savollar[tushdan_keyin[1]]["savol"] = "JEFF — 23 Sat afternoon"
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 2. Unit 11 — "Noun phrases": a-o ro'yxati bitta uzun qatorga yopishgan
# ─────────────────────────────────────────────────────────────────────────────
U11_KORSATMA = "Thirsty Meeples is an unusual café"

# Kitobdagi quti (5th ed. s.88) — ikki ustun, a-o.
U11_IBORALAR = [
    "a  her Belgian husband",
    "b  all of the players win",
    "c  all our smartphones",
    "d  with each other",
    "e  a bright Thursday morning",
    "f  the most successful",
    "g  everyone in the café",
    "h  the café's owners",
    "i  in the desert",
    "j  every culture in the world",
    "k  a burning building",
    "l  describes itself",
    "m  all over the UK",
    "n  tabletop games",
    "o  the original social network",
]


def _u11_iboralar_banki(mashq):
    """Umida: "mashqda foydalanilishi kerak bo'lgan so'zlar tushunarsiz
    berilgan".

    Kitobda a-o iboralari alohida qutida, ikki ustunda turadi. Bizda
    ularning hammasi BITTA `matn` blokiga ("a her Belgian husband  b all
    of the players win  c all our smartphones …") yopishtirilgan edi —
    qaysi ibora qayerda tugashini ajratib bo'lmasdi.

    Endi `soz_banki` bloki: har ibora alohida band sifatida, kitobdagi
    qutiga o'xshash fonda chiqadi."""
    bloklar = mashq.bloklar
    i = _blok_indeksi(bloklar, "a her Belgian husband")
    if i is None:
        return False
    bloklar[i] = {"tur": "soz_banki", "sozlar": list(U11_IBORALAR)}
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unit 12 SB — A/B/C jadvali ko'rsatma qavsiga tiqib yuborilgan
# ─────────────────────────────────────────────────────────────────────────────
U12SB_ABC_KORSATMA = "Work with a partner. Match the lines in A, B, and C"

# Kitobdagi uch ustunli jadval (5th ed. s.114). Ustunlar uzunligi har xil
# (8/9/10), qolgan kataklar bo'sh qoladi — kitobda ham shunday.
U12SB_A = [
    "What (x3)", "Who", "Which", "How much", "How many", "How long", "Why (x2)",
]
U12SB_B = [
    "time", "football team", "is (x2)", "kind of", "time do you spend",
    "times", "did you leave", "have you been", "don't you",
]
U12SB_C = [
    "do you normally get up?", "do you support?", "music do you like?",
    "in front of a screen each day?", "a day do you check your phone?",
    "your last job?", "your dream job?", "learning English?",
    "your favourite sportsperson?", "reply to my texts?",
]


def _u12sb_abc_jadvali(mashq):
    """Umida: "mashq tushunarsiz berilgan".

    Kitobda A/B/C — uchta ustunli jadval, talaba ulardan gap yig'adi.
    Bizda butun jadval ko'rsatmaning QAVSIGA tiqib yuborilgan edi:
    "… (What/Who/Which/… + time/football team/is/… + do you normally get
    up? / do you support? / …)" — o'qib bo'lmaydigan uzun qator.

    Endi ko'rsatma kitobdagidek qisqa, jadval esa alohida blok. Shu
    mashqning 1-bandida allaqachon to'g'ri `jadval` bor edi — demak
    generator buni qila olardi, shu joyda qilmagan."""
    bloklar = mashq.bloklar
    i = _blok_indeksi(bloklar, U12SB_ABC_KORSATMA)
    if i is None or bloklar[i].get("tur") != "korsatma":
        return False
    # Idempotentlik: jadval allaqachon qo'yilgan bo'lsa ikkinchisini
    # qo'shmaymiz (ko'rsatma matni tuzatilgandan keyin ham U12SB_ABC_KORSATMA
    # bilan boshlanadi, ya'ni yuqoridagi qidiruv uni yana topadi).
    keyingi = bloklar[i + 1] if i + 1 < len(bloklar) else {}
    if keyingi.get("tur") == "jadval" and keyingi.get("sarlavhalar") == ["A", "B", "C"]:
        return False
    bloklar[i]["matn"] = (
        "Work with a partner. Match the lines in A, B, and C to make some "
        "everyday questions."
    )
    qatorlar = [
        [
            U12SB_A[k] if k < len(U12SB_A) else "",
            U12SB_B[k] if k < len(U12SB_B) else "",
            U12SB_C[k],
        ]
        for k in range(len(U12SB_C))
    ]
    bloklar.insert(i + 1, {
        "tur": "jadval", "katakli": True,
        "sarlavhalar": ["A", "B", "C"], "qatorlar": qatorlar,
    })
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unit 12 SB — "Talking in clichés": B ustuni (javob variantlari) yo'q edi
# ─────────────────────────────────────────────────────────────────────────────
U12SB_KLISHE_KORSATMA = "Match a line in A with a cliché in B."

# Kitobdagi B ustuni TARTIBI (5th ed. s.119) — faqat TARTIB uchun.
# `ong` ga bu matnlar EMAS, `savollar` dagi javoblarning O'ZI yoziladi:
# chiziq chizilishi uchun `ong` dagi matn kalit bilan AYNAN bir xil
# bo'lishi shart (`Moslashtirish`: `ong.indexOf(javob)`).
U12SB_B_USTUNI = [
    "I know. It's all talk and no action.",
    "Come on! It's not the end of the world.",
    "Yes, it's like banging your head against a brick wall.",
    "Great minds think alike.",
    "Yes, she certainly has both feet on the ground.",
    "Well, it takes all sorts to make a world.",
    "Rather you than me.",
    "It's all right for some.",
    "What! And I just bust a gut to get it done.",
    "Thanks - but it's all in a day's work.",
    "Never mind. It could have been worse.",
    "You can say that again. I fell asleep.",
    "Only time will tell.",
    "Ah, he's a man after my own heart.",
    "That's awful, but you live and learn.",
    "Oh, well. Live and let live. That's what I say.",
]


def _u12sb_klishelar(mashq):
    """Umida: "mashq to'liq berilmagan".

    Kitobda ikkita ustun bor: A — gaplar, B — 16 ta klishe; talaba ularni
    chiziq bilan bog'laydi. Bizda B ustuni BUTUNLAY bo'sh katakchalarga
    aylangan edi — variantlar talabaga umuman ko'rsatilmagan. Ya'ni mashq
    bajarib bo'lmaydigan holatda edi: "Yes, it's like banging your head
    against a brick wall." kabi javobni yoddan yozib bo'lmaydi.

    Endi `moslashtir` bloki — kitobdagidek: chapdan gapni, o'ngdan
    klisheni bosasiz, orasiga chiziq tortiladi."""
    bloklar = mashq.bloklar
    savollar = mashq.savollar
    # DIQQAT: A ustuni kataklari oddiy SATR (dict emas), shuning uchun
    # `_matnlar` ularni ko'rmaydi — qatorlarning o'zidan qidiramiz.
    jadval_i = None
    for i, blok in enumerate(bloklar):
        if blok.get("tur") != "jadval" or blok.get("sarlavhalar") != ["A", "B"]:
            continue
        birinchi = (blok.get("qatorlar") or [[""]])[0][0]
        if isinstance(birinchi, str) and "lost without it" in birinchi:
            jadval_i = i
            break
    if jadval_i is None:
        return False

    chap = []
    for qator in bloklar[jadval_i]["qatorlar"]:
        katak = qator[1]
        if not (isinstance(katak, dict) and katak.get("bolaklar")):
            return False
        chap.append({
            "matn": qator[0].strip(),
            "savol_idx": katak["bolaklar"][0]["savol_idx"],
        })

    # O'ng ustun — kalitdagi javoblarning O'ZI, kitobdagi tartibda.
    # Kutilgan 16 ta javob to'liq chiqmasa — tegmaymiz (izohga qara).
    tartib = {_kalit(t): k for k, t in enumerate(U12SB_B_USTUNI)}
    javoblar = [savollar[band["savol_idx"]].get("togri", "") for band in chap]
    if {_kalit(j) for j in javoblar} != set(tartib):
        return False

    bloklar[jadval_i] = {
        "tur": "moslashtir",
        "chap": chap,
        "ong": sorted(javoblar, key=lambda j: tartib[_kalit(j)]),
    }
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
TUZATISHLAR = [
    (U8SB_KORSATMA, _u8sb_kundaliklar, "Unit 8 SB - Jeff/Kevin kundaliklari"),
    (U11_KORSATMA, _u11_iboralar_banki, "Unit 11 - noun phrases banki"),
    (U12SB_ABC_KORSATMA, _u12sb_abc_jadvali, "Unit 12 SB - A/B/C jadvali"),
    (U12SB_KLISHE_KORSATMA, _u12sb_klishelar, "Unit 12 SB - klishe moslashtirish"),
]


def intermediate_mashqlari(KursTugun, KursMashq):
    darajalar = list(
        KursTugun.objects.filter(kalit="intermediate").values_list("id", flat=True)
    )
    if not darajalar:
        return KursMashq.objects.none()
    tugunlar = set()
    qatlam = darajalar
    for _ in range(4):
        qatlam = list(KursTugun.objects.filter(parent_id__in=qatlam).values_list("id", flat=True))
        if not qatlam:
            break
        tugunlar.update(qatlam)
    return KursMashq.objects.filter(tugun_id__in=tugunlar)


def tuzat(KursTugun, KursMashq):
    """Barcha tuzatishlarni qo'llaydi. Qaytaradi: [(izoh, bajarildimi), ...]"""
    mashqlar = list(intermediate_mashqlari(KursTugun, KursMashq))
    hisobot = []
    for boshlanish, amal, izoh in TUZATISHLAR:
        mashq = _mashq_top(mashqlar, boshlanish)
        hisobot.append((izoh, bool(mashq) and amal(mashq)))
    return hisobot
