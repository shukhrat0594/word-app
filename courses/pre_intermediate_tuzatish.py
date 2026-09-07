"""Pre-Intermediate: mashq turi noto'g'ri qayta yaratilgan 6 ta sahifani tuzatadi.

2026-09-07, Shuxrat tekshiruvi (Pre-inter.docx + talaba sifatida ko'rib chiqish).
Javob kaliti muammosi migratsiya 0019 da hal qilindi; bu yerda qolgan 6 ta
mashq — kitobdagi mashq TURI noto'g'ri qayta yaratilgan holatlar.

Mashqlar ID bo'yicha emas, ko'rsatma MATNI bo'yicha topiladi — prodda id'lar
boshqacha bo'lishi mumkin (kontent export/import orqali ko'chiriladi).

Har bir tuzatish IDEMPOTENT: allaqachon qo'llangan bo'lsa hech narsa
qilmaydi, shuning uchun migratsiyani qayta yugurtirish xavfsiz.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Yordamchilar
# ─────────────────────────────────────────────────────────────────────────────


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
    """Ko'rsatma matni bo'yicha mashqni topadi (Pre-Intermediate ichida)."""
    for mashq in mashqlar:
        if _blok_indeksi(mashq.bloklar or [], boshlanish) is not None:
            return mashq
    return None


def _saqla(mashq):
    mashq.save(update_fields=["bloklar", "savollar"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unit 5 SB — "Discussing grammar": bo'sh joy gap O'RTASIDA turardi
# ─────────────────────────────────────────────────────────────────────────────
U5_KORSATMA = "In these sentences, one or two answers are correct"


def _u5_bosh_joyni_oxiriga(mashq):
    """Kitobda har variant yonida katakcha bor, bizda esa javob HARFLARI
    ("a, c") yoziladi — lekin input gapning o'rtasiga qo'yilgan edi, go'yo
    u yerga SO'Z yozish kerakdek (Shuxrat: "mashq tushunarsiz berilgan").
    Endi gap butun holda o'qiladi, bo'sh joy `___` bilan ko'rsatiladi,
    input esa qator OXIRIDA — ko'rsatmadagi namuna bilan bir xil shakl."""
    bloklar = mashq.bloklar
    ozgardi = False
    for blok in bloklar:
        if blok.get("tur") != "mashq":
            continue
        for qator in blok.get("qatorlar") or []:
            bolaklar = qator.get("bolaklar") or []
            kiritishlar = [b for b in bolaklar if b.get("bosh_joy")]
            if len(kiritishlar) != 1 or bolaklar[-1].get("bosh_joy"):
                continue
            kiritish = kiritishlar[0]
            qismlar = [b["matn"].strip() for b in bolaklar if b.get("matn")]
            qator["bolaklar"] = [
                {"matn": " ___ ".join(qismlar) + "   →"},
                kiritish,
            ]
            ozgardi = True
    if ozgardi:
        _saqla(mashq)
    return ozgardi


# ─────────────────────────────────────────────────────────────────────────────
# 2. Unit 6 SB — A/B/C moslashtirish: C ustuni oddiy matn qatoriga tushib qolgan
# ─────────────────────────────────────────────────────────────────────────────
U6SB_KORSATMA = "Match the lines in A and B, and then match them with a sentence in C"


def _u6sb_c_ustuni(mashq):
    """Kitobda uchta ustun bor (A / B / C), bizda C butun boshli
    "C: … / … / …" degan bitta uzun qatorga aylanib qolgan edi — talaba
    uni mashqning bir qismi deb tanimasdi. Endi C alohida ustun jadvali."""
    bloklar = mashq.bloklar
    i = _blok_indeksi(bloklar, "C: We went to Spain.")
    if i is None:
        return False
    matn = bloklar[i]["matn"]
    gaplar = [g.strip() for g in matn.split(":", 1)[1].split(" / ") if g.strip()]
    bloklar[i] = {
        "tur": "jadval",
        "sarlavhalar": ["C"],
        "qatorlar": [[g] for g in gaplar],
    }
    # Kitobdagi "There is more than one possible answer." eslatmasi tushib
    # qolgan edi — u tekshiruv natijasini tushuntiradi.
    j = _blok_indeksi(bloklar, U6SB_KORSATMA)
    if j is not None and "more than one" not in bloklar[j]["matn"]:
        bloklar[j]["matn"] = (
            "Match the lines in A and B, and then match them with a sentence in C. "
            "There is more than one possible answer. Read them aloud to a partner."
        )
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unit 6 WB — "Word stress": jadval javoblar bilan to'ldirib qo'yilgan
# ─────────────────────────────────────────────────────────────────────────────
U6WB_KORSATMA = "Write the words in the box under the correct stress pattern"

U6WB_NAQSHLAR = ["1 ●•", "2 •●", "3 •●•", "4 ●••", "5 ••●•"]
# So'z tartibi — kitobdagi quti tartibi ("successful" namuna, tashlab ketiladi)
U6WB_SOZLAR = [
    ("invite", "2 •●"),
    ("invitation", "5 ••●•"),
    ("musical", "4 ●••"),
    ("artist", "1 ●•"),
    ("competition", "5 ••●•"),
    ("famous", "1 ●•"),
    ("happiness", "4 ●••"),
    ("collection", "3 •●•"),
    ("decision", "3 •●•"),
    ("photograph", "4 ●••"),
    ("succeed", "2 •●"),
    ("politician", "5 ••●•"),
    ("discuss", "2 •●"),
    ("danger", "1 ●•"),
]


def _u6wb_stress(mashq):
    """Talaba so'zlarni o'zi taqsimlashi kerak edi, lekin jadval allaqachon
    to'ldirilgan holda chiqardi (Shuxrat, image19). Endi to'ldirilgan jadval
    javob kaliti sifatida faqat o'qituvchiga qoladi, talaba esa har so'z
    uchun urg'u naqshini tanlaydi (Unit 3 SB dagi /t/-/d/-/ɪd/ mashqi bilan
    bir xil mexanika)."""
    bloklar = mashq.bloklar
    savollar = mashq.savollar
    jadval_i = None
    for i, blok in enumerate(bloklar):
        if blok.get("tur") == "jadval" and blok.get("sarlavhalar") == ["Stress", "So'zlar"]:
            jadval_i = i
            break
    if jadval_i is None or any(b.get("tur") == "tanlov" and b.get("stress_mashqi") for b in bloklar):
        return False
    bloklar[jadval_i]["oqituvchi_uchun"] = True

    bosh = len(savollar)
    qatorlar = []
    for k, (soz, naqsh) in enumerate(U6WB_SOZLAR):
        savollar.append({"savol": soz, "togri": naqsh})
        qatorlar.append({"raqam": soz, "savol_idx": bosh + k, "variantlar": U6WB_NAQSHLAR})
    bloklar.insert(jadval_i, {"tur": "tanlov", "stress_mashqi": True, "qatorlar": qatorlar})
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Unit 7 WB — "Prepositions": B va C ustunlari birlashtirib yuborilgan
# ─────────────────────────────────────────────────────────────────────────────
U7WB_KORSATMA = "Match a sentence beginning in A with a preposition in B"

U7WB_PREDLOGLAR = ["as", "than", "like", "in", "from"]
U7WB_QATORLAR = [
    ("1 It's the tallest ___ the world.", "in", "the world."),
    ("2 Yours is the same ___ mine.", "as", "mine."),
    ("3 She's younger ___ her brothers.", "than", "her brothers."),
    ("4 He looks ___ his father.", "like", "his father."),
    ("5 They're different ___ the others.", "from", "the others."),
]


def _u7wb_predloglar(mashq):
    """Kitobda uch bosqich bor: A (gap boshi) + B (predlog) + C (gap oxiri).
    Bizda B va C birlashtirilib ("as mine.", "than her brothers.") o'ng
    ustunga qo'yilgan edi — ya'ni PREDLOG TANLASH mashqi umuman yo'qolgan
    (Shuxrat, image21). Endi predlog alohida tanlanadi, moslashtirish esa
    faqat gap oxiri bo'yicha ketadi."""
    bloklar = mashq.bloklar
    savollar = mashq.savollar
    mos_i = None
    for i, blok in enumerate(bloklar):
        if blok.get("tur") == "moslashtir" and "as mine." in (blok.get("ong") or []):
            mos_i = i
            break
    if mos_i is None:
        return False

    # O'ng ustun — faqat gap oxiri; kalitlar ham shunga moslanadi.
    # Tartib KITOBDAGI C ustuni tartibi — javob tartibida bo'lsa mashq
    # o'z-o'zidan yechilib qolardi.
    bloklar[mos_i]["ong"] = [
        "her brothers.",
        "the others.",
        "his father.",
        "mine.",
        "the world.",
    ]
    for band, (_, _, oxiri) in zip(bloklar[mos_i]["chap"], U7WB_QATORLAR):
        savollar[band["savol_idx"]]["togri"] = oxiri

    # Predlog tanlash — alohida blok, alohida savollar.
    bosh = len(savollar)
    qatorlar = []
    for k, (gap, predlog, _) in enumerate(U7WB_QATORLAR):
        savollar.append({"savol": gap, "togri": predlog})
        qatorlar.append(
            {"raqam": str(k + 1), "savol_idx": bosh + k, "variantlar": U7WB_PREDLOGLAR}
        )
    bloklar.insert(mos_i, {"tur": "tanlov", "qatorlar": qatorlar})

    # B va C ro'yxatlari endi mashqning o'zida — ko'rsatmada takrorlanmasin.
    j = _blok_indeksi(bloklar, U7WB_KORSATMA)
    if j is not None:
        bloklar[j]["matn"] = (
            "Match a sentence beginning in A with a preposition in B and an ending in C."
        )
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 5. Unit 8 WB — wordsearch: javob yozadigan joy umuman yo'q edi
# ─────────────────────────────────────────────────────────────────────────────
U8WB_KORSATMA = "Find ten parts of the body in the wordsearch."

U8WB_SOZLAR = ["EAR", "FINGER", "HAND", "MOUTH", "ARM", "EYE", "LEG", "TEETH", "FOOT", "NOSE"]


def _u8wb_wordsearch(mashq):
    """Javoblar ochiq berilgan (bu 0019 da o'qituvchiga o'tkazildi), lekin
    topilgan so'zni yozadigan joy YO'Q edi (Shuxrat, image27) — mashq
    umuman bajarib bo'lmasdi. Endi 10 ta katakcha bor.

    So'zlar TARTIBI muhim emas: 10 savolning matni ham, kaliti ham bir xil
    ro'yxat — `kop_javobli_guruhlar` ularni bitta tartibsiz to'plam sifatida
    tekshiradi (qisman ball bilan)."""
    bloklar = mashq.bloklar
    savollar = mashq.savollar
    i = _blok_indeksi(bloklar, U8WB_KORSATMA)
    if i is None or any(b.get("wordsearch_javoblari") for b in bloklar):
        return False
    # Wordsearch rasmidan keyin qo'yamiz.
    joy = i + 1
    while joy < len(bloklar) and bloklar[joy].get("tur") == "rasm":
        joy += 1

    bosh = len(savollar)
    qatorlar = []
    for k in range(len(U8WB_SOZLAR)):
        savollar.append({"savol": "Topilgan so'z", "togri": list(U8WB_SOZLAR)})
        qatorlar.append(
            {"bolaklar": [{"matn": f"{k + 1}"}, {"bosh_joy": True, "savol_idx": bosh + k}]}
        )
    bloklar.insert(joy, {"tur": "mashq", "wordsearch_javoblari": True, "qatorlar": qatorlar})
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 6. Unit 10 SB — telefon suhbatlari charti javoblar bilan to'ldirilgan
# ─────────────────────────────────────────────────────────────────────────────
U10SB_KORSATMA = "Listen to four phone conversations. Complete the chart after each one."


def _u10sb_chart(mashq):
    """Chart to'liq to'ldirilgan holda chiqardi (Shuxrat, image32) — talaba
    audioni eshitmasdan javobni o'qirdi. To'ldirilgan chart javob kaliti
    sifatida o'qituvchiga qoladi, talaba esa kitobdagidek BO'SH chartni
    ko'radi.

    Katakchalarga input QO'YILMADI: javoblar erkin shakldagi qisqa
    izohlar ("Pat vokzalda"), ularni avtomatik tekshirib bo'lmaydi va
    baholansa talaba adolatsiz ball yo'qotardi."""
    bloklar = mashq.bloklar
    jadval_i = None
    for i, blok in enumerate(bloklar):
        if blok.get("tur") != "jadval" or (blok.get("sarlavhalar") or [""])[1:2] != [
            "Conversation 1"
        ]:
            continue
        if blok.get("oqituvchi_uchun"):
            continue
        # Bo'sh chart allaqachon qo'yilgan bo'lsa — takror qo'shmaymiz
        # (u ham xuddi shu sarlavhalarga ega).
        if not any(katak for qator in blok.get("qatorlar") or [] for katak in qator[1:]):
            continue
        jadval_i = i
        break
    if jadval_i is None:
        return False
    jadval = bloklar[jadval_i]
    jadval["oqituvchi_uchun"] = True
    bosh_jadval = {
        "tur": "jadval",
        "sarlavhalar": jadval["sarlavhalar"],
        "qatorlar": [[qator[0]] + [""] * (len(qator) - 1) for qator in jadval["qatorlar"]],
    }
    bloklar.insert(jadval_i, bosh_jadval)
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 7. Unit 4 WB REVIEW — suhbat mashqdan ajralib, oxiriga tushib qolgan
# ─────────────────────────────────────────────────────────────────────────────
U4WB_KORSATMA = "Underline the correct words in the conversation."


def _u4wb_suhbat(mashq):
    """Kitobda A/B suhbati butun holda turadi, tanlov variantlari esa gap
    ichida raqamlangan. Bizda suhbatning birinchi qatoridan boshqasi
    tanlov tugmalaridan KEYIN, "Suhbat matni:" degan alohida blokka
    tushib qolgan edi — talaba nima haqida javob berayotganini bilmasdi
    (Shuxrat, image10: "mashq dialogi to'liq berilmagan").

    Endi suhbat bitta blok bo'lib, tanlovdan OLDIN turadi."""
    bloklar = mashq.bloklar
    suhbat_i = _blok_indeksi(bloklar, "Suhbat matni:")
    bosh_i = _blok_indeksi(bloklar, "A Good morning! Can I help you?")
    if suhbat_i is None or bosh_i is None or suhbat_i < bosh_i:
        return False
    qolgani = bloklar[suhbat_i]["matn"].split(":", 1)[1].strip()
    bloklar[bosh_i] = {
        "tur": "matn",
        "matn": "A Good morning! Can I help you?\n" + qolgani,
    }
    del bloklar[suhbat_i]
    _saqla(mashq)
    return True


# ─────────────────────────────────────────────────────────────────────────────
TUZATISHLAR = [
    (U4WB_KORSATMA, _u4wb_suhbat, "Unit 4 WB — REVIEW suhbati"),
    (U5_KORSATMA, _u5_bosh_joyni_oxiriga, "Unit 5 SB — bo'sh joy qator oxiriga"),
    (U6SB_KORSATMA, _u6sb_c_ustuni, "Unit 6 SB — C ustuni"),
    (U6WB_KORSATMA, _u6wb_stress, "Unit 6 WB — word stress mashqi"),
    (U7WB_KORSATMA, _u7wb_predloglar, "Unit 7 WB — predlog tanlash"),
    (U8WB_KORSATMA, _u8wb_wordsearch, "Unit 8 WB — wordsearch katakchalari"),
    (U10SB_KORSATMA, _u10sb_chart, "Unit 10 SB — bo'sh chart"),
]


def pre_intermediate_mashqlari(KursTugun, KursMashq):
    darajalar = list(
        KursTugun.objects.filter(kalit="pre_intermediate").values_list("id", flat=True)
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
    mashqlar = list(pre_intermediate_mashqlari(KursTugun, KursMashq))
    hisobot = []
    for boshlanish, amal, izoh in TUZATISHLAR:
        mashq = _mashq_top(mashqlar, boshlanish)
        hisobot.append((izoh, bool(mashq) and amal(mashq)))
    return hisobot
