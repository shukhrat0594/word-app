"""CDI uslubidagi IELTS Listening HTML'ini saytning IELTS testiga o'giradi
(2026-10-22, Shuhrat: "IELTS CDI Materials" kanali eksportidagi testlar).

Kanaldagi HTML'larda javob kaliti sahifa skriptida ochiq yozilgan
(`correctAnswers`) — o'quvchi "sahifa kodi"dan ko'ra oladi. Bu yerda savollar
va kalit `_test_yarat` JSON formatiga o'tkaziladi: saytda kalit serverda
qoladi, o'quvchiga `togri`siz yuboriladi (`savollar_talaba_uchun`).

Shablon ("Full Listening CDI"): har qism — `div.section` (h2 "Part N ...").
Savollar:
  * `input[type=text][id=qN]` — bo'sh joy (fill_blanks); `maxlength=1` bo'lsa
    oldingi qutidagi A–H variantlardan harf (matching);
  * `input[type=radio][name=qN]` — bitta harf (multiple_choice);
  * `input[type=checkbox][name=qN]` — "Choose TWO": ikki KETMA-KET savol
    (N va N+1) bir xil matn bilan — sayt ularni tartibsiz to'plam sifatida
    baholaydi (`javoblarni_tekshir`). HTML'dagi "hammasini belgilasa ham
    to'liq ball" xatosi saytda yo'q: har savolga bitta harf tanlanadi.

Boshqa shablon kelsa — `HtmlXatosi` bilan to'xtaydi (jim noto'g'ri test
yasamaydi): `tekshir` 1..N uzluksiz raqam, har savolda kalit, harfli kalit
variantlar ichida ekanini talab qiladi."""

import re

from lxml import html as lxml_html


class HtmlXatosi(ValueError):
    """HTML shablonga mos emas yoki kalit/savollar to'liq emas."""


BOSH_JOY = "___"
_BELGILAR = str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'", "\xa0": " "})
# "A air B ash ..." yoki "A – Obtaining permission B – ..." (keyingi harfdan
# keyin tire bo'lsin yoki kichik harf bilan so'z boshlansin).
_VARIANT = re.compile(r"(?:^|\s)([A-H])\s*(?:[-:.)]\s*)?(.+?)(?=\s+[A-H](?:\s*[-:.)]\s*|\s+(?=[a-z]))|$)")


def _toza(matn):
    matn = re.sub(r"\s+", " ", (matn or "").translate(_BELGILAR)).strip()
    return re.sub(r"\s+([).,;:?!])", r"\1", matn)


def kalitni_ol(sahifa):
    """Skriptdagi `correctAnswers = {q1: ["..."], ...}` — {raqam: [javoblar]}."""
    blok = re.search(r"correctAnswers\s*=\s*\{(.*?)\}\s*;", sahifa, re.S)
    if not blok:
        raise HtmlXatosi("Javob kaliti (correctAnswers) topilmadi")
    kalit = {}
    for m in re.finditer(r"q(\d+)\s*:\s*\[([^\]]*)\]", blok.group(1)):
        javoblar = [_toza(j) for j in re.findall(r"""["']([^"']*)["']""", m.group(2))]
        kalit[int(m.group(1))] = [j for j in javoblar if j]
    return kalit


def _matn_bosh_joy_bilan(el, maydon):
    """Element matni, bo'sh joy o'rnida "___". Satrda savol raqami belgisi
    (`q-badge`) bo'lsa — joy o'sha belgi turgan yerda (maydon esa ba'zan
    satr oxirida turadi: "reluctant to (7) )" + maydon); bo'lmasa — maydon o'rnida."""
    qismlar = []
    belgili = bool(el.xpath(".//*[contains(@class, 'q-badge')]"))

    def yur(e):
        if "q-badge" in (e.get("class") or "") or (e is maydon and not belgili):
            qismlar.append(f" {BOSH_JOY} ")
        elif e.tag == "br":
            qismlar.append(" ")
        elif e.tag != "input":
            qismlar.append(e.text or "")
            for bola in e:
                yur(bola)
        if e is not el:
            qismlar.append(e.tail or "")

    yur(el)
    matn = re.sub(rf"{BOSH_JOY}(\s*{BOSH_JOY})+", BOSH_JOY, _toza("".join(qismlar)))
    return re.sub(r"^(?:\d+\.|[•·])\s*", "", matn)


def _kontekst(maydon):
    """Maydon tegishli satr: form-row / li / div.question / p / label."""
    for ota in maydon.iterancestors():
        sinf = ota.get("class") or ""
        if ota.tag in ("li", "p", "label") or "form-row" in sinf or "question" in sinf:
            return ota
        if "section" in sinf:
            break
    return maydon.getparent()


def _variantlar_qutisi(maydon, bolim):
    """Maydondan oldingi eng yaqin "A ... B ... C ..." qutisi — [(harf, matn)]."""
    topilgan = None
    for el in bolim.iter("p", "div"):
        if el is maydon or maydon in el.iterancestors():
            continue
        if el.sourceline and maydon.sourceline and el.sourceline > maydon.sourceline:
            break
        juft = _VARIANT.findall(_toza(el.text_content()))
        if len(juft) >= 3 and [h for h, _ in juft] == [chr(65 + i) for i in range(len(juft))]:
            topilgan = [(h, t.strip()) for h, t in juft]
    return topilgan


def _guruh_korsatmasi(maydon, bolim):
    """Maydondan oldingi eng yaqin "Questions a-b" va yo'riqnoma."""
    boshi, korsatma = None, None
    for x in bolim.iter("h2", "h3", "p"):
        if x.sourceline and maydon.sourceline and x.sourceline >= maydon.sourceline:
            break
        matn = _toza(x.text_content())
        mos = re.search(r"Questions?\s+(\d+\s*-\s*\d+)", matn, re.I)
        if x.tag in ("h2", "h3") and mos:
            boshi, korsatma = f"Questions {mos.group(1).replace(' ', '')}", None
        if "instructions" in (x.get("class") or ""):
            if mos and matn.lower().startswith("questions"):
                boshi = f"Questions {mos.group(1).replace(' ', '')}"
                matn = _toza(matn[mos.end():])
            korsatma = matn
    return boshi or "", korsatma or ""


def _savol_oldi_matni(label):
    """Radio guruhi: savol matni — konteynerdagi birinchi variantgacha bo'lgan qism."""
    ota = label.getparent()
    qismlar = [ota.text or ""]
    for b in ota:
        if b.tag == "label":
            break
        qismlar.append(" " if b.tag == "br" else b.text_content())
        qismlar.append(b.tail or "")
    return re.sub(r"^\d+\.\s*", "", _toza("".join(qismlar)))


def _savol(raqam, tur, savol, kalit, variantlar, boshi, korsatma):
    return {"raqam": raqam, "tur": tur, "savol": savol, "togri": kalit, "variantlar": variantlar,
            "guruh_boshi": boshi, "guruh_korsatma": korsatma}


def html_dan_test(sahifa, nom=None):
    """HTML matni -> `_test_yarat` uchun dict (bolim=listening, korinish=private)."""
    kalit = kalitni_ol(sahifa)
    hujjat = lxml_html.fromstring(sahifa)
    bolimlar = hujjat.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' section ')]")
    if not bolimlar:
        raise HtmlXatosi("Qismlar (div.section) topilmadi")

    qismlar = []
    for tartib, bolim in enumerate(bolimlar, start=1):
        h2 = bolim.find(".//h2")
        mos = re.match(r"(part\s*\d+)", _toza(h2.text_content()) if h2 is not None else "", re.I)
        sarlavha = mos.group(1).title() if mos else f"Part {tartib}"
        savollar, korilgan = [], set()
        for maydon in bolim.iter("input"):
            tur = (maydon.get("type") or "text").lower()
            belgi = maydon.get("id") if tur == "text" else maydon.get("name")
            mos = re.fullmatch(r"q(\d+)", belgi or "")
            if not mos or belgi in korilgan:
                continue
            korilgan.add(belgi)
            raqam = int(mos.group(1))
            boshi, korsatma = _guruh_korsatmasi(maydon, bolim)
            javob = kalit.get(raqam, [])

            if tur == "text":
                matn = _matn_bosh_joy_bilan(_kontekst(maydon), maydon)
                quti = _variantlar_qutisi(maydon, bolim) if maydon.get("maxlength") == "1" else None
                if quti:
                    # "Observing lessons: ___" — sarlavha+joy, joy kerak emas (harf tanlovi
                    # yonida chiqadi); oqim sxemasidagi "Remove ___" esa o'zgarmaydi.
                    matn = re.sub(rf"\s*:\s*{BOSH_JOY}$", "", matn)
                    savollar.append(_savol(raqam, "matching", matn, [j.upper() for j in javob],
                                           [f"{h} {t}" for h, t in quti], boshi, korsatma))
                else:
                    savollar.append(_savol(raqam, "fill_blanks", matn, javob, [], boshi, korsatma))
                continue

            guruh = [x for x in bolim.iter("input") if x.get("name") == belgi]
            variantlar = [re.sub(r"^[A-H][.)]?\s+", "", _toza(x.getparent().text_content())) for x in guruh]
            if tur == "radio":
                savollar.append(_savol(raqam, "multiple_choice", _savol_oldi_matni(guruh[0].getparent()),
                                       [j.upper() for j in javob], variantlar, boshi, korsatma))
            elif tur == "checkbox":
                savol_el = guruh[0].getparent().getprevious()
                while savol_el is not None and savol_el.tag not in ("p", "h3", "h4"):
                    savol_el = savol_el.getprevious()
                if len(javob) < 2:
                    raise HtmlXatosi(f"{raqam}-savol 'Choose TWO', lekin kalitda {len(javob)} ta javob")
                for i, harf in enumerate(javob):
                    savollar.append(_savol(raqam + i, "multiple_choice",
                                           _toza(savol_el.text_content()) if savol_el is not None else "",
                                           [harf.upper()], variantlar, boshi, korsatma))

        savollar.sort(key=lambda s: s["raqam"])
        # Guruh sarlavhasi va yo'riqnomasi faqat guruhning BIRINCHI savolida
        # (Cambridge testlaridagidek) — aks holda frontend har savol oldida takrorlaydi.
        oldingi = None
        for s in savollar:
            guruh = (s["guruh_boshi"], s["guruh_korsatma"])
            if guruh == oldingi:
                s["guruh_boshi"] = s["guruh_korsatma"] = ""
            oldingi = guruh
        qismlar.append({"tartib": tartib, "sarlavha": sarlavha, "yoriqnoma": "", "savollar": savollar})

    if nom is None:
        h3 = bolimlar[0].find(".//h3")
        nom = "CDI Listening — " + (_toza(h3.text_content()) if h3 is not None else "test")
    test = {"name": nom, "bolim": "listening", "korinish": "private", "qismlar": qismlar}
    tekshir(test)
    for q in test["qismlar"]:
        for s in q["savollar"]:
            del s["raqam"]
    return test


def tekshir(test):
    """Raqamlar 1..N uzluksiz, har savolda kalit va matn, harfli kalit variantlar ichida."""
    savollar = [s for q in test["qismlar"] for s in q["savollar"]]
    raqamlar = [s["raqam"] for s in savollar]
    if not raqamlar or raqamlar != list(range(1, len(raqamlar) + 1)):
        raise HtmlXatosi(f"Savol raqamlari 1 dan uzluksiz emas: {raqamlar}")
    for s in savollar:
        if not s["togri"]:
            raise HtmlXatosi(f"{s['raqam']}-savolda javob kaliti yo'q")
        if not s["savol"]:
            raise HtmlXatosi(f"{s['raqam']}-savol matni bo'sh")
        if s["variantlar"]:
            harflar = {chr(65 + i) for i in range(len(s["variantlar"]))}
            if not set(s["togri"]) <= harflar:
                raise HtmlXatosi(f"{s['raqam']}-savol kaliti {s['togri']} variantlarda yo'q")
