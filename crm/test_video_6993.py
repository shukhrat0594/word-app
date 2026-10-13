"""Video-TZ IMG_6993.MOV: muzlatilgan o'quvchiga muzlatilgan kundan davomat qo'yilmaydi."""

from datetime import date

from academics.models import Davomat
from crm.test_api import ApiAsos


class MuzlatilganDavomatTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.azolik_qosh(holat="muzlatilgan", muzlatish_sana=date(2026, 9, 10), muzlatish_izoh="SINOV sabab")
        self.url = f"/api/crm/guruhlar/{self.guruh.id}/davomat/"

    def test_jadvalda_qulf(self):
        d = self.mijoz(self.owner).get(self.url + "?oy=2026-09").data
        kunlar = d["talabalar"][0]["kunlar"]
        self.assertTrue(all(k["qulf"] and k["muzlatilgan"] for k in kunlar if k["sana"] >= date(2026, 9, 10)))
        self.assertFalse(any(k["qulf"] for k in kunlar if k["sana"] < date(2026, 9, 10)))

    def test_belgilash_rad(self):
        m = self.mijoz(self.owner)
        post = lambda s: m.post(self.url, {"talaba_id": self.talaba.id, "sana": s, "holat": "keldi"}, format="json")
        self.assertEqual(post("2026-09-10").status_code, 400)
        self.assertEqual(post("2026-09-08").status_code, 200)
        m.post(self.url + "hammasi/", {"sana": "2026-09-15"}, format="json")
        self.assertFalse(Davomat.objects.filter(talaba=self.talaba, sana=date(2026, 9, 15)).exists())
