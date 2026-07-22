"""Provider-agnostic AI baholash qatlami (B5).

Claude va Gemini bir xil interfeys ortida: har provider `writing_baholash(matn)`
metodini beradi va bir xil tuzilmadagi dict qaytaradi. Markaz faqat provayderni
(Markaz.ai_provider) tanlaydi — API kalit har doim platforma (owner) kaliti,
markaz o'z kalitini kirita olmaydi (2026-07-17).
"""

import json

from django.conf import settings


class ProviderXatosi(Exception):
    """AI provider bilan ishlashdagi xato (kalit yo'q, javob buzuq va h.k.)."""


# v5 prompt (2026-07-20): B8.1'da talaba Task turini tanlamasligi uchun
# AI mavzuni MATNDAN TAXMIN qilar edi — bu, savol/mavzu matni AI'ga UMUMAN
# yuborilmagani sababli, mavzudan butunlay chetga chiqqan javoblarni ham
# yuqori ball bilan baholab yuborish bug'iga olib kelgan (2026-07-20
# aniqlangan: sinov — real Task 2 mavzusiga umuman aloqasi yo'q insho
# "Mavzu to'liq yoritilgan" deb 7.0 band olgan). v5'da: talabaga berilgan
# ASL SAVOL matni va turi (task1/task2) endi ANIQ, kontent ichida beriladi
# — AI endi mavzuni taxmin qilmaydi, TASdiqlaydi va mavzuga moslikni
# tekshiradi.
WRITING_SYSTEM_PROMPT = (
    "Siz professional IELTS imtihonchisiz. Sizga (1) talabaga berilgan aniq "
    "Writing SAVOL/MAVZU matni va uning turi (Task 1 yoki Task 2), (2) "
    "talabaning shu savolga yozgan javobi beriladi. Quyidagi tartibda "
    "baholang:\n\n"

    "1) MAVZUGA MOSLIK (ENG MUHIM TEKSHIRUV): talabaning javobi BERILGAN "
    "SAVOLGA haqiqatda javob berayotganini albatta tekshiring. Agar talaba "
    "butunlay boshqa mavzuda yozgan bo'lsa, savolni chetlab o'tgan bo'lsa "
    "yoki savolning barcha qismlariga javob bermagan bo'lsa (masalan savol "
    "ikki qismli bo'lsa-yu, faqat bittasiga javob bergan bo'lsa) — Task "
    "Achievement balini KESKIN pasaytiring (bunday holatda 2-4 balldan "
    "oshmasin) va buni izohda ANIQ ayting (masalan: \"talaba berilgan "
    "savolga javob bermadi, butunlay boshqa mavzuda yozdi\"). Til sifati "
    "qanchalik yaxshi bo'lishidan qat'iy nazar, javob mavzuga mos kelmasa "
    "yuqori ball berilmasin.\n\n"

    "2) SO'Z SONI: sanang. Task 1 uchun minimal 150 so'z, Task 2 uchun "
    "minimal 250 so'z. Sizga berilgan turga mos minimumdan kam bo'lsa, "
    "Task Achievement balini pasaytiring va buni izohda ayting.\n\n"

    "3) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 1 gaplik xulosa yozing — shu asosda ball bering.\n"
    "Band yo'riqnomasi: 4-5=ko'p tizimli xato/rivojlanmagan fikr; "
    "6=tushunarli lekin sezilarli xato; 7=xato kam, fikr dalillangan; "
    "8-9=deyarli xatosiz, murakkab til.\n\n"

    "4) XATOLAR: matnni qatorma-qator o'qib, BARCHA xatolarni toping "
    "(ega-kesim, birlik/ko'plik, artikl, egalik, imlo). Har birini "
    'ANIQ shu formatda yozing: "noto\'g\'ri qism -> to\'g\'ri qism (sabab)". '
    "Bir xil xato matnda necha marta uchrasa, HAR BIRINI ALOHIDA, aniq "
    "qaysi so'z birikmasida ekanini ko'rsatib yozing.\n\n"

    "5) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "6) KUCHLI TOMONLAR: 1-2 ta ijobiy narsani ko'rsating.\n\n"

    "7) GRAFIK (agar rasm sifatida berilgan bo'lsa): sizga talabaning matni "
    "bilan birga Task 1 grafigi/jadvali/diagrammasi RASM sifatida ham "
    "berilishi mumkin. Shunday bo'lsa, talabaning tavsifi rasmdagi haqiqiy "
    "ma'lumotlarga (raqamlar, tendentsiyalar, taqqoslashlar) qanchalik mos "
    "kelishini tekshiring va bu Task Achievement bahosiga bevosita ta'sir "
    "qilsin — talaba rasmda yo'q narsani yozgan yoki asosiy tendentsiyani "
    "noto'g'ri tasvirlagan bo'lsa, buni aniq ayting.\n\n"

    "Faqat quyidagi JSON qaytaring, boshqa matn yozmang. 'task_type' "
    "maydoniga sizga berilgan turni ('task1' yoki 'task2') aynan shu "
    "ko'rinishda yozing (o'zingiz taxmin qilmang, sizga aniq berilgan):\n"
    "{\n"
    '  "task_type": "task1 yoki task2",\n'
    '  "word_count": 0,\n'
    '  "analysis": {\n'
    '    "task_achievement": "", "coherence_cohesion": "",\n'
    '    "lexical_resource": "", "grammatical_range": ""\n'
    "  },\n"
    '  "task_achievement": {"score": 0, "comment": ""},\n'
    '  "coherence_cohesion": {"score": 0, "comment": ""},\n'
    '  "lexical_resource": {"score": 0, "comment": ""},\n'
    '  "grammatical_range": {"score": 0, "comment": ""},\n'
    '  "overall_band": 0,\n'
    '  "errors": ["noto\'g\'ri -> to\'g\'ri (sabab)"],\n'
    '  "strengths": [""]\n'
    "}"
)


def _writing_kontent_tuz(savol_matni, tur, matn):
    """AI'ga yuboriladigan kontentni tuzadi — talaba javobi bilan birga
    ASL SAVOL matni va turi (task1/task2) ANIQ beriladi, AI taxmin qilmaydi."""
    tur_nomi = "Task 1" if tur == "task1" else "Task 2"
    minimum = 150 if tur == "task1" else 250
    savol_qismi = (
        f"BERILGAN SAVOL/MAVZU MATNI:\n{savol_matni}\n\n" if savol_matni else ""
    )
    return (
        f"BU — WRITING {tur_nomi.upper()} (minimal {minimum} so'z talab qilinadi).\n\n"
        f"{savol_qismi}"
        f"TALABANING JAVOBI (shu savolga nisbatan baholang):\n{matn}"
    )


# Speaking matn-mazmun tahlili — v5 (2026-07-20): Writing bilan bir xil
# sabab bilan, AI'ga endi ASL SAVOL/MAVZU matni va turi (part1/part2) ANIQ
# beriladi, taxmin qilinmaydi. "part2" turi — bu tizimda Part 2 (cue card
# monolog) VA Part 3 (chuqurroq munozara) BIRLASHTIRILGAN holda saqlanadi.
# Pronunciation BAHOLANMAYDI — u Azure vazifasi (Tezkor tahlil rejimida).
SPEAKING_SYSTEM_PROMPT = (
    "Siz professional IELTS Speaking imtihonchisiz. Sizga (1) talabaga "
    "berilgan aniq savol/mavzu (cue card) matni va uning turi (Part 1, yoki "
    "Part 2/3 — bu tizimda ular birlashtirilgan holda beriladi), (2) "
    "talabaning OG'ZAKI javobining matni (transkripsiya yoki yozma "
    "kiritilgan) beriladi. FAQAT quyidagi 3 mezon bo'yicha baholang. "
    "PRONUNCIATION (talaffuz)ni BAHOLAMANG — u alohida audio tizim orqali "
    "baholanadi.\n\n"

    "1) MAVZUGA MOSLIK (ENG MUHIM TEKSHIRUV): talabaning javobi BERILGAN "
    "SAVOL/MAVZUGA haqiqatda javob berayotganini albatta tekshiring. Agar "
    "talaba butunlay boshqa mavzuda gapirgan bo'lsa yoki savolni chetlab "
    "o'tgan bo'lsa — bu mezonlarning barchasiga (ayniqsa fluency_coherence) "
    "salbiy ta'sir qilsin va buni izohda ANIQ ayting.\n\n"

    "2) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 1 gaplik xulosa yozing.\n"
    "Band yo'riqnomasi: 4-5=ko'p pauza/takrorlash, oddiy bog'lovchilar, "
    "tez-tez xato; 6=tushunarli oqim lekin ba'zan ikkilanish, xato bor-yu "
    "tushunishga xalaqit bermaydi; 7=nisbatan erkin, moslashuvchan lug'at, "
    "xato kam; 8-9=deyarli erkin va tabiiy, murakkab til.\n\n"

    "3) MEZONLAR: fluency_coherence (nutq oqimi, discourse markerlar, "
    "izchillik), lexical_resource (so'z boyligi, idiomalar), "
    "grammatical_range (gap tuzilishi xilma-xilligi, og'zaki nutqda kichik "
    "xato kechiriladi, tizimli xato pasaytiradi).\n\n"

    "4) XATOLAR: faqat GRAMMATIK va LEKSIK xatolar. Har birini ANIQ shu "
    'formatda: "noto\'g\'ri qism -> to\'g\'ri qism (sabab)". Bir xil turdagi '
    "xato necha marta uchrasa, HAR BIRINI ALOHIDA yozing.\n\n"

    "5) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "6) KUCHLI TOMONLAR: 1-2 ta ijobiy narsani ko'rsating.\n\n"

    "Faqat quyidagi JSON qaytaring ('overall_band_no_pronunciation' — "
    "Pronunciation'siz 3 mezon o'rtachasi, yakuniy IELTS ball EMAS). "
    "'part_type' maydoniga sizga berilgan turni aynan shu ko'rinishda "
    "yozing (o'zingiz taxmin qilmang):\n"
    "{\n"
    '  "part_type": "part1 yoki part2",\n'
    '  "word_count": 0,\n'
    '  "analysis": {"fluency_coherence": "", "lexical_resource": "", '
    '"grammatical_range": ""},\n'
    '  "fluency_coherence": {"score": 0, "comment": ""},\n'
    '  "lexical_resource": {"score": 0, "comment": ""},\n'
    '  "grammatical_range": {"score": 0, "comment": ""},\n'
    '  "overall_band_no_pronunciation": 0,\n'
    '  "errors": ["noto\'g\'ri -> to\'g\'ri (sabab)"],\n'
    '  "strengths": [""]\n'
    "}"
)


def _speaking_kontent_tuz(savol_matni, tur, matn):
    """Speaking uchun ham xuddi shu naqsh — asl savol/cue card matni va
    turi (part1/part2) ANIQ beriladi."""
    tur_nomi = "Part 1" if tur == "part1" else "Part 2/3"
    savol_qismi = (
        f"BERILGAN SAVOL/MAVZU (CUE CARD) MATNI:\n{savol_matni}\n\n" if savol_matni else ""
    )
    return (
        f"BU — SPEAKING {tur_nomi.upper()}.\n\n"
        f"{savol_qismi}"
        f"TALABANING OG'ZAKI JAVOBI MATNI (shu savol/mavzuga nisbatan "
        f"baholang):\n{matn}"
    )


def javobni_parse_qil(raw_text):
    """AI javobidan JSON ajratadi (```json ... ``` o'ramini olib tashlab)."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ProviderXatosi(f"AI javobi JSON emas: {e}") from e


# 2026-07-22: Gemma 4 26B — butunlay bepul (Google narxlar sahifasida
# pullik tarif yo'q), kunlik limit ~14,400 so'rov (Gemini 3.1 Flash
# Lite'ning 500'idan ~29 baravar ko'p), sifat sinovda yaxshi chiqdi
# (rasmli Task 1'ni to'g'ri tahlil qildi, rasmga zid tavsifni ushlab
# oldi). Kamchiligi: ba'zan (~1/3 holatda) MAX_TOKENS bilan bo'sh javob
# qaytaradi — shuning uchun qayta urinish + zaxira model kerak (pastda).
GEMMA_MODEL = "gemma-4-26b-a4b-it"
GEMINI_ZAXIRA_MODEL = "gemini-3.1-flash-lite"
MAX_OUTPUT_TOKENS = 8192


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model=GEMMA_MODEL):
        if not api_key:
            raise ProviderXatosi("Gemini API kaliti berilmagan")
        self.api_key = api_key
        self.model = model

    def _bitta_sorov(self, model, system_prompt, matn, rasm_bytes=None, rasm_mime=None):
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        contents = matn
        if rasm_bytes:
            contents = [types.Part.from_bytes(data=rasm_bytes, mime_type=rasm_mime), matn]
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )

    def _generate(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None):
        """1-urinish: asosiy model. Javob bo'sh/kesilgan bo'lsa (masalan
        MAX_TOKENS) — 2-urinish: XUDDI SHU model bilan qayta. Yana bo'sh
        bo'lsa va asosiy model Gemma bo'lsa — 3-urinish: barqaror zaxira
        modelga (Gemini 3.1 Flash Lite) o'tiladi (2026-07-22 qarori)."""
        response = self._bitta_sorov(self.model, system_prompt, matn, rasm_bytes, rasm_mime)
        if not response.text:
            response = self._bitta_sorov(self.model, system_prompt, matn, rasm_bytes, rasm_mime)

        ishlatilgan_model = self.model
        if not response.text and self.model != GEMINI_ZAXIRA_MODEL:
            response = self._bitta_sorov(GEMINI_ZAXIRA_MODEL, system_prompt, matn, rasm_bytes, rasm_mime)
            ishlatilgan_model = GEMINI_ZAXIRA_MODEL

        if not response.text:
            raise ProviderXatosi("AI javob bermadi (bo'sh javob, qayta urinish va zaxira modeldan keyin ham)")

        usage = response.usage_metadata
        return {
            "natija": javobni_parse_qil(response.text),
            "provider": self.name,
            "model": ishlatilgan_model,
            "input_tokens": usage.prompt_token_count or 0,
            "output_tokens": usage.candidates_token_count or 0,
        }

    def writing_baholash(self, matn, savol_matni="", tur="task2", rasm_bytes=None, rasm_mime=None):
        kontent = _writing_kontent_tuz(savol_matni, tur, matn)
        return self._generate(WRITING_SYSTEM_PROMPT, kontent, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn, savol_matni="", tur="part1"):
        kontent = _speaking_kontent_tuz(savol_matni, tur, matn)
        return self._generate(SPEAKING_SYSTEM_PROMPT, kontent)


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key, model="claude-haiku-4-5"):
        if not api_key:
            raise ProviderXatosi("Claude API kaliti berilmagan")
        self.api_key = api_key
        self.model = model

    def _generate(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None):
        import base64

        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        content = matn
        if rasm_bytes:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": rasm_mime,
                        "data": base64.b64encode(rasm_bytes).decode(),
                    },
                },
                {"type": "text", "text": matn},
            ]
        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        return {
            "natija": javobni_parse_qil(response.content[0].text),
            "provider": self.name,
            "model": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    def writing_baholash(self, matn, savol_matni="", tur="task2", rasm_bytes=None, rasm_mime=None):
        kontent = _writing_kontent_tuz(savol_matni, tur, matn)
        return self._generate(WRITING_SYSTEM_PROMPT, kontent, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn, savol_matni="", tur="part1"):
        kontent = _speaking_kontent_tuz(savol_matni, tur, matn)
        return self._generate(SPEAKING_SYSTEM_PROMPT, kontent)


def provider_tanla(user):
    """Foydalanuvchi uchun AI provider tanlaydi.

    Markaz faqat AI provayderni (Gemini/Claude) tanlaydi — API kalit har
    doim platforma (owner) kaliti orqali to'lanadi, markazlar o'z kalitini
    kirita olmaydi. Shunday qilib har bir Writing/Speaking tekshiruvi
    xarajati platformaga tushadi (2026-07-17'da shunday qaror qilingan).

    "gemini" provayder tanlansa — endi asosiy model **Gemma 4 26B**
    (2026-07-22'dan, `GeminiProvider.__init__` default qiymati orqali) —
    bepul, kunlik limiti ancha yuqori (~14,400), sifat sinovda yaxshi
    chiqdi. Ishonchlilik uchun `GeminiProvider._generate` ichida avtomatik
    qayta urinish + Gemini 3.1 Flash Lite'ga zaxira o'tish bor.
    """
    markaz = user.markaz
    provider_nomi = markaz.ai_provider if markaz else "gemini"

    if provider_nomi == "claude":
        kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not kalit:
            raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
        return ClaudeProvider(kalit)

    kalit = getattr(settings, "GEMINI_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma GEMINI_API_KEY sozlanmagan (.env)")
    return GeminiProvider(kalit)
