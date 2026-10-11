"""Foydalanuvchilar ro'yxatida qidiruv (2026-10-08, video IMG_2153).

Avval faqat login bo'yicha qidirardi — endi ism, familiya yoki login;
bir nechta so'z bo'lsa, har biri alohida mos kelishi kerak.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class FoydalanuvchiQidiruvTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(username="owner", password="x")
        self.fotima = User.objects.create_user(
            username="u9405778552", password="x", role=User.Role.STUDENT,
            first_name="Fotima", last_name="Nazrullayeva",
        )
        self.zuhra = User.objects.create_user(
            username="u940577855", password="x", role=User.Role.STUDENT,
            first_name="Zuhra", last_name="Nazrullayeva",
        )
        self.mijoz = APIClient()
        self.mijoz.force_authenticate(self.owner)

    def _qidir(self, q):
        j = self.mijoz.get("/api/foydalanuvchilar/", {"q": q})
        self.assertEqual(j.status_code, 200, j.data)
        return {x["id"] for x in j.data}

    def test_ism_boyicha(self):
        self.assertEqual(self._qidir("fot"), {self.fotima.id})

    def test_familiya_boyicha(self):
        self.assertEqual(self._qidir("nazrul"), {self.fotima.id, self.zuhra.id})

    def test_login_boyicha_avvalgidek(self):
        self.assertEqual(self._qidir("u9405778552"), {self.fotima.id})

    def test_familiya_va_ism_birga(self):
        self.assertEqual(self._qidir("Nazrullayeva Zuh"), {self.zuhra.id})
        self.assertEqual(self._qidir("  zuhra   nazrul "), {self.zuhra.id})

    def test_topilmasa_bosh(self):
        self.assertEqual(self._qidir("Fotima Zuhra"), set())
