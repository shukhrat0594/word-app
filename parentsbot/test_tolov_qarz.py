from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.utils import timezone

from crm.models import Hisob, Tolov
from crm.test_api import ApiAsos
from parentsbot import xabarlar as xb
from parentsbot.models import Abonent, Boglanish, ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from parentsbot.test_bot import SoxtaTg

TOSH = ZoneInfo("Asia/Tashkent")


class Asos(ApiAsos):
    def setUp(self):
        super().setUp()
        ParentsBotSozlama.ol()  # sozlama yozuvi bo'lsin: testlardagi update() bo'shga ketmasin
        self.tg = SoxtaTg()
        self.kun = timezone.localdate()
        # Vaqt QAT'IY: bugun 12:00 Toshkent (tinch soat emas)
        self.t0 = datetime.combine(self.kun, time(12, 0), tzinfo=TOSH)
        self.ota = Abonent.objects.create(telegram_id=501, ism="Ota", til="uz", holat="tayyor")
        Boglanish.objects.create(abonent=self.ota, talaba=self.talaba, usul="telefon")
        xb.skanerla_tolov(timezone.now() - timedelta(hours=1))  # baseline

    def tolov(self, summa=500000, turi=Tolov.Turi.TOLOV, talaba=None):
        t = talaba or self.talaba
        return Tolov.objects.create(
            talaba=t, talaba_ism=t.username, guruh=self.guruh, guruh_nomi=self.guruh.name,
            sana=self.kun, summa=Decimal(summa), turi=turi,
        )

    def hisob(self, summa=600000):
        return Hisob.objects.create(
            talaba=self.talaba, talaba_ism=self.talaba.username, guruh=self.guruh,
            guruh_nomi=self.guruh.name, oy=self.kun.replace(day=1), summa=Decimal(summa),
        )

    def yubor(self, vaqt):
        return xb.yubor_navbat(self.tg, vaqt, pauza=0)


class TolovXabariTest(Asos):
    def skaner(self, minut=0):
        return xb.skanerla_tolov(self.t0 + timedelta(minutes=minut))

    def test_birinchi_ishga_tushganda_eski_tolov_yuborilmaydi(self):
        ParentsBotKuzatuv.objects.update(tolov_boshlandi=None)
        self.tolov()
        self.assertEqual(xb.skanerla_tolov(timezone.now() + timedelta(hours=1)), 0)  # faqat baseline
        self.assertEqual(self.skaner(61), 0)
        self.assertEqual(Xabar.objects.count(), 0)

    def test_tolov_kechiktirib_yuboriladi(self):
        self.tolov(1250000)
        self.assertEqual(self.skaner(), 1)
        self.assertEqual(self.yubor(self.t0 + timedelta(minutes=1)), 0)
        self.assertEqual(self.yubor(self.t0 + timedelta(minutes=6)), 1)
        chat, matn, _ = self.tg.yuborilgan[-1]
        self.assertEqual(chat, 501)
        self.assertIn("1 250 000 so'm", matn)
        self.assertIn("to'lov qabul qilindi", matn)
        self.assertIn(self.guruh.name, matn)

    def test_takror_yuborilmaydi(self):
        self.tolov()
        self.skaner(); self.skaner(1); self.skaner(2)
        self.assertEqual(Xabar.objects.count(), 1)
        self.yubor(self.t0 + timedelta(minutes=6))
        self.yubor(self.t0 + timedelta(minutes=7))
        self.assertEqual(len(self.tg.yuborilgan), 1)

    def test_chegirma_bonus_qaytarish_xabar_bermaydi(self):
        for turi in (Tolov.Turi.CHEGIRMA, Tolov.Turi.BONUS, Tolov.Turi.QAYTARISH):
            self.tolov(turi=turi)
        self.assertEqual(self.skaner(), 0)

    def test_ochirilsa_bekor(self):
        a = self.tolov(100000)
        self.skaner()
        a.delete()
        self.assertEqual(self.yubor(self.t0 + timedelta(minutes=6)), 0)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_summa_tuzatilsa_togri_summa_bilan_ketadi(self):
        b = self.tolov(2000000)
        self.skaner()
        Tolov.objects.filter(pk=b.pk).update(summa=Decimal(200000))  # kassir nolni ortiqcha yozgan edi
        self.assertEqual(self.yubor(self.t0 + timedelta(minutes=6)), 1)
        self.assertIn("200 000 so'm", self.tg.yuborilgan[-1][1])
        self.assertNotIn("2 000 000", self.tg.yuborilgan[-1][1])

    def test_turi_ozgarsa_bekor(self):
        b = self.tolov()
        self.skaner()
        Tolov.objects.filter(pk=b.pk).update(turi=Tolov.Turi.CHEGIRMA)
        self.yubor(self.t0 + timedelta(minutes=6))
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_sozlamada_ochirilgan(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(tolov_yoqilgan=False)
        self.tolov()
        self.skaner()
        self.assertEqual(self.yubor(self.t0 + timedelta(minutes=6)), 0)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_qayta_yoqilganda_eski_tolovlar_yogilmaydi(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(tolov_yoqilgan=False)
        self.tolov()
        self.skaner()
        self.yubor(self.t0 + timedelta(minutes=6))
        ParentsBotSozlama.objects.filter(pk=1).update(tolov_yoqilgan=True)
        self.assertEqual(self.skaner(7), 0)
        self.yubor(self.t0 + timedelta(minutes=13))
        self.assertEqual(self.tg.yuborilgan, [])

    def test_stop_qilgan_ota_ona_start_bossa_eski_tolov_kelmaydi(self):
        Abonent.objects.filter(pk=self.ota.pk).update(faol=False)
        self.tolov()
        self.skaner()
        self.yubor(self.t0 + timedelta(minutes=6))
        Abonent.objects.filter(pk=self.ota.pk).update(faol=True)
        self.skaner(7)
        self.yubor(self.t0 + timedelta(minutes=13))
        self.assertEqual(self.tg.yuborilgan, [])

    def test_ulanishdan_oldingi_tolov_xabar_bermaydi(self):
        self.tolov()
        Boglanish.objects.update(faollashgan=timezone.now() + timedelta(seconds=5))  # keyin ulangan
        self.assertEqual(self.skaner(), 0)

    def test_qayta_ulanganda_faollashgan_yangilanadi(self):
        from parentsbot import xizmat

        b = Boglanish.objects.get()
        Boglanish.objects.filter(pk=b.pk).update(faol=False, faollashgan=timezone.now() - timedelta(days=30))
        self.tolov()  # uzilgan paytdagi to'lov
        xizmat.ulash(self.ota, [self.talaba], "admin")
        self.assertGreater(Boglanish.objects.get().faollashgan, timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.skaner(), 0)

    def test_sozlama_kechikish_ichida_ochirilsa_bekor(self):
        self.tolov()
        self.skaner()
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(tolov_yoqilgan=False)
        self.yubor(self.t0 + timedelta(minutes=6))
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_ota_ona_toifani_ochirgan(self):
        Abonent.objects.filter(pk=self.ota.pk).update(toifa_ochirilgan=["tolov"])
        self.tolov()
        self.skaner()
        self.yubor(self.t0 + timedelta(minutes=6))
        self.assertEqual(Xabar.objects.get().holat, "bekor")
        self.assertEqual(self.tg.yuborilgan, [])

    def test_boshqa_talabaning_tolovi_xabar_bermaydi(self):
        from accounts.models import User

        boshqa = User.objects.create_user(username="t2", password="x", role=User.Role.STUDENT, markaz=self.markaz)
        self.tolov(talaba=boshqa)
        self.assertEqual(self.skaner(), 0)

    def test_nofaol_talaba_xabar_olmaydi(self):
        self.tolov()
        self.skaner()
        self.talaba.is_active = False
        self.talaba.save(update_fields=["is_active"])
        self.yubor(self.t0 + timedelta(minutes=6))
        self.assertEqual(Xabar.objects.get().holat, "bekor")
        self.assertEqual(self.skaner(10), 0)  # yangi xabar ham yaratilmaydi

    def test_ruscha(self):
        Abonent.objects.filter(pk=self.ota.pk).update(til="ru")
        self.tolov(300000)
        self.skaner()
        self.yubor(self.t0 + timedelta(minutes=6))
        self.assertIn("Оплата", self.tg.yuborilgan[-1][1])
        self.assertIn("300 000 сум", self.tg.yuborilgan[-1][1])


class QarzEslatmasiTest(Asos):
    def setUp(self):
        super().setUp()
        # Shu haftaning dushanbasi (standart qarz_kunlari=[0], qarz_soati=10:00)
        self.dushanba = self.kun - timedelta(days=self.kun.weekday())

    def vaqt(self, kun=None, soat=10, minut=30):
        return datetime.combine(kun or self.dushanba, time(soat, minut), tzinfo=TOSH)

    def test_qarzdorga_dushanba_soat_10_dan_keyin(self):
        self.hisob(600000)
        self.tolov(100000)  # balans -500 000
        self.assertEqual(xb.skanerla_qarz(self.vaqt(soat=9, minut=59)), 0)  # hali vaqti emas
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 1)
        self.assertEqual(self.yubor(self.vaqt(minut=31)), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("500 000 so'm", matn)
        self.assertIn("qarzdorlik", matn)

    def test_boshqa_kunda_yuborilmaydi(self):
        self.hisob()
        self.assertEqual(xb.skanerla_qarz(self.vaqt(kun=self.dushanba + timedelta(days=1))), 0)

    def test_kuniga_bitta_haftada_qayta(self):
        self.hisob()
        xb.skanerla_qarz(self.vaqt())
        xb.skanerla_qarz(self.vaqt(soat=15))
        self.assertEqual(Xabar.objects.count(), 1)
        self.assertEqual(xb.skanerla_qarz(self.vaqt(kun=self.dushanba + timedelta(days=7))), 1)

    def test_qarzi_yoq(self):
        self.hisob(600000)
        self.tolov(600000)
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)

    def test_oldindan_tolagan(self):
        self.hisob(600000)
        self.tolov(700000)  # balans +100 000
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)

    def test_tiyinlik_qarz_eslatma_emas(self):
        self.hisob(Decimal("600000.50"))
        self.tolov(600000)
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)

    def test_kuniga_bir_marta_skanerlanadi(self):
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)  # hozir qarz yo'q
        self.hisob()
        self.assertEqual(xb.skanerla_qarz(self.vaqt(soat=11)), 0)  # shu kun skanerlangan
        self.assertEqual(ParentsBotKuzatuv.ol().qarz_skanlandi, self.dushanba)

    def test_ikki_farzand_ikkalasiga_eslatma(self):
        from accounts.models import User

        ikkinchi = User.objects.create_user(username="t2", password="x", role=User.Role.STUDENT,
                                            markaz=self.markaz, first_name="Malika")
        Boglanish.objects.create(abonent=self.ota, talaba=ikkinchi, usul="admin")
        self.hisob(600000)
        Hisob.objects.create(talaba=ikkinchi, talaba_ism="t2", guruh=self.guruh, guruh_nomi=self.guruh.name,
                             oy=self.kun.replace(day=1), summa=Decimal(300000))
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 2)
        self.assertEqual(self.yubor(self.vaqt(minut=31)), 2)
        matnlar = " | ".join(m for _, m, _ in self.tg.yuborilgan)
        self.assertIn("600 000 so'm", matnlar)
        self.assertIn("300 000 so'm", matnlar)
        self.assertIn("Malika", matnlar)

    def test_orada_tolasa_bekor(self):
        self.hisob(600000)
        xb.skanerla_qarz(self.vaqt())
        self.tolov(600000)
        self.yubor(self.vaqt(minut=31))
        self.assertEqual(Xabar.objects.filter(turi="qarz").get().holat, "bekor")
        self.assertFalse(any("qarzdorlik" in m for _, m, _ in self.tg.yuborilgan))

    def test_qisman_tolasa_yangi_summa_yoziladi(self):
        self.hisob(600000)
        xb.skanerla_qarz(self.vaqt())
        self.tolov(200000)
        self.yubor(self.vaqt(minut=31))
        self.assertIn("400 000 so'm", [m for _, m, _ in self.tg.yuborilgan if "qarzdorlik" in m][0])

    def test_kunlar_va_soat_sozlamadan(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(qarz_kunlari=[2], qarz_soati=time(15, 0))
        self.hisob()
        chorshanba = self.dushanba + timedelta(days=2)
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)
        self.assertEqual(xb.skanerla_qarz(self.vaqt(kun=chorshanba, soat=14)), 0)
        self.assertEqual(xb.skanerla_qarz(self.vaqt(kun=chorshanba, soat=15, minut=0)), 1)

    def test_ochirilgan(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(qarz_yoqilgan=False)
        self.hisob()
        self.assertEqual(xb.skanerla_qarz(self.vaqt()), 0)

    def test_tinch_soatda_kutadi_eskirsa_bekor(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(qarz_soati=time(23, 0))
        self.hisob()
        self.assertEqual(xb.skanerla_qarz(self.vaqt(soat=23)), 1)
        self.assertEqual(self.yubor(self.vaqt(soat=23, minut=1)), 0)  # tinch soat
        # ertasi ertalab — yuboriladi (1 kun ichida)
        self.assertEqual(self.yubor(self.vaqt(kun=self.dushanba + timedelta(days=1), soat=9)), 1)

    def test_bot_uzoq_toxtasa_eski_eslatma_yuborilmaydi(self):
        self.hisob()
        xb.skanerla_qarz(self.vaqt())
        self.yubor(self.vaqt(kun=self.dushanba + timedelta(days=3), soat=12))
        self.assertEqual(Xabar.objects.get().holat, "bekor")
