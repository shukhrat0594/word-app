from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone

from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from courses.models import KursMashq, KursMashqYechim, KursSozYechim, KursTugun
from crm.test_api import ApiAsos
from exercises.models import ImtihonTest, TestYechim
from parentsbot import xabarlar as xb
from parentsbot.models import Abonent, Boglanish, ParentsBotSozlama, Xabar
from parentsbot.test_bot import SoxtaTg

TOSH = ZoneInfo("Asia/Tashkent")


class DavrTest(SimpleTestCase):
    def test_har_kuni_songgi_24_soat(self):
        boshi, oxiri = xb.natija_davri(date(2026, 10, 7), list(range(7)), time(19, 0))
        self.assertEqual(timezone.localtime(boshi).replace(tzinfo=None), datetime(2026, 10, 6, 19, 0))
        self.assertEqual(timezone.localtime(oxiri).replace(tzinfo=None), datetime(2026, 10, 7, 19, 0))

    def test_haftada_ikki_marta_oraliq_bosh_qolmaydi(self):
        # dushanba (0) va payshanba (3): payshanbadagi yig'ma dushanba 19:00 dan boshlanadi
        boshi, _ = xb.natija_davri(date(2026, 10, 8), [0, 3], time(19, 0))  # 8-oktabr — payshanba
        self.assertEqual(timezone.localtime(boshi).replace(tzinfo=None), datetime(2026, 10, 5, 19, 0))
        # dushanbadagi yig'ma oldingi payshanbadan
        boshi, _ = xb.natija_davri(date(2026, 10, 12), [0, 3], time(19, 0))
        self.assertEqual(timezone.localtime(boshi).replace(tzinfo=None), datetime(2026, 10, 8, 19, 0))


class NatijaAsos(ApiAsos):
    def setUp(self):
        super().setUp()
        ParentsBotSozlama.ol()  # sozlama yozuvi bo'lsin: testlardagi update() bo'shga ketmasin
        self.tg = SoxtaTg()
        self.kun = timezone.localdate()
        self.hozir = datetime.combine(self.kun, time(19, 30), tzinfo=TOSH)  # standart 19:00 dan keyin
        self.ichida = datetime.combine(self.kun, time(15, 0), tzinfo=TOSH)  # davr ichida
        self.ota = Abonent.objects.create(telegram_id=501, ism="Ota", til="uz", holat="tayyor")
        Boglanish.objects.create(abonent=self.ota, talaba=self.talaba, usul="telefon")
        self.mashq = KursMashq.objects.create(tugun=self.daraja, savollar=[])
        self.vocab = KursTugun.objects.create(markaz=self.markaz, nomi="Vocabulary", parent=self.daraja,
                                               kalit="vocabulary")

    def yechim(self, ball, jami, vaqt=None, talaba=None):
        y = KursMashqYechim.objects.create(talaba=talaba or self.talaba, mashq=self.mashq, javoblar=[],
                                           ball=ball, jami=jami, natijalar=[])
        KursMashqYechim.objects.filter(pk=y.pk).update(created_at=vaqt or self.ichida)

    def soz_yechim(self, ball, jami, vaqt=None, talaba=None):
        y = KursSozYechim.objects.create(talaba=talaba or self.talaba, tugun=self.vocab, ball=ball, jami=jami)
        KursSozYechim.objects.filter(pk=y.pk).update(created_at=vaqt or self.ichida)

    def writing(self, band, holat="tayyor", vaqt=None):
        w = WritingTekshiruv.objects.create(talaba=self.talaba, matn="x", overall_band=band, holat=holat)
        WritingTekshiruv.objects.filter(pk=w.pk).update(created_at=vaqt or self.ichida)

    def imtihon_yechim(self, bolim, band, nomi="Cambridge 13 Test 4", vaqt=None, talaba=None):
        test = ImtihonTest.objects.create(name=nomi, bolim=bolim, markaz=self.markaz)
        y = TestYechim.objects.create(talaba=talaba or self.talaba, test=test, javoblar=[],
                                       ball=8, jami=10, natijalar=[], band=band)
        TestYechim.objects.filter(pk=y.pk).update(created_at=vaqt or self.ichida)


class NatijaTest(NatijaAsos):
    def test_kunlik_yigma(self):
        self.yechim(8, 10)
        self.yechim(6, 10)
        self.writing(6.5)
        self.assertEqual(xb.skanerla_natija(self.hozir), 1)
        self.assertEqual(xb.yubor_navbat(self.tg, self.hozir, pauza=0), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("kunlik natijalar", matn)
        self.assertIn("Mashqlar: 2 ta, o'rtacha natija 70%", matn)
        self.assertIn("Writing: 1 ta, band 6.5", matn)
        self.assertNotIn("Speaking", matn)

    def test_vokabulyar_natijasi_kunlik_yigmaga_kiradi(self):
        # Video-TZ 2026-10-08: Vocabulary mashqi natijasi ham "Mashqlar"
        # umumiy hisobiga qo'shiladi — ota-ona botiga alohida yuboriladi
        # deb talab qilinmagan, mavjud kunlik yig'maga qo'shiladi.
        self.soz_yechim(2, 2)
        self.assertEqual(xb.skanerla_natija(self.hozir), 1)
        self.assertEqual(xb.yubor_navbat(self.tg, self.hozir, pauza=0), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("Mashqlar: 1 ta, o'rtacha natija 100%", matn)

    def test_vokabulyar_va_boshqa_mashqlar_birga_hisoblanadi(self):
        self.yechim(8, 10)
        self.soz_yechim(1, 2)
        xb.skanerla_natija(self.hozir)
        xb.yubor_navbat(self.tg, self.hozir, pauza=0)
        matn = self.tg.yuborilgan[-1][1]
        # (8+1)/(10+2) = 75%
        self.assertIn("Mashqlar: 2 ta, o'rtacha natija 75%", matn)

    def test_hech_narsa_qilmagan_bolsa_xabar_yoq(self):
        self.yechim(5, 10, vaqt=self.ichida - timedelta(days=2))  # davrdan tashqarida
        self.writing(7.0, holat="kutilmoqda")  # tayyor emas
        self.assertEqual(xb.skanerla_natija(self.hozir), 0)

    def test_soatdan_oldin_va_kuniga_bitta(self):
        self.yechim(8, 10)
        self.assertEqual(xb.skanerla_natija(self.hozir.replace(hour=18)), 0)
        # 19:05 — AI tekshiruvlari tugashi uchun NATIJA_KUTISH (10 daqiqa) hali o'tmagan
        self.assertEqual(xb.skanerla_natija(self.hozir.replace(hour=19, minute=5)), 0)
        xb.skanerla_natija(self.hozir)
        xb.skanerla_natija(self.hozir + timedelta(hours=1))
        self.assertEqual(Xabar.objects.filter(turi="natija").count(), 1)

    def test_soat_chegarasida_topshirilgan_writing_yigmaga_tushadi(self):
        # 18:59 da topshirilgan, AI 19:03 da tugatgan — 19:10 dagi yig'mada bor
        w = WritingTekshiruv.objects.create(talaba=self.talaba, matn="x", overall_band=None, holat="kutilmoqda")
        WritingTekshiruv.objects.filter(pk=w.pk).update(
            created_at=datetime.combine(self.kun, time(18, 59), tzinfo=TOSH))
        WritingTekshiruv.objects.filter(pk=w.pk).update(holat="tayyor", overall_band=7.0)
        self.assertEqual(xb.skanerla_natija(self.hozir.replace(hour=19, minute=10)), 1)

    def test_band_ielts_qoidasida_yaxlitlanadi(self):
        self.writing(6.0)
        self.writing(6.5)  # o'rtacha 6.25 -> 6.5
        xb.skanerla_natija(self.hozir)
        xb.yubor_navbat(self.tg, self.hozir, pauza=0)
        self.assertIn("band 6.5", self.tg.yuborilgan[-1][1])

    def test_ikki_farzand_ikkalasining_natijasi(self):
        from accounts.models import User

        ikkinchi = User.objects.create_user(username="t2", password="x", role=User.Role.STUDENT,
                                            markaz=self.markaz, first_name="Malika")
        Boglanish.objects.create(abonent=self.ota, talaba=ikkinchi, usul="admin")
        self.yechim(8, 10)
        self.yechim(5, 10, talaba=ikkinchi)
        self.assertEqual(xb.skanerla_natija(self.hozir), 2)
        self.assertEqual(xb.yubor_navbat(self.tg, self.hozir, pauza=0), 2)
        self.assertTrue(any("Malika" in m and "50%" in m for _, m, _ in self.tg.yuborilgan))

    def test_davr_chegarasi_19_00(self):
        # 19:00 dan keyin qilingani — ertangi yig'maga kiradi, bugungiga emas
        self.yechim(8, 10, vaqt=datetime.combine(self.kun, time(19, 10), tzinfo=TOSH))
        self.assertEqual(xb.skanerla_natija(self.hozir), 0)

    def test_markaz_ochirgan(self):
        self.yechim(8, 10)
        ParentsBotSozlama.objects.filter(pk=1).update(natija_yoqilgan=False)
        self.assertEqual(xb.skanerla_natija(self.hozir), 0)

    def test_bloklagan_ota_onaga_yaratilmaydi(self):
        self.yechim(8, 10)
        Abonent.objects.filter(pk=self.ota.pk).update(faol=False)
        self.assertEqual(xb.skanerla_natija(self.hozir), 0)

    def test_jadvalda_yoq_kun(self):
        ParentsBotSozlama.ol()
        ParentsBotSozlama.objects.filter(pk=1).update(natija_kunlari=[(self.kun.weekday() + 1) % 7])
        self.yechim(8, 10)
        self.assertEqual(xb.skanerla_natija(self.hozir), 0)

    def test_ielts_toliq_test_listening_reading_bandi(self):
        # video-TZ 2026-10-08: IELTS to'liq testlari (Cambridge va h.k.) natijasi
        # ham Writing/Speaking kabi band bilan ota-onaga yuborilsin.
        self.imtihon_yechim("listening", 8.5, nomi="Cambridge 13 Test 4 Listening")
        self.imtihon_yechim("reading", 7.0, nomi="Cambridge 13 Test 4 Reading")
        self.assertEqual(xb.skanerla_natija(self.hozir), 1)
        self.assertEqual(xb.yubor_navbat(self.tg, self.hozir, pauza=0), 1)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("Listening: 1 ta, band 8.5", matn)
        self.assertIn("Reading: 1 ta, band 7.0", matn)

    def test_speaking_va_ruscha(self):
        Abonent.objects.filter(pk=self.ota.pk).update(til="ru")
        s = SpeakingTekshiruv.objects.create(talaba=self.talaba, rejim="matn", overall_band=6.0)
        SpeakingTekshiruv.objects.filter(pk=s.pk).update(created_at=self.ichida)
        xb.skanerla_natija(self.hozir)
        xb.yubor_navbat(self.tg, self.hozir, pauza=0)
        matn = self.tg.yuborilgan[-1][1]
        self.assertIn("результаты за день", matn)
        self.assertIn("Speaking: 1, band 6.0", matn)
        self.assertNotIn("Упражнения", matn)
