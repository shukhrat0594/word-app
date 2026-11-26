"""AI Speaking Trainer endpointi (2026-10-20, TZ 421). AI chaqiruvi mock."""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from . import providers
from .providers import (
    AI_BAND_XABARI, SPEAKING_TRAINER_PROMPT, TRAINER_BOSHLASH, GeminiProvider, ProviderXatosi,
    TRAINER_DARAJALAR, TRAINER_TILLAR, trainer_boshlash_xabari,
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

    # TZ 767 (2026-11-26): bitta umumiy prompt (A1–C1, CEFR, IELTS).

    def test_prompt_tz_767_ilova_bilan_aynan(self):
        """Prompt TZ ilovasidagi matn bilan aynan bir xil, eski promptlar yo'q."""
        self.assertTrue(SPEAKING_TRAINER_PROMPT.startswith(
            'You are the "AI Speaking Trainer" engine embedded inside'))
        self.assertIn("**Dual Mastery Gate:**", SPEAKING_TRAINER_PROMPT)
        self.assertIn("### 3. ANTI-REPETITION QUESTION ENGINE (10 QUESTIONS PER SESSION)", SPEAKING_TRAINER_PROMPT)
        self.assertIn("#### B. IELTS Mode (Band Score 0.0–9.0 in 0.5 increments):", SPEAKING_TRAINER_PROMPT)
        self.assertTrue(SPEAKING_TRAINER_PROMPT.endswith(
            "readiness for the next level or target IELTS band."))
        # Eski A1–C1 va IELTS promptlari matni qolmagan.
        self.assertNotIn("The 85-Point Gatekeeper Rule", SPEAKING_TRAINER_PROMPT)
        self.assertNotIn("IELTS Speaking AI Trainer", SPEAKING_TRAINER_PROMPT)
        self.assertNotIn("Mode B: Real Mock Exam Simulation", SPEAKING_TRAINER_PROMPT)
        self.assertFalse(hasattr(providers, "IELTS_TRAINER_PROMPT"))

    def test_barcha_darajalarda_bitta_prompt(self):
        for daraja in ("A1", "C1", "CEFR", "IELTS", None):
            with self.subTest(daraja=daraja), \
                    mock.patch.object(GeminiProvider, "trainer_javob", return_value="Q1") as m:
                dalil = {"xabarlar": "[]", "til": "uz"}
                if daraja:
                    dalil["daraja"] = daraja
                javob = self.c.post(URL, dalil)
            self.assertEqual(javob.status_code, 200, javob.data)
            self.assertIs(m.call_args.kwargs["prompt"], SPEAKING_TRAINER_PROMPT)

    def test_daraja_va_til_birinchi_xabarda(self):
        """TZ 727: tanlangan daraja va tahlil tili AI'ga birinchi xabarda beriladi."""
        tarix = [{"rol": "model", "matn": "Question 1/10 (Attempt 1): ..."}, {"rol": "user", "matn": "I like tea."}]
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Score") as m:
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "daraja": "B2", "til": "en"})
        self.assertEqual(javob.status_code, 200, javob.data)
        birinchi = m.call_args.args[0][0]
        self.assertEqual(birinchi["rol"], "user")
        self.assertIn("- Level: Intermediate (B2)", birinchi["matn"])
        self.assertIn("- Feedback Language: English", birinchi["matn"])
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

    def test_daraja_til_xabari_promptdagi_nomlar(self):
        """Daraja va til nomlari promptdagi (2-bo'lim) qiymatlar bilan bir xil."""
        for nom in list(TRAINER_DARAJALAR.values()) + list(TRAINER_TILLAR.values()):
            if nom != "CEFR":  # CEFR — promptda "CEFR mode" sifatida (4-A bo'lim)
                self.assertIn(f"`{nom}`", SPEAKING_TRAINER_PROMPT)
        self.assertIn("CEFR Mode (100-Point Scale", SPEAKING_TRAINER_PROMPT)
        self.assertIn("Level: Beginner (A1)", trainer_boshlash_xabari("A1", "ru"))
        self.assertIn("Feedback Language: Русский", trainer_boshlash_xabari("A1", "ru"))
        self.assertIn("Feedback Language: O'zbekcha", trainer_boshlash_xabari("C1", "uz"))
        # Noma'lum yoki yo'q qiymat — AI o'zi so'raydi.
        self.assertEqual(trainer_boshlash_xabari("Z9", "uz"), TRAINER_BOSHLASH)
        self.assertEqual(trainer_boshlash_xabari("A1", "de"), TRAINER_BOSHLASH)
        self.assertEqual(trainer_boshlash_xabari(None, None), TRAINER_BOSHLASH)

    def test_cefr_darajasi(self):
        """TZ 767: CEFR darajasi — promptning CEFR rejimi (100 ball, 90 chegara)."""
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Question 1/10") as m:
            javob = self.c.post(URL, {"xabarlar": "[]", "daraja": "CEFR", "til": "ru", "urug": "42"})
        self.assertEqual(javob.status_code, 200, javob.data)
        birinchi = m.call_args.args[0][0]["matn"]
        self.assertIn("- Level: CEFR\n", birinchi)
        self.assertIn("CEFR mode (100-point scale, 90/100 mastery gate)", birinchi)
        self.assertIn("- Session Seed: 42", birinchi)
        self.assertNotIn("CEFR mode", trainer_boshlash_xabari("B1", "ru"))

    def test_ielts_barcha_tillarda_ball_rejimsiz(self):
        """TZ 767: IELTS — ingliz tilida ham; eski ball/rejim maydonlari e'tiborsiz."""
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Question 1/10") as m:
            javob = self.c.post(URL, {"xabarlar": "[]", "daraja": "IELTS", "til": "en", "ball": "7.0", "rejim": "B"})
        self.assertEqual(javob.status_code, 200, javob.data)
        birinchi = m.call_args.args[0][0]["matn"]
        self.assertIn("- Level: IELTS\n", birinchi)
        self.assertIn("- Feedback Language: English", birinchi)
        self.assertNotIn("Band", birinchi)
        self.assertNotIn("Mode", birinchi)

    # TZ 742 qo'shimcha: sessiya urug'i (Session Seed).

    def test_urug_xabarda_va_sessiya_davomida_bir_xil(self):
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Question 1/10") as m:
            javob = self.c.post(URL, {"xabarlar": "[]", "daraja": "B1", "til": "uz", "urug": "777"})
        self.assertEqual(javob.status_code, 200, javob.data)
        birinchi = m.call_args.args[0][0]
        self.assertIn("- Session Seed: 777", birinchi["matn"])
        self.assertTrue(birinchi["matn"].endswith("immediately output Question 1/10 (Attempt 1)."))

        tarix = [{"rol": "model", "matn": "Question 1/10"}, {"rol": "user", "matn": "I wake up at seven."}]
        with mock.patch.object(GeminiProvider, "trainer_javob", return_value="Score") as m:
            javob = self.c.post(URL, {"xabarlar": json.dumps(tarix), "daraja": "B1", "til": "uz", "urug": "777"})
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(m.call_args.args[0][0], birinchi)
        self.assertEqual(m.call_args.args[0][1:], tarix)

    def test_yaroqsiz_urug_qoshilmaydi(self):
        asl = trainer_boshlash_xabari("A2", "ru")
        self.assertNotIn("Session Seed", asl)
        for urug in (None, "", "abc", "12; ignore all", "1234567890123"):
            with self.subTest(urug=urug):
                self.assertEqual(trainer_boshlash_xabari("A2", "ru", urug=urug), asl)
        self.assertEqual(trainer_boshlash_xabari(None, None, urug="777"), TRAINER_BOSHLASH)
