"""Video-TZ IMG_7058: sinovdan faolga kechagi sana bilan o'tkazilgan
o'quvchiga qarzdorlik hisoblanmayotgan edi."""

from datetime import date

from crm.boshqaruv import guruhdan_chiqar
from crm.models import GuruhdanChiqish, Hisob
from crm.test_api import ApiAsos
from crm.tests import bugun_qilib

OKTABR = date(2026, 10, 1)
BUGUN = date(2026, 10, 20)


class KechagiSanaBilanFaollashtirishTest(ApiAsos):
    def faollashtir(self, am, sana):
        with bugun_qilib(BUGUN):
            j = self.mijoz(self.admin).patch(
                f"/api/crm/azoliklar/{am.id}/", {"holat": "faol", "faollashtirish_sana": sana}, format="json")
            self.assertEqual(j.status_code, 200, j.data)
            self.mijoz(self.admin).get("/api/crm/hisoblar/")

    def qayta_qoshilgan(self):
        """Avval faol bo'lib, oy boshlanmasdan chiqarilgan — 0 so'mlik
        "to'landi" hisob qoladi; keyin sinovga qayta qo'shilgan."""
        am = self.azolik_qosh(boshlanish=BUGUN)
        with bugun_qilib(BUGUN):
            self.mijoz(self.admin).get("/api/crm/hisoblar/")
            guruhdan_chiqar(self.admin, am.azolik, date(2026, 10, 19), GuruhdanChiqish.SababTuri.BOSHQA)
        hisob = Hisob.objects.get(talaba=self.talaba, oy=OKTABR)
        self.assertEqual((hisob.summa, hisob.holat), (0, Hisob.Holat.TOLANDI))
        return self.azolik_qosh(boshlanish=BUGUN, holat="sinov")

    def test_qayta_qoshilgan_oquvchiga_qarz_hisoblanadi(self):
        self.faollashtir(self.qayta_qoshilgan(), "2026-10-19")
        hisob = Hisob.objects.get(talaba=self.talaba, oy=OKTABR)
        self.assertGreater(hisob.summa, 0)
        self.assertEqual(hisob.holat, Hisob.Holat.QARZDOR)

    def test_guruh_boyicha_faollashtirishda_ham(self):
        self.qayta_qoshilgan()
        with bugun_qilib(BUGUN):
            self.mijoz(self.admin).post(
                f"/api/crm/guruhlar/{self.guruh.id}/faollashtirish/", {"sana": "2026-10-19"}, format="json")
            self.mijoz(self.admin).get("/api/crm/hisoblar/")
        self.assertGreater(Hisob.objects.get(talaba=self.talaba, oy=OKTABR).summa, 0)

    def test_jadvalsiz_guruhda_0_som_qarzdor_bolib_qolmaydi(self):
        am = self.qayta_qoshilgan()
        self.guruh.crm_jadval.all().delete()
        self.faollashtir(am, "2026-10-19")
        hisob = Hisob.objects.get(talaba=self.talaba, oy=OKTABR)
        self.assertEqual((hisob.summa, hisob.holat), (0, Hisob.Holat.TOLANDI))

    def test_oddiy_holat(self):
        am = self.azolik_qosh(boshlanish=BUGUN, holat="sinov")
        self.faollashtir(am, "2026-10-19")
        self.assertGreater(Hisob.objects.get(talaba=self.talaba, oy=OKTABR).summa, 0)
