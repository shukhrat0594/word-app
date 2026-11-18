"""AI Speaking Trainer endpointi (2026-10-20, TZ 421). AI chaqiruvi mock."""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .providers import (
    AI_BAND_XABARI, SPEAKING_TRAINER_PROMPT, TRAINER_BOSHLASH, GeminiProvider, ProviderXatosi,
    IELTS_TRAINER_PROMPT, trainer_boshlash_xabari, trainer_prompti,
)

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

    def test_transkripsiya_503_qayta_urinadi(self):
        """TZ 434: 503 UNAVAILABLE (model band) — qayta uriladi."""
        xato = Exception("503 UNAVAILABLE. high demand")
        xato.code = 503
        javob = mock.Mock(text=" Intermediate ")
        client = mock.Mock()
        client.models.generate_content.side_effect = [xato, javob]
        with mock.patch("google.genai.Client", return_value=client), \
                mock.patch("assessment.providers.time.sleep"):
            matn = GeminiProvider("sinov-kalit").audio_transkripsiya_qil(b"RIFFsinov")
        self.assertEqual(matn, "Intermediate")
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_transkripsiya_503_tushunarli_xabar(self):
        xato = Exception("503 UNAVAILABLE. high demand")
        xato.code = 503
        client = mock.Mock()
        client.models.generate_content.side_effect = xato
        with mock.patch("google.genai.Client", return_value=client), \
                mock.patch("assessment.providers.time.sleep"):
            with self.assertRaises(ProviderXatosi) as ctx:
                GeminiProvider("sinov-kalit").audio_transkripsiya_qil(b"RIFFsinov")
        self.assertEqual(str(ctx.exception), AI_BAND_XABARI)

    def test_prompt_tz_bilan(self):
        """TZ 727: prompt TZ ilovasidagi yangi matn bilan almashtirilgan."""
        self.assertTrue(SPEAKING_TRAINER_PROMPT.startswith('You are the "Speaking AI Trainer"'))
        self.assertIn("STRICT 2-STEP MASTERY CYCLE", SPEAKING_TRAINER_PROMPT)
        self.assertIn("The 85-Point Gatekeeper Rule", SPEAKING_TRAINER_PROMPT)
        self.assertTrue(SPEAKING_TRAINER_PROMPT.endswith("readiness for the next CEFR level."))
        self.assertNotIn("Act as an interactive English Speaking Coach", SPEAKING_TRAINER_PROMPT)

    def test_daraja_va_til_birinchi_xabarda(self):
        """TZ 727: tanlangan daraja va tahlil tili AI'ga birinchi xabarda beriladi."""
        tarix = [{"rol": "model", "matn": "Question 1/10 (Attempt 1): ..."}, {"rol": "user", "matn": "I like tea."}]
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Score") as m:
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "daraja": "B2", "til": "en"})
        self.assertEqual(javob.status_code, 200, javob.data)
        birinchi = m.call_args.args[0][0]
        self.assertEqual(birinchi["rol"], "user")
        self.assertIn("Intermediate (B2)", birinchi["matn"])
        self.assertIn("Feedback Language: English", birinchi["matn"])
        self.assertEqual(m.call_args.args[0][1:], tarix)

    def test_10_savollik_uzun_suhbat_sigadi(self):
        """TZ 727: 10 savol, har biriga 5 urinish (100 xabar) — rad etilmaydi; undan uzuni — 400."""
        tarix = [{"rol": "model" if i % 2 == 0 else "user", "matn": f"x{i}"} for i in range(100)]
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Passed!"):
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "daraja": "A1", "til": "uz"})
        self.assertEqual(javob.status_code, 200, javob.data)
        tarix.append({"rol": "model", "matn": "ortiqcha"})
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Passed!") as m:
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "daraja": "A1", "til": "uz"})
        self.assertEqual(javob.status_code, 400)
        m.assert_not_called()

    def test_daraja_til_xabari_variantlari(self):
        self.assertIn("Russian", trainer_boshlash_xabari("A1", "ru"))
        self.assertIn("Beginner (A1)", trainer_boshlash_xabari("A1", "ru"))
        self.assertIn("Uzbek", trainer_boshlash_xabari("C1", "uz"))
        # Noma'lum yoki yo'q qiymat — AI o'zi so'raydi (eski xatti-harakat).
        self.assertEqual(trainer_boshlash_xabari("Z9", "uz"), TRAINER_BOSHLASH)
        self.assertEqual(trainer_boshlash_xabari("A1", "de"), TRAINER_BOSHLASH)
        self.assertEqual(trainer_boshlash_xabari(None, None), TRAINER_BOSHLASH)

    def test_ielts_alohida_prompt(self):
        """TZ 733: IELTS darajasida IELTS prompti, ball va rejim AI'ga beriladi."""
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Part 1 — Step 1/10") as m:
            javob = self.c.post(URL, {"xabarlar": "[]", "daraja": "IELTS", "til": "ru", "ball": "7.0", "rejim": "B"})
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertIs(m.call_args.kwargs["prompt"], IELTS_TRAINER_PROMPT)
        birinchi = m.call_args.args[0][0]["matn"]
        self.assertIn("Feedback Language: Russian", birinchi)
        self.assertIn("Target IELTS Band Score: Band 7.0", birinchi)
        self.assertIn("Mode B: Real Mock Exam Simulation", birinchi)

    def test_boshqa_darajalarda_eski_prompt(self):
        """TZ 733: IELTS bo'lmagan darajalarda prompt o'zgarmagan."""
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Q1") as m:
            self.c.post(URL, {"xabarlar": "[]", "daraja": "C1", "til": "uz"})
        self.assertIs(m.call_args.kwargs["prompt"], SPEAKING_TRAINER_PROMPT)
        self.assertIs(trainer_prompti(None), SPEAKING_TRAINER_PROMPT)

    def test_ielts_prompt_tz_bilan(self):
        self.assertTrue(IELTS_TRAINER_PROMPT.startswith('You are the "IELTS Speaking AI Trainer"'))
        self.assertIn("GATEKEEPER RULE (CRITICAL)", IELTS_TRAINER_PROMPT)
        self.assertTrue(IELTS_TRAINER_PROMPT.endswith("realistic exam-day advice."))

    def test_ielts_toliq_tanlanmasa_ai_ozi_soraydi(self):
        self.assertEqual(trainer_boshlash_xabari("IELTS", "uz", "7.0", None), TRAINER_BOSHLASH)
        self.assertEqual(trainer_boshlash_xabari("IELTS", "uz", "9.0", "A"), TRAINER_BOSHLASH)
        # IELTS prompti tahlilni faqat o'zbek/rus tilida beradi.
        self.assertEqual(trainer_boshlash_xabari("IELTS", "en", "7.0", "A"), TRAINER_BOSHLASH)
        self.assertIn("Mode A", trainer_boshlash_xabari("IELTS", "uz", "8.0", "A"))
