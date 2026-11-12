from rest_framework.test import APIClient

from accounts.models import User
from accounts.tests import DrosselsizTest, PAROL


class ListeningPanelTest(DrosselsizTest):
    """TZ 712: "Listening trainer" paneli "ko'rinadigan panellar" tanlovida
    ruxsat etilgan yo'l bo'lishi kerak (frontend Layout.jsx bilan bir xil)."""

    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_superuser(username="SINOV_owner", password=PAROL)
        self.talaba = User.objects.create_user(username="SINOV_talaba", password=PAROL, role=User.Role.STUDENT)
        self.c = APIClient()
        self.c.force_authenticate(self.owner)

    def test_listening_panelini_belgilash_mumkin(self):
        javob = self.c.patch(
            f"/api/foydalanuvchilar/{self.talaba.id}/panellar/",
            {"panellar": ["/listening-trainer"]}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.talaba.refresh_from_db()
        self.assertEqual(self.talaba.korinadigan_panellar, ["/listening-trainer"])

    def test_notanish_panel_rad_etiladi(self):
        javob = self.c.patch(
            f"/api/foydalanuvchilar/{self.talaba.id}/panellar/",
            {"panellar": ["/yoq-panel"]}, format="json")
        self.assertEqual(javob.status_code, 400)
