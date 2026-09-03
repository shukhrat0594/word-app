import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Bolim(models.TextChoices):
    LISTENING = "listening", "Listening"
    READING = "reading", "Reading"
    WRITING = "writing", "Writing"
    SPEAKING = "speaking", "Speaking"


class Tur(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
    FILL_BLANKS = "fill_blanks", "Fill in the Blanks"
    MATCHING = "matching", "Matching"
    MAP_LABELLING = "map_labelling", "Plan/Map/Diagram Labelling"
    SHORT_ANSWER = "short_answer", "Short Answer"
    MATCHING_HEADINGS = "matching_headings", "Matching Headings"
    TFNG = "tfng", "True/False/Not Given"
    TASK1 = "task1", "Writing Task 1"
    TASK2 = "task2", "Writing Task 2"
    PART1 = "part1", "Speaking Part 1"
    PART2 = "part2", "Speaking Part 2"
    PART3 = "part3", "Speaking Part 3"


# Har bo'limda qaysi turlar bor (real IELTS formati, 2026-07-16).
# Kunlik limit (B4.1) shu ro'yxat uzunligidan hisoblanadi — tur qo'shilsa
# limit avtomatik moslashadi (qattiq kodlangan "5" yo'q). Writing/Speaking —
# auto-baholanmaydigan kontent banki (mavzu/namuna), shuning uchun limitga
# kirmaydi (ular MashqYechim orqali emas, faqat o'qish uchun).
BOLIM_TURLARI = {
    Bolim.LISTENING: [
        Tur.MULTIPLE_CHOICE,
        Tur.FILL_BLANKS,
        Tur.MATCHING,
        Tur.MAP_LABELLING,
        Tur.SHORT_ANSWER,
    ],
    Bolim.READING: [
        Tur.MULTIPLE_CHOICE,
        Tur.FILL_BLANKS,
        Tur.MATCHING_HEADINGS,
        Tur.TFNG,
        Tur.SHORT_ANSWER,
    ],
    Bolim.WRITING: [Tur.TASK1, Tur.TASK2],
    Bolim.SPEAKING: [Tur.PART1, Tur.PART2, Tur.PART3],
}

# Auto-baholanadigan (savollar/to'g'ri javob talab qiladigan) bo'limlar.
AVTO_BAHOLANADIGAN_BOLIMLAR = (Bolim.LISTENING, Bolim.READING)


def kop_javobli_guruhlar(savollar):
    """Ketma-ket kelgan, savol matni VA variantlari bir xil savollarni
    guruhlaydi — bu asl kitobdagi "Choose TWO letters, A-E" kabi BITTA
    ko'p-javobli savol (2026-07-27).

    Masalan Questions 19 va 20 — kitobda bitta savol, talaba A-E dan
    IKKITASINI tanlaydi, lekin javoblar kaliti ikkita alohida band beradi.
    Ma'lumot bazasida ular ikkita savol bo'lib turadi, shuning uchun
    guruhni shakli bo'yicha (bir xil matn + bir xil variantlar, yonma-yon)
    aniqlaymiz — JSON formatiga yangi maydon qo'shish shart emas, mavjud
    testlar ham avtomatik to'g'ri ishlaydi.

    Qaytaradi: [(bosh_indeks, uzunlik), ...] — barcha savollarni qoplaydi,
    yolg'iz savollar uchun uzunlik 1.
    """
    guruhlar = []
    i = 0
    while i < len(savollar):
        s = savollar[i]
        j = i + 1
        if (s.get("variantlar") or []) and s.get("tur") == "multiple_choice":
            while (
                j < len(savollar)
                and savollar[j].get("tur") == "multiple_choice"
                and str(savollar[j].get("savol", "")).strip() == str(s.get("savol", "")).strip()
                and (savollar[j].get("variantlar") or []) == (s.get("variantlar") or [])
            ):
                j += 1
        guruhlar.append((i, j - i))
        i = j
    return guruhlar


HARFLAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# 2026-08-26, foydalanuvchi topgan xato: telefon/planshet klaviaturasi
# apostrofni avtomatik "aqlli" ko'rinishga (‘ ’) o'zgartiradi,
# lekin kontentdagi "togri" qiymatlar oddiy to'g'ri chiziqli (' ')
# apostrof bilan yozilgan — natijada "can't" kabi to'g'ri javob ham
# XATO deb belgilanardi. Solishtirishdan oldin apostrof/tirnoq
# variantlari bir xillashtiriladi (faqat taqqoslash uchun — talabaga
# ko'rsatiladigan matn o'zgarmaydi).
_TIRNOQ_JADVALI = str.maketrans({
    "‘": "'", "’": "'", "ʼ": "'", "´": "'", "`": "'",
    "“": '"', "”": '"',
})

# 2026-08-26, Elementary QA: javob kalitlari kitobdagidek to'liq gap bo'lib
# yozilgan ("To the shops.", "Yes, there is."), lekin talaba odatda faqat
# mazmunni yozadi — nuqta/vergulni tashlab ketgani uchun to'g'ri javob
# XATO deb belgilanardi (butun Elementary bo'ylab 250 ta savol). Tinish
# belgisi mashqning o'zi tekshiradigan narsa emas, shuning uchun
# solishtirishda e'tiborga olinmaydi. Apostrof va defis SAQLANADI — ular
# so'zning bir qismi ("don't", "twenty-five").
_TINISH = str.maketrans({c: " " for c in ".,!?;:…–—"})

# 2026-08-27, Pre-Intermediate QA: javob kalitlari kitobdagidek QISQARTMA
# shaklda yozilgan ("I'll", "don't have to", "'d travel", "mustn't"), lekin
# to'liq shakl ham xuddi shunday to'g'ri javob ("I will", "do not have to",
# "would travel", "must not") — 12 Unit bo'ylab 114 ta savolda talaba
# bilimini bilib turib xato olardi.
#
# 2026-08-28, TUZATILDI (jiddiy xato). Avvalgi yechim har ikkala shaklni
# BITTA "kanonik" ko'rinishga keltirardi — ya'ni "he is" ham, "he has" ham
# bir xil "he's" ga tushardi. Natijada butun baza bo'ylab 85 ta grammatik
# BEMA'NI javob to'g'ri deb qabul qilinardi (24 ta mashqda):
#     kalit "Yes, he has."  <-  talaba "Yes, he is."          -> QABUL
#     kalit "He had woken up"  <-  "He would woken up"        -> QABUL
#     kalit "She has tea."  <-  "She is tea."                 -> QABUL
# Eng yomoni — bular AYNAN shu farqni o'rgatadigan mashqlar edi (Present
# Perfect qisqa javoblari, Past Perfect).
#
# Yangi yechim: normalizator yo'qotishli EMAS (qisqartmaga tegmaydi),
# uning o'rniga KALITDAN qabul qilinadigan variantlar TO'PLAMI yasaladi
# (`_qabul_variantlari`). Kengaytirish faqat KALITNING O'ZIDAGI
# qisqartmaga qo'llanadi, yasalgan variantga QAYTA qo'llanmaydi — aynan
# shu zanjirni uzish "he is" -> "he's" -> "he has" sirg'alishini
# to'xtatadi:
#     "he is"  -> {he is, he's}          ("he has" YO'Q)
#     "he has" -> {he has, he's}          ("he is" YO'Q)
#     "he's"   -> {he's, he is, he has}   (kalitning O'ZI noaniq — o'rinli)
_EGA = r"(?:i|you|he|she|it|we|they|there|that|this|who|what|where)"
_YORDAMCHI = (r"(do|does|did|is|are|was|were|has|have|had|could|should"
              r"|would|must|might|need|ought|dare)")

# To'liq shakl -> qisqartma. Maxsus shakllar umumiy "... not" qoidasidan
# OLDIN turishi shart, aks holda "will not" dan "willn't" chiqadi.
_QISQARTIRISH = [
    (r"\bcan\s?not\b", "can't"),
    (r"\bwill not\b", "won't"),
    (r"\bshall not\b", "shan't"),
    (rf"\b{_YORDAMCHI}\s+not\b", r"\1n't"),
    (rf"\b({_EGA})\s+am\b", r"\1'm"),
    (rf"\b({_EGA})\s+is\b", r"\1's"),
    (rf"\b({_EGA})\s+has\b", r"\1's"),
    (rf"\b({_EGA})\s+are\b", r"\1're"),
    (rf"\b({_EGA})\s+have\b", r"\1've"),
    (rf"\b({_EGA})\s+will\b", r"\1'll"),
    (rf"\b({_EGA})\s+would\b", r"\1'd"),
    (rf"\b({_EGA})\s+had\b", r"\1'd"),
    # Ega gapda qolib, bo'sh joyga faqat fe'l yoziladigan mashqlar:
    # kalit "'d travel", talaba "would travel".
    (r"^\s*will\s+", "'ll "),
    (r"^\s*would\s+", "'d "),
    (r"^\s*had\s+", "'d "),
    (r"^\s*have\s+", "'ve "),
    (r"^\s*am\s+", "'m "),
    (r"^\s*are\s+", "'re "),
]

# Qisqartma -> to'liq shakl. FAQAT MA'NOSI ANIQ qisqartmalar kengaytiriladi.
#
# `'s` (= is yoki has) va `'d` (= would yoki had) ATAYLAB YO'Q. Ular ikki
# xil ma'noni bersa, kalit "There's" dan "there has" ham chiqib ketardi va
# talaba bema'ni javob yozib ham o'tib ketardi. Amalda tekshirildi: kontent
# mualliflari bunday holatda to'liq shaklni ALLAQACHON alohida variant
# qilib yozishgan — masalan ['There is', "There's"], ['Who is', "Who's"],
# ["he had woken up ...", "he'd woken up ..."] — shuning uchun taxmin
# qilishning hojati yo'q, kalit o'zi aytib turadi.
_KENGAYTIRISH = [
    (r"\bcan't\b", ["cannot", "can not"]),
    (r"\bwon't\b", ["will not"]),
    (r"\bshan't\b", ["shall not"]),
    (rf"\b{_YORDAMCHI}n't\b", [r"\1 not"]),
    (rf"\b({_EGA})'m\b", [r"\1 am"]),
    (rf"\b({_EGA})'re\b", [r"\1 are"]),
    (rf"\b({_EGA})'ve\b", [r"\1 have"]),
    (rf"\b({_EGA})'ll\b", [r"\1 will"]),
    (r"^\s*'ll\s+", ["will "]),
    (r"^\s*'ve\s+", ["have "]),
    (r"^\s*'m\s+", ["am "]),
    (r"^\s*'re\s+", ["are "]),
]
_QISQARTIRISH = [(re.compile(q), a) for q, a in _QISQARTIRISH]
_KENGAYTIRISH = [(re.compile(q), a) for q, a in _KENGAYTIRISH]

# Bitta kalitdan yasaladigan variantlar soni chegarasi — bir nechta noaniq
# qisqartmali uzun kalitda kombinatorika o'smasin.
_VARIANT_CHEGARA = 32


def _norm(s):
    """Taqqoslash uchun normalizator (registr, tirnoq, tinish, probel).

    Qisqartmaga ATAYLAB TEGMAYDI — u yo'qotishli bo'lardi ("he is" va
    "he has" ni ajratib bo'lmay qolardi). Qisqartma `_qabul_variantlari`
    orqali, faqat KALIT tomonda hisobga olinadi."""
    s = str(s).lower().translate(_TIRNOQ_JADVALI).translate(_TINISH)
    return re.sub(r"\s+", " ", s).strip()


def _qabul_variantlari(kalit):
    """`kalit` uchun qabul qilinadigan normallashgan shakllar to'plami:
    kalitning o'zi + qisqartirilgan shakli + (kalitda qisqartma bo'lsa)
    uning to'liq shakl(lar)i.

    Kengaytirish FAQAT asl kalitga qo'llanadi — qisqartirish natijasida
    yasalgan variantga qayta qo'llanmaydi (yuqoridagi izohga qara)."""
    asl = str(kalit).lower().translate(_TIRNOQ_JADVALI)
    natija = {asl}

    # 1) To'liq shakl -> qisqartma (bitta variant, ketma-ket qo'llanadi).
    qisqa = asl
    for qolip, almash in _QISQARTIRISH:
        qisqa = qolip.sub(almash, qisqa)
    natija.add(qisqa)

    # 2) Asl kalitdagi qisqartmalarni to'liq shaklga yoyish. Noaniqlari
    #    uchun har bir variant alohida shox beradi.
    yoyilgan = {asl}
    for qolip, almashlar in _KENGAYTIRISH:
        yangi = set()
        for v in yoyilgan:
            for a in almashlar:
                y = qolip.sub(a, v)
                if y != v:
                    yangi.add(y)
        yoyilgan |= yangi
        if len(yoyilgan) > _VARIANT_CHEGARA:
            break
    natija |= yoyilgan

    # Bo'sh natija ATAYLAB filtrlanmaydi: "nol artikl" mashqlarida kalit
    # tire ("–") bo'lib, normalizatsiyadan keyin bo'sh satr qoladi — uni
    # tashlab yuborsak, o'sha savollar (bazada 54 ta) javobsiz qolardi.
    return {_norm(v) for v in natija}


_RIM_YOKI_RAQAM_PREFIKS = re.compile(r"^([ivxlcdm]+|\d+)[.\)]?\s+", re.IGNORECASE)

# 2026-09-03: Listening'ning "Plan/Map Labelling" savollarida variantlar
# asl kitobda "KOD + nom" ko'rinishida beriladi ("L Library",
# "SCR Student Common Room"), javob kaliti esa kodning O'ZI ("L", "SCR").
# Rim raqami qolipi bunday kodlarning faqat bir qismini ilib olardi
# (tasodifan "L" va "CL" rim raqamiga o'xshaydi, "MH"/"SR"/"SAR" esa
# yo'q) — natijada bir xil savol guruhida bir savol ishlab, boshqasi
# ishlamasdi. Kod — variantning boshidagi 1-4 harfli, TO'LIQ BOSH
# HARFLI so'z va u BARCHA variantlarda uchrashi SHART — aks holda
# oddiy matnli ro'yxatda ("A big room", "The main hall") birinchi
# variantning "A" so'zi kod deb qabul qilinib, kaliti "A" bo'lgan
# savolda talabaning "B" javobi ham to'g'ri hisoblanib ketardi.
_BOSH_HARFLI_KOD_PREFIKS = re.compile(r"^([A-Z]{1,4})[.\)]?\s+")


def _harf_va_matn_qabul(savol, qabul):
    """Variantli savolda HARF ham, VARIANT MATNI ham qabul qilinsin
    (2026-08-01).

    Nega kerak: asl kitobda moslashtirish savollariga talaba HARF yozadi
    ("Write the correct letter, A-F, in boxes 18-20"), lekin AI javob
    kalitini ba'zan harf ("A"), ba'zan to'liq matn ("Markus Heinrichs")
    qilib saqlagan — bir xil test ichida ham turlicha. Talaba to'g'ri
    javob bergani holda faqat shu nomuvofiqlik tufayli ball yo'qotmasligi
    uchun ikkala shakl ham qabul qilinadi.

    2026-09-03 qo'shildi: "Matching Headings" savollarida variant matni
    odatda RIM RAQAMI bilan boshlanadi ("iv Explaining the inductive
    method"), lekin AI javob kalitini ko'pincha shu rim raqamining O'ZINI
    ("iv") saqlagan — bu na to'liq variant matniga, na harfga teng
    kelmagani uchun yuqoridagi ikkita shart ham ishlamay, talaba to'g'ri
    harf yozgan holda ball yo'qotardi. Endi variantning boshidagi
    rim raqami/raqami alohida ajratib olinadi va kalit shu prefiks bilan
    solishtiriladi.

    `qabul` — normalizatsiya qilingan (kichik harf, trim) to'plam/ro'yxat.
    Qaytaradi: kengaytirilgan to'plam."""
    variantlar = savol.get("variantlar") or []
    if not variantlar:
        return set(qabul)
    kengaytirilgan = set(qabul)
    past_variantlar = [_norm(v) for v in variantlar]
    # Prefiks ASL (normallashtirilmagan) variantdan olinadi — bosh harfli
    # kodni aniqlash uchun registr kerak.
    kod_moslari = [_BOSH_HARFLI_KOD_PREFIKS.match(str(v).strip()) for v in variantlar]
    kodli_royxat = all(kod_moslari)
    prefikslar = []
    for kod_mos, v in zip(kod_moslari, past_variantlar):
        mos = _RIM_YOKI_RAQAM_PREFIKS.match(v) or (kod_mos if kodli_royxat else None)
        prefikslar.append(mos.group(1).lower() if mos else None)
    for t in qabul:
        # Kalit to'liq matn bo'lsa — mos harfni ham qabul qilamiz.
        if t in past_variantlar:
            idx = past_variantlar.index(t)
            if idx < len(HARFLAR):
                kengaytirilgan.add(HARFLAR[idx].lower())
        # Kalit harf bo'lsa — mos variant matnini ham qabul qilamiz.
        if len(t) == 1 and t.upper() in HARFLAR:
            idx = HARFLAR.index(t.upper())
            if idx < len(past_variantlar):
                kengaytirilgan.add(past_variantlar[idx])
        # Kalit variant matnining boshidagi kod/rim raqami/raqami bo'lsa —
        # mos to'liq matn VA harfni ham qabul qilamiz.
        #
        # 2026-09-03, HAQIQIY XATO: bu shart `elif` edi — kalit BITTA
        # harfli kod bo'lganda ("L" = Library) yuqoridagi "harf" shoxi
        # ishga tushib, bu shox HECH QACHON tekshirilmasdi. Natijada
        # talaba variant qutisidan ko'rgan to'liq matnni ("L Library")
        # yozsa, javob RAD ETILARDI. Shoxlar bir-birini almashtirmaydi —
        # ikkalasi ham qo'shimcha qabul shakli beradi, shuning uchun
        # mustaqil `if`.
        if t in prefikslar:
            idx = prefikslar.index(t)
            kengaytirilgan.add(past_variantlar[idx])
            if idx < len(HARFLAR):
                kengaytirilgan.add(HARFLAR[idx].lower())
    return kengaytirilgan


def javoblarni_tekshir(savollar, javoblar):
    """Talaba javoblarini tekshiradi (barcha turlar uchun yagona mexanizm).

    savollar: [{"savol": str, "variantlar": [...] (ixtiyoriy),
                "togri": str yoki [str, ...] (qabul qilinadigan variantlar)}]
    javoblar: [str, ...] — savollar tartibida talaba javoblari.

    Qaytaradi: {"ball": int, "jami": int, "natijalar": [bool, ...]}
    Solishtirish registr/bo'shliqqa sezgir emas.

    2026-07-27 — "Choose TWO letters" holati: bir xil matnli ketma-ket
    savollar bitta guruh sifatida, TARTIBGA BOG'LIQ BO'LMAGAN holda
    tekshiriladi. Avval 19-savolga "E", 20-savolga "B" yozgan talaba
    (kalitda 19="B", 20="E" bo'lsa) ikkala bandni ham yo'qotardi, holbuki
    ikkala harfni ham to'g'ri tanlagan. Endi javoblar to'plam sifatida
    solishtiriladi; qisman ball saqlanadi (2 tadan 1 tasi to'g'ri bo'lsa —
    1 ball, real IELTS'dagidek), takroriy javob esa faqat bir marta
    hisoblanadi.
    """

    norm = _norm

    natijalar = [False] * len(savollar)
    for bosh, uzunlik in kop_javobli_guruhlar(savollar):
        if uzunlik == 1:
            savol = savollar[bosh]
            # 2026-08-10, foydalanuvchi talabi: "erkin" savolda to'g'ri
            # javob YO'Q (masalan talaba o'z ismini yozadi) — qanday javob
            # yozilsa ham to'g'ri hisoblanadi, FAQAT bo'sh qoldirilmagan
            # bo'lishi tekshiriladi.
            if savol.get("erkin"):
                javob = javoblar[bosh] if bosh < len(javoblar) else ""
                natijalar[bosh] = bool(str(javob).strip())
                continue
            togri = savol.get("togri", "")
            qabul = togri if isinstance(togri, list) else [togri]
            qabul = [norm(t) for t in qabul if str(t).strip()]
            # 2026-08-17, foydalanuvchi talabi: "togri" bo'sh (AI hali
            # javobni bilmay, admin to'ldirishi kutilgan savol — qarang:
            # courses/blok_generatsiya.py) — bunday savolda talaba
            # yozgan HAR QANDAY (bo'sh bo'lmagan) javob to'g'ri
            # hisoblanadi, bo'sh qoldirilsa noto'g'ri (xuddi "erkin"
            # savol kabi). Avval bunday savol HECH QACHON to'g'ri
            # hisoblanmasdi — endi kalit hali kiritilmagan bo'lsa ham
            # talaba adolatsiz ball yo'qotmaydi.
            if not qabul:
                javob = javoblar[bosh] if bosh < len(javoblar) else ""
                natijalar[bosh] = bool(str(javob).strip())
                continue
            # Kengaytirilishidan OLDINGI ro'yxat — ko'p-katakchali savolda
            # "nechta javob kerak"ni aynan shundan bilamiz (kengaytirilgan
            # to'plamda harf/matn juftliklari qo'shilib, son buzilishi mumkin).
            asl_qabul_soni = len(set(qabul))
            # 2026-08-28: qisqartma variantlari (I'll <-> I will) SHU YERDA,
            # kalit tomonda qo'shiladi — normalizatorda emas (izohga qara).
            qabul = set().union(*(_qabul_variantlari(t) for t in qabul))
            qabul = _harf_va_matn_qabul(savol, qabul)
            javob = javoblar[bosh] if bosh < len(javoblar) else ""

            # 2026-08-15: BITTA savol ichida BIR NECHTA bo'sh joy
            # (masalan Reading "...pictures of both 33 ..... and ..... ").
            # Asl IELTS kalitida: "IN EITHER ORDER; BOTH REQUIRED FOR ONE
            # MARK" — ya'ni ikkala so'z ham kerak, TARTIB muhim emas,
            # ball esa BITTA. Frontend bunday savolda javobni RO'YXAT
            # qilib yuboradi (matnda `{{N}}` bir necha marta uchraganda),
            # oddiy savollarda esa avvalgidek satr — shuning uchun
            # ro'yxatmi-yo'qmi degan shaklning O'ZI ajratuvchi belgi
            # bo'lib xizmat qiladi (yangi maydon kerak emas, eski
            # testlar o'zgarishsiz ishlaydi).
            #
            # DIQQAT — semantika farqi: `togri` ro'yxat bo'lsa odatda
            # "shulardan HAR BIRI qabul qilinadi" (alternativalar)
            # degani. Bu yerda esa talaba javobi ham ro'yxat bo'lgani
            # uchun "HAMMASI kerak" deb talqin qilinadi.
            if isinstance(javob, list):
                berilgan = {norm(x) for x in javob if str(x).strip()}
                natijalar[bosh] = (
                    len(berilgan) == asl_qabul_soni
                    and berilgan <= set(qabul)
                )
                continue

            natijalar[bosh] = norm(javob) in qabul
            continue

        # Guruhdagi barcha to'g'ri javoblar bitta to'plamga yig'iladi
        qabul = set()
        for k in range(bosh, bosh + uzunlik):
            t = savollar[k]["togri"]
            for x in (t if isinstance(t, list) else [t]):
                if str(x).strip():
                    qabul |= _qabul_variantlari(x)
        if not qabul:
            continue
        qabul = _harf_va_matn_qabul(savollar[bosh], qabul)

        ishlatilgan = set()
        for k in range(bosh, bosh + uzunlik):
            javob = norm(javoblar[k]) if k < len(javoblar) else ""
            if javob and javob in qabul and javob not in ishlatilgan:
                natijalar[k] = True
                ishlatilgan.add(javob)

    return {
        "ball": sum(natijalar),
        "jami": len(savollar),
        "natijalar": natijalar,
    }


class Mashq(models.Model):
    """Bitta Listening yoki Reading mashqi — savollar JSON'da saqlanadi.

    Muhim (B3.2): "savollar" ichida to'g'ri javoblar bor — API orqali
    talabaga yuborishda "togri" maydonlari OLIB TASHLANISHI shart.
    """

    name = models.CharField(max_length=200)
    bolim = models.CharField(max_length=10, choices=Bolim.choices)
    tur = models.CharField(max_length=20, choices=Tur.choices)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="mashqlar"
    )
    korinish = models.CharField(
        max_length=10,
        choices=[("private", "Shaxsiy"), ("public", "Umumiy")],
        default="private",
    )
    sun_iy_intellekt_yaratgan = models.BooleanField(
        default=False,
        help_text=(
            "Mashq management-buyruq orqali (masalan wordapp_import, "
            "listening_yangi_mashqlar, writing_speaking_yangi_mashqlar) AI "
            "yordamida ommaviy yaratilganmi — talabaga 'SI tomonidan "
            "tuzilgan' belgisi ko'rsatish uchun. Admin UI orqali qo'lda "
            "kiritilgan mashqlarda False qoladi."
        ),
    )

    # Kontent (turi/bo'limiga qarab)
    matn = models.TextField(
        blank=True, help_text="Reading passage / Writing topshirig'i / Speaking savoli"
    )
    audio_fayl = models.FileField(upload_to="mashqlar/audio/", blank=True)
    rasm = models.ImageField(
        upload_to="mashqlar/rasm/", blank=True,
        help_text="Plan/Map/Diagram Labelling yoki Writing Task 1 grafigi uchun",
    )
    namuna_javob = models.TextField(
        blank=True, help_text="Writing/Speaking uchun namuna javob (ixtiyoriy)"
    )

    savollar = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Ro\'yxat: [{"savol": "...", "variantlar": ["A", "B"], '
            '"togri": "A"}] — "togri" ro\'yxat ham bo\'lishi mumkin. '
            "Writing/Speaking uchun bo'sh qoldirilishi mumkin."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Mashqlar"

    def clean(self):
        xatolar = {}

        if self.bolim and self.tur:
            ruxsat = BOLIM_TURLARI.get(self.bolim, [])
            if self.tur not in ruxsat:
                xatolar["tur"] = (
                    f"'{self.get_tur_display()}' turi "
                    f"{self.get_bolim_display()} bo'limida yo'q."
                )

        if self.bolim == Bolim.LISTENING and not self.audio_fayl:
            xatolar["audio_fayl"] = "Listening mashqi uchun audio majburiy."
        if self.bolim in (Bolim.READING, Bolim.WRITING, Bolim.SPEAKING) and not self.matn:
            xatolar["matn"] = "Matn (passage/topshiriq/savol) majburiy."
        if self.tur == Tur.MAP_LABELLING and not self.rasm:
            xatolar["rasm"] = "Labelling turi uchun rasm majburiy."

        if self.bolim in AVTO_BAHOLANADIGAN_BOLIMLAR:
            if not isinstance(self.savollar, list) or not self.savollar:
                xatolar["savollar"] = "Kamida bitta savoldan iborat ro'yxat bo'lishi kerak."
            else:
                for i, s in enumerate(self.savollar):
                    if not isinstance(s, dict) or "savol" not in s or "togri" not in s:
                        xatolar["savollar"] = (
                            f"{i + 1}-savolda 'savol' va 'togri' maydonlari majburiy."
                        )
                        break

        if xatolar:
            raise ValidationError(xatolar)

    def __str__(self):
        return f"{self.name} [{self.get_bolim_display()}/{self.get_tur_display()}]"


class MashqYechim(models.Model):
    """Talabaning mashqqa bergan javoblari va avtomatik natijasi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mashq_yechimlari",
        limit_choices_to={"role": "student"},
    )
    mashq = models.ForeignKey(
        Mashq, on_delete=models.CASCADE, related_name="yechimlar"
    )
    javoblar = models.JSONField()
    ball = models.PositiveIntegerField()
    jami = models.PositiveIntegerField()
    natijalar = models.JSONField(help_text="Har savol bo'yicha [true/false]")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Mashq yechimlari"
        ordering = ["-created_at"]

    @classmethod
    def yechish(cls, talaba, mashq, javoblar):
        """Javoblarni tekshirib, natijani saqlaydi."""
        natija = javoblarni_tekshir(mashq.savollar, javoblar)
        return cls.objects.create(
            talaba=talaba,
            mashq=mashq,
            javoblar=javoblar,
            ball=natija["ball"],
            jami=natija["jami"],
            natijalar=natija["natijalar"],
        )

    def __str__(self):
        return f"{self.talaba} — {self.mashq} — {self.ball}/{self.jami}"


def kunlik_limit_holati(talaba, bolim):
    """Talabaning bugungi limiti: har tur bo'yicha ruxsat/ishlatilgan/qolgan.

    Qoida (B4.1): har turdan kuniga 1 ta bepul. Tur ro'yxati
    BOLIM_TURLARI'dan olinadi — moslashuvchan.
    """
    import datetime

    bugun = datetime.date.today()
    ruxsat = 1

    holat = {}
    for tur in BOLIM_TURLARI[bolim]:
        ishlatilgan = MashqYechim.objects.filter(
            talaba=talaba,
            mashq__bolim=bolim,
            mashq__tur=tur,
            created_at__date=bugun,
        ).count()
        holat[str(tur)] = {
            "ruxsat": ruxsat,
            "ishlatilgan": ishlatilgan,
            "qolgan": max(0, ruxsat - ishlatilgan),
        }
    return holat


def korinadigan_mashqlar(user):
    """Foydalanuvchiga ko'rinadigan mashqlar.

    Markazga biriktirilmagan foydalanuvchi (masalan "oddiy foydalanuvchi")
    ham "hammaga ochiq" (`korinish="public"`) mashqlarni ko'radi — 9-faza
    qoidasi: Mashqlar Utmost talabasi bo'lmaganlar uchun ham ochiq.

    2026-08-14: ko'p-markazli "boshqa markazning public kontentini
    ochish" logikasi olib tashlandi — sayt bitta markaz rejimiga
    o'tkazilmoqda, ko'p-markazli qoidalar kerak emas.
    """
    if user.markaz_id is None:
        return Mashq.objects.filter(korinish="public")
    return Mashq.objects.filter(markaz_id=user.markaz_id)


class Manba(models.TextChoices):
    """Test qayerdan kelgan (2026-07-27).

    Ikkala tur ham bir xil `ImtihonTest` modelida saqlanadi — test yechish,
    baholash, mock yig'ish, `maxsus_format`, `pozitsiya`, audio va R2
    mexanizmlari umumiy, faqat ro'yxatlar shu maydon bo'yicha ajratiladi:
      * ADMIN — admin/owner qo'lda yuklagan haqiqiy testlar ("IELTS testlari")
      * AI    — to'liq AI tomonidan generatsiya qilingan ("AI mashqlari")
    """

    ADMIN = "admin", "Admin yuklagan"
    AI = "ai", "AI generatsiya qilgan"


class TestPapkasi(models.Model):
    """Testlarni guruhlash uchun papka (2026-08-01, foydalanuvchi talabi).

    2026-08-11 (kech): CHUQURLIK 2 gacha kengaytirildi (foydalanuvchi
    talabi — "papkalarni ichiga yana papka qo'shish imkonini berish
    kerak, ikkinchi darajadagi papkani ichiga papka qo'shib bo'lmaydi").
    `parent` — self FK, faqat 1-DARAJALI (parent=None) papka ichiga
    ichki (2-darajali) papka qo'shilishi mumkin, ichki papkaning o'ziga
    yana ichki papka QO'SHILMAYDI — bu `clean()`da majburlanadi va
    `TestPapkaBoshqaruvView.post`da ham view darajasida tekshiriladi.

    2-darajali papka — Mock test yig'ish uchun MO'LJALLANGAN: unga har
    bo'limdan (reading/listening/writing/speaking) FAQAT BITTADAN test
    qo'shish mumkin (`ImtihonBoshqaruvDetailView.patch`da majburlanadi),
    to'lgach "Mock sifatida boshlash" bilan shu 4 (yoki kamroq) testdan
    `ImtihonMock` yaratiladi/qayta ishlatiladi (`PapkadanMockYaratishView`).

    2026-08-11: `bolim` maydoni OLIB TASHLANDI (foydalanuvchi talabi:
    "IELTS Testlari bo'limidagi papkalarni birlashtirish"). Avval har
    papka BITTA bo'limga tegishli edi — masalan "Cambridge 17 Test 1"
    to'plamini kiritish uchun Reading/Listening/Writing/Speaking'ning
    HAR BIRIDA alohida, bir xil nomli papka yaratish kerak bo'lardi.
    Endi bitta papka barcha bo'lim testlarini birga saqlaydi; admin
    biror bo'limni tanlaganda esa (masalan Reading) SHU PAPKA ICHIDAGI
    faqat o'sha bo'lim testlari ko'rinadi — bu filtr backendda emas,
    frontendda amalga oshadi (`ImtihonBoshqarish.jsx`: bo'lim bo'yicha
    olingan test ro'yxati va papka ro'yxati kesishtiriladi).

    Papka hamon BITTA manbaga (admin — "IELTS testlari", ai — "AI
    mashqlari") tegishli — bu ikkisi admin panelida alohida tab, aralashib
    ketmasligi kerak.
    """

    nomi = models.CharField(max_length=120)
    manba = models.CharField(max_length=10, choices=Manba.choices, default=Manba.ADMIN)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="test_papkalari"
    )
    # Faqat 1-darajali papka (parent=None) berilishi mumkin — CASCADE:
    # tashqi papka o'chsa, ichidagi 2-darajali papkalar ham o'chadi
    # (ular tashqarisiz mustaqil ma'no bermaydi, testlar esa ularning
    # ichida bo'lsa ham SET_NULL orqali baribir saqlanib qoladi).
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="ichki_papkalar",
        help_text="Faqat 1-darajali papkaga bog'lanadi — ichki papkaning o'ziga yana ichki papka bo'lmaydi.",
    )
    tartib = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tartib", "nomi"]
        verbose_name_plural = "Test papkalari"

    def __str__(self):
        return f"{self.nomi} [{self.get_manba_display()}]"

    def clean(self):
        super().clean()
        if self.parent_id and self.parent.parent_id:
            raise ValidationError(
                "Ichki papkaning ichiga yana ichki papka qo'shib bo'lmaydi — chuqurlik 2 bilan chegaralangan."
            )


class ImtihonTest(models.Model):
    """To'liq IELTS testi (masalan Cambridge uslubidagi Reading/Listening Test)
    — bir nechta TestQismi'dan iborat, uzluksiz raqamlangan yagona imtihon.

    Mavjud Mashq bankidan (bitta passage/audio = alohida kichik mashq)
    mustaqil — kunlik limit tizimiga bog'lanmaydi (10/11-faza, 2026-07-19).
    """

    name = models.CharField(max_length=200)
    bolim = models.CharField(max_length=10, choices=Bolim.choices)
    manba = models.CharField(
        max_length=10, choices=Manba.choices, default=Manba.ADMIN,
        help_text="Testni kim yaratgan — admin (IELTS testlari) yoki AI (AI mashqlari)",
    )
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="imtihon_testlari"
    )
    # Papka O'CHIRILSA testlar YO'QOLMAYDI — faqat papkasiz holatga
    # qaytadi (SET_NULL). Test qimmatli kontent, papka esa shunchaki
    # tartibga solish vositasi.
    papka = models.ForeignKey(
        "TestPapkasi", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testlar",
    )
    korinish = models.CharField(
        max_length=10,
        choices=[("private", "Shaxsiy"), ("public", "Umumiy")],
        default="private",
    )
    yaratuvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="yaratgan_imtihon_testlari",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Imtihon testlari"

    def __str__(self):
        return f"{self.name} [{self.get_bolim_display()}]"


class TestQismi(models.Model):
    """Bitta testning bir qismi (Reading passage / Listening audio bo'lagi)."""

    test = models.ForeignKey(ImtihonTest, on_delete=models.CASCADE, related_name="qismlar")
    tartib = models.PositiveSmallIntegerField()
    sarlavha = models.CharField(max_length=200, blank=True, help_text="masalan 'Passage 1'")
    yoriqnoma = models.CharField(
        max_length=300, blank=True,
        help_text="masalan 'You should spend about 20 minutes on Questions 1-13.'",
    )
    matn = models.TextField(
        blank=True, help_text="Reading passage matni / Writing-Speaking uchun savol-topshiriq matni"
    )
    tur = models.CharField(
        max_length=20, choices=Tur.choices, blank=True,
        help_text="Faqat Writing/Speaking uchun: task1/task2/part1/part2/part3. Reading/Listening'da savol turlari 'savollar' ichida, bu yerda bo'sh qoladi.",
    )
    audio_fayl = models.FileField(upload_to="imtihon/audio/", blank=True)
    rasm = models.ImageField(
        upload_to="imtihon/rasm/", blank=True,
        help_text="Plan/Map/Diagram Labelling yoki Writing Task 1 grafigi uchun",
    )
    savollar = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Reading/Listening uchun ro\'yxat: [{"savol": "...", "tur": "multiple_choice", '
            '"variantlar": ["A", "B"], "togri": "A", "guruh_boshi": "Questions 1-7" (ixtiyoriy)}]. '
            "Writing/Speaking'da bo'sh qoladi — javob AI orqali baholanadi."
        ),
    )
    maxsus_format = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Ixtiyoriy — Table/Note/Summary/Flow-chart Completion uchun, javoblarni "
            "oddiy ro'yxat o'rniga asl kitobdagidek jadval/blok-sxema ko'rinishida "
            "ko'rsatish (2026-07-24). Grading'ga ta'sir qilmaydi — faqat ko'rinish "
            "(render) uchun, javob/to'g'ri javob hamon 'savollar'da saqlanadi. "
            'Format: {"tur": "jadval", "sarlavha": "...", "ustunlar": ["...", "..."], '
            '"qatorlar": [["katak matni {{1}} bilan", "...", "..."], ...]} yoki '
            '{"tur": "oqim", "sarlavha": "...", "qadamlar": ["matn {{26}} bilan", "..."]}. '
            "{{n}} — o'sha savolning testdagi UMUMIY (uzluksiz) raqami, shu joyda "
            "kichik input avtomatik chiqadi."
        ),
    )

    class Meta:
        ordering = ["tartib"]
        unique_together = [("test", "tartib")]
        verbose_name_plural = "Test qismlari"

    def __str__(self):
        return f"{self.test.name} — {self.sarlavha or self.tur or self.tartib}"


class TestYechim(models.Model):
    """Talabaning to'liq testga bergan javoblari va natijasi (flat, uzluksiz)."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="imtihon_yechimlari",
        limit_choices_to={"role": "student"},
    )
    test = models.ForeignKey(ImtihonTest, on_delete=models.CASCADE, related_name="yechimlar")
    javoblar = models.JSONField()
    ball = models.PositiveIntegerField()
    jami = models.PositiveIntegerField()
    natijalar = models.JSONField()
    band = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Imtihon yechimlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — {self.test} — {self.ball}/{self.jami} (Band {self.band})"


class ImtihonMock(models.Model):
    """To'liq IELTS mock imtihoni — 4 ta mustaqil ImtihonTest'ni (Listening/
    Reading/Writing/Speaking) bitta yaxlit sessiyaga bog'laydi. Talaba ketma-
    ket o'tadi, oxirida 4 bo'lim bandidan Overall Band hisoblanadi
    (2026-07-25). Odatda 4-papkali ZIP yuklashda avtomatik yaratiladi."""

    name = models.CharField(max_length=200)
    markaz = models.ForeignKey(
        "accounts.Markaz", on_delete=models.CASCADE, related_name="imtihon_moklari"
    )
    # Mock ham o'z bo'limida ko'rinishi uchun (AI mocki "AI mashqlari"da,
    # admin mocki "IELTS testlari"da) — testlar bilan bir xil ajratish.
    manba = models.CharField(
        max_length=10, choices=Manba.choices, default=Manba.ADMIN,
        help_text="Mock qaysi bo'limda ko'rinadi — admin yoki AI",
    )
    listening = models.ForeignKey(
        ImtihonTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reading = models.ForeignKey(
        ImtihonTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    writing = models.ForeignKey(
        ImtihonTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    speaking = models.ForeignKey(
        ImtihonTest, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # 2026-08-11: 2-darajali papkadan "Mock sifatida boshlash" tugmasi bilan
    # avtomatik yaratilgan/qayta ishlatilgan mocklar shu orqali bog'lanadi
    # (`PapkadanMockYaratishView`, idempotent — get_or_create papka bo'yicha).
    # `unique=True` — bitta papkaga bitta mock, qayta bosilganda YANGISI
    # emas, MAVJUDI yangilanadi (testlar almashtirilgan bo'lishi mumkin).
    papka = models.OneToOneField(
        "TestPapkasi", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mock",
    )
    korinish = models.CharField(
        max_length=10, choices=[("private", "Shaxsiy"), ("public", "Umumiy")], default="private"
    )
    yaratuvchi = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    BOLIM_TARTIBI = ["listening", "reading", "writing", "speaking"]

    class Meta:
        verbose_name_plural = "Mock imtihonlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def bolimlar(self):
        """[(bolim_nomi, ImtihonTest), ...] — faqat mavjud (o'chirilmagan) bo'limlar."""
        return [(b, getattr(self, b)) for b in self.BOLIM_TARTIBI if getattr(self, b)]


class MockYechim(models.Model):
    """Talabaning bitta mock imtihoniga urinishi — 4 bo'lim natijasi bosqichma-
    bosqich to'planadi (har bo'lim tugagach tegishli maydon to'ldiriladi),
    hammasi tugagach Overall Band hisoblanadi."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_yechimlari",
        limit_choices_to={"role": "student"},
    )
    mock = models.ForeignKey(ImtihonMock, on_delete=models.CASCADE, related_name="yechimlar")
    listening_yechim = models.ForeignKey(
        TestYechim, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reading_yechim = models.ForeignKey(
        TestYechim, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    writing_band = models.FloatField(null=True, blank=True)
    speaking_band = models.FloatField(null=True, blank=True)
    overall_band = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tugallandi_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Mock yechimlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.talaba} — {self.mock} (Overall {self.overall_band})"

    def band_royxati(self):
        bandlar = []
        if self.listening_yechim and self.listening_yechim.band is not None:
            bandlar.append(float(self.listening_yechim.band))
        if self.reading_yechim and self.reading_yechim.band is not None:
            bandlar.append(float(self.reading_yechim.band))
        if self.writing_band is not None:
            bandlar.append(self.writing_band)
        if self.speaking_band is not None:
            bandlar.append(self.speaking_band)
        return bandlar

    def hammasi_tugadimi(self, mock):
        kerakli = [b for b, t in mock.bolimlar()]
        holat = {
            "listening": self.listening_yechim_id is not None,
            "reading": self.reading_yechim_id is not None,
            "writing": self.writing_band is not None,
            "speaking": self.speaking_band is not None,
        }
        return all(holat[b] for b in kerakli)


# Ommaviy IELTS tayyorgarlik manbalaridan olingan TAXMINIY xom ball -> band
# jadvali (Academic, 40 savol asosida). Rasmiy Cambridge/IDP konvertatsiya
# jadvali bilan ozgina farq qilishi mumkin — aniq rasmiy manba emas.
_READING_BAND_JADVALI = [
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0), (27, 6.5),
    (23, 6.0), (19, 5.5), (15, 5.0), (13, 4.5), (10, 4.0), (8, 3.5),
    (6, 3.0), (4, 2.5),
]
_LISTENING_BAND_JADVALI = [
    (39, 9.0), (37, 8.5), (35, 8.0), (32, 7.5), (30, 7.0), (26, 6.5),
    (23, 6.0), (18, 5.5), (16, 5.0), (13, 4.5), (11, 4.0), (8, 3.5),
    (6, 3.0), (4, 2.5),
]


def band_hisobla(ball, jami, bolim):
    """Xom ballni (ball/jami) taxminiy IELTS bandiga aylantiradi.

    jami 40'dan farq qilsa, 40 savolga proporsional moslashtiriladi.
    """
    if jami <= 0:
        return None
    ball40 = round(ball / jami * 40)
    jadval = _READING_BAND_JADVALI if bolim == Bolim.READING else _LISTENING_BAND_JADVALI
    for chegara, band in jadval:
        if ball40 >= chegara:
            return band
    return 2.0


def korinadigan_testlar(user, manba=None):
    """Foydalanuvchiga ko'rinadigan to'liq testlar.

    Platforma bitta markaz rejimida ishlaydi (REJA.md) — shuning uchun
    markaz/korinish bo'yicha filtrlash foyda bermaydi, faqat guruhga hali
    qo'shilmagan (`markaz=None`, masalan Google orqali endigina ro'yxatdan
    o'tgan) talabani noto'g'ri barcha testlardan mahrum qilardi. Endi
    "oddiy foydalanuvchi" (Utmost talabasi emas) dan boshqa barcha
    autentifikatsiyalangan foydalanuvchi (talaba/o'qituvchi/admin/owner)
    barcha testlarni ko'radi (2026-07-21).

    2026-07-27: `manba` berilsa — faqat o'sha manbadagi testlar ("IELTS
    testlari" bo'limi admin testlarini, "AI mashqlari" AI testlarini
    ko'rsatadi). Berilmasa — hammasi (ID orqali ochish, mock ichidan
    yuklash va h.k. uchun).

    2026-07-27 (2): "oddiy foydalanuvchi" (Utmost talabasi emas) endi
    butunlay mahrum emas — unga AI generatsiya qilgan testlar OCHIQ, admin
    yuklagan (Cambridge va h.k.) testlar esa yopiq. Avval "Namunaviy
    mashqlar" uning yagona bo'limi edi, u yopilgach hech narsa qolmagandi.
    """
    qs = (
        ImtihonTest.objects.filter(manba=Manba.AI)
        if user.role == "oddiy"
        else ImtihonTest.objects.all()
    )
    return qs.filter(manba=manba) if manba else qs


def korinadigan_moklar(user, manba=None):
    """`korinadigan_testlar` bilan bir xil qoida — bitta markaz rejimi,
    "oddiy foydalanuvchi" faqat AI mocklarini ko'radi."""
    qs = (
        ImtihonMock.objects.filter(manba=Manba.AI)
        if user.role == "oddiy"
        else ImtihonMock.objects.all()
    )
    return qs.filter(manba=manba) if manba else qs
