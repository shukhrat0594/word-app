"""Elementary: javob kaliti noto'g'ri bo'lgan mashqlarni tuzatish.

2026-10-10, Isroil (guruh TZ #153/#157): Elementary WB Unit 2,
"Complete the words with -or or -er." — talaba qanday to'g'ri javob
yozmasin ("er", "waiter"), hammasi noto'g'ri deb ko'rsatilardi.

Prod kontentini repodan ko'rib bo'lmaydi, shuning uchun kalit BOR
qiymatiga tayanmasdan qaytadan quriladi: har bo'sh joyning oldidagi
so'z o'zagi ("2 wait") bo'yicha qo'shimcha aniqlanadi va kalit
[qo'shimcha, to'liq so'z] bo'ladi — talaba "er" ham, "waiter" ham yozsa
to'g'ri. Shu bilan `savol_idx` siljigan bo'lsa ham tuzaladi (kalit aynan
o'sha input ko'rsatayotgan so'zdan olinadi).

Naqsh `courses/intermediate_tuzatish.py` dan: mashq ID bo'yicha emas,
ko'rsatma MATNI bo'yicha topiladi; tuzatish IDEMPOTENT.
"""

import re

KORSATMA = "complete the words with -or or -er"

# So'z o'zagi -> to'g'ri qo'shimcha (kitobdagi 1-10 bandlar).
QOSHIMCHALAR = {
    "football": "er",
    "wait": "er",
    "act": "or",
    "hairdress": "er",
    "profess": "or",
    "doct": "or",
    "manag": "er",
    "police offic": "er",
    "interpret": "er",
    "film direct": "or",
}


def _kalit(matn):
    return re.sub(r"[^a-z]", "", str(matn).lower())


def _ozak(matn):
    """Matn oxiridagi ma'lum so'z o'zagi ("2 wait" -> "wait") yoki None.
    Uzunroq o'zak birinchi tekshiriladi ("police offic" > "offic")."""
    k = _kalit(matn)
    for ozak in sorted(QOSHIMCHALAR, key=len, reverse=True):
        if k.endswith(_kalit(ozak)):
            return ozak
    return None


def _matnlar(obj):
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


def _bolaklar_royxatlari(obj):
    """Blok ichidagi barcha `bolaklar` ro'yxatlari (chuqurlikda)."""
    natija = []
    if isinstance(obj, dict):
        if isinstance(obj.get("bolaklar"), list):
            natija.append(obj["bolaklar"])
        for qiymat in obj.values():
            natija.extend(_bolaklar_royxatlari(qiymat))
    elif isinstance(obj, list):
        for qiymat in obj:
            natija.extend(_bolaklar_royxatlari(qiymat))
    return natija


def _mashq_oraligi(bloklar):
    """-or/-er ko'rsatmasidan keyingi bloklar — keyingi ko'rsatmagacha.

    Bitta KursMashq — kitobning butun sahifasi (bir nechta mashq). Faqat
    shu mashqning bloklari olinadi: aks holda boshqa mashqdagi "... wait
    ___" kabi bo'sh joyning kaliti ham "er"ga almashib ketardi."""
    for i, blok in enumerate(bloklar):
        if not isinstance(blok, dict) or blok.get("tur") != "korsatma":
            continue
        if not any(KORSATMA in m.lower() for m in _matnlar(blok)):
            continue
        oxiri = i + 1
        while oxiri < len(bloklar) and not (
            isinstance(bloklar[oxiri], dict) and bloklar[oxiri].get("tur") == "korsatma"
        ):
            oxiri += 1
        return bloklar[i + 1:oxiri], bloklar[:i + 1] + bloklar[oxiri:]
    return [], bloklar


def _band_idxlar(bloklar):
    return {
        b.get("savol_idx")
        for bolaklar in _bolaklar_royxatlari(bloklar)
        for b in bolaklar
        if isinstance(b, dict) and b.get("bosh_joy")
    }


def or_er_kalitlari(mashq):
    """Bitta mashqning kalitlarini tuzatadi. Qaytaradi: o'zgargan savollar soni."""
    savollar = mashq.savollar or []
    ichki, tashqi = _mashq_oraligi(mashq.bloklar or [])
    # Siljigan savol_idx boshqa mashq bo'sh joyi bilan UMUMIY bo'lsa — uning
    # kalitini buzmaslik uchun bu bo'sh joyga yangi savol ochiladi.
    band = _band_idxlar(tashqi)
    ozgardi = 0
    bloklar_ozgardi = False
    for bolaklar in _bolaklar_royxatlari(ichki):
        oldingi = ""
        for b in bolaklar:
            if not isinstance(b, dict):
                continue
            if not b.get("bosh_joy"):
                oldingi = str(b.get("matn", ""))
                continue
            idx = b.get("savol_idx")
            if not isinstance(idx, int) or not 0 <= idx < len(savollar):
                continue
            ozak = _ozak(oldingi) or _ozak(savollar[idx].get("savol", ""))
            oldingi = ""
            if not ozak:
                continue
            qosh = QOSHIMCHALAR[ozak]
            yangi = [qosh, ozak + qosh]
            if idx in band:
                savollar.append({"savol": ozak, "togri": yangi})
                b["savol_idx"] = len(savollar) - 1
                bloklar_ozgardi = True
                ozgardi += 1
                continue
            band.add(idx)
            if savollar[idx].get("togri") != yangi:
                savollar[idx]["togri"] = yangi
                ozgardi += 1
    if ozgardi:
        mashq.savollar = savollar
        mashq.save(update_fields=["savollar", "bloklar"] if bloklar_ozgardi else ["savollar"])
    return ozgardi


def tuzat(KursTugun, KursMashq):
    """Hisobot: [(izoh, bajarildimi), ...]."""
    hisobot = []
    topildi = False
    for mashq in KursMashq.objects.filter(bloklar__icontains="-or or -er"):
        if not any(KORSATMA in m.lower() for m in _matnlar(mashq.bloklar or [])):
            continue
        topildi = True
        soni = or_er_kalitlari(mashq)
        hisobot.append((f"WB U2 -or/-er (mashq {mashq.pk}): {soni} kalit", bool(soni)))
    if not topildi:
        hisobot.append(("WB U2 -or/-er", False))
    return hisobot
