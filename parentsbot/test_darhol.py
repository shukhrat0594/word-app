"""Darhol xabarlar (2026-10-09): davomat "keldi", IELTS to'liq testi, Writing/Speaking, Vocabulary —
sozlamaga qarab (o'chiq / darhol / kunlik yig'mada)."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from parentsbot import xabarlar as xb
from parentsbot.models import ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from parentsbot.test_natija import TOSH, NatijaAsos
from parentsbot.test_xabarlar import XabarAsos


class KeldiTest(XabarAsos):
    def setUp(self):
        super().setUp()
        xb.skanerla_davomat(timezone.now() - timedelta(minutes=30))  # "keldi" kuzatuvi shu paytdan

    def test_keldi_xabari(self):
        self.belgi("keldi")
        self.assertEqual(self.skaner(), 1)
        self.assertEqual(self.yubor(minut=6), 1)
        self.assertIn("darsga keldi", self.tg.yuborilgan[-1][1])

    def test_sozlamada_ochirilgan(self):
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_keldi=False)
        self.belgi("keldi")
        self.skaner()
        self.assertEqual(self.yubor(minut=6), 0)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_keldi_kelmadiga_tuzatilsa_bekor_va_kelmadi_ketadi(self):
        d = self.belgi("keldi")
        self.skaner()
        d.holat = "kelmadi"
        d.save()
        self.skaner(2)
        self.assertEqual(self.yubor(minut=8), 1)
        self.assertIn("darsga kelmadi", self.tg.yuborilgan[-1][1])
        self.assertEqual(Xabar.objects.get(kalit__endswith=":keldi").holat, "bekor")

    def test_keldi_yoqilishidan_oldingi_davomatga_xabar_yoq(self):
        self.belgi("keldi")
        ParentsBotKuzatuv.objects.update(keldi_boshlandi=timezone.now() + timedelta(minutes=1))
        self.assertEqual(self.skaner(), 0)


class DarholNatijaTest(NatijaAsos):
    def setUp(self):
        super().setUp()
        ParentsBotSozlama.objects.filter(pk=1).update(ielts_rejimi="darhol", ws_rejimi="darhol", soz_rejimi="darhol")
        self.t0 = timezone.now()
        from parentsbot.models import Boglanish
        Boglanish.objects.update(faollashgan=self.t0 - timedelta(days=1))  # ota-ona avvaldan ulangan
        xb.skanerla_yechim(self.t0 - timedelta(hours=2))  # boshlanish vaqti
        self.ichida = self.t0 - timedelta(minutes=30)

    def yubor(self, minut):
        # tinch soatga tushmasin: ish vaqtini qat'iy qo'yamiz
        ParentsBotSozlama.objects.filter(pk=1).update(tinch_boshi=time(0, 0), tinch_oxiri=time(0, 0))
        return xb.yubor_navbat(self.tg, self.t0 + timedelta(minutes=minut), pauza=0)

    def test_ielts_test_darhol(self):
        self.imtihon_yechim("listening", 6.5, nomi="Cambridge 13 Test 4")
        self.assertEqual(xb.skanerla_yechim(self.t0), 1)
        self.assertEqual(self.yubor(1), 0)  # 5 daqiqa kechikish
        self.assertEqual(self.yubor(6), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("IELTS Listening testini yechdi: «Cambridge 13 Test 4» — band 6.5", matn)
        self.assertEqual(xb.skanerla_yechim(self.t0 + timedelta(minutes=7)), 0)  # takror yo'q

    def test_writing_faqat_tayyor_bolganda(self):
        self.writing(None, holat="kutilmoqda")
        self.assertEqual(xb.skanerla_yechim(self.t0), 0)
        from assessment.models import WritingTekshiruv
        WritingTekshiruv.objects.update(holat="tayyor", overall_band=7)
        self.assertEqual(xb.skanerla_yechim(self.t0 + timedelta(minutes=1)), 1)
        self.yubor(7)
        self.assertIn("IELTS Writing topshirdi — band 7.0", self.tg.yuborilgan[-1][1])

    def test_vocabulary_kuniga_bitta_oxirgi_natija_bilan(self):
        self.soz_yechim(5, 10)
        self.soz_yechim(9, 10, vaqt=self.ichida + timedelta(minutes=2))
        self.assertEqual(xb.skanerla_yechim(self.t0), 1)
        self.assertEqual(self.yubor(6), 0)  # Vocabulary 10 daqiqa kutadi
        self.assertEqual(self.yubor(11), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("Vocabulary mashqini bajardi", matn)
        self.assertIn("9/10 — 90%", matn)
        self.assertIn("2 marta urindi", matn)

    def test_rejim_yigma_yoki_ochiq_bolsa_darhol_ketmaydi(self):
        ParentsBotSozlama.objects.filter(pk=1).update(ielts_rejimi="yigma", soz_rejimi="ochiq")
        self.imtihon_yechim("reading", 7.0)
        self.soz_yechim(5, 10)
        self.assertEqual(xb.skanerla_yechim(self.t0), 2)  # yaratiladi, lekin...
        self.assertEqual(self.yubor(15), 0)  # ...yuborishda bekor
        self.assertEqual(set(Xabar.objects.values_list("holat", flat=True)), {"bekor"})

    def test_boshlanishdan_oldingi_yechim_yuborilmaydi(self):
        self.imtihon_yechim("listening", 6.0, vaqt=self.t0 - timedelta(hours=3))
        self.assertEqual(xb.skanerla_yechim(self.t0), 0)

    def test_ochirilgan_yechim_bekor(self):
        from exercises.models import TestYechim
        self.imtihon_yechim("listening", 6.0)
        xb.skanerla_yechim(self.t0)
        TestYechim.objects.all().delete()
        self.assertEqual(self.yubor(6), 0)

    def test_ruscha(self):
        from parentsbot.models import Abonent
        Abonent.objects.filter(pk=self.ota.pk).update(til="ru")
        self.imtihon_yechim("reading", 7.0, nomi="Cambridge 14 Test 1")
        xb.skanerla_yechim(self.t0)
        self.yubor(6)
        self.assertIn("решил(а) тест IELTS Reading: «Cambridge 14 Test 1» — band 7.0", self.tg.yuborilgan[-1][1])
