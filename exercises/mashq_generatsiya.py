"""AI orqali yangi IELTS mashq/test generatsiya qilish (2026-08-02).

"AI mashqlari" sahifasida admin "Generatsiya qil" tugmasini bosganda,
tanlangan bo'lim (reading/listening/writing/speaking) va IELTS band
darajasi bo'yicha AI'dan BITTA yangi mini-test so'raladi:
  - reading:   1 passage + 13 savol
  - listening: 1 part + 10 savol + TTS audio
  - writing:   Task 1 + Task 2 (juftlik)
  - speaking:  Part 1 + Part 2 + Part 3 (uchlik)

PDF import (`pdf_generatsiya.py`)dan farqi: manba matn YO'Q — AI mavzuni
O'ZI o'ylab topadi, shuning uchun ko'p-bosqichli sahifa-chegara mantiqi
kerak emas, bitta chaqiruv yetarli. Savol turlari/qoidalari (matching,
maxsus_format) `pdf_generatsiya.py`dagi bilan ATAYLAB bir xil — u yerda
haqiqiy production baglar orqali sinalgan, shu qoidalarni qayta yozish
o'rniga saqlab qolindi.
"""

from assessment.providers import GEMINI_MODEL, GeminiProvider, ProviderXatosi

BAND_GURUHLAR = ["4-5", "5.5-6.5", "7-9"]

BAND_TAVSIFI = {
    "4-5": "past-o'rta (band 4-5) — sodda, kundalik so'zlar, qisqa va aniq gaplar, oson topiladigan javoblar",
    "5.5-6.5": "o'rta (band 5.5-6.5) — umumiy akademik lug'at, o'rtacha uzunlikdagi gaplar, ba'zi xulosa chiqarish talab qilinadi",
    "7-9": "yuqori (band 7-9) — murakkab/abstrakt lug'at, uzun va ko'p qatlamli gaplar, chuqur tushunish va xulosa chiqarish talab qilinadi",
}

# `pdf_generatsiya.QISM_SXEMASI`dagi bilan BIR XIL (ataylab) — savollar
# ro'yxati tuzilishi, "tur" enum, maxsus_format shakli productionda
# sinalgan, qayta yozilmaydi.
from .pdf_generatsiya import QISM_SXEMASI  # noqa: E402


def _provider():
    from django.conf import settings

    kalit = getattr(settings, "GEMINI_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
    return GeminiProvider(kalit, model=GEMINI_MODEL)


_SAVOLLAR_QOIDASI = (
    "\"savol\" matniga raqam yozmang. \"raqam\" — shu savolning guruh "
    "ichidagi ketma-ket raqami (1 dan boshlab, uzluksiz, takrorsiz).\n"
    "\"tur\": multiple_choice, tfng, matching_headings, matching, "
    "fill_blanks, short_answer, map_labelling — FAQAT shu qiymatlardan "
    "biri, boshqa nom yozmang.\n"
    "True/False/Not Given: \"variantlar\": [\"True\",\"False\",\"Not Given\"].\n"
    "Ochiq javobli (fill_blanks/short_answer): \"variantlar\" bo'sh massiv [].\n"
    "MOSLASHTIRISH (matching) — ikki xil holat:\n"
    "  (a) Ro'yxat/quti bilan (masalan \"List of researchers\"): "
    "\"variantlar\"ga TO'LIQ MATN yozing, harf yozmang.\n"
    "  (b) Ro'yxatsiz, faqat paragraf harfi: \"variantlar\"ni BO'SH "
    "massiv [] qoldiring — talaba paragraf harfini to'g'ridan-to'g'ri yozadi.\n"
    "\"togri\"ga to'g'ri javobni albatta yozing (o'zingiz yaratgan test "
    "bo'lgani uchun javobni bilasiz, hech qachon bo'sh qoldirmang).\n\n"
    "MAXSUS FORMAT: agar savol guruhi summary/note/table/flow-chart "
    "completion bo'lsa, \"maxsus_format\"ni albatta to'ldiring (jadval/"
    "oqim/matn, {{n}} bilan) — bog'lovchi matnni savollarga bo'lib "
    "tashlab, maxsus_format'ni bo'sh (null) qoldirmang."
)

READING_PROMPT_SHABLON = (
    "Siz tajribali IELTS Reading test materiali yozuvchisiz. YANGI, "
    "original mavzu o'ylab toping (ilm-fan, tarix, ekologiya, texnologiya, "
    "jamiyat kabi umumiy qiziqarli mavzulardan birini) va xuddi Cambridge "
    "IELTS kitoblaridagi kabi BITTA to'liq Reading passage (350-400 so'z) "
    "va unga tegishli ANIQ 13 ta savol yozing.\n\n"
    f"TALABA MAQSADLI DARAJASI: {{band_tavsifi}} — passage va savollar "
    "shu darajaga mos qiyinlikda bo'lsin.\n\n"
    "\"matn\" — passage matni to'liq (paragraflarni A, B, C... deb "
    "belgilang, matching_headings/information turi uchun kerak bo'ladi).\n"
    "\"guruh_boshi\"/\"guruh_korsatma\" — har savol guruhi boshida "
    "kitobdagidek to'liq ko'rsatma yozing (masalan \"Questions 1-4\", "
    "\"Do the following statements agree...\").\n"
    "\"mavzu\" — passage mavzusini 3-5 so'zda qisqa ifodalang (masalan "
    "\"Deep sea exploration\") — bu keyingi safar takrorlanmasligi uchun "
    "ishlatiladi.\n\n{oldingi_mavzular}\n\n"
    + _SAVOLLAR_QOIDASI
)

READING_YARATISH_SXEMASI = {
    **QISM_SXEMASI,
    "properties": {**QISM_SXEMASI["properties"], "mavzu": {"type": "string"}},
    "required": [*QISM_SXEMASI["required"], "mavzu"],
}

LISTENING_PROMPT_SHABLON = (
    "Siz tajribali IELTS Listening test materiali yozuvchisiz. YANGI "
    "mavzu o'ylab toping (masalan restoran buyurtmasi, universitet "
    "ma'lumoti, sayohat rejasi, ish suhbati kabi kundalik vaziyat) va "
    "ikki kishi orasidagi TABIIY suhbat transkriptini (150-200 so'z, "
    "\"Speaker1: ...\\nSpeaker2: ...\" formatida) va unga tegishli ANIQ "
    "10 ta savol yozing.\n\n"
    f"TALABA MAQSADLI DARAJASI: {{band_tavsifi}}.\n\n"
    "\"matn\"ni BO'SH qoldiring — bu maydon Reading uchun, Listening "
    "transkripti alohida \"transkript\" maydonida.\n"
    "\"transkript\" — TTS uchun tayyor matn, \"Speaker1: ...\\nSpeaker2: "
    "...\" formatida.\n"
    "\"mavzu\" — suhbat mavzusini 3-5 so'zda qisqa ifodalang — bu keyingi "
    "safar takrorlanmasligi uchun ishlatiladi.\n\n{oldingi_mavzular}\n\n"
    + _SAVOLLAR_QOIDASI
)

LISTENING_SXEMASI = {
    **QISM_SXEMASI,
    "properties": {
        **QISM_SXEMASI["properties"],
        "transkript": {"type": "string"},
        "mavzu": {"type": "string"},
    },
    "required": [*QISM_SXEMASI["required"], "transkript", "mavzu"],
}

WRITING_PROMPT_SHABLON = (
    "Siz tajribali IELTS Writing test materiali yozuvchisiz. YANGI Task 1 "
    "va YANGI Task 2 topshirig'ini yozing.\n\n"
    f"TALABA MAQSADLI DARAJASI: {{band_tavsifi}} — Task 1'dagi "
    "ma'lumotlar tuzilishi (necha toifa/yil, farqlar kattaligi) va Task 2 "
    "mavzusining abstraktligi shu darajaga mos tanlansin (past band uchun "
    "sodda/aniq, yuqori band uchun murakkab/bahsli).\n\n"
    "TASK 1 — MUHIM: bu yerda HAQIQIY grafik/diagramma RASM sifatida "
    "chiziladi (siz raqam o'ylab topasiz, dastur chizadi) — shuning uchun "
    "\"matn\"da raqamlarni SANAB O'TIRMANG, faqat rasmiy topshiriq jumlasini "
    "yozing (masalan \"The chart below shows the percentage of households "
    "with internet access in four countries between 2000 and 2020. "
    "Summarise the information...\"). Haqiqiy raqamlarni ALOHIDA "
    "\"diagramma\" maydoniga yozing:\n"
    "  \"turi\": \"bar\" (ustunli, toifalarni solishtirish uchun), "
    "\"line\" (chiziqli, vaqt bo'yicha o'zgarish uchun) yoki \"pie\" "
    "(doiraviy, ulushlarni ko'rsatish uchun) — mavzuga eng mos turini "
    "tanlang.\n"
    "  \"kategoriyalar\": X o'qidagi qiymatlar (masalan yillar yoki "
    "davlatlar nomlari).\n"
    "  \"seriyalar\": [{\"nomi\":\"...\", \"qiymatlar\":[...]}] — har "
    "seriya bitta chiziq/ustun to'plami (masalan har davlat uchun bitta "
    "seriya). \"pie\" turida FAQAT BITTA seriya bo'lsin.\n"
    "  \"kategoriyalar\" va har seriyaning \"qiymatlar\" massivi BIR XIL "
    "UZUNLIKDA bo'lsin.\n\n"
    "TASK 2 — \"diagramma\"ni null qoldiring (Task 2'da rasm yo'q).\n\n"
    "Har biri uchun \"tur\" (\"task1\"/\"task2\"), \"matn\" (to'liq "
    "topshiriq matni, raqamlarsiz) va \"diagramma\".\n"
    "Butun javob uchun BITTA \"mavzu\" maydoni ham qo'shing — Task "
    "1+Task 2 mavzularini 3-5 so'zda birgalikda ifodalang (masalan "
    "\"Internet usage / urban planning\") — bu keyingi safar "
    "takrorlanmasligi uchun ishlatiladi.\n\n{oldingi_mavzular}"
)

DIAGRAMMA_SXEMASI = {
    "type": "object",
    "properties": {
        "turi": {"type": "string", "enum": ["bar", "line", "pie"]},
        "sarlavha": {"type": "string"},
        "y_nomi": {"type": "string"},
        "kategoriyalar": {"type": "array", "items": {"type": "string"}},
        "seriyalar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nomi": {"type": "string"},
                    "qiymatlar": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["nomi", "qiymatlar"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["turi", "sarlavha", "y_nomi", "kategoriyalar", "seriyalar"],
    "additionalProperties": False,
}

WRITING_YARATISH_SXEMASI = {
    "type": "object",
    "properties": {
        "mavzu": {"type": "string"},
        "qismlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tur": {"type": "string", "enum": ["task1", "task2"]},
                    "matn": {"type": "string"},
                    "diagramma": {"anyOf": [{"type": "null"}, DIAGRAMMA_SXEMASI]},
                },
                "required": ["tur", "matn", "diagramma"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["mavzu", "qismlar"],
    "additionalProperties": False,
}


def _diagramma_chiz(diagramma):
    """Writing Task 1 uchun AI o'ylab topgan raqamlardan HAQIQIY rasm
    (PNG) chizadi (2026-08-02, foydalanuvchi talabi — matn o'rniga rasm
    bo'lishi kerak). matplotlib "Agg" backend — serverda display yo'q."""
    import matplotlib
    matplotlib.use("Agg")
    import io

    import matplotlib.pyplot as plt
    import numpy as np

    turi = diagramma.get("turi") or "bar"
    kategoriyalar = diagramma.get("kategoriyalar") or []
    seriyalar = diagramma.get("seriyalar") or []

    fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=150)
    if turi == "pie":
        qiymatlar = (seriyalar[0].get("qiymatlar") if seriyalar else []) or []
        ax.pie(qiymatlar, labels=kategoriyalar, autopct="%1.0f%%", startangle=90)
    elif turi == "line":
        for s in seriyalar:
            ax.plot(kategoriyalar, s.get("qiymatlar") or [], marker="o", label=s.get("nomi"))
        ax.set_ylabel(diagramma.get("y_nomi") or "")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        if len(seriyalar) > 1:
            ax.legend()
    else:
        x = np.arange(len(kategoriyalar))
        soni = max(len(seriyalar), 1)
        kenglik = 0.8 / soni
        for i, s in enumerate(seriyalar):
            ax.bar(x + i * kenglik - 0.4 + kenglik / 2, s.get("qiymatlar") or [], kenglik, label=s.get("nomi"))
        ax.set_xticks(x)
        ax.set_xticklabels(kategoriyalar)
        ax.set_ylabel(diagramma.get("y_nomi") or "")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        if len(seriyalar) > 1:
            ax.legend()
    ax.set_title(diagramma.get("sarlavha") or "")
    fig.tight_layout()
    bufer = io.BytesIO()
    fig.savefig(bufer, format="png")
    plt.close(fig)
    return bufer.getvalue()

SPEAKING_PROMPT_SHABLON = (
    "Siz tajribali IELTS Speaking test materiali yozuvchisiz. YANGI Part "
    "1 (4-5 oddiy shaxsiy savol), Part 2 (cue card — mavzu + 3-4 izoh "
    "band) va Part 3 (Part 2 mavzusiga bog'liq 4-5 chuqurroq munozara "
    "savoli) yozing.\n\n"
    f"TALABA MAQSADLI DARAJASI: {{band_tavsifi}} — savollarning "
    "chuqurligi/abstraktligi shu darajaga mos bo'lsin.\n\n"
    "Har biri uchun \"tur\" (\"part1\"/\"part2\"/\"part3\") va \"matn\" "
    "(to'liq savol/cue card matni).\n"
    "\"mavzu\" — Part 2 cue card mavzusini 3-5 so'zda ifodalang — bu "
    "keyingi safar takrorlanmasligi uchun ishlatiladi.\n\n{oldingi_mavzular}"
)

SPEAKING_YARATISH_SXEMASI = {
    "type": "object",
    "properties": {
        "mavzu": {"type": "string"},
        "qismlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tur": {"type": "string", "enum": ["part1", "part2", "part3"]},
                    "matn": {"type": "string"},
                },
                "required": ["tur", "matn"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["mavzu", "qismlar"],
    "additionalProperties": False,
}


def _band_tavsifi_yoki_xato(band):
    if band not in BAND_GURUHLAR:
        raise ValueError(f"band noto'g'ri — {BAND_GURUHLAR} dan biri kerak")
    return BAND_TAVSIFI[band]


def _oldingi_mavzular_matni(oldingi_mavzular):
    """Takrorlanishning oldini olish uchun (2026-08-02, foydalanuvchi
    talabi) — avval generatsiya qilingan mavzular ro'yxati promtga
    qo'shiladi, AI ulardan farqli YANGI mavzu tanlashi shart bo'ladi."""
    if not oldingi_mavzular:
        return ""
    royxat = "\n".join(f"- {m}" for m in oldingi_mavzular if m)
    if not royxat:
        return ""
    return (
        "\n\nQAT'IY TAQIQ — TAKRORLASH: quyidagi mavzular ALLAQACHON "
        "ishlatilgan, ULARNI VA ULARGA JUDA YAQIN mavzularni QAYTA "
        "ISHLATMANG, har safar BUTUNLAY BOSHQA sohadan mavzu tanlang:\n"
        f"{royxat}"
    )


def reading_yarat(band, oldingi_mavzular=None):
    """Qaytaradi: (data, xato) — `data` `_test_yarat` kutadigan format."""
    band_tavsifi = _band_tavsifi_yoki_xato(band)
    provider = _provider()
    promt = (
        READING_PROMPT_SHABLON.replace("{band_tavsifi}", band_tavsifi)
        .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular))
    )
    try:
        javob = provider.generate_json(
            promt, "Shu ko'rsatmalar bo'yicha yangi Reading passage va savollarni yarating.",
            javob_sxemasi=READING_YARATISH_SXEMASI, max_tokens=8000,
        )
    except ProviderXatosi as e:
        return None, str(e)
    natija = javob.get("natija") or {}
    savollar = natija.get("savollar") or []
    if not savollar:
        return None, "AI savol qaytarmadi"
    mavzu = (natija.get("mavzu") or "").strip()
    return {
        "name": f"AI Reading — {mavzu} ({band})" if mavzu else f"AI Reading ({band})",
        "bolim": "reading",
        "korinish": "public",
        "qismlar": [{
            "tartib": 1,
            "sarlavha": "READING PASSAGE",
            "yoriqnoma": "You should spend about 20 minutes on this passage.",
            "matn": natija.get("matn") or "",
            "savollar": savollar,
            "maxsus_format": natija.get("maxsus_format") or None,
        }],
    }, None


def listening_yarat(band, oldingi_mavzular=None):
    """Qaytaradi: (data, audio_wav_bytes, xato)."""
    from .gemini_tts import RateLimitTugadi, audio_yarat

    band_tavsifi = _band_tavsifi_yoki_xato(band)
    provider = _provider()
    promt = (
        LISTENING_PROMPT_SHABLON.replace("{band_tavsifi}", band_tavsifi)
        .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular))
    )
    try:
        javob = provider.generate_json(
            promt, "Shu ko'rsatmalar bo'yicha yangi Listening suhbati va savollarni yarating.",
            javob_sxemasi=LISTENING_SXEMASI, max_tokens=8000,
        )
    except ProviderXatosi as e:
        return None, None, str(e)
    natija = javob.get("natija") or {}
    savollar = natija.get("savollar") or []
    transkript = natija.get("transkript") or ""
    if not savollar or not transkript.strip():
        return None, None, "AI savol yoki transkript qaytarmadi"
    mavzu = (natija.get("mavzu") or "").strip()

    try:
        audio_bytes = audio_yarat(
            transkript, "gemini-2.5-flash-preview-tts",
            speakerlar=[("Speaker1", "Kore"), ("Speaker2", "Puck")],
        )
    except RateLimitTugadi:
        return None, None, "TTS kunlik/daqiqalik limiti tugadi — birozdan so'ng qayta urinib ko'ring"
    except Exception as e:  # noqa: BLE001
        return None, None, f"Audio generatsiyasida xato: {e}"

    return {
        "name": f"AI Listening — {mavzu} ({band})" if mavzu else f"AI Listening ({band})",
        "bolim": "listening",
        "korinish": "public",
        "qismlar": [{
            "tartib": 1,
            "sarlavha": "LISTENING PART",
            "yoriqnoma": "",
            "matn": "",
            "savollar": savollar,
            "maxsus_format": natija.get("maxsus_format") or None,
        }],
    }, audio_bytes, None


def writing_yarat(band, oldingi_mavzular=None):
    """Qaytaradi: (data, rasm_bytes_yoki_None, xato). `rasm_bytes` — Task
    1'ning diagramma rasmi (PNG), qism.rasm'ga (tartib=1) biriktiriladi."""
    band_tavsifi = _band_tavsifi_yoki_xato(band)
    provider = _provider()
    promt = (
        WRITING_PROMPT_SHABLON.replace("{band_tavsifi}", band_tavsifi)
        .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular))
    )
    try:
        javob = provider.generate_json(
            promt, "Shu ko'rsatmalar bo'yicha yangi Task 1 va Task 2 topshirig'ini yarating.",
            javob_sxemasi=WRITING_YARATISH_SXEMASI, max_tokens=4000,
        )
    except ProviderXatosi as e:
        return None, None, str(e)
    natija = javob.get("natija") or {}
    qismlar_data = natija.get("qismlar") or []
    qismlar = [
        {"tartib": i, "tur": q.get("tur") or "", "matn": q.get("matn") or ""}
        for i, q in enumerate(qismlar_data, start=1)
    ]
    if len(qismlar) < 2:
        return None, None, "AI Task 1/Task 2'ning ikkisini ham qaytarmadi"

    rasm_bytes = None
    task1 = next((q for q in qismlar_data if q.get("tur") == "task1"), None)
    if task1 and task1.get("diagramma"):
        try:
            rasm_bytes = _diagramma_chiz(task1["diagramma"])
        except Exception:  # noqa: BLE001 — rasm ixtiyoriy, xatosi testni buzmasin
            rasm_bytes = None

    mavzu = (natija.get("mavzu") or "").strip()
    return (
        {
            "name": f"AI Writing — {mavzu} ({band})" if mavzu else f"AI Writing ({band})",
            "bolim": "writing", "korinish": "public", "qismlar": qismlar,
        },
        rasm_bytes,
        None,
    )


def speaking_yarat(band, oldingi_mavzular=None):
    band_tavsifi = _band_tavsifi_yoki_xato(band)
    provider = _provider()
    promt = (
        SPEAKING_PROMPT_SHABLON.replace("{band_tavsifi}", band_tavsifi)
        .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular))
    )
    try:
        javob = provider.generate_json(
            promt, "Shu ko'rsatmalar bo'yicha yangi Part 1/2/3 savollarini yarating.",
            javob_sxemasi=SPEAKING_YARATISH_SXEMASI, max_tokens=4000,
        )
    except ProviderXatosi as e:
        return None, str(e)
    natija = javob.get("natija") or {}
    qismlar_data = natija.get("qismlar") or []
    qismlar = [
        {"tartib": i, "tur": q.get("tur") or "", "matn": q.get("matn") or ""}
        for i, q in enumerate(qismlar_data, start=1)
    ]
    if len(qismlar) < 3:
        return None, "AI Part 1/2/3'ning barchasini qaytarmadi"
    mavzu = (natija.get("mavzu") or "").strip()
    return {
        "name": f"AI Speaking — {mavzu} ({band})" if mavzu else f"AI Speaking ({band})",
        "bolim": "speaking", "korinish": "public", "qismlar": qismlar,
    }, None


def mashq_yarat(bolim, band, oldingi_mavzular=None):
    """Yagona kirish nuqtasi — view shu funksiyani chaqiradi.

    `oldingi_mavzular` — shu bo'limda avval generatsiya qilingan test
    nomlari (yoki mavzular) ro'yxati — takrorlanmaslik uchun promtga
    qo'shiladi (2026-08-02, foydalanuvchi talabi).

    Qaytaradi: (data, rasm_bytes, audio_bytes, xato). `data` — `_test_yarat`
    kutadigan format yoki None (xato bo'lsa). `rasm_bytes`/`audio_bytes` —
    faqat mos bo'lim uchun (writing->rasm, listening->audio), aks holda
    None."""
    if bolim == "reading":
        data, xato = reading_yarat(band, oldingi_mavzular)
        return data, None, None, xato
    if bolim == "listening":
        data, audio_bytes, xato = listening_yarat(band, oldingi_mavzular)
        return data, None, audio_bytes, xato
    if bolim == "writing":
        data, rasm_bytes, xato = writing_yarat(band, oldingi_mavzular)
        return data, rasm_bytes, None, xato
    if bolim == "speaking":
        data, xato = speaking_yarat(band, oldingi_mavzular)
        return data, None, None, xato
    return None, None, None, "bolim noto'g'ri — reading/listening/writing/speaking dan biri kerak"
