"""Qurilma cookie'si: brauzer tarixi/localStorage tozalansa ham qurilma
"yangi" bo'lib qolmasin (2026-10-02). Cookie ham tozalansa — eskicha."""

from rest_framework.test import APIClient

from accounts.models import User
from accounts.tests import PAROL, DrosselsizTest


class QurilmaCookieTest(DrosselsizTest):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="qurilmachi", password=PAROL, role=User.Role.STUDENT)

    def kirish(self, client, qurilma):
        return client.post(
            "/api/token/", {"username": "qurilmachi", "password": PAROL, "qurilma_id": qurilma}, format="json"
        )

    def test_birinchi_kirishda_cookie_beriladi(self):
        j = self.kirish(APIClient(), "asl-qurilma-1")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["qurilma_id"], "asl-qurilma-1")
        c = j.cookies["qurilma"]
        self.assertEqual(c.value, "asl-qurilma-1")
        self.assertTrue(c["httponly"])
        self.assertEqual(c["samesite"], "Lax")

    def test_localstorage_tozalansa_cookie_qurilmani_taniydi(self):
        brauzer = APIClient()
        self.kirish(brauzer, "asl-qurilma-1")  # cookie klientda qoladi
        # localStorage tozalandi: tanada YANGI tasodifiy ID, cookie esa joyida
        j = self.kirish(brauzer, "butunlay-yangi-id")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["qurilma_id"], "asl-qurilma-1")  # frontend shuni qayta saqlaydi
        self.user.refresh_from_db()
        self.assertEqual(self.user.qurilmalar, ["asl-qurilma-1"])  # ro'yxat o'smadi

    def test_hammasi_tozalansa_yangi_qurilma_rad_etiladi(self):
        self.kirish(APIClient(), "asl-qurilma-1")
        j = self.kirish(APIClient(), "boshqa-brauzer-2")  # na cookie, na eski ID
        self.assertEqual(j.status_code, 403)
        self.assertEqual(j.data["kod"], "qurilma_mos_emas")
        self.assertNotIn("qurilma", j.cookies)

    def test_boshqa_foydalanuvchi_cookie_bilan_limitni_aylanib_otolmaydi(self):
        # cookie'dagi ID shu foydalanuvchining ro'yxatida bo'lmasa, limit baribir ishlaydi
        self.kirish(APIClient(), "asl-qurilma-1")
        boshqa = APIClient()
        boshqa.cookies["qurilma"] = "uydirma-id-77"
        j = self.kirish(boshqa, "uydirma-id-77")
        self.assertEqual(j.status_code, 403)

    def test_yaroqsiz_cookie_e_tiborsiz_qoldiriladi(self):
        c = APIClient()
        c.cookies["qurilma"] = "x;y<script>"
        j = self.kirish(c, "asl-qurilma-1")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["qurilma_id"], "asl-qurilma-1")
