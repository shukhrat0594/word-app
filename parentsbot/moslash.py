"""Ota-onani farzandiga moslash: telefon, ism, tug'ilgan sana.

Qoidalar (Shuhrat, 2026-10-04):
- telefon mos kelsa — ulanadi (ota-ona kontaktni O'Z hisobidan ulashgan bo'lishi shart —
  bu `bot.py`da tekshiriladi);
- mos kelmasa — ism-familiya VA tug'ilgan sana ikkalasi aniq BITTA o'quvchiga mos kelsa;
- aks holda — adminlarga so'rov. Ism yumshoq taqqoslanadi (harf registri, apostrof,
  lotin/kirill, ism-familiya tartibi hisobga olinmaydi).
"""

import difflib
import re
from datetime import date

from django.contrib.auth import get_user_model

User = get_user_model()

_KIRILL = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "s", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g",
    "ҳ": "h",
}
_APOSTROFLAR = "'`’ʻʼ‘´"


def telefon_kaliti(xom):
    """Telefonning oxirgi 9 raqami (998 90 123 45 67 -> 901234567); 9 raqamdan kam bo'lsa — ''."""
    raqamlar = re.sub(r"\D", "", xom or "")
    return raqamlar[-9:] if len(raqamlar) >= 9 else ""


def ism_kaliti(xom):
    """Ism-familiya uchun taqqoslash kaliti: kirill->lotin, apostrofsiz, harf registrisiz,
    so'zlar tartibsiz (Karimov Aziz == Aziz Karimov)."""
    matn = (xom or "").lower()
    matn = "".join(_KIRILL.get(h, h) for h in matn)
    for a in _APOSTROFLAR:
        matn = matn.replace(a, "")
    sozlar = [_birlashtir(s) for s in re.findall(r"[a-z]+", matn)]
    return " ".join(sorted(sozlar))


def _birlashtir(soz):
    """Bir ismning turli yozilishini bitta kalitga keltiradi (lotin/kirill, eski/yangi imlo):
    unlilar orasidagi `y` tushadi (Jorayeva = Жўраева), q=k, h=x, w=v, ikkilangan harf bitta.
    Bu faqat TAQQOSLASH uchun; tug'ilgan sana baribir ikkinchi omil sifatida talab qilinadi."""
    soz = re.sub(r"(?<=[aeiou])y(?=[aeiou])", "", soz)
    soz = soz.translate(str.maketrans({"q": "k", "h": "x", "w": "v"}))
    return re.sub(r"(.)\1+", r"\1", soz)


def sana_tahlil(xom):
    """'16.01.2010', '16/01/2010', '16-01-2010', '2010-01-16' -> date; tushunarsiz bo'lsa None."""
    matn = (xom or "").strip()
    m = re.fullmatch(r"(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{4})", matn)
    if m:
        k, o, y = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.fullmatch(r"(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})", matn)
        if not m:
            return None
        y, o, k = int(m[1]), int(m[2]), int(m[3])
    try:
        return date(y, o, k)
    except ValueError:
        return None


def _talabalar():
    return User.objects.filter(role=User.Role.STUDENT, is_active=True)


def telefon_boyicha(telefon):
    """Ota-ona telefoni shu raqamga mos talabalar (CRM'dagi `ota_ona_telefon` yoki bog'langan
    ota-ona hisobining raqami)."""
    kalit = telefon_kaliti(telefon)
    if not kalit:
        return []
    topildi = []
    for t in _talabalar().select_related("ota_ona"):
        if telefon_kaliti(t.ota_ona_telefon) == kalit or (
            t.ota_ona_id and telefon_kaliti(t.ota_ona.telefon) == kalit
        ):
            topildi.append(t)
    return topildi


def talaba_ismi(t):
    return (t.get_full_name() or t.username or "").strip()


def aniq_moslik(ism, sana):
    """Ism va tug'ilgan sana IKKALASI mos kelgan talabalar. Ro'yxat: odatda 0 yoki 1 ta."""
    kalit = ism_kaliti(ism)
    if not kalit or sana is None:
        return []
    return [
        t for t in _talabalar().filter(tugilgan_sana=sana)
        if ism_kaliti(talaba_ismi(t)) == kalit
    ]


def nomzodlar(ism, sana=None, chegara=0.72, eng_kop=5):
    """Admin uchun taxminiy mos talabalar (aniq mos kelmaganda): ism o'xshashligi yoki
    tug'ilgan sana mos kelishi. Qaytaradi: talaba ID'lari (eng o'xshashi birinchi)."""
    kalit = ism_kaliti(ism)
    if not kalit:
        return []
    sozlar = set(kalit.split())
    baholar = []
    for t in _talabalar():
        k = ism_kaliti(talaba_ismi(t))
        if not k:
            continue
        ball = difflib.SequenceMatcher(None, kalit, k).ratio()
        umumiy = sozlar & set(k.split())
        if umumiy:
            ball = max(ball, 0.6 + 0.1 * len(umumiy))
        if sana is not None and t.tugilgan_sana == sana:
            ball += 0.3
        if ball >= chegara:
            baholar.append((ball, t.id))
    baholar.sort(reverse=True)
    return [i for _, i in baholar[:eng_kop]]
