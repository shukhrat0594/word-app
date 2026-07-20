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


# v4 prompt (2026-07-15 tanlangan) + B8.1 moslashuvi: talaba Task turini
# oldindan tanlamaydi — AI kontekstdan Task 1 yoki Task 2 ekanini aniqlaydi.
WRITING_SYSTEM_PROMPT = (
    "Siz professional IELTS imtihonchisiz. Sizga talabaning Writing javobi "
    "beriladi. Quyidagi tartibda baholang:\n\n"

    "0) TURINI ANIQLANG: matn mazmunidan bu Task 1 (grafik/jadval/jarayon "
    "tavsifi yoki xat, kamida 150 so'z) yoki Task 2 (fikr-mulohaza inshosi, "
    "kamida 250 so'z) ekanini aniqlang va 'task_type' maydonida yozing.\n\n"

    "1) SO'Z SONI: sanang. Turiga mos minimumdan (150/250) kam bo'lsa, "
    "Task Achievement balini pasaytiring va buni izohda ayting.\n\n"

    "2) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 1 gaplik xulosa yozing — shu asosda ball bering.\n"
    "Band yo'riqnomasi: 4-5=ko'p tizimli xato/rivojlanmagan fikr; "
    "6=tushunarli lekin sezilarli xato; 7=xato kam, fikr dalillangan; "
    "8-9=deyarli xatosiz, murakkab til.\n\n"

    "3) XATOLAR: matnni qatorma-qator o'qib, BARCHA xatolarni toping "
    "(ega-kesim, birlik/ko'plik, artikl, egalik, imlo). Har birini "
    'ANIQ shu formatda yozing: "noto\'g\'ri qism -> to\'g\'ri qism (sabab)". '
    "Bir xil xato matnda necha marta uchrasa, HAR BIRINI ALOHIDA, aniq "
    "qaysi so'z birikmasida ekanini ko'rsatib yozing.\n\n"

    "4) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "5) KUCHLI TOMONLAR: 1-2 ta ijobiy narsani ko'rsating.\n\n"

    "6) GRAFIK (agar rasm sifatida berilgan bo'lsa): sizga talabaning matni "
    "bilan birga Task 1 grafigi/jadvali/diagrammasi RASM sifatida ham "
    "berilishi mumkin. Shunday bo'lsa, talabaning tavsifi rasmdagi haqiqiy "
    "ma'lumotlarga (raqamlar, tendentsiyalar, taqqoslashlar) qanchalik mos "
    "kelishini tekshiring va bu Task Achievement bahosiga bevosita ta'sir "
    "qilsin — talaba rasmda yo'q narsani yozgan yoki asosiy tendentsiyani "
    "noto'g'ri tasvirlagan bo'lsa, buni aniq ayting.\n\n"

    "Faqat quyidagi JSON qaytaring, boshqa matn yozmang:\n"
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


# Speaking matn-mazmun tahlili (B8, sinovdan o'tgan prompt 2026-07-15) +
# B8.1: talaba Part turini tanlamaydi — AI kontekstdan aniqlaydi.
# Pronunciation BAHOLANMAYDI — u Azure vazifasi (Tezkor tahlil rejimida).
SPEAKING_SYSTEM_PROMPT = (
    "Siz professional IELTS Speaking imtihonchisiz. Sizga talabaning OG'ZAKI "
    "javobining matni (transkripsiya yoki yozma kiritilgan) beriladi. FAQAT "
    "quyidagi 3 mezon bo'yicha baholang. PRONUNCIATION (talaffuz)ni "
    "BAHOLAMANG — u alohida audio tizim orqali baholanadi.\n\n"

    "0) TURINI ANIQLANG: javob mazmunidan bu Part 1 (qisqa shaxsiy savollar), "
    "Part 2 (2 daqiqalik monolog — cue card tavsifi) yoki Part 3 (mavzu "
    "bo'yicha chuqurroq munozara) ekanini aniqlang, 'part_type'da yozing.\n\n"

    "1) TAHLIL (ball qo'yishdan oldin): 'analysis' maydonida har mezon "
    "bo'yicha 1 gaplik xulosa yozing.\n"
    "Band yo'riqnomasi: 4-5=ko'p pauza/takrorlash, oddiy bog'lovchilar, "
    "tez-tez xato; 6=tushunarli oqim lekin ba'zan ikkilanish, xato bor-yu "
    "tushunishga xalaqit bermaydi; 7=nisbatan erkin, moslashuvchan lug'at, "
    "xato kam; 8-9=deyarli erkin va tabiiy, murakkab til.\n\n"

    "2) MEZONLAR: fluency_coherence (nutq oqimi, discourse markerlar, "
    "izchillik), lexical_resource (so'z boyligi, idiomalar), "
    "grammatical_range (gap tuzilishi xilma-xilligi, og'zaki nutqda kichik "
    "xato kechiriladi, tizimli xato pasaytiradi).\n\n"

    "3) XATOLAR: faqat GRAMMATIK va LEKSIK xatolar. Har birini ANIQ shu "
    'formatda: "noto\'g\'ri qism -> to\'g\'ri qism (sabab)". Bir xil turdagi '
    "xato necha marta uchrasa, HAR BIRINI ALOHIDA yozing.\n\n"

    "4) TEKSHIRUV: xatolar ro'yxatini yozgach, matnni qayta o'qing — "
    "tashlab ketilgan xato bo'lsa qo'shing.\n\n"

    "5) KUCHLI TOMONLAR: 1-2 ta ijobiy narsani ko'rsating.\n\n"

    "Faqat quyidagi JSON qaytaring ('overall_band_no_pronunciation' — "
    "Pronunciation'siz 3 mezon o'rtachasi, yakuniy IELTS ball EMAS):\n"
    "{\n"
    '  "part_type": "part1 yoki part2 yoki part3",\n'
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


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model="gemini-3.1-flash-lite"):
        if not api_key:
            raise ProviderXatosi("Gemini API kaliti berilmagan")
        self.api_key = api_key
        self.model = model

    def _generate(self, system_prompt, matn, rasm_bytes=None, rasm_mime=None):
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        contents = matn
        if rasm_bytes:
            contents = [types.Part.from_bytes(data=rasm_bytes, mime_type=rasm_mime), matn]
        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=4096,
            ),
        )
        usage = response.usage_metadata
        return {
            "natija": javobni_parse_qil(response.text),
            "provider": self.name,
            "model": self.model,
            "input_tokens": usage.prompt_token_count or 0,
            "output_tokens": usage.candidates_token_count or 0,
        }

    def writing_baholash(self, matn, rasm_bytes=None, rasm_mime=None):
        return self._generate(WRITING_SYSTEM_PROMPT, matn, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn):
        return self._generate(SPEAKING_SYSTEM_PROMPT, matn)


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

    def writing_baholash(self, matn, rasm_bytes=None, rasm_mime=None):
        return self._generate(WRITING_SYSTEM_PROMPT, matn, rasm_bytes, rasm_mime)

    def speaking_matn_baholash(self, matn):
        return self._generate(SPEAKING_SYSTEM_PROMPT, matn)


def provider_tanla(user):
    """Foydalanuvchi uchun AI provider tanlaydi.

    Markaz faqat AI provayderni (Gemini/Claude) tanlaydi — API kalit har
    doim platforma (owner) kaliti orqali to'lanadi, markazlar o'z kalitini
    kirita olmaydi. Shunday qilib har bir Writing/Speaking tekshiruvi
    xarajati platformaga tushadi (2026-07-17'da shunday qaror qilingan).
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
