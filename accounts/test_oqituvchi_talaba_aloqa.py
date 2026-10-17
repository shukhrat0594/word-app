"""O'qituvchi o'z guruhidagi talabaning aloqa ma'lumotini ko'radi
(2026-10-17, video-TZ): telefon, ota-onasining ismi va telefoni.
Qolgan shaxsiy maydonlar (tug'ilgan sana, manba, izoh) — faqat adminga."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from academics.models import Guruh
from .models import Markaz, User


class OqituvchiTalabaAloqaTest(TestCase):
    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="SINOV markaz")
        self.oqituvchi = User.objects.create_user(
            username="sinov_oqituvchi", password="x", role=User.Role.TEACHER, markaz=self.markaz
        )
        self.talaba = User.objects.create_user(
            username="sinov_talaba", password="x", role=User.Role.STUDENT,
            telefon="+998901112233", ota_ona_telefon="+998907778899",
            ota_ona_ismi="SINOV Ota", izoh="maxfiy izoh",
        )
        guruh = Guruh.objects.create(name="SINOV guruh", markaz=self.markaz, oqituvchi=self.oqituvchi)
        guruh.talabalar.add(self.talaba)
        self.client = APIClient()

    def test_oqituvchi_aloqa_maydonlarini_koradi(self):
        self.client.force_authenticate(self.oqituvchi)
        res = self.client.get("/api/talabalar/")
        self.assertEqual(res.status_code, 200)
        t = res.json()[0]
        self.assertEqual(t["telefon"], "+998901112233")
        self.assertEqual(t["ota_ona_telefon"], "+998907778899")
        self.assertEqual(t["ota_ona_ismi"], "SINOV Ota")
        self.assertNotIn("izoh", t)
        self.assertNotIn("tugilgan_sana", t)
