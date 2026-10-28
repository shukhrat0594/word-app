"""Papkani boshqa papka ichiga qo'shish / ajratib chiqarish (2026-10-28, TZ #652)."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Markaz, User
from exercises.models import Bolim, ImtihonTest, TestPapkasi


class PapkaKochirishTest(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.admin = APIClient()
        self.admin.force_authenticate(User.objects.create_user(username="adm", password="x", role=User.Role.ADMIN))
        self.cambridge = TestPapkasi.objects.create(nomi="SINOV Cambridge", markaz=self.markaz)
        self.c3 = TestPapkasi.objects.create(nomi="SINOV Cambridge 3", markaz=self.markaz)

    def kochir(self, papka, parent):
        return self.admin.patch(f"/api/imtihon/papkalar/{papka.id}/", {"parent": parent}, format="json")

    def test_ichiga_qoshish_va_ajratish(self):
        javob = self.kochir(self.c3, self.cambridge.id)
        self.assertEqual(javob.status_code, 200, javob.data)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.parent_id, self.cambridge.id)

        javob = self.kochir(self.c3, None)
        self.assertEqual(javob.status_code, 200, javob.data)
        self.c3.refresh_from_db()
        self.assertIsNone(self.c3.parent_id)

    def test_nomi_ozgarmaydi_faqat_parent(self):
        self.kochir(self.c3, self.cambridge.id)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.nomi, "SINOV Cambridge 3")

    def test_ichki_papkasi_bor_papka_kira_olmaydi(self):
        TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.c3)
        javob = self.kochir(self.c3, self.cambridge.id)
        self.assertEqual(javob.status_code, 400)

    def test_ichki_papkaga_qoshib_bolmaydi(self):
        ichki = TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.cambridge)
        self.assertEqual(self.kochir(self.c3, ichki.id).status_code, 400)
        self.assertEqual(self.kochir(self.c3, self.c3.id).status_code, 400)

    def test_bir_bolimdan_ikki_test_bolsa_rad(self):
        for i in range(2):
            ImtihonTest.objects.create(name=f"SINOV {i}", bolim=Bolim.READING, markaz=self.markaz, papka=self.c3)
        self.assertEqual(self.kochir(self.c3, self.cambridge.id).status_code, 400)

    def test_nomni_tahrirlash_ishlaydi(self):
        javob = self.admin.patch(f"/api/imtihon/papkalar/{self.c3.id}/", {"nomi": "SINOV yangi"}, format="json")
        self.assertEqual(javob.status_code, 200)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.nomi, "SINOV yangi")
        self.assertIsNone(self.c3.parent_id)
