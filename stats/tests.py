from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Markaz
from exercises.models import Bolim, Mashq, MashqYechim, Tur

from .services import talaba_statistikasi

User = get_user_model()


class KonikmalarRadarTest(TestCase):
    """Bosh sahifadagi 'Ko'nikmalar' radar diagrammasida hamma o'q (Writing,
    Speaking, Listening, Reading) IELTS band (0-9) shkalasida bo'lishi kerak
    — avval Listening/Reading foiz (0-100) bilan hisoblanardi, bu diagramma
    chekkasini (9 ball) noto'g'ri ko'rsatardi (video-TZ: IMG_2140.MOV)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="Test markaz")
        self.talaba = User.objects.create_user(
            username="talaba1", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )

    def _mashq(self, bolim):
        return Mashq.objects.create(
            name="Test mashq", bolim=bolim, tur=Tur.MULTIPLE_CHOICE, markaz=self.markaz,
        )

    def test_yuqori_natija_band_9(self):
        """39/40 to'g'ri (97.5%) — band jadvali bo'yicha 9.0, foiz emas."""
        mashq = self._mashq(Bolim.READING)
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=mashq, javoblar={}, ball=39, jami=40, natijalar=[],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["ortacha_band"], 9.0)
        self.assertEqual(stat["konikmalar"]["reading_band"], 9.0)
        self.assertNotIn("reading_foiz", stat["konikmalar"])
        # Foiz eski joyida (OtaOna sahifasi, CRM kunlik xabar) o'zgarmagan qoladi.
        self.assertEqual(stat["reading"]["ortacha_foiz"], 98)

    def test_past_natija_band_ham_past(self):
        """4/10 to'g'ri -> 40 savolga moslashtirilsa 16 ball -> band 5.0."""
        mashq = self._mashq(Bolim.LISTENING)
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=mashq, javoblar={}, ball=4, jami=10, natijalar=[],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["konikmalar"]["listening_band"], 5.0)

    def test_yechim_yoq_bolsa_band_none(self):
        stat = talaba_statistikasi(self.talaba)
        self.assertIsNone(stat["konikmalar"]["listening_band"])
        self.assertIsNone(stat["konikmalar"]["reading_band"])
