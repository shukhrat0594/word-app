from rest_framework.test import APIClient

from accounts.models import Bildirishnoma, User
from accounts.tests import DrosselsizTest, PAROL
from accounts.views import havola_xavfsiz


class HavolaTest(DrosselsizTest):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(username="adm", password=PAROL, role=User.Role.ADMIN)
        self.c = APIClient()
        self.c.force_authenticate(self.u)

    def yarat(self, havola):
        return Bildirishnoma.objects.create(
            foydalanuvchi=self.u, turi="ogohlantirish", kalit=f"k{Bildirishnoma.objects.count()}",
            sarlavha="S", matn="m", havola=havola)

    def test_xavfsiz_havola(self):
        self.assertEqual(havola_xavfsiz("/crm/otabot"), "/crm/otabot")
        for yomon in ("https://yomon.example", "//yomon.example", "javascript:alert(1)", "\\x", "", None):
            self.assertEqual(havola_xavfsiz(yomon), "", yomon)

    def test_api_havolani_qaytaradi(self):
        self.yarat("/crm/otabot")
        d = self.c.get("/api/bildirishnomalar/").data["bildirishnomalar"]
        self.assertEqual(d[0]["havola"], "/crm/otabot")

    def test_tashqi_havola_api_orqali_chiqmaydi(self):
        self.yarat("https://yomon.example/x")
        d = self.c.get("/api/bildirishnomalar/").data["bildirishnomalar"]
        self.assertEqual(d[0]["havola"], "")

    def test_havolasiz_eski_bildirishnoma_bo_sh(self):
        Bildirishnoma.objects.create(foydalanuvchi=self.u, kalit="eski", sarlavha="Eski")
        d = self.c.get("/api/bildirishnomalar/").data["bildirishnomalar"]
        self.assertEqual(d[0]["havola"], "")

    def test_ochilganda_oqilgan_belgilanadi(self):
        b = self.yarat("/crm/otabot")
        j = self.c.post("/api/bildirishnomalar/", {"id": b.id}, format="json")
        self.assertEqual(j.data["oqilmagan"], 0)
