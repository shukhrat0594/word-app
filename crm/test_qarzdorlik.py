"""Qarzdorlik — bosh sahifa va Talabalar -> "Qarzdorlar" BITTA qoida bilan
(2026-09-28, Shuhrat): qarzdor — balansi manfiy o'quvchi; filial tanlansa,
balans faqat o'sha filialning hisob va to'lovlaridan.

Avval bosh sahifa har oy hisobini alohida qarardi: bir oyga ortiqcha
to'langan pul boshqa oy qarzini yopmasdi, arxivlangan / guruhdan chiqqan
qarzdor esa ro'yxatda chiqmasdi — prod'da "4 qarzdor", ro'yxat bo'sh edi.
"""

from datetime import date
from decimal import Decimal

from academics.models import Guruh, GuruhAzoligi
from crm.models import AzolikMoliya, Filial, GuruhMoliya, Hisob, Tolov
from crm.test_api import ApiAsos
from crm.tests import AVGUST, NARX, SENTABR


class QarzdorlikTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.azolik_qosh()

    def hisob(self, oy, guruh=None, filial=None, summa=NARX):
        guruh = guruh or self.guruh
        return Hisob.objects.create(
            talaba=self.talaba, talaba_ism="T", guruh=guruh, guruh_nomi=guruh.name,
            filial=filial or self.filial, oy=oy, summa=summa, holat=Hisob.Holat.QARZDOR,
        )

    def tolov(self, hisob, summa):
        from crm import mantiq

        Tolov.objects.create(talaba=self.talaba, talaba_ism="T", guruh=hisob.guruh, guruh_nomi="G", hisob=hisob,
                             sana=date(2026, 9, 5), summa=summa, turi=Tolov.Turi.TOLOV)
        mantiq.hisobni_yangila(hisob)

    def ikkalasi(self, filial=None):
        """(bosh sahifa: qarzdorlar, qolgan qarz) va Talabalar -> Qarzdorlar ro'yxati."""
        m = self.mijoz(self.owner)
        f = f"filial={filial}" if filial else ""
        k = m.get(f"/api/crm/korsatkichlar/?{f}").data
        royxat = m.get(f"/api/crm/talabalar/?qarzdor=1&{f}").data
        # Ikkala joy har doim bir xil sonni va summani ko'rsatadi.
        self.assertEqual(k["qarzdorlar"], len(royxat))
        self.assertEqual(k["qolgan_qarz"], -sum((x["balans"] for x in royxat), Decimal(0)))
        return k["qarzdorlar"], k["qolgan_qarz"], royxat

    def test_boshqa_oyga_ortiqcha_tolangan_pul_qarz_emas(self):
        """Avgustga 2 oylik pul — sentabr hisobi "ochiq", lekin balans 0: qarzdor emas."""
        avgust = self.hisob(AVGUST)
        self.hisob(SENTABR)
        self.tolov(avgust, NARX * 2)
        soni, summa, _ = self.ikkalasi()
        self.assertEqual((soni, summa), (0, 0))

    def test_ortiqcha_tolagan_balansi_musbat(self):
        self.tolov(self.hisob(SENTABR), NARX + 100000)
        d = self.mijoz(self.owner).get("/api/crm/talabalar/").data
        self.assertEqual([x["balans"] for x in d if x["id"] == self.talaba.id], [Decimal("100000")])

    def test_arxivlangan_qarzdor_royxatda_chiqadi(self):
        self.hisob(SENTABR)
        GuruhAzoligi.objects.filter(talaba=self.talaba).delete()
        self.talaba.is_active = False
        self.talaba.save()
        soni, summa, royxat = self.ikkalasi()
        self.assertEqual((soni, summa), (1, NARX))
        self.assertEqual(royxat[0]["id"], self.talaba.id)
        self.assertFalse(royxat[0]["faol"])

    def test_guruhsiz_qarzdor_filial_tanlanganda_ham_chiqadi(self):
        self.hisob(SENTABR)
        GuruhAzoligi.objects.filter(talaba=self.talaba).delete()
        self.assertEqual(self.ikkalasi()[0], 1)
        self.assertEqual(self.ikkalasi(filial=self.filial.id)[0], 1)

    def test_filial_tanlansa_balans_shu_filial_boyicha(self):
        """A filialda 100 000 ortiqcha to'lagan, B filialda 660 000 qarz:
        A — qarzdor emas, B — qarzdor 660 000, umumiy — 560 000."""
        fb = Filial.objects.create(markaz=self.markaz, nomi="B")
        gb = Guruh.objects.create(name="B guruh", markaz=self.markaz, daraja=self.daraja)
        GuruhMoliya.objects.create(guruh=gb, filial=fb, boshlanish_sana=date(2026, 1, 1))
        AzolikMoliya.objects.create(azolik=GuruhAzoligi.objects.create(guruh=gb, talaba=self.talaba),
                                    boshlanish_sana=SENTABR)
        self.tolov(self.hisob(SENTABR), NARX + 100000)
        self.hisob(SENTABR, guruh=gb, filial=fb)
        self.assertEqual(self.ikkalasi(filial=self.filial.id)[:2], (0, 0))
        self.assertEqual(self.ikkalasi(filial=fb.id)[:2], (1, NARX))
        self.assertEqual(self.ikkalasi()[:2], (1, NARX - 100000))
        # Ro'yxatdagi balans ustuni ham tanlangan filial bo'yicha.
        d = self.mijoz(self.owner).get(f"/api/crm/talabalar/?filial={self.filial.id}").data
        self.assertEqual([x["balans"] for x in d if x["id"] == self.talaba.id], [Decimal("100000")])
