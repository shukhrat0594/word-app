"""AI orqali yangi IELTS mashq/test generatsiya qilish (2026-08-02).

"AI mashqlari" sahifasida admin "Generatsiya qil" tugmasini bosganda,
tanlangan bo'lim (reading/listening/writing/speaking) va IELTS band
darajasi bo'yicha AI'dan BITTA yangi TO'LIQ test so'raladi (2026-08-02
tuzatildi — avval Reading/Listening faqat 1 qism edi, foydalanuvchi
haqiqiy IELTS testiga mos to'liq hajm so'radi):
  - reading:   3 passage, 40 savol (1-13, 14-26, 27-40) — har passage
    ALOHIDA AI chaqiruvi (bitta katta chaqiruvda token chegarasiga
    urilish xavfi bor, `pdf_generatsiya.py`dagi bilan bir xil sabab).
  - listening: 4 part, 40 savol (1-10, 11-20, 21-30, 31-40) — har part
    ALOHIDA AI chaqiruvi + ALOHIDA TTS audio (Part1/3 — 2 kishilik
    suhbat, Part2/4 — 1 kishilik monolog, haqiqiy IELTS tuzilishiga mos).
    Transkript uzunligi band'ga qarab ~4-8 daqiqa (2026-08-05, avval
    150-200 so'z bilan cheklangan edi — judayam qisqa audio chiqargan).
    Har part'ning asosiy savol turi ham haqiqiy IELTS tuzilishiga mos
    tavsiya etiladi (avval barcha part bir xil turni tanlab qo'yardi).
  - writing:   Task 1 + Task 2 (juftlik)
  - speaking:  Part 1 + Part 2 + Part 3 (uchlik)

PDF import (`pdf_generatsiya.py`)dan farqi: manba matn YO'Q — AI mavzuni
O'ZI o'ylab topadi. Savol turlari/qoidalari (matching, maxsus_format)
`pdf_generatsiya.py`dagi bilan ATAYLAB bir xil — u yerda haqiqiy
production baglar orqali sinalgan, shu qoidalarni qayta yozish o'rniga
saqlab qolindi.

TIL (2026-08-02, foydalanuvchi topgan bag): promtlarning o'zi o'zbek
tilida yozilgan bo'lgani uchun AI ba'zan javobni ham o'zbekcha qaytargan
(masalan Speaking savollari) — bu haqiqiy IELTS savoli, INGLIZCHA bo'lishi
SHART. Shuning uchun har promtga `_TIL_QOIDASI` qo'shildi."""

from assessment.providers import GEMINI_MODEL, GeminiProvider, ProviderXatosi

BAND_GURUHLAR = ["5-6", "6.5-7.5", "8-9"]

BAND_TAVSIFI = {
    "5-6": "past-o'rta (band 5-6) — sodda, kundalik so'zlar, qisqa va aniq gaplar, oson topiladigan javoblar",
    "6.5-7.5": "o'rta-yuqori (band 6.5-7.5) — umumiy akademik lug'at, o'rtacha uzunlikdagi gaplar, ba'zi xulosa chiqarish talab qilinadi",
    "8-9": "yuqori (band 8-9) — murakkab/abstrakt lug'at, uzun va ko'p qatlamli gaplar, chuqur tushunish va xulosa chiqarish talab qilinadi",
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


_TIL_QOIDASI = (
    "TIL — QATTIQ MAJBURIY: bu ko'rsatmalar o'zbek tilida yozilgan bo'lsa "
    "ham, siz yaratayotgan JSON'dagi BARCHA matn (passage/transkript, "
    "savollar, guruh_korsatma, variantlar, mavzu — MUTLAQO HAMMASI, "
    "istisnosiz) FAQAT INGLIZ TILIDA bo'lsin — bu haqiqiy IELTS imtihon "
    "materiali, talaba buni inglizcha o'qiydi/eshitadi. O'zbek, rus yoki "
    "boshqa tilda BIRON BIR SO'Z yozmang.\n\n"
)

_SAVOLLAR_QOIDASI = (
    "\"savol\" matniga raqam yozmang. \"raqam\" — shu savolning BUTUN TEST "
    "bo'yicha raqami: aynan {boshi} dan {oxiri} gacha, ketma-ket, "
    "bo'shliqsiz, takrorsiz (masalan {boshi}=14, {oxiri}=26 bo'lsa: 14, "
    "15, 16, ... 26). BITTA TASHLAB KETILGAN yoki IKKI MARTA TAKRORLANGAN "
    "raqam — jiddiy xato.\n"
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
    _TIL_QOIDASI +
    "Siz tajribali IELTS Reading test materiali yozuvchisiz. Bu — 3 "
    "passagedan iborat TO'LIQ testning BITTA passage'i (Passage "
    "{passage_raqami}/3). YANGI, original mavzu o'ylab toping (ilm-fan, "
    "tarix, ekologiya, texnologiya, jamiyat kabi umumiy qiziqarli "
    "mavzulardan birini, boshqa passagelardan BUTUNLAY FARQLI soha) va "
    "xuddi Cambridge IELTS kitoblaridagi kabi BITTA to'liq Reading "
    "passage (350-400 so'z) va unga tegishli ANIQ {soni} ta savol "
    "(raqamlar {boshi}-{oxiri}) yozing.\n\n"
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
    _TIL_QOIDASI +
    "Siz tajribali IELTS Listening test materiali yozuvchisiz. Bu — 4 "
    "partdan iborat TO'LIQ testning BITTA part'i (Part {part_raqami}/4, "
    "{uslub}). YANGI mavzu o'ylab toping (boshqa partlardan BUTUNLAY "
    "FARQLI, masalan restoran buyurtmasi, universitet ma'lumoti, sayohat "
    "rejasi, ma'ruza kabi) va {gapiruvchilar_soni} kishi{ishtirok_matni} "
    "TABIIY transkript ({soz_oraligi} so'z — bu HAQIQIY imtihondagidek "
    "uzunlikda bo'lishi SHART, qisqartirmang, \"Speaker1: ...\\n"
    "Speaker2: ...\" formatida — bitta kishi bo'lsa faqat "
    "\"Speaker1: ...\") va unga tegishli ANIQ {soni} ta savol (raqamlar "
    "{boshi}-{oxiri}) yozing.\n\n"
    "{tur_talabi}\n\n"
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
    _TIL_QOIDASI +
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
    _TIL_QOIDASI +
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


READING_ORALIQLAR = [(1, 13), (14, 26), (27, 40)]


def reading_yarat(band, oldingi_mavzular=None):
    """Qaytaradi: (data, xato). To'liq test — 3 passage, 40 savol
    (2026-08-02 talabi). Har passage ALOHIDA AI chaqiruvi — bitta katta
    chaqiruvda chiqish token chegarasiga urilish xavfi bor (`pdf_generatsiya.
    py`dagi ikki-bosqichli yondashuv bilan bir xil sabab)."""
    oldingi_mavzular = oldingi_mavzular or []
    band_tavsifi = _band_tavsifi_yoki_xato(band)
    provider = _provider()
    qismlar = []
    mavzular_shu_testda = []
    for i, (boshi, oxiri) in enumerate(READING_ORALIQLAR, start=1):
        promt = (
            READING_PROMPT_SHABLON
            .replace("{band_tavsifi}", band_tavsifi)
            .replace("{passage_raqami}", str(i))
            .replace("{boshi}", str(boshi))
            .replace("{oxiri}", str(oxiri))
            .replace("{soni}", str(oxiri - boshi + 1))
            .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular + mavzular_shu_testda))
        )
        try:
            javob = provider.generate_json(
                promt, f"Passage {i}/3 (Questions {boshi}-{oxiri}) uchun yangi matn va savollarni yarating.",
                javob_sxemasi=READING_YARATISH_SXEMASI, max_tokens=8000,
            )
        except ProviderXatosi as e:
            return None, f"Passage {i}: {e}"
        natija = javob.get("natija") or {}
        savollar = natija.get("savollar") or []
        kutilgan = oxiri - boshi + 1
        if len(savollar) != kutilgan:
            return None, f"Passage {i}: {kutilgan} ta savol kutilgandi, {len(savollar)} ta chiqdi"
        savollar = sorted(savollar, key=lambda s: s.get("raqam") if isinstance(s.get("raqam"), int) else 10**9)
        for s in savollar:
            s.pop("raqam", None)
        mavzu = (natija.get("mavzu") or "").strip()
        if mavzu:
            mavzular_shu_testda.append(mavzu)
        qismlar.append({
            "tartib": i,
            "sarlavha": f"READING PASSAGE {i}",
            "yoriqnoma": f"You should spend about 20 minutes on Questions {boshi}-{oxiri}.",
            "matn": natija.get("matn") or "",
            "savollar": savollar,
            "maxsus_format": natija.get("maxsus_format") or None,
        })

    nomi_qismi = " / ".join(mavzular_shu_testda) if mavzular_shu_testda else ""
    return {
        "name": f"AI Reading — {nomi_qismi} ({band})" if nomi_qismi else f"AI Reading ({band})",
        "bolim": "reading",
        "korinish": "public",
        "qismlar": qismlar,
    }, None


# Band bo'yicha transkript so'z hajmi (2026-08-05, avval 150-200 so'z
# bilan cheklangan edi — bu haqiqiy IELTS part'iga nisbatan judayam qisqa
# audio chiqargan). Taxminan ~140 so'z/daqiqa tabiiy suhbat sur'ati bilan
# hisoblangan: 5-6 -> ~4-5 daq, 6.5-7.5 -> ~5.5-6.5 daq, 8-9 -> ~7-8 daq.
BAND_SOZ_ORALIGI = {
    "5-6": "550-700",
    "6.5-7.5": "800-950",
    "8-9": "1000-1150",
}

# (boshi, oxiri, gapiruvchilar_soni, asosiy_tur, tur_tavsifi) — haqiqiy
# IELTS Listening tuzilishiga mos: Part1 — 2 kishilik kundalik/maishiy
# suhbat (forma to'ldirish), Part2 — 1 kishilik kundalik/ijtimoiy monolog
# (masalan ekskursiya/e'lon), Part3 — 2-4 kishilik o'quv/trening
# konteksti, Part4 — 1 kishilik akademik ma'ruza. Avval barcha part bir
# xil savol turini olib qo'yardi (2026-08-05 tuzatildi) — endi har
# part'ga TAVSIYA etilgan asosiy tur beriladi (majburiy emas, chunki
# real IELTS'da ba'zan bitta part ichida ikki xil tur aralashadi).
LISTENING_ORALIQLAR = [
    (1, 10, 2, "fill_blanks", "form/note completion — kundalik/maishiy suhbat kontekstida (masalan buyurtma, ro'yxatdan o'tish)"),
    (11, 20, 1, "multiple_choice", "kundalik/ijtimoiy monolog (masalan ekskursiya, e'lon) — multiple_choice yoki map_labelling"),
    (21, 30, 2, "matching", "o'quv/trening konteksti (masalan talaba-o'qituvchi muhokamasi) — matching yoki multiple_choice"),
    (31, 40, 1, "fill_blanks", "akademik ma'ruza — summary/note completion (maxsus_format bilan) yoki short_answer"),
]


def listening_yarat(band, oldingi_mavzular=None):
    """Qaytaradi: (data, audio_bytes_royxati, xato). To'liq test — 4 part,
    40 savol (2026-08-02 talabi). Har part ALOHIDA AI+TTS chaqiruvi.
    `audio_bytes_royxati` — `data["qismlar"]` bilan bir xil uzunlik/tartib,
    har elementi shu qismning WAV baytlari.

    Transkript uzunligi va har part'ning asosiy savol turi band/part'ga
    qarab farqlanadi — batafsil: `BAND_SOZ_ORALIGI`, `LISTENING_ORALIQLAR`."""
    oldingi_mavzular = oldingi_mavzular or []
    from .gemini_tts import RateLimitTugadi, audio_yarat

    band_tavsifi = _band_tavsifi_yoki_xato(band)
    soz_oraligi = BAND_SOZ_ORALIGI[band]
    provider = _provider()
    qismlar, audio_royxati = [], []
    mavzular_shu_testda = []
    for i, (boshi, oxiri, gap_soni, asosiy_tur, tur_tavsifi) in enumerate(LISTENING_ORALIQLAR, start=1):
        uslub = "ikki kishi suhbati" if gap_soni == 2 else "bitta kishi monologi/ma'ruzasi"
        tur_talabi = (
            f"BU PART UCHUN SAVOL TURI: savollarning ASOSIY qismi "
            f"\"{asosiy_tur}\" turida bo'lsin — {tur_tavsifi}. Boshqa "
            "part'larda ishlatilgan turni takrorlamang, har part TURLI "
            "savol turida bo'lishi SHART (haqiqiy IELTS'dagidek)."
        )
        promt = (
            LISTENING_PROMPT_SHABLON
            .replace("{band_tavsifi}", band_tavsifi)
            .replace("{part_raqami}", str(i))
            .replace("{uslub}", uslub)
            .replace("{gapiruvchilar_soni}", str(gap_soni))
            .replace("{ishtirok_matni}", " orasidagi" if gap_soni == 2 else "ning")
            .replace("{boshi}", str(boshi))
            .replace("{oxiri}", str(oxiri))
            .replace("{soni}", str(oxiri - boshi + 1))
            .replace("{soz_oraligi}", soz_oraligi)
            .replace("{tur_talabi}", tur_talabi)
            .replace("{oldingi_mavzular}", _oldingi_mavzular_matni(oldingi_mavzular + mavzular_shu_testda))
        )
        try:
            javob = provider.generate_json(
                promt, f"Part {i}/4 (Questions {boshi}-{oxiri}) uchun yangi suhbat/monolog va savollarni yarating.",
                javob_sxemasi=LISTENING_SXEMASI, max_tokens=16000,
            )
        except ProviderXatosi as e:
            return None, None, f"Part {i}: {e}"
        natija = javob.get("natija") or {}
        savollar = natija.get("savollar") or []
        transkript = natija.get("transkript") or ""
        kutilgan = oxiri - boshi + 1
        if len(savollar) != kutilgan or not transkript.strip():
            return None, None, f"Part {i}: {kutilgan} ta savol kutilgandi, {len(savollar)} ta chiqdi (yoki transkript bo'sh)"
        savollar = sorted(savollar, key=lambda s: s.get("raqam") if isinstance(s.get("raqam"), int) else 10**9)
        for s in savollar:
            s.pop("raqam", None)
        mavzu = (natija.get("mavzu") or "").strip()
        if mavzu:
            mavzular_shu_testda.append(mavzu)

        speakerlar = [("Speaker1", "Kore"), ("Speaker2", "Puck")] if gap_soni == 2 else None
        try:
            audio_bytes = audio_yarat(transkript, "gemini-2.5-flash-preview-tts", speakerlar=speakerlar)
        except RateLimitTugadi:
            return None, None, f"Part {i}: TTS kunlik/daqiqalik limiti tugadi — birozdan so'ng qayta urinib ko'ring"
        except Exception as e:  # noqa: BLE001
            return None, None, f"Part {i}: audio generatsiyasida xato: {e}"

        qismlar.append({
            "tartib": i,
            "sarlavha": f"LISTENING PART {i}",
            "yoriqnoma": "",
            "matn": "",
            "savollar": savollar,
            "maxsus_format": natija.get("maxsus_format") or None,
        })
        audio_royxati.append(audio_bytes)

    nomi_qismi = " / ".join(mavzular_shu_testda) if mavzular_shu_testda else ""
    return {
        "name": f"AI Listening — {nomi_qismi} ({band})" if nomi_qismi else f"AI Listening ({band})",
        "bolim": "listening",
        "korinish": "public",
        "qismlar": qismlar,
    }, audio_royxati, None


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

    Qaytaradi: (data, rasm_bytes, audio_royxati, xato). `data` — `_test_yarat`
    kutadigan format yoki None (xato bo'lsa). `rasm_bytes` — faqat writing
    (Task 1 diagrammasi, birinchi qismga biriktiriladi). `audio_royxati` —
    faqat listening, `data["qismlar"]` bilan BIR XIL tartib/uzunlikdagi
    ro'yxat (har elementi shu qismning WAV baytlari). Boshqa bo'limlarda
    ikkisi ham None."""
    if bolim == "reading":
        data, xato = reading_yarat(band, oldingi_mavzular)
        return data, None, None, xato
    if bolim == "listening":
        data, audio_royxati, xato = listening_yarat(band, oldingi_mavzular)
        return data, None, audio_royxati, xato
    if bolim == "writing":
        data, rasm_bytes, xato = writing_yarat(band, oldingi_mavzular)
        return data, rasm_bytes, None, xato
    if bolim == "speaking":
        data, xato = speaking_yarat(band, oldingi_mavzular)
        return data, None, None, xato
    return None, None, None, "bolim noto'g'ri — reading/listening/writing/speaking dan biri kerak"
