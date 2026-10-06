from django.test import TestCase

from accounts.models import Markaz, User
from exercises.models import Bolim, Mashq, MashqYechim, Tur

from .services import talaba_statistikasi


class StatistikaDinamikaTest(TestCase):
    """B6: Reading/Listening uchun ham Writing/Speaking kabi har bir
    bajarilgan mashq natijasi bo'yicha chiziqli (dinamika) grafik
    ma'lumoti qaytishi kerak (video-TZ, 2026-10-06)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(
            username="talaba",
            password="Sinov!Parol2026",
            role=User.Role.STUDENT,
            markaz=self.markaz,
        )
        self.mashq = Mashq.objects.create(
            markaz=self.markaz,
            name="Reading 1",
            bolim=Bolim.READING,
            tur=Tur.TFNG,
            matn="Sinov matni",
            savollar=[{"savol": "S1", "togri": "TRUE", "tur": "tfng"}],
        )

    def test_reading_dinamika_har_mashq_boyicha_foiz(self):
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=self.mashq, javoblar=["TRUE"],
            ball=1, jami=1, natijalar=[True],
        )
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=self.mashq, javoblar=["FALSE"],
            ball=0, jami=1, natijalar=[False],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(len(stat["reading"]["dinamika"]), 2)
        self.assertEqual(stat["reading"]["dinamika"][0]["foiz"], 100)
        self.assertEqual(stat["reading"]["dinamika"][1]["foiz"], 0)
        self.assertEqual(stat["listening"]["dinamika"], [])
