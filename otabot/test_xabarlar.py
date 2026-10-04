from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from academics.models import Davomat
from accounts.models import User
from crm.models import DavomatIzoh
from crm.test_api import ApiAsos
from otabot import xabarlar as xb
from otabot.models import Abonent, Boglanish, OtaBotKuzatuv, OtaBotSozlama, Xabar
from otabot.telegram import TgXato
from otabot.test_bot import SoxtaTg
from django.test import SimpleTestCase

TOSH = ZoneInfo("Asia/Tashkent")


class TinchSoatlarTest(SimpleTestCase):
    def test_yarim_tundan_oshadigan(self):
        b, o = time(22, 0), time(8, 0)
        for v, kutilgan in ((time(23, 0), True), (time(2, 0), True), (time(7, 59), True), (time(8, 0), False),
                            (time(12, 0), False), (time(21, 59), False), (time(22, 0), True)):
            self.assertEqual(xb.tinch_mi(v, b, o), kutilgan, v)

    def test_oddiy_oraliq_va_teng(self):
        self.assertTrue(xb.tinch_mi(time(13, 0), time(12, 0), time(14, 0)))
        self.assertFalse(xb.tinch_mi(time(15, 0), time(12, 0), time(14, 0)))
        self.assertFalse(xb.tinch_mi(time(3, 0), time(8, 0), time(8, 0)))  # teng — tinch soat yo'q


class XabarAsos(ApiAsos):
    def setUp(self):
        super().setUp()
        self.tg = SoxtaTg()
        self.kun = timezone.localdate()
        # Ish vaqti (tinch soat emas): bugun 12:00 Toshkent
        self.t0 = datetime.combine(self.kun, time(12, 0), tzinfo=TOSH)
        self.ota = Abonent.objects.create(telegram_id=501, ism="Ota", til="uz", holat="tayyor")
        Boglanish.objects.create(abonent=self.ota, talaba=self.talaba, usul="telefon")
        # baseline: skanerlash birinchi marta o'tgan (hozirdan oldin)
        xb.skanerla_davomat(timezone.now() - timedelta(hours=1))

    def belgi(self, holat="kelmadi", sababli=False, kechikdi=False, sana=None, talaba=None):
        d = Davomat.objects.create(sana=sana or self.kun, guruh=self.guruh, talaba=talaba or self.talaba, holat=holat)
        if sababli or kechikdi:
            DavomatIzoh.objects.create(davomat=d, sababli=sababli, kechikdi=kechikdi)
        return d

    # Vaqt QAT'IY (bugun 12:00 Toshkent + minut): testlar kun vaqtiga (tinch soatlarga) bog'liq emas.
    def skaner(self, minut=0):
        return xb.skanerla_davomat(self.t0 + timedelta(minutes=minut))

    def yubor(self, minut=0):
        return xb.yubor_navbat(self.tg, self.t0 + timedelta(minutes=minut), pauza=0)


class SkanerTest(XabarAsos):
    def test_birinchi_ishga_tushganda_eski_davomat_yuborilmaydi(self):
        Xabar.objects.all().delete()
        OtaBotKuzatuv.objects.update(davomat_boshlandi=None)
        self.belgi()  # baseline'dan OLDIN yaratilgan
        self.assertEqual(xb.skanerla_davomat(timezone.now() + timedelta(hours=1)), 0)  # faqat baseline
        self.assertEqual(self.skaner(61), 0)  # shu yozuv baseline'dan oldin edi
        self.assertEqual(Xabar.objects.count(), 0)

    def test_kelmadi_xabari_kechiktirib_yuboriladi(self):
        self.belgi()
        self.assertEqual(self.skaner(), 1)
        self.assertEqual(self.yubor(minut=1), 0)  # kechikish hali tugamagan
        self.assertEqual(self.yubor(minut=6), 1)
        chat, matn, _ = self.tg.yuborilgan[-1]
        self.assertEqual(chat, 501)
        self.assertIn("darsga kelmadi", matn)
        self.assertIn(self.talaba.get_full_name() or self.talaba.username, matn)
        self.assertIn("bugun", matn)
        self.assertEqual(Xabar.objects.get().holat, "yuborildi")

    def test_takror_yuborilmaydi(self):
        self.belgi()
        self.skaner(); self.skaner(1); self.skaner(2)
        self.assertEqual(Xabar.objects.count(), 1)
        self.yubor(minut=6)
        self.yubor(minut=7)
        self.assertEqual(len(self.tg.yuborilgan), 1)

    def test_keldi_xabar_bermaydi(self):
        self.belgi(holat="keldi")
        self.assertEqual(self.skaner(), 0)

    def test_kechikdi(self):
        self.belgi(holat="keldi", kechikdi=True)
        self.assertEqual(self.skaner(), 1)
        self.yubor(minut=6)
        self.assertIn("kechikib", self.tg.yuborilgan[-1][1])

    def test_sababli_standart_ochiq_emas_yoqilsa_ketadi(self):
        self.belgi(sababli=True)
        self.assertEqual(self.skaner(), 0)  # davomat_sababli=False
        OtaBotSozlama.objects.filter(pk=1).update(davomat_sababli=True)
        self.assertEqual(self.skaner(1), 1)
        self.yubor(minut=7)
        self.assertIn("sababli", self.tg.yuborilgan[-1][1])

    def test_sozlamada_ochirilgan(self):
        OtaBotSozlama.ol()
        OtaBotSozlama.objects.filter(pk=1).update(davomat_kelmadi=False)
        self.belgi()
        self.assertEqual(self.skaner(), 0)
        OtaBotSozlama.objects.filter(pk=1).update(davomat_kelmadi=True, davomat_yoqilgan=False)
        self.assertEqual(self.skaner(1), 0)

    def test_ulanmagan_ota_ona_xabar_olmaydi(self):
        Boglanish.objects.all().update(faol=False)
        self.belgi()
        self.assertEqual(self.skaner(), 0)

    def test_eski_sana_xabar_bermaydi(self):
        self.belgi(sana=self.kun - timedelta(days=5))  # admin orqaga qarab to'ldirmoqda
        self.assertEqual(self.skaner(), 0)

    def test_ikki_ota_ona_ikkalasi_oladi(self):
        ona = Abonent.objects.create(telegram_id=502, ism="Ona", til="ru", holat="tayyor")
        Boglanish.objects.create(abonent=ona, talaba=self.talaba, usul="admin")
        self.belgi()
        self.assertEqual(self.skaner(), 2)
        self.yubor(minut=6)
        chatlar = {c for c, _, _ in self.tg.yuborilgan}
        self.assertEqual(chatlar, {501, 502})
        ruscha = [m for c, m, _ in self.tg.yuborilgan if c == 502][0]
        self.assertIn("отсутствовал", ruscha)
        self.assertIn("сегодня", ruscha)

    def test_boshqa_kun_sanasi_aniq_yoziladi(self):
        kecha = self.kun - timedelta(days=1)
        self.belgi(sana=kecha)
        self.skaner()
        self.yubor(minut=6)
        self.assertIn(kecha.strftime("%d.%m.%Y") + " kuni", self.tg.yuborilgan[-1][1])


class BekorQilishTest(XabarAsos):
    def test_kechikish_ichida_tuzatilsa_bekor(self):
        d = self.belgi()
        self.skaner()
        Davomat.objects.filter(pk=d.pk).update(holat="keldi")  # admin adashganini tuzatdi
        self.assertEqual(self.yubor(minut=6), 0)
        self.assertEqual(Xabar.objects.get().holat, "bekor")
        self.assertEqual(self.tg.yuborilgan, [])

    def test_davomat_ochirilsa_bekor(self):
        d = self.belgi()
        self.skaner()
        d.delete()
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_sababliga_ozgarsa_eski_xabar_bekor(self):
        d = self.belgi()
        self.skaner()
        DavomatIzoh.objects.create(davomat=d, sababli=True)  # "kelmadi" -> "sababli"
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get(kalit__endswith=":kelmadi").holat, "bekor")
        self.assertEqual(self.tg.yuborilgan, [])

    def test_ota_ona_stop_qilsa_bekor(self):
        self.belgi()
        self.skaner()
        Abonent.objects.filter(pk=self.ota.pk).update(faol=False)
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_ota_ona_toifani_ochirgan(self):
        Abonent.objects.filter(pk=self.ota.pk).update(toifa_ochirilgan=["davomat"])
        self.belgi()
        self.skaner()
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "bekor")

    def test_bog_lanish_uzilsa_bekor(self):
        self.belgi()
        self.skaner()
        Boglanish.objects.update(faol=False)
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "bekor")


class TinchSoatXabarTest(XabarAsos):
    def test_tunda_yuborilmaydi_ertalab_yuboriladi(self):
        self.belgi()
        self.skaner()
        tun = datetime.combine(self.kun, time(23, 0), tzinfo=TOSH)
        self.assertEqual(xb.yubor_navbat(self.tg, tun + timedelta(days=0), pauza=0), 0)
        self.assertEqual(Xabar.objects.get().holat, "kutilmoqda")  # kutadi
        ertalab = datetime.combine(self.kun + timedelta(days=1), time(9, 0), tzinfo=TOSH)
        self.assertEqual(xb.yubor_navbat(self.tg, ertalab, pauza=0), 1)
        # ertalab xabarda sana "kecha" bo'lib qoladi — "bugun" emas, aniq sana yoziladi
        self.assertIn(self.kun.strftime("%d.%m.%Y") + " kuni", self.tg.yuborilgan[-1][1])

    def test_tinch_soat_sozlamadan_olinadi(self):
        self.belgi()
        self.skaner()
        OtaBotSozlama.objects.filter(pk=1).update(tinch_boshi=time(11, 0), tinch_oxiri=time(13, 0))
        self.assertEqual(xb.yubor_navbat(self.tg, self.t0 + timedelta(minutes=0), pauza=0), 0)  # 12:00 tinch
        # yuborilsin vaqti (hozir+5 daq) ham o'tgan bo'lishi kerak: 13:30 da hammasi ochiq
        self.assertEqual(xb.yubor_navbat(self.tg, self.t0 + timedelta(hours=1, minutes=30), pauza=0), 1)


class XatolarTest(XabarAsos):
    def test_bot_bloklangan_403(self):
        self.belgi()
        self.skaner()
        self.tg.yubor = lambda *a, **k: (_ for _ in ()).throw(TgXato("sendMessage: 403 Forbidden: bot was blocked"))
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "xato")
        self.assertFalse(Abonent.objects.get(pk=self.ota.pk).faol)

    def test_vaqtincha_xato_qayta_uriniladi_chegaragacha(self):
        self.belgi()
        self.skaner()
        self.tg.yubor = lambda *a, **k: (_ for _ in ()).throw(TgXato("sendMessage: 500 server"))
        for i in range(xb.URINISH_CHEGARASI):
            self.yubor(minut=6 + i)
        x = Xabar.objects.get()
        self.assertEqual((x.holat, x.urinish), ("xato", xb.URINISH_CHEGARASI))
        self.assertTrue(Abonent.objects.get(pk=self.ota.pk).faol)  # bloklanmagan — faol qoladi

    def test_bitta_xato_qolganini_to_xtatmaydi(self):
        ona = Abonent.objects.create(telegram_id=502, ism="Ona", til="uz", holat="tayyor")
        Boglanish.objects.create(abonent=ona, talaba=self.talaba, usul="admin")
        self.belgi()
        self.skaner()
        asl = self.tg.yubor

        def yubor(chat, matn, tugmalar=None):
            if chat == 501:
                raise TgXato("sendMessage: 500 x")
            return asl(chat, matn, tugmalar)

        self.tg.yubor = yubor
        self.assertEqual(self.yubor(minut=6), 1)  # 502 ga ketdi
        self.assertEqual(Xabar.objects.get(abonent=ona).holat, "yuborildi")
        self.assertEqual(Xabar.objects.get(abonent=self.ota).holat, "kutilmoqda")
