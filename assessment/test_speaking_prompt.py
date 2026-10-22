from django.test import SimpleTestCase

from assessment.providers import SPEAKING_SYSTEM_PROMPT


class SpeakingPromptTest(SimpleTestCase):
    """Matn-TZ 459: Speaking baholash prompti yangi examiner promptidan
    boshlanadi, JSON sxemasi esa (frontend uchun) saqlanadi."""

    def test_yangi_rol_matni(self):
        self.assertTrue(SPEAKING_SYSTEM_PROMPT.startswith(
            "You are an expert AI IELTS Speaking Examiner and Assessor"))
        self.assertIn("official IELTS Band Descriptors", SPEAKING_SYSTEM_PROMPT)

    def test_json_sxemasi_saqlangan(self):
        self.assertIn('"overall_band_no_pronunciation"', SPEAKING_SYSTEM_PROMPT)
        self.assertIn('"strengths"', SPEAKING_SYSTEM_PROMPT)
        self.assertNotIn("{question_text}", SPEAKING_SYSTEM_PROMPT)
