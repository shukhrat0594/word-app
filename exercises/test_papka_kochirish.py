"""Papkani boshqa papka ichiga qo'shish / ajratib chiqarish (2026-10-28, TZ #652).

TZ #657 (qayta tekshiruv): "Cambridge 3" kabi ichida "Test 1..4" papkalari
bor papkalar ham "Cambridge" ichiga yig'ilishi kerak — chuqurlik 3.
"""

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

    def test_ichki_papkasi_bor_papka_ham_kiradi(self):
        # TZ #657: asl holat — Cambridge 3 ichida Test 1 bor.
        t1 = TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.c3)
        javob = self.kochir(self.c3, self.cambridge.id)
        self.assertEqual(javob.status_code, 200, javob.data)
        self.c3.refresh_from_db()
        t1.refresh_from_db()
        self.assertEqual(self.c3.parent_id, self.cambridge.id)
        self.assertEqual(t1.parent_id, self.c3.id)
        self.assertEqual(t1.daraja, 3)

    def test_chuqurlik_3_dan_oshmaydi(self):
        TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.c3)
        self.kochir(self.c3, self.cambridge.id)
        c5 = TestPapkasi.objects.create(nomi="SINOV Cambridge 5", markaz=self.markaz)
        TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=c5)
        # Cambridge › Cambridge 3 › Cambridge 5 › Test 1 — 4 daraja.
        self.assertEqual(self.kochir(c5, self.c3.id).status_code, 400)

    def test_ichki_papkaga_qoshish(self):
        ichki = TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.cambridge)
        # Bo'sh ichki papka — 3-daraja bo'lib kira oladi.
        self.assertEqual(self.kochir(self.c3, ichki.id).status_code, 200)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.daraja, 3)
        # 3-darajali papka ichiga — yo'q.
        boshqa = TestPapkasi.objects.create(nomi="SINOV boshqa", markaz=self.markaz)
        self.assertEqual(self.kochir(boshqa, self.c3.id).status_code, 400)

    def test_ozini_yoki_avlodini_nishon_qilib_bolmaydi(self):
        self.assertEqual(self.kochir(self.c3, self.c3.id).status_code, 400)
        self.kochir(self.c3, self.cambridge.id)
        self.assertEqual(self.kochir(self.cambridge, self.c3.id).status_code, 400)

    def test_testli_mock_papkasiga_papka_kirmaydi(self):
        ichki = TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.cambridge)
        ImtihonTest.objects.create(name="SINOV R", bolim=Bolim.READING, markaz=self.markaz, papka=ichki)
        self.assertEqual(self.kochir(self.c3, ichki.id).status_code, 400)
        javob = self.admin.post("/api/imtihon/papkalar/", {"nomi": "SINOV x", "parent": ichki.id}, format="json")
        self.assertEqual(javob.status_code, 400)

    def test_bir_bolimdan_ikki_test_bolsa_rad(self):
        for i in range(2):
            ImtihonTest.objects.create(name=f"SINOV {i}", bolim=Bolim.READING, markaz=self.markaz, papka=self.c3)
        self.assertEqual(self.kochir(self.c3, self.cambridge.id).status_code, 400)

    def test_ichida_papkasi_bor_papkada_bolim_cheklovi_yoq(self):
        # Cambridge › Cambridge 3 (ichida Test 1) — Mock papkasi emas.
        TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.c3)
        self.kochir(self.c3, self.cambridge.id)
        for i in range(2):
            ImtihonTest.objects.create(name=f"SINOV {i}", bolim=Bolim.READING, markaz=self.markaz, papka=self.c3)
        self.assertEqual(self.kochir(self.c3, None).status_code, 200)
        self.assertEqual(self.kochir(self.c3, self.cambridge.id).status_code, 200)
        t = ImtihonTest.objects.create(name="SINOV 3", bolim=Bolim.READING, markaz=self.markaz)
        javob = self.admin.patch(f"/api/imtihon/testlar-boshqaruv/{t.id}/", {"papka": self.c3.id}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)

    def test_ichki_papka_yaratish_3_darajagacha(self):
        self.kochir(self.c3, self.cambridge.id)
        javob = self.admin.post("/api/imtihon/papkalar/", {"nomi": "SINOV Test 1", "parent": self.c3.id}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        javob = self.admin.post("/api/imtihon/papkalar/", {"nomi": "SINOV x", "parent": javob.data["id"]}, format="json")
        self.assertEqual(javob.status_code, 400)

    def test_mock_sahifasi_va_eksport_3_darajada(self):
        t1 = TestPapkasi.objects.create(nomi="SINOV Test 1", markaz=self.markaz, parent=self.c3)
        for b in (Bolim.READING, Bolim.LISTENING, Bolim.WRITING, Bolim.SPEAKING):
            t = ImtihonTest.objects.create(name=f"SINOV {b}", bolim=b, markaz=self.markaz)
            self.admin.patch(f"/api/imtihon/testlar-boshqaruv/{t.id}/", {"papka": t1.id}, format="json")
        self.assertEqual(self.kochir(self.c3, self.cambridge.id).status_code, 200)

        javob = self.admin.get("/api/imtihon-mock/papkalar/")
        self.assertEqual(javob.status_code, 200)
        guruhlar = {g["nomi"]: [i["nomi"] for i in g["ichki"]] for g in javob.data["papkalar"]}
        self.assertEqual(guruhlar, {"SINOV Cambridge 3": ["SINOV Test 1"]})

        javob = self.admin.get(f"/api/imtihon/papkalar/{self.cambridge.id}/eksport/?sanoq=1")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob.data["jami"], 4)

    def test_nomni_tahrirlash_ishlaydi(self):
        javob = self.admin.patch(f"/api/imtihon/papkalar/{self.c3.id}/", {"nomi": "SINOV yangi"}, format="json")
        self.assertEqual(javob.status_code, 200)
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.nomi, "SINOV yangi")
        self.assertIsNone(self.c3.parent_id)
