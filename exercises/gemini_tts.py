"""Gemini TTS orqali listening audio generatsiya qilish (2026-07-20).

Ikki model ishlatiladi (Shukhrat bilan kelishilgan): `gemini-2.5-flash-preview-tts`
oddiyroq/qisqa dialoglar uchun, `gemini-3.1-flash-tts-preview` murakkabroq
dialoglar uchun. Bepul tarif juda cheklangan (RPD=10/kun, RPM=3/daqiqa,
HAR BIR MODEL UCHUN ALOHIDA) — limit tugasa `RateLimitTugadi` chiqadi,
chaqiruvchi kod shuni ushlab TO'XTASHI kerak (pullik tarifga o'tmaslik
uchun, 2026-07-20 qarori).
"""

import base64
import io
import wave

from django.conf import settings
from google import genai
from google.genai._gaos.lib.compat_errors import RateLimitError


class RateLimitTugadi(Exception):
    """Bepul kunlik/daqiqalik limit tugadi — generatsiyani to'xtatish kerak."""


def _pcm_dan_wav(pcm_bytes):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def audio_yarat(matn, model, speakerlar=None):
    """Transkriptdan audio (WAV bytes) generatsiya qiladi.

    matn — TTS matni. Ko'p ovozli bo'lsa "Speaker1: ...\\nSpeaker2: ..."
    formatida yozilgan bo'lishi kerak (promt avtomatik "TTS the following
    conversation..." bilan o'raladi — buni bermasa model matnga JAVOB
    berishga urinadi, ovozlashtirmaydi).
    speakerlar — [(speaker_nomi, voice_nomi), ...] — berilsa ko'p ovozli
    (max 2), aks holda bitta ovozli ("Kore").
    """
    if speakerlar:
        speech_config = [{"speaker": s, "voice": v} for s, v in speakerlar]
        nomlar = " and ".join(s for s, _ in speakerlar)
        promt = f"TTS the following conversation between {nomlar} exactly as written:\n{matn}"
    else:
        speech_config = [{"voice": "Kore"}]
        promt = matn

    try:
        with genai.Client(api_key=settings.GEMINI_API_KEY) as client:
            resp = client.interactions.create(
                model=model,
                input=promt,
                response_format={"type": "audio"},
                generation_config={"speech_config": speech_config},
            )
    except RateLimitError as e:
        raise RateLimitTugadi(str(e)) from e

    if not resp.output_audio:
        raise RuntimeError("Gemini javobida audio yo'q")
    pcm = base64.b64decode(resp.output_audio.data)
    return _pcm_dan_wav(pcm)
