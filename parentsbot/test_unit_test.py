"""Video-TZ 2026-10-16: Kurslar Unit "Tests" natijasi ota-onaga (nechta to'g'ri, necha foiz)."""

from datetime import time, timedelta

from django.utils import timezone

from courses.models import KursMashq, KursMashqYechim, KursTugun
from parentsbot import xabarlar as xb
from parentsbot.models import Boglanish, ParentsBotSozlama, Xabar
from parentsbot.test_natija import NatijaAsos


class UnitTestNatijaTest(NatijaAsos):
    def setUp(self):
        super().setUp()
        self.daraja.nomi = "Beginner"
        self.daraja.save(update_fields=["nomi"])
        unit = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1 — Hello!", parent=self.daraja)
        tests = KursTugun.objects.create(markaz=self.markaz, nomi="Tests", parent=unit, kalit="tests")
        self.test_mashq = KursMashq.objects.create(tugun=tests, savollar=[])
        # Oddiy mashq — Workbook'da (Video-TZ 2026-10-16: u ota-onaga umuman bormaydi)
        wb = KursTugun.objects.create(markaz=self.markaz, nomi="Workbook", parent=unit, kalit="workbook")
        self.mashq = KursMashq.objects.create(tugun=wb, savollar=[])
        ParentsBotSozlama.objects.filter(pk=1).update(test_rejimi="darhol")
        self.t0 = timezone.now()
        Boglanish.objects.update(faollashgan=self.t0 - timedelta(days=1))
        xb.skanerla_yechim(self.t0 - timedelta(hours=2))  # boshlanish vaqti
        ParentsBotSozlama.objects.filter(pk=1).update(tinch_boshi=time(0, 0), tinch_oxiri=time(0, 0))

    def unit_test(self, ball, jami, vaqt=None):
        y = KursMashqYechim.objects.create(talaba=self.talaba, mashq=self.test_mashq, javoblar=[],
                                           ball=ball, jami=jami, natijalar=[])
        KursMashqYechim.objects.filter(pk=y.pk).update(created_at=vaqt or self.t0 - timedelta(minutes=30))
        return y

    def yubor(self, minut):
        return xb.yubor_navbat(self.tg, self.t0 + timedelta(minutes=minut), pauza=0)

    def test_darhol_togri_soni_va_foiz(self):
        self.unit_test(24, 30)
        self.yechim(5, 10, vaqt=self.t0 - timedelta(minutes=30))  # oddiy mashq — darhol xabar emas
        self.assertEqual(xb.skanerla_yechim(self.t0), 1)
        self.assertEqual(self.yubor(6), 1)
        self.assertIn("Beginner Unit 1 — Hello! testini yechdi: 24/30 to'g'ri — 80%", self.tg.yuborilgan[-1][1])

    def test_ruscha(self):
        self.ota.til = "ru"
        self.ota.save(update_fields=["til"])
        self.unit_test(3, 4)
        xb.skanerla_yechim(self.t0)
        self.yubor(6)
        self.assertIn("решил(а) тест Beginner Unit 1 — Hello!: 3/4 верно — 75%", self.tg.yuborilgan[-1][1])

    def test_ochiq_rejimda_bekor(self):
        ParentsBotSozlama.objects.filter(pk=1).update(test_rejimi="ochiq")
        self.unit_test(3, 4)
        xb.skanerla_yechim(self.t0)
        self.assertEqual(self.yubor(6), 0)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_darholda_yigmaga_kirmaydi_yigmada_kiradi(self):
        self.unit_test(8, 10, vaqt=self.ichida)
        self.yechim(6, 10)  # Workbook — yig'maga ham kirmaydi
        self.assertNotIn(self.talaba.id, xb.natijalar([self.talaba.id], self.ichida - timedelta(hours=1),
                                                      self.hozir, {"test": "darhol"}))
        self.assertEqual(xb.natijalar([self.talaba.id], self.ichida - timedelta(hours=1), self.hozir,
                                      {"test": "yigma"})[self.talaba.id]["mashq_soni"], 1)
