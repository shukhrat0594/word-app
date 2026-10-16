"""Video-TZ 2026-10-16: farzand o'quv saytiga bir sutkadan ortiq kirmasa — ota-onaga xabar."""

from datetime import datetime, time, timedelta

from accounts.models import User
from parentsbot import xabarlar as xb
from parentsbot.models import ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from parentsbot.test_tolov_qarz import TOSH, Asos


class FaollikTest(Asos):
    def setUp(self):
        super().setUp()
        self.t18 = datetime.combine(self.kun, time(18, 1), tzinfo=TOSH)  # standart faollik_soati=18:00
        User.objects.filter(pk=self.talaba.pk).update(date_joined=self.t18 - timedelta(days=10), last_login=None)

    def kirgan(self, vaqt):
        User.objects.filter(pk=self.talaba.pk).update(oxirgi_faollik=vaqt)

    def test_ikki_kun_kirmagan_xabar_boradi(self):
        self.kirgan(self.t18 - timedelta(days=2))
        self.assertEqual(xb.skanerla_faollik(self.t18), 1)
        self.assertEqual(xb.skanerla_faollik(self.t18 + timedelta(minutes=5)), 0)  # kuniga bir marta
        self.assertEqual(self.yubor(self.t18 + timedelta(minutes=1)), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("o'quv saytiga kirmadi", matn)
        self.assertIn((self.t18 - timedelta(days=2)).strftime("%d.%m.%Y"), matn)

    def test_umuman_kirmagan(self):
        self.kirgan(None)
        self.assertEqual(xb.skanerla_faollik(self.t18), 1)
        self.yubor(self.t18 + timedelta(minutes=1))
        self.assertIn("umuman kirmagan", self.tg.yuborilgan[-1][1])

    def test_bugun_kirgan_xabar_yoq(self):
        self.kirgan(self.t18 - timedelta(hours=3))
        self.assertEqual(xb.skanerla_faollik(self.t18), 0)

    def test_yangi_hisob_xabar_yoq(self):
        self.kirgan(None)
        User.objects.filter(pk=self.talaba.pk).update(date_joined=self.t18 - timedelta(hours=5))
        self.assertEqual(xb.skanerla_faollik(self.t18), 0)

    def test_soatdan_oldin_va_ochiq_sozlama(self):
        self.kirgan(self.t18 - timedelta(days=3))
        self.assertEqual(xb.skanerla_faollik(self.t18 - timedelta(hours=1)), 0)
        ParentsBotSozlama.objects.filter(pk=1).update(faollik_yoqilgan=False)
        self.assertEqual(xb.skanerla_faollik(self.t18), 0)
        self.assertIsNone(ParentsBotKuzatuv.ol().faollik_skanlandi)

    def test_orada_kirsa_bekor(self):
        self.kirgan(self.t18 - timedelta(days=2))
        xb.skanerla_faollik(self.t18)
        self.kirgan(self.t18)
        self.assertEqual(self.yubor(self.t18 + timedelta(minutes=1)), 0)
        self.assertEqual(Xabar.objects.get(turi="faollik").holat, Xabar.Holat.BEKOR)
