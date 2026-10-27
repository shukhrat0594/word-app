"""AI Grammar Coach endpointi (2026-10-26, TZ 613). AI chaqiruvi mock."""

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .providers import (
    GRAMMAR_COACH_PROMPT,
    GRAMMAR_FOLLOWUP_PROMPT,
    GeminiProvider,
    grammar_coach_promt_tuz,
    grammar_followup_promt_tuz,
)

URL = "/api/grammar/coach/"


@override_settings(GEMINI_API_KEY="sinov-kalit")
class GrammarCoachTest(TestCase):
    def setUp(self):
        markaz = Markaz.objects.create(name="SINOV markaz")
        self.talaba = User.objects.create_user(
            username="sinov_talaba", password="Sinov!Parol2026",
            role=User.Role.STUDENT, markaz=markaz,
        )
        self.c = APIClient()
        self.c.force_authenticate(self.talaba)

    def test_kirmagan_foydalanuvchi_rad(self):
        self.assertEqual(APIClient().post(URL, {}, format="json").status_code, 401)

    def test_javob(self):
        with mock.patch.object(GeminiProvider, "grammar_coach_javob", return_value="### 📌 MAVZU") as m:
            javob = self.c.post(URL, {"matn": " Present Perfect ", "til": "Uzbek"}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["javob"], "### 📌 MAVZU")
        self.assertEqual(m.call_args.args, ("Present Perfect", "Uzbek"))

    def test_bosh_matn_rad(self):
        self.assertEqual(self.c.post(URL, {"matn": "  ", "til": "Uzbek"}, format="json").status_code, 400)

    def test_notogri_til_rad(self):
        self.assertEqual(self.c.post(URL, {"matn": "x", "til": "German"}, format="json").status_code, 400)

    def test_uzun_matn_rad(self):
        self.assertEqual(
            self.c.post(URL, {"matn": "a" * 1001, "til": "English"}, format="json").status_code, 400
        )

    def test_prompt_tz_bilan_va_qiymat_qoyiladi(self):
        self.assertTrue(GRAMMAR_COACH_PROMPT.startswith("You are an expert English Grammar Tutor"))
        promt = grammar_coach_promt_tuz("If I {target_language} known", "Russian")
        self.assertIn("- Student Input: If I {target_language} known", promt)
        self.assertIn('If Russian is "Russian"', promt)
        self.assertNotIn("{student_input}", promt)

    def test_followup_kontekst_bilan(self):
        with mock.patch.object(GeminiProvider, "grammar_coach_followup", return_value="Javob") as m, \
                mock.patch.object(GeminiProvider, "grammar_coach_javob") as asosiy:
            javob = self.c.post(
                URL, {"matn": " Nega had? ", "til": "Uzbek", "kontekst": " Tushuntirish "}, format="json"
            )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["javob"], "Javob")
        self.assertEqual(m.call_args.args, ("Tushuntirish", "Nega had?", "Uzbek"))
        asosiy.assert_not_called()

    def test_followup_uzun_kontekst_boshi_va_oxiri_qoladi(self):
        uzun = "MAVZU " + "x" * 40000 + " OXIRGI"
        with mock.patch.object(GeminiProvider, "grammar_coach_followup", return_value="J") as m:
            javob = self.c.post(URL, {"matn": "Savol", "til": "Uzbek", "kontekst": uzun}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        kontekst = m.call_args.args[0]
        self.assertTrue(kontekst.startswith("MAVZU "))
        self.assertTrue(kontekst.endswith(" OXIRGI"))
        self.assertLess(len(kontekst), 30100)

    def test_followup_notogri_kontekst_rad(self):
        self.assertEqual(
            self.c.post(URL, {"matn": "x", "til": "Uzbek", "kontekst": ["a"]}, format="json").status_code, 400
        )

    def test_followup_prompt_tz_bilan_va_qiymat_qoyiladi(self):
        self.assertTrue(GRAMMAR_FOLLOWUP_PROMPT.startswith("You are the AI Grammar Coach (Follow-up Mode)"))
        promt = grammar_followup_promt_tuz("ctx {followup_question}", "Q {target_language}", "Russian")
        self.assertIn("- Previous Explanation Context: ctx {followup_question}", promt)
        self.assertIn("- Student's Follow-up Question: Q {target_language}", promt)
        self.assertIn("Maintain the chosen language (Russian)", promt)
