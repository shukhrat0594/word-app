from django.test import TestCase

from accounts.models import Markaz, User
from exercises.models import ImtihonTest, TestYechim
from stats.services import talaba_statistikasi


class ReadingListeningDinamikaTest(TestCase):
    """2026-10-06: Reading/Listening uchun ham Writing/Speaking kabi har
    urinish bo'yicha band dinamikasi (video-TZ: 4 ko'nikma uchun alohida
    grafik)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="M")
        self.talaba = User.objects.create_user(
            username="ali", password="x", role=User.Role.STUDENT
        )
        self.test_r = ImtihonTest.objects.create(
            name="Cambridge 11 Test 1 Reading", bolim="reading", markaz=self.markaz
        )
        self.test_l = ImtihonTest.objects.create(
            name="Cambridge 11 Test 1 Listening", bolim="listening", markaz=self.markaz
        )

    def test_reading_dinamika_band_bilan(self):
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_r, javoblar={}, ball=30, jami=40,
            natijalar={}, band="7.0",
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["soni"], 1)
        self.assertEqual(stat["reading"]["oxirgi_band"], 7.0)
        self.assertEqual(stat["reading"]["dinamika"][0]["test_nomi"], "Cambridge 11 Test 1 Reading")

    def test_listening_dinamika_oxirgi_urinish(self):
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_l, javoblar={}, ball=20, jami=40,
            natijalar={}, band="5.0",
        )
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_l, javoblar={}, ball=35, jami=40,
            natijalar={}, band="8.0",
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["listening"]["soni"], 2)
        self.assertEqual(stat["listening"]["oxirgi_band"], 8.0)

    def test_hech_narsa_yechilmagan_bolsa_bosh(self):
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["dinamika"], [])
        self.assertIsNone(stat["reading"]["oxirgi_band"])
