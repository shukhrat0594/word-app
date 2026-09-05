"""So'zlarni ruscha tarjima qilish (2026-09-05, foydalanuvchi talabi).

Vocabulary bo'limidagi "Rus tiliga tarjima qilish" tugmasi shu modulni
chaqiradi. Gemini ishlatiladi (`assessment.providers`), chunki loyihada
allaqachon shu provider sozlangan va arzon.

MUHIM — tarjima sifati uchun modelga ingliz so'zining O'ZIGINA emas,
mavjud O'ZBEKCHA tarjimasi ham kontekst sifatida beriladi. Sabab:
ingliz so'zlari ko'p ma'noli, kontekstsiz model noto'g'ri ma'noni
tanlaydi. Masalan bazadagi `app` -> `ilova (telefon dasturi)`; o'zbekcha
tarjimasiz model "аппликация" deb yozib qo'yishi mumkin, u bilan esa
`приложение` ekani aniq. Xuddi shunday `turkum` (so'z turkumi) ham
yuboriladi: `book (n)` -> `книга`, `book (v)` -> `бронировать`.
"""

import json

from assessment.providers import ProviderXatosi, gemini_provider_ol

# Bitta so'rovda nechta so'z. 60 — o'lchov emas, ehtiyotkor tanlov:
# javob JSON'i katta bo'lsa model uni yarimda uzib qo'yishi mumkin
# (MAX_TOKENS), kichik partiya esa so'rovlar sonini oshiradi. Beginner
# Unit'da ~56 so'z bor, ya'ni odatdagi Unit bitta so'rovga sig'adi.
PARTIYA = 60

SYSTEM_PROMPT = (
    "Sen ingliz-rus lug'at tarjimonisan. Sanga ingliz so'zlari ro'yxati "
    "beriladi; har biri uchun RUSCHA tarjimasini qaytar.\n\n"
    "Har bir band quyidagilarni o'z ichiga oladi:\n"
    "- \"en\" — ingliz so'zi (tarjima qilinadigan so'z)\n"
    "- \"uz\" — SHU so'zning o'zbekcha tarjimasi. Bu MA'NONI ANIQLASH "
    "uchun beriladi: ingliz so'zi ko'p ma'noli bo'lsa, aynan o'zbekchada "
    "berilgan ma'noni tarjima qil, boshqa ma'noni EMAS.\n"
    "- \"turkum\" — so'z turkumi (n/v/adj/adv va h.k.), bo'lishi mumkin\n\n"
    "QOIDALAR:\n"
    "1. Faqat tarjima yoz — izoh, transkripsiya, misol gap YO'Q.\n"
    "2. O'zbekchada bir necha ma'no vergul bilan berilgan bo'lsa "
    "(masalan \"doim, har doim\"), ruschada ham xuddi shu uslubda "
    "vergul bilan ber (\"всегда, постоянно\").\n"
    "3. O'zbekchada qavs ichida aniqlik berilgan bo'lsa (masalan "
    "\"ilova (telefon dasturi)\") — ruschada ham qavsni saqla, agar u "
    "ma'noni ajratish uchun kerak bo'lsa.\n"
    "4. Fe'llarni infinitiv shaklda ber (\"to wonder\" -> "
    "\"удивляться, размышлять\").\n"
    "5. Bosh harf bilan boshlash SHART emas — lug'at uslubi, kichik "
    "harf. Faqat atoqli otlar bosh harf bilan (\"Arabic\" -> "
    "\"арабский язык\").\n"
    "6. HAR BIR band uchun javob qaytar, birontasini ham tashlab "
    "ketma. Tartib raqami \"n\" bilan bog'la.\n"
)

JAVOB_SXEMASI = {
    "type": "object",
    "properties": {
        "tarjimalar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer"},
                    "ru": {"type": "string"},
                },
                "required": ["n", "ru"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tarjimalar"],
    "additionalProperties": False,
}


def _partiyalar(royxat, olcham):
    for i in range(0, len(royxat), olcham):
        yield royxat[i : i + olcham]


def ruscha_tarjima_qil(sozlar, provider=None):
    """`sozlar` — `KursSoz`/`games.Soz` obyektlari ro'yxati (`en`, `uz`,
    `turkum` maydonlari kerak).

    Qaytaradi: `{soz.id: "ruscha tarjima"}` — FAQAT model javob bergan
    so'zlar uchun. Javob bermagan yoki bo'sh qaytargan so'z lug'atga
    tushmaydi (chaqiruvchi ularni "tarjima qilinmadi" deb hisoblaydi va
    `ru` bo'sh qoladi — bu xavfsiz, chunki bo'sh `ru` da hamma joyda
    `uz` ishlatiladi).

    `provider` — sinov uchun (haqiqiy API chaqirmasdan). Berilmasa
    platformaning Gemini kaliti ishlatiladi.
    """
    if not sozlar:
        return {}
    if provider is None:
        provider = gemini_provider_ol("flash_lite")

    natija = {}
    for partiya in _partiyalar(list(sozlar), PARTIYA):
        # `n` — partiya ICHIDAGI tartib raqami (id emas): id'lar katta va
        # siyrak bo'lgani uchun model ularni chalkashtirishi mumkin.
        bandlar = [
            {
                "n": i,
                "en": s.en,
                "uz": s.uz,
                "turkum": s.turkum or "",
            }
            for i, s in enumerate(partiya, start=1)
        ]
        javob = provider.generate_json(
            SYSTEM_PROMPT,
            json.dumps(bandlar, ensure_ascii=False),
            javob_sxemasi=JAVOB_SXEMASI,
            max_tokens=8000,
        )
        for band in javob["natija"].get("tarjimalar") or []:
            try:
                indeks = int(band["n"]) - 1
            except (KeyError, TypeError, ValueError):
                continue
            if not (0 <= indeks < len(partiya)):
                continue
            ru = str(band.get("ru") or "").strip()
            if ru:
                # Model ba'zan chegaradan uzun matn qaytaradi (izoh
                # qo'shib yuboradi) — maydon 300 belgi, kesib qo'yamiz,
                # aks holda butun partiya saqlanmay qolardi.
                natija[partiya[indeks].id] = ru[:300]
    return natija


__all__ = ["ProviderXatosi", "ruscha_tarjima_qil", "PARTIYA"]
