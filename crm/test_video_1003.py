"""Video-TZ 2026-10-03 (IMG_6825): sinovdagi o'quvchini faollashtirishda
sana tanlanadi, oylik hisob shu sanadan o'zi hisoblanadi."""

from datetime import date

from accounts.models import User
from crm.models import CrmRol, Hisob, XodimProfil
from crm.test_api import ApiAsos
from crm.tests import NARX, SENTABR, bugun_qilib


class FaollashtirishSanasiTest(ApiAsos):
    def hisob_summasi(self):
        with bugun_qilib(date(2026, 9, 30)):
            self.mijoz(self.admin).get("/api/crm/hisoblar/")
        return Hisob.objects.get(talaba=self.talaba, oy=SENTABR).summa

    def test_sana_bilan_faollashtirish_hisobni_shu_sanadan_boshlaydi(self):
        am = self.azolik_qosh(boshlanish=SENTABR, holat="sinov")
        j = self.mijoz(self.admin).patch(
            f"/api/crm/azoliklar/{am.id}/", {"holat": "faol", "faollashtirish_sana": "2026-09-16"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        am.refresh_from_db()
        self.assertEqual((am.holat, am.boshlanish_sana), ("faol", date(2026, 9, 16)))
        summa = self.hisob_summasi()
        self.assertTrue(0 < summa < NARX, summa)

    def test_sanasiz_faollashtirish_avvalgidek(self):
        am = self.azolik_qosh(boshlanish=SENTABR, holat="sinov")
        j = self.mijoz(self.admin).patch(f"/api/crm/azoliklar/{am.id}/", {"holat": "faol"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        am.refresh_from_db()
        self.assertEqual(am.boshlanish_sana, SENTABR)
        self.assertEqual(self.hisob_summasi(), NARX)

    def test_sana_faqat_sinovdan_faolga_otishda_ishlaydi(self):
        am = self.azolik_qosh(boshlanish=SENTABR)  # allaqachon faol
        self.mijoz(self.admin).patch(
            f"/api/crm/azoliklar/{am.id}/", {"holat": "faol", "faollashtirish_sana": "2026-09-20"}, format="json")
        am.refresh_from_db()
        self.assertEqual(am.boshlanish_sana, SENTABR)

    def test_guruhga_oquvchi_qoshish_ruxsati_yetadi(self):
        rol = CrmRol.objects.create(nomi="Qoshuvchi", ruxsatlar=["guruhlar.talaba_qoshish"])
        u = User.objects.create_user(username="qoshuvchi1", password="x", role=User.Role.ODDIY)
        XodimProfil.objects.create(user=u, lavozim="boshqa", rol=rol)
        am = self.azolik_qosh(boshlanish=SENTABR, holat="sinov")
        j = self.mijoz(u).patch(
            f"/api/crm/azoliklar/{am.id}/", {"holat": "faol", "faollashtirish_sana": "2026-09-16"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)

    def test_guruh_boyicha_faollashtirish_sanasi(self):
        am = self.azolik_qosh(boshlanish=SENTABR, holat="sinov")
        j = self.mijoz(self.admin).post(
            f"/api/crm/guruhlar/{self.guruh.id}/faollashtirish/", {"sana": "2026-09-16"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        am.refresh_from_db()
        self.assertEqual((am.holat, am.boshlanish_sana), ("faol", date(2026, 9, 16)))

    def test_yaroqsiz_sana_400(self):
        am = self.azolik_qosh(boshlanish=SENTABR, holat="sinov")
        j = self.mijoz(self.admin).patch(
            f"/api/crm/azoliklar/{am.id}/", {"holat": "faol", "faollashtirish_sana": "kecha"}, format="json")
        self.assertEqual(j.status_code, 400)
        am.refresh_from_db()
        self.assertEqual(am.holat, "sinov")
