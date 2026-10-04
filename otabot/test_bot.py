from datetime import date

from django.test import TestCase

from accounts.models import Bildirishnoma, User
from otabot.bot import Bot
from otabot.models import Abonent, Boglanish, Sorov


class SoxtaTg:
    def __init__(self):
        self.yuborilgan = []

    def yubor(self, chat_id, matn, tugmalar=None):
        self.yuborilgan.append((chat_id, matn, tugmalar))

    def callback_javob(self, callback_id):
        pass

    def oxirgi(self):
        return self.yuborilgan[-1][1] if self.yuborilgan else None


def xabar(uid, matn=None, contact=None, chat="private", ism="Ota"):
    m = {"chat": {"type": chat, "id": uid}, "from": {"id": uid, "first_name": ism}}
    if matn is not None:
        m["text"] = matn
    if contact is not None:
        m["contact"] = contact
    return {"message": m}


def tugma(uid, data):
    return {"callback_query": {"id": "cb1", "from": {"id": uid, "first_name": "Ota"}, "data": data}}


class BotAsos(TestCase):
    def setUp(self):
        self.tg = SoxtaTg()
        self.bot = Bot(self.tg)
        self.t1 = User.objects.create_user(
            username="aziz", password="x", role=User.Role.STUDENT, first_name="Aziz", last_name="Karimov",
            tugilgan_sana=date(2010, 1, 16), ota_ona_telefon="+998 90 123 45 67")
        self.t2 = User.objects.create_user(
            username="sevara", password="x", role=User.Role.STUDENT, first_name="Sevara", last_name="Jo'rayeva",
            tugilgan_sana=date(2011, 3, 3), ota_ona_telefon="")

    def yubor(self, *a, **k):
        self.bot.qayta_ishla(xabar(*a, **k))

    def tilgacha(self, uid=100, til="uz"):
        self.yubor(uid, "/start")
        self.bot.qayta_ishla(tugma(uid, f"til:{til}"))


class TelefonBilanUlashTest(BotAsos):
    def test_start_til_so_raydi(self):
        self.yubor(100, "/start")
        self.assertIn("Tilni tanlang", self.tg.oxirgi())
        self.assertEqual(Abonent.objects.get().holat, "til")

    def test_til_tanlangach_telefon_so_raydi(self):
        self.tilgacha()
        self.assertIn("telefon", self.tg.oxirgi().lower())
        self.assertTrue(self.tg.yuborilgan[-1][2]["keyboard"][0][0]["request_contact"])

    def test_telefon_mos_kelsa_ulanadi(self):
        self.tilgacha()
        self.yubor(100, contact={"phone_number": "+998901234567", "user_id": 100})
        self.assertIn("Ulandi", self.tg.oxirgi())
        self.assertIn("Aziz Karimov", self.tg.oxirgi())
        b = Boglanish.objects.get()
        self.assertEqual((b.talaba, b.usul, b.faol), (self.t1, "telefon", True))

    def test_begona_kontakt_qabul_qilinmaydi(self):
        self.tilgacha()
        self.yubor(100, contact={"phone_number": "+998901234567", "user_id": 999})  # boshqaning raqami
        self.assertIn("o'zingizning", self.tg.oxirgi())
        self.assertEqual(Boglanish.objects.count(), 0)
        self.assertEqual(Abonent.objects.get().telefon, "")

    def test_kontaktda_user_id_yoq_bolsa_ham_rad(self):
        self.tilgacha()
        self.yubor(100, contact={"phone_number": "+998901234567"})
        self.assertEqual(Boglanish.objects.count(), 0)

    def test_ruscha(self):
        self.tilgacha(til="ru")
        self.yubor(100, contact={"phone_number": "+998901234567", "user_id": 100})
        self.assertIn("Подключено", self.tg.oxirgi())

    def test_guruh_xabari_e_tiborsiz(self):
        self.bot.qayta_ishla(xabar(100, "/start", chat="supergroup"))
        self.assertEqual(self.tg.yuborilgan, [])
        self.assertEqual(Abonent.objects.count(), 0)


class IsmBilanUlashTest(BotAsos):
    def telefonsiz(self):
        self.tilgacha()
        self.yubor(100, contact={"phone_number": "+998931112233", "user_id": 100})  # CRM'da yo'q raqam

    def test_telefon_topilmasa_ism_so_raydi(self):
        self.telefonsiz()
        self.assertIn("ism-familiya", self.tg.oxirgi())
        self.yubor(100, "Sevara Jorayeva")
        self.assertIn("sanasini", self.tg.oxirgi())

    def test_ism_va_sana_aniq_mos_kelsa_ulanadi(self):
        self.telefonsiz()
        self.yubor(100, "Sevara Jorayeva")
        self.yubor(100, "03.03.2011")
        self.assertIn("Ulandi", self.tg.oxirgi())
        b = Boglanish.objects.get()
        self.assertEqual((b.talaba, b.usul), (self.t2, "ism_sana"))
        self.assertEqual(Sorov.objects.count(), 0)

    def test_sana_noto_gri_bolsa_sorov_adminga_va_javob_bir_xil(self):
        self.telefonsiz()
        self.yubor(100, "Sevara Jorayeva")
        self.yubor(100, "01.01.2000")  # sana mos emas
        self.assertIn("adminlariga yuborildi", self.tg.oxirgi())
        self.assertEqual(Boglanish.objects.count(), 0)
        s = Sorov.objects.get()
        self.assertEqual((s.holat, s.farzand_ismi), ("kutilmoqda", "Sevara Jorayeva"))

    def test_umuman_topilmasa_ham_javob_bir_xil(self):
        # begona ism: bot "topilmadi" demaydi — kim o'qishini aniqlab bo'lmasin
        self.telefonsiz()
        self.yubor(100, "Mavjud Emas")
        self.yubor(100, "01.01.2000")
        javob_topilmagan = self.tg.oxirgi()
        self.assertIn("adminlariga yuborildi", javob_topilmagan)
        self.assertNotIn("topilmadi", javob_topilmagan.lower())

    def test_sana_formati_xato(self):
        self.telefonsiz()
        self.yubor(100, "Sevara Jorayeva")
        self.yubor(100, "kecha")
        self.assertIn("kk.oo.yyyy", self.tg.oxirgi())
        self.assertEqual(Abonent.objects.get().holat, "farzand_sana")  # shu bosqichda qoladi

    def test_urinishlar_cheklovi(self):
        self.telefonsiz()
        for _ in range(3):
            self.yubor(100, "/start")  # holatni qayta ism bosqichiga qaytarish uchun
            Abonent.objects.filter(telegram_id=100).update(holat="farzand_ism")
            self.yubor(100, "Mavjud Emas")
            self.yubor(100, "01.01.2000")
        Abonent.objects.filter(telegram_id=100).update(holat="farzand_ism")
        self.yubor(100, "Sevara Jorayeva")
        self.yubor(100, "03.03.2011")  # to'g'ri bo'lsa ham — 4-urinish rad etiladi
        self.assertIn("Urinishlar soni", self.tg.oxirgi())
        self.assertEqual(Boglanish.objects.count(), 0)

    def test_sorov_takrorlanmaydi(self):
        self.telefonsiz()
        for _ in range(2):
            Abonent.objects.filter(telegram_id=100).update(holat="farzand_ism")
            self.yubor(100, "Mavjud Emas")
            self.yubor(100, "01.01.2000")
        self.assertEqual(Sorov.objects.count(), 1)


class BuyruqlarTest(BotAsos):
    def ulangan(self):
        self.tilgacha()
        self.yubor(100, contact={"phone_number": "+998901234567", "user_id": 100})

    def test_farzandlarim(self):
        self.ulangan()
        self.yubor(100, "/farzandlarim")
        self.assertIn("Aziz Karimov", self.tg.oxirgi())

    def test_stop_va_qayta_start(self):
        self.ulangan()
        self.yubor(100, "/stop")
        self.assertFalse(Abonent.objects.get().faol)
        self.yubor(100, "/start")
        self.assertTrue(Abonent.objects.get().faol)
        self.assertIn("Aziz Karimov", self.tg.oxirgi())

    def test_til_almashtirish(self):
        self.ulangan()
        self.yubor(100, "/til")
        self.bot.qayta_ishla(tugma(100, "til:ru"))
        self.assertEqual(Abonent.objects.get().til, "ru")

    def test_notanish_til_tugmasi_e_tiborsiz(self):
        self.tilgacha()
        self.bot.qayta_ishla(tugma(100, "til:xx"))
        self.assertEqual(Abonent.objects.get().til, "uz")

    def test_tushunarsiz_buyruq(self):
        self.ulangan()
        self.yubor(100, "/notanish")
        self.assertIn("Tushunmadim", self.tg.oxirgi())
