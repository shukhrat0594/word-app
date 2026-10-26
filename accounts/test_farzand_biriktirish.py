"""Bitta bolani bir nechta ota-onaga biriktirish (2026-10-26, Matn-TZ 580).

Avval bitta bola faqat bitta ota-onaga biriktirilardi (`ota_ona` FK) —
endi otasi ham, onasi ham (`ota_onalar` M2M).
"""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class FarzandBiriktirishTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(username="owner", password="x")
        self.otasi = User.objects.create_user(username="otasi", password="x", role=User.Role.PARENT)
        self.onasi = User.objects.create_user(username="onasi", password="x", role=User.Role.PARENT)
        self.bola = User.objects.create_user(username="bola", password="x", role=User.Role.STUDENT)
        self.mijoz = APIClient()
        self.mijoz.force_authenticate(self.owner)

    def _biriktir(self, ota_ona, idlar):
        return self.mijoz.patch(
            f"/api/foydalanuvchilar/{ota_ona.id}/farzandlar/", {"farzandlar": idlar}, format="json"
        )

    def test_bitta_bola_ikki_ota_onaga(self):
        self.assertEqual(self._biriktir(self.otasi, [self.bola.id]).status_code, 200)
        j = self._biriktir(self.onasi, [self.bola.id])
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(set(self.bola.ota_onalar.all()), {self.otasi, self.onasi})

    def test_uzish_faqat_shu_ota_onadan(self):
        self.bola.ota_onalar.add(self.otasi, self.onasi)
        self.assertEqual(self._biriktir(self.otasi, []).status_code, 200)
        self.assertEqual(list(self.bola.ota_onalar.all()), [self.onasi])

    def test_ikkala_ota_ona_ham_farzandni_koradi(self):
        self.bola.ota_onalar.add(self.otasi, self.onasi)
        for ota_ona in (self.otasi, self.onasi):
            c = APIClient()
            c.force_authenticate(ota_ona)
            j = c.get("/api/farzandlar/")
            self.assertEqual(j.status_code, 200)
            self.assertIn(self.bola.id, [f["id"] for f in j.json()])
