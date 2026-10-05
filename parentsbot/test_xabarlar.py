from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from academics.models import Davomat
from accounts.models import User
from crm.models import DavomatIzoh
from crm.test_api import ApiAsos
from parentsbot import xabarlar as xb
from parentsbot.models import Abonent, Boglanish, ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from parentsbot.telegram import TgXato
from parentsbot.test_bot import SoxtaTg
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
        ParentsBotSozlama.ol()  # sozlama yozuvi bo'lsin: testlardagi update() bo'shga ketmasin
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
        ParentsBotKuzatuv.objects.update(davomat_boshlandi=None)
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

    def test_sababli_standart_ochiq_emas_yoqilsa_faqat_yangilari_ketadi(self):
        self.belgi(sababli=True)
        self.skaner()  # davomat_sababli=False: xabar yaratiladi, lekin yuborilmaydi
        self.assertEqual(self.yubor(minut=6), 0)
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_sababli=True)
        self.assertEqual(self.skaner(7), 0)  # yoqilganda eski davomat qayta yog'ilmaydi
        self.belgi(sababli=True, talaba=self.yangi_talaba())
        self.skaner(8)
        self.yubor(minut=14)
        self.assertEqual(len(self.tg.yuborilgan), 1)
        self.assertIn("sababli", self.tg.yuborilgan[-1][1])

    def yangi_talaba(self):
        t = User.objects.create_user(username="t_yangi", password="x", role=User.Role.STUDENT, markaz=self.markaz)
        Boglanish.objects.create(abonent=self.ota, talaba=t, usul="admin")
        return t

    def test_sozlamada_ochirilgan(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_kelmadi=False)
        self.belgi()
        self.skaner()
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_kelmadi=True, davomat_yoqilgan=False)
        self.belgi(talaba=self.yangi_talaba())
        self.skaner(1)
        self.assertEqual(self.yubor(minut=7), 0)
        self.assertEqual(set(Xabar.objects.values_list("holat", flat=True)), {"bekor"})

    def test_yoqilganda_ochiq_paytdagi_davomat_yogilmaydi(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_yoqilgan=False)
        self.belgi()
        self.skaner()
        self.yubor(minut=6)
        ParentsBotSozlama.objects.filter(pk=1).update(davomat_yoqilgan=True)
        self.skaner(7)
        self.yubor(minut=13)
        self.assertEqual(self.tg.yuborilgan, [])

    def test_blokdan_chiqqanda_eski_davomat_yogilmaydi(self):
        Abonent.objects.filter(pk=self.ota.pk).update(faol=False)
        self.belgi()
        self.skaner()
        self.yubor(minut=6)
        Abonent.objects.filter(pk=self.ota.pk).update(faol=True)
        self.skaner(7)
        self.yubor(minut=13)
        self.assertEqual(self.tg.yuborilgan, [])

    def test_ulanishdan_oldingi_davomat_yuborilmaydi(self):
        self.belgi()
        Boglanish.objects.update(faollashgan=timezone.now() + timedelta(seconds=5))  # hozir ulangan
        self.assertEqual(self.skaner(), 0)

    def test_davomat_boshqa_talabaga_otkazilsa_bekor(self):
        d = self.belgi()
        self.skaner()
        Davomat.objects.filter(pk=d.pk).update(talaba=self.yangi_talaba())
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get(talaba=self.talaba).holat, "bekor")

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

    def test_ota_ona_bloklasa_bekor(self):
        self.belgi()
        self.skaner()
        Abonent.objects.filter(pk=self.ota.pk).update(faol=False)
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
        ParentsBotSozlama.objects.filter(pk=1).update(tinch_boshi=time(11, 0), tinch_oxiri=time(13, 0))
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

    def test_chat_topilmadi_doimiy_xato(self):
        self.belgi()
        self.skaner()
        self.tg.yubor = lambda *a, **k: (_ for _ in ()).throw(TgXato("sendMessage: 400 Bad Request: chat not found"))
        self.yubor(minut=6)
        self.assertEqual(Xabar.objects.get().holat, "xato")
        self.assertFalse(Abonent.objects.get(pk=self.ota.pk).faol)

    def test_429_urinish_sanalmaydi_partiya_toxtaydi(self):
        ona = Abonent.objects.create(telegram_id=502, ism="Ona", til="uz", holat="tayyor")
        Boglanish.objects.create(abonent=ona, talaba=self.talaba, usul="admin")
        self.belgi()
        self.skaner()
        chaqiruvlar = []

        def yubor(chat, matn, tugmalar=None):
            chaqiruvlar.append(chat)
            raise TgXato("sendMessage: 429 Too Many Requests: retry after 3")

        self.tg.yubor = yubor
        self.assertEqual(self.yubor(minut=6), 0)
        self.assertEqual(len(chaqiruvlar), 1)  # birinchisidan keyin to'xtadi
        self.assertEqual(set(Xabar.objects.values_list("urinish", "holat")), {(0, "kutilmoqda")})

    def test_egallangan_xabar_qayta_yuborilmaydi(self):
        # Ikkinchi jarayon xabarni yuborish paytida egallab bo'lgan (yuborilsin surilgan) holat
        self.belgi()
        self.skaner()
        x = Xabar.objects.get()
        asl = self.tg.yubor

        def yubor(chat, matn, tugmalar=None):
            # yuborish paytida parallel jarayon ham shu daqiqada navbatni ko'radi
            self.assertEqual(xb.yubor_navbat(SoxtaTg(), self.t0 + timedelta(minutes=6), pauza=0), 0)
            return asl(chat, matn, tugmalar)

        self.tg.yubor = yubor
        self.assertEqual(self.yubor(minut=6), 1)
        self.assertEqual(len(self.tg.yuborilgan), 1)
        self.assertNotEqual(Xabar.objects.get().yuborilsin, x.yuborilsin)


class BloklashTest(XabarAsos):
    """Ota-ona botni bloklasa — markazga 🔔 bildirishnoma (Shuhrat, 2026-10-05)."""

    def bildirishnomalar(self, user=None):
        from accounts.models import Bildirishnoma

        return Bildirishnoma.objects.filter(foydalanuvchi=user or self.owner, kalit__startswith="parentsbot:blok:")

    def test_403_da_markazga_bitta_bildirishnoma(self):
        ona_bola = User.objects.create_user(username="t_ikki", password="x", role=User.Role.STUDENT,
                                            markaz=self.markaz)
        Boglanish.objects.create(abonent=self.ota, talaba=ona_bola, usul="admin")
        self.belgi()
        self.belgi(talaba=ona_bola)
        self.skaner()
        self.tg.yubor = lambda *a, **k: (_ for _ in ()).throw(TgXato("sendMessage: 403 Forbidden: bot was blocked"))
        self.yubor(minut=6)  # ikkala xabar ham 403 — bildirishnoma baribir bitta
        b = self.bildirishnomalar().get()
        self.assertEqual(b.havola, "/crm/parentsbot")
        self.assertIn("bloklab", b.matn)
        self.assertIn(self.talaba.get_full_name() or self.talaba.username, b.matn)
        ab = Abonent.objects.get(pk=self.ota.pk)
        self.assertFalse(ab.faol)
        self.assertIsNotNone(ab.bloklangan)
        self.assertFalse(self.bildirishnomalar(self.oqituvchi).exists())  # ruxsatsiz xodimga emas

    def test_my_chat_member_kicked_darhol_bildiradi(self):
        from parentsbot.bot import Bot

        bot = Bot(self.tg)
        yangilanish = {"my_chat_member": {"chat": {"type": "private", "id": 501}, "from": {"id": 501},
                                          "new_chat_member": {"status": "kicked"}}}
        bot.qayta_ishla(yangilanish)
        bot.qayta_ishla(yangilanish)  # takror kelsa ham bitta bildirishnoma
        self.assertFalse(Abonent.objects.get(pk=self.ota.pk).faol)
        self.assertEqual(self.bildirishnomalar().count(), 1)
        # blokdan chiqardi
        yangilanish["my_chat_member"]["new_chat_member"]["status"] = "member"
        bot.qayta_ishla(yangilanish)
        ab = Abonent.objects.get(pk=self.ota.pk)
        self.assertTrue(ab.faol)
        self.assertIsNone(ab.bloklangan)

    def test_qayta_bloklasa_yana_bildiradi(self):
        from parentsbot import xizmat

        self.assertTrue(xizmat.bloklandi(self.ota))
        xizmat.blokdan_chiqdi(Abonent.objects.get(pk=self.ota.pk))
        self.assertTrue(xizmat.bloklandi(Abonent.objects.get(pk=self.ota.pk)))
        self.assertEqual(self.bildirishnomalar().count(), 2)

    def test_botga_yozsa_blokdan_chiqqan_hisoblanadi(self):
        from parentsbot import xizmat
        from parentsbot.bot import Bot
        from parentsbot.test_bot import xabar

        xizmat.bloklandi(self.ota)
        Bot(self.tg).qayta_ishla(xabar(501, "/farzandlarim"))
        self.assertTrue(Abonent.objects.get(pk=self.ota.pk).faol)
        self.assertIn("Farzandlaringiz", self.tg.oxirgi())

    def test_farzandsiz_abonent_bildirmaydi(self):
        from parentsbot import xizmat

        Boglanish.objects.update(faol=False)
        self.assertTrue(xizmat.bloklandi(self.ota))
        self.assertFalse(self.bildirishnomalar().exists())

    def test_crm_royxatida_bloklagani_korinadi(self):
        from parentsbot import xizmat

        xizmat.bloklandi(self.ota)
        d = self.mijoz(self.owner).get("/api/crm/parentsbot/abonentlar/").data
        self.assertEqual(len(d), 1)
        self.assertFalse(d[0]["faol"])
        self.assertIsNotNone(d[0]["bloklangan"])
