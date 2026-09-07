"""GRAMMAR SPOT: javoblarni talabadan yashirish (o'qituvchiga qoldirib).

2026-09-07, Shuxrat topshirig'i. Kitobdagi GRAMMAR SPOT qutisida FAQAT
savollar va namuna gaplar bo'ladi — javob YO'Q (SB p21, p31 bilan
solishtirib tekshirildi). Bizning kontentda esa javoblar o'sha qatorning
ichiga qavs/tire bilan yozib qo'yilgan edi:

    "1 Which two present tenses are used in the texts? Find examples of
     both. (Present Simple va Present Continuous)"

Endi javob qismi qatordan AJRATILIB, `oqituvchi_uchun` belgili alohida
qatorga chiqariladi — savol talabada qoladi, javob faqat o'qituvchida.

Kitobning O'ZI bosgan izohlarga TEGILMAYDI: masalan U3 dagi
"I had a bath last night. (= completed action)" kitobda ham shunday —
ular ro'yxatga kiritilmagan.

Har bir band: (grammar_spot birinchi qatori, [(qator_indeksi, ajratuvchi)])
`ajratuvchi` None bo'lsa — BUTUN qator javob; aks holda qator o'sha
matndan boshlab ikkiga bo'linadi.
"""

BANDLAR = [
    # Unit 1 SB — "Find examples of present, past, and future tenses"
    (
        "1  Find examples of present, past, and future tenses",
        [
            (1, None),
            (2, None),
            (3, None),
            (5, "(Present Simple"),
            (6, "(Present Continuous"),
        ],
    ),
    # Unit 2 SB — Present Simple / Present Continuous, have got
    (
        "1 Which two present tenses are used in the texts?",
        [
            (0, "(Present Simple va"),
            (2, "= all time"),
            (3, "= now"),
            (5, None),
        ],
    ),
    # Unit 3 SB — Past Simple / Past Continuous
    (
        "1 The Past Simple expresses a completed action",
        [(4, "→ did"), (5, "→ didn't")],
    ),
    # Unit 6 SB — Past Simple vs Present Perfect
    (
        "1 Find examples of the Past Simple and the Present Perfect in 2.",
        [
            (1, None),
            (4, "(Past Simple —"),
            (5, "(Present Perfect —"),
            (6, "(Chunki u vafot etgan"),
            (8, "— DAVOMIYLIK"),
            (9, "— BOSHLANISH NUQTASI"),
        ],
    ),
    # Unit 6 SB — Present Perfect (tajriba) / Past Simple
    (
        "1 What are the tenses in these sentences?",
        [
            (1, "(Present Perfect — hayotdagi"),
            (2, "(Present Perfect)"),
            (3, "(Past Simple — o'tmishdagi"),
        ],
    ),
    # Unit 5 SB — Verb patterns
    (
        "1  Find examples in exercises 1, 2 and 3 of:",
        [
            (1, "→  I try"),
            (2, "→  I can't"),
            (3, "→  We love"),
            (4, "→  I'm looking forward"),
            (6, "(now — I work there"),
            (7, "(hypothetical —"),
            (10, None),
            (11, None),
            (12, None),
            (13, None),
            (14, None),
            (15, None),
            (16, None),
        ],
    ),
    # Unit 8 SB — should / must
    (
        "1 Look at these sentences. Which sentence expresses stronger advice?",
        [(2, None), (5, None), (6, None)],
    ),
    # Unit 10 SB — Passive
    (
        "1 Many of the verb forms in the text are in the passive.",
        [(4, "→ be (to'g'ri shaklda)")],
    ),
    # Unit 11 SB — Present Perfect Simple / Continuous
    (
        "1  Read the sentences.",
        [(6, None), (7, None), (8, None), (9, None)],
    ),
]


def _qator_matni(qator):
    if isinstance(qator, str):
        return qator
    if isinstance(qator, dict):
        return qator.get("matn")
    return None


def _grammar_spotlar(mashq):
    for blok in mashq.bloklar or []:
        if isinstance(blok, dict) and blok.get("tur") == "grammar_spot" and blok.get("qatorlar"):
            yield blok


def _mos_blok(mashqlar, boshlanish):
    for mashq in mashqlar:
        for blok in _grammar_spotlar(mashq):
            birinchi = _qator_matni((blok["qatorlar"] or [None])[0])
            if birinchi and birinchi.strip().startswith(boshlanish):
                return mashq, blok
    return None, None


def _qolla(blok, bandlar):
    """Qatorlarni qayta quradi. Idempotent: allaqachon ajratilgan bo'lsa
    (javob qatori mavjud) hech narsa qilmaydi."""
    qatorlar = blok["qatorlar"]
    if any(isinstance(q, dict) and q.get("oqituvchi_uchun") for q in qatorlar):
        return False
    xarita = dict(bandlar)
    yangi = []
    ozgardi = False
    for i, qator in enumerate(qatorlar):
        if i not in xarita:
            yangi.append(qator)
            continue
        matn = _qator_matni(qator)
        ajratuvchi = xarita[i]
        if matn is None:
            yangi.append(qator)
            continue
        if ajratuvchi is None:
            yangi.append({"matn": matn, "oqituvchi_uchun": True})
            ozgardi = True
            continue
        joy = matn.find(ajratuvchi)
        if joy == -1:
            yangi.append(qator)
            continue
        bosh, javob = matn[:joy].rstrip(), matn[joy:].strip()
        if bosh:
            yangi.append(bosh)
        yangi.append({"matn": javob, "oqituvchi_uchun": True})
        ozgardi = True
    if ozgardi:
        blok["qatorlar"] = yangi
    return ozgardi


def tuzat(KursTugun, KursMashq):
    """Qaytaradi: [(grammar_spot boshlanishi, bajarildimi), ...]"""
    from courses.pre_intermediate_tuzatish import pre_intermediate_mashqlari

    mashqlar = list(pre_intermediate_mashqlari(KursTugun, KursMashq))
    hisobot = []
    for boshlanish, bandlar in BANDLAR:
        mashq, blok = _mos_blok(mashqlar, boshlanish)
        bajarildi = False
        if blok is not None and _qolla(blok, bandlar):
            mashq.save(update_fields=["bloklar"])
            bajarildi = True
        hisobot.append((boshlanish[:50], bajarildi))
    return hisobot
