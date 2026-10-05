"""Writing/Speaking: hamma xatoni bir yo'la topish (2026-10-05).

MUAMMO: asosiy baholash BIR o'tishda 1-2 ta xato topadi (model recall'i past). Talaba tuzatib qayta
yuborsa, yana 1-2 ta topiladi. Ko'rsatmada "hammasini sanang" deyilgani yetmaydi.

YECHIM — ko'p bosqichli tekshiruv (asosiy baholashdan KEYIN, uning ustiga):
  1) Matn dastur tomonidan RAQAMLANGAN GAPLARGA bo'linadi; model har bir gap uchun javob berishga
     MAJBUR (to'g'ri gap uchun ham bo'sh ro'yxat) — hech bir gapni o'tkazib yubora olmaydi. Javobda
     tushib qolgan gaplar alohida qayta tekshiriladi.
  2) AUDITOR: model topilgan xatolarni ko'rib, FAQAT tashlab ketilganlarni qidiradi (yangi xato
     qolmaguncha, ko'pi bilan `AUDIT_AYLANISH` marta).
  3) AI'siz dastur tekshiruvlari (takror so'z, a/an, kichik "i").
  4) Natija "errors" (albatta tuzatish kerak) va "suggestions" (uslub, majburiy emas) ga AJRATILADI —
     tuzatgandan keyin faqat tavsiyalar qoladi, "yana yangi xato" tuyg'usi bo'lmaydi.

Hamma qo'shimcha bosqichlar xato bersa yoki vaqt byudjeti tugasa — asosiy baholash natijasi
O'ZGARISHSIZ qaytadi (talaba hech qachon tekshiruvsiz qolmaydi).
"""

import difflib
import logging
import re
import time

log = logging.getLogger("assessment")

AUDIT_AYLANISH = 2  # auditor ko'pi bilan shuncha marta ishlaydi
BYUDJET_SEK = 80  # qo'shimcha bosqichlar uchun umumiy vaqt (gunicorn 300s chegarasidan past qolsin)
CHAQIRUV_TIMEOUT_MS = 45_000
GAPDA_ENG_KOP_SOZ = 40  # tinish belgisiz transkriptda shuncha so'zdan keyin bo'lib yuboriladi

_IZOH = {
    "type": "object",
    "properties": {"en": {"type": "string"}, "uz": {"type": "string"}, "ru": {"type": "string"}},
    "required": ["en", "uz", "ru"],
}
_XATO = {
    "type": "object",
    "properties": {
        "xato": {"type": "string"},
        "tuzatish": {"type": "string"},
        "turi": {"type": "string", "enum": [
            "spelling", "agreement", "tense", "article", "plural", "word_form", "preposition",
            "word_order", "punctuation", "word_choice", "other",
        ]},
        "daraja": {"type": "string", "enum": ["xato", "tavsiya"]},
        "izoh": _IZOH,
    },
    "required": ["xato", "tuzatish", "turi", "daraja", "izoh"],
}
SXEMA_GAPLAR = {
    "type": "object",
    "properties": {"gaplar": {"type": "array", "items": {
        "type": "object",
        "properties": {"n": {"type": "integer"}, "xatolar": {"type": "array", "items": _XATO}},
        "required": ["n", "xatolar"],
    }}},
    "required": ["gaplar"],
}
SXEMA_YANGI = {
    "type": "object",
    "properties": {"yangi": {"type": "array", "items": {
        "type": "object",
        "properties": {"n": {"type": "integer"}, **_XATO["properties"]},
        "required": ["n", *_XATO["required"]],
    }}},
    "required": ["yangi"],
}

_UMUMIY_QOIDALAR = (
    "REPORTING RULES (apply to every error):\n"
    "- Report EACH error separately, even when the same kind of mistake appears many times, even when "
    "several are in the same sentence.\n"
    "- \"xato\": quote the smallest incorrect fragment (2-5 words, enough context to find it) EXACTLY as the "
    "student wrote it. \"tuzatish\": the corrected fragment. Both ALWAYS in English, never translated.\n"
    "- \"daraja\": \"xato\" for real grammar / spelling / vocabulary mistakes a teacher would mark wrong; "
    "\"tavsiya\" ONLY for optional style improvements where the sentence is already grammatical. Never mark a "
    "style preference as \"xato\".\n"
    "- Do NOT invent errors. If you are not sure something is wrong, do not report it as \"xato\".\n"
    "- Optional punctuation CHOICES are NOT errors: the serial (Oxford) comma, optional commas after short "
    "introductory words, colon vs comma before a list. Report punctuation only when it is clearly wrong "
    "(missing full stop, comma splice, wrong apostrophe).\n"
    "- \"izoh\": a short reason in three languages: {\"en\": ..., \"uz\": ..., \"ru\": ...} (natural, not word-for-word).\n"
    "- Return JSON only.\n"
)

_TEKSHIRUV_RO_YXATI = (
    "Check every sentence systematically for: (a) spelling; (b) subject-verb agreement (also after who/which/"
    "that, both, each, people, advantages, news); (c) verb tense and verb form (modal + base verb, "
    "preposition + -ing, passive participle, gerund vs infinitive); (d) articles a/an/the/zero; "
    "(e) singular/plural and uncountable nouns; (f) word forms (noun/adjective/adverb); (g) prepositions; "
    "(h) word order and missing or extra words; (i) punctuation and capitalisation; (j) wrong word choice or "
    "unnatural collocation."
)

PASS1_WRITING = (
    "You are a meticulous English proofreader for IELTS Writing. You receive the student's text split into "
    "NUMBERED SENTENCES. Your ONLY job: find EVERY language error.\n\n"
    "You MUST go through EVERY numbered sentence, one by one, in order, and return an entry for EACH sentence "
    "number — with an empty \"xatolar\" list if the sentence is fully correct. Never skip, merge or summarise "
    "sentences.\n\n" + _TEKSHIRUV_RO_YXATI + "\n\n" + _UMUMIY_QOIDALAR
)

PASS1_SPEAKING = (
    "You are a meticulous English proofreader for IELTS Speaking. You receive a TRANSCRIPT of what the "
    "student said, split into NUMBERED SEGMENTS. Because it is spoken language, IGNORE punctuation, "
    "capitalisation, fillers (um, uh, you know) and natural self-corrections. Report only GRAMMAR and LEXICAL "
    "errors (agreement, tense, articles, plural, word form, prepositions, word choice).\n\n"
    "You MUST go through EVERY numbered segment, one by one, in order, and return an entry for EACH segment "
    "number — with an empty \"xatolar\" list if it is correct. Never skip or merge segments.\n\n"
    + _UMUMIY_QOIDALAR
)

AUDITOR_PROMPT = (
    "You are a second, independent proofreader. A first proofreader has already marked the errors listed "
    "under ALREADY FOUND ERRORS. Read the numbered sentences/segments again, slowly, one by one, and find "
    "ONLY errors that are NOT in that list (never repeat a listed error). " + _TEKSHIRUV_RO_YXATI + "\n"
    "Put the sentence number in \"n\". If there are no additional real errors, return {\"yangi\": []}.\n\n"
    + _UMUMIY_QOIDALAR
)


# ── Matnni gaplarga bo'lish ─────────────────────────────────────────

def gaplarga_bol(matn, soha="writing"):
    """Raqamlanadigan gaplar ro'yxati. Tinish belgisiz transkriptda (Speaking) uzun parcha
    `GAPDA_ENG_KOP_SOZ` so'zlik bo'laklarga bo'linadi."""
    bolaklar = [b.strip() for b in re.split(r"(?<=[.!?])\s+|\n+", matn or "") if b.strip()]
    natija = []
    for b in bolaklar:
        sozlar = b.split()
        if len(sozlar) <= GAPDA_ENG_KOP_SOZ:
            natija.append(b)
        else:
            for i in range(0, len(sozlar), GAPDA_ENG_KOP_SOZ):
                natija.append(" ".join(sozlar[i:i + GAPDA_ENG_KOP_SOZ]))
    return natija


def _raqamlangan(gaplar, raqamlar=None):
    return "\n".join(f"{n}. {g}" for n, g in enumerate(gaplar, start=1) if raqamlar is None or n in raqamlar)


# ── AI'siz tekshiruvlar ─────────────────────────────────────────────

_MUSTASNO_TAKROR = {"that", "had", "is", "can"}  # "that that", "had had" to'g'ri bo'lishi mumkin
_A_UNLI_ISTISNO = ("uni", "use", "usu", "uti", "eu", "one", "once", "ubiq", "ura")
_AN_UNSIZ_ISTISNO = ("hour", "honest", "honor", "honour", "heir")


def _izoh3(en, uz, ru):
    return {"en": en, "uz": uz, "ru": ru}


# Ko'p uchraydigan, QAT'IY qoida bilan topiladigan xatolar: (regex, almashtirish, turi, izoh).
# Faqat noaniqlik deyarli yo'q holatlar — yolg'on signal bermasligi uchun.
ODATIY_XATOLAR = [
    (r"\bin the end of\b", "at the end of", "preposition",
     _izoh3("'At the end of' (not 'in the end of') is used for the final part of something.",
            "Biror narsaning oxiri uchun 'at the end of' ishlatiladi ('in the end of' emas).",
            "Для обозначения конца чего-либо используется 'at the end of', а не 'in the end of'.")),
    (r"\bmore (better|easier|cheaper|bigger|worse|faster|smaller|larger|higher|lower|nicer|happier|healthier)\b",
     r"\1", "word_form",
     _izoh3("Double comparative: use either 'more' or '-er', not both.",
            "Ikki marta qiyoslash: 'more' yoki '-er' dan faqat bittasi ishlatiladi.",
            "Двойная сравнительная степень: нужно либо 'more', либо '-er', не оба.")),
    (r"\bmore easy\b", "easier", "word_form",
     _izoh3("Short adjectives take '-er': 'easier'.", "Qisqa sifatlar '-er' oladi: 'easier'.",
            "Короткие прилагательные образуют степень сравнения с '-er': 'easier'.")),
    (r"\b(informations|advices|furnitures|equipments|knowledges|researchs|homeworks)\b",
     lambda m: m.group(1)[:-1], "plural",
     _izoh3("This noun is uncountable — it has no plural form.", "Bu ot sanalmaydi — ko'plik shakli yo'q.",
            "Это существительное неисчисляемое — множественного числа нет.")),
    (r"\b(childrens|womans)\b", lambda m: {"childrens": "children", "womans": "women"}[m.group(1).lower()], "plural",
     _izoh3("Irregular plural form.", "Noto'g'ri ko'plik shakli.", "Неправильная форма множественного числа.")),
    (r"\bpeoples\b", "people", "plural",
     _izoh3("'People' is already plural.", "'People' o'zi ko'plik.", "'People' уже во множественном числе.")),
    (r"\b(discuss|mention) about\b", r"\1", "preposition",
     _izoh3("This verb is not followed by 'about'.", "Bu fe'ldan keyin 'about' kerak emas.",
            "После этого глагола 'about' не нужен.")),
    (r"\bdepends? of\b", lambda m: m.group(0).replace(" of", " on"), "preposition",
     _izoh3("'Depend on', not 'depend of'.", "'Depend on' bo'ladi, 'depend of' emas.",
            "Правильно 'depend on', а не 'depend of'.")),
]

# Bosh harf bilan yoziladigan so'zlar (Writing): kichik harfda uchrasa — xato. 'may', 'march', 'turkey' kabi
# ko'p ma'noli so'zlar ATAYLAB yo'q.
KATTA_HARF_SOZLARI = (
    "canadian|brazilian|indian|american|british|english|french|german|chinese|japanese|korean|russian|european|"
    "african|asian|uzbek|uzbekistan|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|"
    "april|june|july|september|october|november|december"
)
KATTA_HARF_RX = r"\b(?:" + KATTA_HARF_SOZLARI + r")\b"


def _gap_boshlanishlari(matn, soha):
    """Har gapning matndagi boshlanish indeksi (gap raqami = indeks + 1). Topilmasa — None."""
    bosh, joy = [], 0
    for g in gaplarga_bol(matn, soha):
        # `gaplarga_bol` bo'shliqlarni bittaga keltiradi — asl matnda esa qo'sh bo'shliq/yangi qator bo'lishi
        # mumkin, shuning uchun so'zlar orasida istalgan bo'shliqqa mos keluvchi regex ishlatiladi.
        rx = r"\s+".join(re.escape(so) for so in g.split())
        m = re.compile(rx).search(matn or "", joy)
        if not m:
            return None
        bosh.append(m.start())
        joy = m.start() + 1
    return bosh


def _gap_raqami(bosh, pozitsiya):
    if not bosh:
        return None
    n = 0
    for i, b in enumerate(bosh):
        if b <= pozitsiya:
            n = i + 1
    return n or None


def dastur_xatolari(matn, soha="writing"):
    """Aniq, AI'siz topiladigan xatolar: takror so'z, a/an, kichik 'i' va ko'p uchraydigan qat'iy
    qoidalar. Har xatoga `gap` (gap raqami) yoziladi — bir xil xato ikki gapda uchrasa, ikkalasi
    alohida qoladi."""
    xatolar = _dastur_xatolari_xom(matn, soha)
    bosh = _gap_boshlanishlari(matn, soha)
    for e in xatolar:
        pozitsiya = e.pop("_pozitsiya", None)
        if pozitsiya is not None:
            e["gap"] = _gap_raqami(bosh, pozitsiya)
    return xatolar


def _dastur_xatolari_xom(matn, soha="writing"):
    xatolar = []
    for m in re.finditer(r"\b(\w+)\s+\1\b", matn or "", flags=re.IGNORECASE):
        if m.group(1).lower() in _MUSTASNO_TAKROR:
            continue
        xatolar.append({
            "_pozitsiya": m.start(),
            "xato": m.group(0), "tuzatish": m.group(1), "turi": "other", "daraja": "xato",
            "izoh": _izoh3("Repeated word.", "So'z takrorlangan.", "Слово повторено."),
        })
    for m in re.finditer(r"\b([Aa])\s+([aeiouAEIOU]\w*)", matn or ""):
        soz = m.group(2).lower()
        if soz.startswith(_A_UNLI_ISTISNO):
            continue
        xatolar.append({
            "_pozitsiya": m.start(),
            "xato": m.group(0), "tuzatish": f"an {m.group(2)}", "turi": "article", "daraja": "xato",
            "izoh": _izoh3("Use 'an' before a vowel sound.", "Unli tovush oldidan 'an' ishlatiladi.",
                           "Перед гласным звуком употребляется 'an'."),
        })
    for m in re.finditer(r"\b([Aa]n)\s+([b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]\w*)", matn or ""):
        soz = m.group(2).lower()
        if soz.startswith(_AN_UNSIZ_ISTISNO) or m.group(2).isupper():
            continue
        xatolar.append({
            "_pozitsiya": m.start(),
            "xato": m.group(0), "tuzatish": f"a {m.group(2)}", "turi": "article", "daraja": "xato",
            "izoh": _izoh3("Use 'a' before a consonant sound.", "Undosh tovush oldidan 'a' ishlatiladi.",
                           "Перед согласным звуком употребляется 'a'."),
        })
    for rx, almashtirish, turi, izoh in ODATIY_XATOLAR:
        for m in re.finditer(rx, matn or "", flags=re.IGNORECASE):
            tuzatish = re.sub(rx, almashtirish, m.group(0), flags=re.IGNORECASE)
            if tuzatish != m.group(0):
                xatolar.append({"_pozitsiya": m.start(), "xato": m.group(0), "tuzatish": tuzatish, "turi": turi,
                                "daraja": "xato", "izoh": izoh})
    if soha == "writing":
        for m in re.finditer(KATTA_HARF_RX, matn or ""):
            soz = m.group(0)
            xatolar.append({
                "_pozitsiya": m.start(),
                "xato": soz, "tuzatish": soz.capitalize(), "turi": "punctuation", "daraja": "xato",
                "izoh": _izoh3("Nationalities, languages, days and months start with a capital letter.",
                               "Millat, til, hafta kuni va oy nomlari bosh harf bilan yoziladi.",
                               "Национальности, языки, дни недели и месяцы пишутся с заглавной буквы."),
            })
        for m in re.finditer(r"(?<![\w'’])i(?![\w'’])(?=\s)", matn or ""):
            xatolar.append({
                "_pozitsiya": m.start(),
                "xato": "i", "tuzatish": "I", "turi": "punctuation", "daraja": "xato",
                "izoh": _izoh3("The pronoun 'I' is always capitalised.", "'I' olmoshi doim bosh harf bilan yoziladi.",
                               "Местоимение 'I' всегда пишется с заглавной буквы."),
            })
    return xatolar


# ── Birlashtirish ───────────────────────────────────────────────────

def _norm(s):
    return re.sub(r"[^a-z0-9' ]+", "", (s or "").lower()).strip()


def _farq(e):
    """Xato va tuzatish orasidagi FARQ ("technology play"->"technology plays" va "play an"->"plays an"
    ikkalasida ham play->plays). AI bir xil xatoni turlicha qirqib yozadi — farq shuni tenglashtiradi."""
    a, b = _norm(e.get("xato")).split(), _norm(e.get("tuzatish")).split()
    sm = difflib.SequenceMatcher(None, a, b)
    return tuple((" ".join(a[i1:i2]), " ".join(b[j1:j2])) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")


def _bir_xil(a, b):
    """a, b — bitta xatomi? Ikkalasining gap raqami ma'lum va FARQLI bo'lsa — yo'q (bir xil xato ikki
    gapda uchrasa, ikkalasi alohida hisoblanadi)."""
    ga, gb = a.get("gap"), b.get("gap")
    if ga is not None and gb is not None and ga != gb:
        return False
    na, nb = _norm(a.get("xato")), _norm(b.get("xato"))
    if na and nb and (na == nb or (len(na) >= 4 and na in nb) or (len(nb) >= 4 and nb in na)):
        return True
    fa, fb = _farq(a), _farq(b)
    return bool(fa) and fa == fb


def _faqat_tinish_farqi(e):
    """Xato va tuzatish faqat tinish belgisi yoki katta-kichik harfda farq qiladimi?"""
    def harflar(x):
        return re.sub(r"[^a-z0-9]+", " ", (x or "").lower()).split()
    return harflar(e.get("xato")) == harflar(e.get("tuzatish"))


def birlashtir(*royxatlar):
    """Bir necha xatolar ro'yxatini takrorsiz birlashtiradi (birinchi uchragani qoladi).
    Xato=tuzatish bo'lib qolgan (ma'nosiz) yozuvlar tashlanadi. Gap raqami NOMA'LUM yozuv (asosiy
    baholash) ko'pi bilan BITTA takrorni yutadi — aks holda bir xil xatoning ikkinchi haqiqiy uchrashuvi
    ham tushib qolardi."""
    chiqish = []  # [yozuv, yutgan]
    for royxat in royxatlar:
        for e in royxat or []:
            # Ma'nosiz yozuv: xato va tuzatish AYNAN bir xil. Katta-kichik harf farqi (canadian ->
            # Canadian, i -> I) ma'noli tuzatish — shuning uchun kichik harfga o'tkazib taqqoslanmaydi.
            if not isinstance(e, dict) or (e.get("xato") or "").strip() == (e.get("tuzatish") or "").strip():
                continue
            takror = False
            for joy in chiqish:
                x, yutgan = joy
                if x.get("gap") is None and yutgan and e.get("gap") is not None:
                    continue  # gap raqami yo'q yozuv allaqachon bitta (raqamli) takrorni yutgan
                if _bir_xil(e, x):
                    if x.get("gap") is None and e.get("gap") is not None:
                        joy[1] = True
                    takror = True
                    break
            if not takror:
                chiqish.append([e, False])
    return [x for x, _ in chiqish]


def _matndagi_orni(e, matn):
    i = (matn or "").lower().find((e.get("xato") or "").lower().strip())
    return i if i >= 0 else 10 ** 9


# ── Asosiy oqim ─────────────────────────────────────────────────────

def _yig(chaqiruv_natijasi, hisob):
    hisob["chaqiruvlar"] += 1
    hisob["input_tokens"] += chaqiruv_natijasi.get("input_tokens", 0) or 0
    hisob["output_tokens"] += chaqiruv_natijasi.get("output_tokens", 0) or 0


def chuqur_xatolar(ai, matn, savol_matni="", tur="task2", soha="writing"):
    """`ai` — `generate_json(system, matn, javob_sxemasi=...)` bor provider. Qaytaradi:
    {"errors": [...], "suggestions": [...], "hisob": {...}, "gaplar_soni": N}."""
    boshlandi = time.monotonic()
    hisob = {"chaqiruvlar": 0, "input_tokens": 0, "output_tokens": 0}
    gaplar = gaplarga_bol(matn, soha)
    topilgan = []  # [(gap_raqami, xato)]

    def vaqt_bor():
        return time.monotonic() - boshlandi < BYUDJET_SEK

    sarlavha = (f"Question/topic: {savol_matni}\n\n" if savol_matni else "") + \
        ("NUMBERED SENTENCES:\n" if soha == "writing" else "NUMBERED SEGMENTS:\n")
    prompt1 = PASS1_WRITING if soha == "writing" else PASS1_SPEAKING

    # 1) Gap-ma-gap majburiy tekshiruv (tushib qolgan gaplar bir marta qayta tekshiriladi)
    korilgan = set()
    kutilayotgan = set(range(1, len(gaplar) + 1))
    for _ in range(2):
        if not kutilayotgan or not vaqt_bor():
            break
        r = ai.generate_json(prompt1, sarlavha + _raqamlangan(gaplar, kutilayotgan),
                             javob_sxemasi=SXEMA_GAPLAR, max_tokens=16000)
        _yig(r, hisob)
        for g in (r["natija"].get("gaplar") or []):
            n = g.get("n")
            if n in kutilayotgan:
                korilgan.add(n)
                topilgan.extend((n, dict(x, gap=n)) for x in (g.get("xatolar") or []))
        kutilayotgan -= korilgan

    # 2) Auditor: tashlab ketilganlarni qidiradi
    for _ in range(AUDIT_AYLANISH):
        if not vaqt_bor():
            break
        mavjud = "\n".join(f"- [{n}] {x.get('xato')} -> {x.get('tuzatish')}" for n, x in topilgan) or "(none)"
        r = ai.generate_json(
            AUDITOR_PROMPT, sarlavha + _raqamlangan(gaplar) + f"\n\nALREADY FOUND ERRORS:\n{mavjud}",
            javob_sxemasi=SXEMA_YANGI, max_tokens=16000,
        )
        _yig(r, hisob)
        yangi = [(y.get("n"), dict(y, gap=y.get("n"))) for y in (r["natija"].get("yangi") or [])
                 if isinstance(y, dict)]
        haqiqiy_yangi = [(n, y) for n, y in yangi if not any(_bir_xil(y, x) for _, x in topilgan)]
        if not haqiqiy_yangi:
            break
        topilgan.extend(haqiqiy_yangi)

    return {
        "xatolar": [x for _, x in topilgan],
        "hisob": hisob,
        "gaplar_soni": len(gaplar),
        "tekshirilgan_gaplar": len(korilgan),
    }


def chuqurlashtir(ai, javob, matn, savol_matni="", tur="task2", soha="writing"):
    """Asosiy baholash javobi (`javob`, `_generate` qaytargani) ustiga chuqur tekshiruvni qo'yadi.
    Har qanday xatoda — asosiy javob O'ZGARISHSIZ qaytadi."""
    try:
        chuqur = chuqur_xatolar(ai, matn, savol_matni, tur, soha)
    except Exception:  # noqa: BLE001 — qo'shimcha tekshiruv talabani tekshiruvsiz qoldirmasligi kerak
        log.warning("Chuqur xato qidiruvi ishlamadi — asosiy natija qaytariladi", exc_info=True)
        return javob

    natija = javob["natija"]
    asosiy = [e for e in (natija.get("errors") or []) if isinstance(e, dict)]
    hammasi = birlashtir(asosiy, chuqur["xatolar"], dastur_xatolari(matn, soha))
    if soha == "speaking":
        # Og'zaki nutq transkriptida tinish belgisi va bosh harf yo'q — bu til xatosi EMAS ("house i go" ->
        # "house. I go" kabilar yolg'on signal). Faqat grammatika va leksika qoladi.
        hammasi = [e for e in hammasi if e.get("turi") != "punctuation" and not _faqat_tinish_farqi(e)]
    xatolar = [e for e in hammasi if e.get("daraja", "xato") != "tavsiya"]
    tavsiyalar = [e for e in hammasi if e.get("daraja") == "tavsiya"]
    xatolar.sort(key=lambda e: _matndagi_orni(e, matn))

    natija["errors"] = xatolar
    natija["suggestions"] = tavsiyalar
    natija["tekshiruv"] = {
        "chuqur": True,
        "gaplar": chuqur["gaplar_soni"],
        "tekshirilgan_gaplar": chuqur["tekshirilgan_gaplar"],
        "qoshimcha_chaqiruvlar": chuqur["hisob"]["chaqiruvlar"],
    }
    javob["input_tokens"] = (javob.get("input_tokens") or 0) + chuqur["hisob"]["input_tokens"]
    javob["output_tokens"] = (javob.get("output_tokens") or 0) + chuqur["hisob"]["output_tokens"]
    return javob
