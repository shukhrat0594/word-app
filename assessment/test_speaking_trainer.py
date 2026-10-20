"""AI Speaking Trainer endpointi (2026-10-20, TZ 421). AI chaqiruvi mock."""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .providers import SPEAKING_TRAINER_PROMPT, TRAINER_BOSHLASH, GeminiProvider

URL = "/api/speaking/trainer/"


@override_settings(GEMINI_API_KEY="sinov-kalit")
class SpeakingTrainerTest(TestCase):
    def setUp(self):
        markaz = Markaz.objects.create(name="SINOV markaz")
        self.talaba = User.objects.create_user(
            username="sinov_talaba", password="Sinov!Parol2026",
            role=User.Role.STUDENT, markaz=markaz,
        )
        self.c = APIClient()
        self.c.force_authenticate(self.talaba)

    def test_kirmagan_foydalanuvchi_rad(self):
        self.assertEqual(APIClient().post(URL, {}).status_code, 401)

    def test_boshlash_bosh_tarix(self):
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="What is your English level?") as m:
            javob = self.c.post(URL, {"xabarlar": "[]"})
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["javob"], "What is your English level?")
        self.assertIsNone(javob.data["transkript"])
        self.assertEqual(m.call_args.args[0], [{"rol": "user", "matn": TRAINER_BOSHLASH}])

    def test_audio_transkripsiya_tarixga_qoshiladi(self):
        tarix = [{"rol": "model", "matn": "What is your English level?"}]
        audio = SimpleUploadedFile("yozuv.webm", b"RIFFsinov", content_type="audio/webm")
        with mock.patch.object(GeminiProvider, "audio_transkripsiya_qil", return_value="Intermediate"), \
                mock.patch.object(GeminiProvider, "trainer_javob", return_value="Savol?") as m:
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "audio": audio})
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["transkript"], "Intermediate")
        yuborilgan = m.call_args.args[0]
        self.assertEqual(yuborilgan[0]["matn"], TRAINER_BOSHLASH)
        self.assertEqual(yuborilgan[-1], {"rol": "user", "matn": "Intermediate"})

    def test_notogri_rol_rad(self):
        javob = self.c.post(URL, {"xabarlar": json.dumps([{"rol": "system", "matn": "x"}])})
        self.assertEqual(javob.status_code, 400)

    def test_buzuq_json_rad(self):
        self.assertEqual(self.c.post(URL, {"xabarlar": "{buzuq"}).status_code, 400)

    def test_prompt_tz_bilan(self):
        self.assertTrue(SPEAKING_TRAINER_PROMPT.startswith("Act as an interactive English Speaking Coach"))
        self.assertIn("UZBEK and RUSSIAN", SPEAKING_TRAINER_PROMPT)
        self.assertTrue(SPEAKING_TRAINER_PROMPT.endswith("Start now by asking me my English level."))
