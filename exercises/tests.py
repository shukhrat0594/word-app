"""Mashq yechish testlari (2026-09-07 auditi).

Kunlik bepul limit ("har turdan 1 ta, keyin 500 so'm") mahsulotdan olib
tashlangan, lekin BACKENDDA qolib ketgan edi — talaba kunda ikkinchi
mashqni yechsa 429 va endi mavjud bo'lmagan to'lov haqidagi xabar
qaytardi. Quyidagi test cheklov qaytib kelmasligini qulflaydi.
"""

from django.core.cache import cache
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .models import Bolim, Mashq, MashqYechim, Tur

PAROL = "Sinov!Parol2026"


class KunlikLimitOlibTashlandiTest(TestCase):
    def setUp(self):
        # Login drosseli (10/daqiqa) testlar orasida saqlanib qolmasin.
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(
            username="talaba", password=PAROL, role=User.Role.STUDENT, markaz=self.markaz
        )
        self.mashqlar = [
            Mashq.objects.create(
                markaz=self.markaz,
                name=f"TFNG {i}",
                bolim=Bolim.READING,
                tur=Tur.TFNG,
                matn="Sinov matni",
                savollar=[{"savol": f"Savol {i}", "togri": "TRUE", "tur": "tfng"}],
            )
            for i in (1, 2, 3)
        ]

        self.client_ = APIClient()
        javob = self.client_.post(
            "/api/token/",
            {"username": "talaba", "password": PAROL, "qurilma_id": "q1"},
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.client_.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"])

    def _yech(self, mashq):
        return self.client_.post(
            f"/api/mashqlar/{mashq.id}/yechish/", {"javoblar": ["TRUE"]}, format="json"
        )

    def test_bir_kunda_bir_necha_mashq_yechish_mumkin(self):
        """Avval IKKINCHISI 429 bilan rad etilardi."""
        for i, mashq in enumerate(self.mashqlar, start=1):
            javob = self._yech(mashq)
            self.assertEqual(
                javob.status_code, 200, f"{i}-mashq rad etildi: {javob.data}"
            )
            self.assertEqual(javob.data["ball"], 1)
            self.assertEqual(javob.data["jami"], 1)

        self.assertEqual(MashqYechim.objects.filter(talaba=self.talaba).count(), 3)

    def test_bitta_mashqni_qayta_yechish_mumkin(self):
        """Bir xil mashqni qayta ishlash ham to'silmasligi kerak."""
        for _ in range(3):
            self.assertEqual(self._yech(self.mashqlar[0]).status_code, 200)
        self.assertEqual(MashqYechim.objects.count(), 3)

    def test_limit_endpointi_yoq(self):
        """`/api/limit/` marshruti butunlay olib tashlangan."""
        with self.assertRaises(NoReverseMatch):
            reverse("limit_holati")

    def test_notogri_javoblar_hamon_rad_etiladi(self):
        """Tozalash kirish tekshiruvini birga olib ketmaganini tasdiqlaydi."""
        javob = self.client_.post(
            f"/api/mashqlar/{self.mashqlar[0].id}/yechish/",
            {"javoblar": "ro'yxat emas"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400)
        self.assertEqual(MashqYechim.objects.count(), 0)
