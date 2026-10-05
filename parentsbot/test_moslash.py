from datetime import date

from django.test import SimpleTestCase, TestCase

from accounts.models import User
from parentsbot import moslash as m


class TozaFunksiyalarTest(SimpleTestCase):
    def test_telefon_kaliti(self):
        self.assertEqual(m.telefon_kaliti("+998 90 123-45-67"), "901234567")
        self.assertEqual(m.telefon_kaliti("901234567"), "901234567")
        self.assertEqual(m.telefon_kaliti("(90) 123 45 67"), "901234567")
        self.assertEqual(m.telefon_kaliti("12345"), "")  # juda qisqa — mos kelmaydi
        self.assertEqual(m.telefon_kaliti(""), "")
        self.assertEqual(m.telefon_kaliti(None), "")

    def test_ism_kaliti_tartib_va_registr(self):
        self.assertEqual(m.ism_kaliti("Karimov Aziz"), m.ism_kaliti("aziz KARIMOV"))
        self.assertEqual(m.ism_kaliti("  Aziz   Karimov "), "aziz karimov")

    def test_ism_kaliti_apostrof(self):
        self.assertEqual(m.ism_kaliti("Jo'rayeva Sevara"), m.ism_kaliti("Jorayeva Sevara"))
        self.assertEqual(m.ism_kaliti("Jo‘rayeva Sevara"), m.ism_kaliti("Jo`rayeva Sevara"))
        self.assertEqual(m.ism_kaliti("Oʻrinova Dilnoza"), m.ism_kaliti("Orinova Dilnoza"))

    def test_ism_kaliti_kirill(self):
        self.assertEqual(m.ism_kaliti("Азиз Каримов"), m.ism_kaliti("Aziz Karimov"))
        self.assertEqual(m.ism_kaliti("Жўраева Севара"), m.ism_kaliti("Jorayeva Sevara"))

    def test_imlo_variantlari(self):
        self.assertEqual(m.ism_kaliti("Qodirov Xurshid"), m.ism_kaliti("Кодиров Хуршид"))
        self.assertEqual(m.ism_kaliti("Hasanov Ali"), m.ism_kaliti("Xasanov Ali"))
        self.assertEqual(m.ism_kaliti("Aziiz Karimov"), m.ism_kaliti("Aziz Karimov"))

    def test_boshqa_ism_mos_emas(self):
        self.assertNotEqual(m.ism_kaliti("Aziz Karimov"), m.ism_kaliti("Aziza Karimova"))
        self.assertEqual(m.ism_kaliti(""), "")
        self.assertEqual(m.ism_kaliti("123 !!!"), "")

    def test_sana_tahlil(self):
        d = date(2010, 1, 16)
        for matn in ("16.01.2010", "16/01/2010", "16-01-2010", "2010-01-16", " 16.1.2010 ", "16 01 2010"):
            self.assertEqual(m.sana_tahlil(matn), d, matn)
        for matn in ("31.02.2010", "kecha", "", None, "16.01.10"):
            self.assertIsNone(m.sana_tahlil(matn), matn)


class BazaBilanTest(TestCase):
    def setUp(self):
        self.t1 = User.objects.create_user(
            username="aziz", password="x", role=User.Role.STUDENT, first_name="Aziz", last_name="Karimov",
            tugilgan_sana=date(2010, 1, 16), ota_ona_telefon="+998 90 123 45 67")
        self.t2 = User.objects.create_user(
            username="aziz2", password="x", role=User.Role.STUDENT, first_name="Aziz", last_name="Karimov",
            tugilgan_sana=date(2012, 5, 5), ota_ona_telefon="+998 90 123 45 67")
        self.t3 = User.objects.create_user(
            username="sevara", password="x", role=User.Role.STUDENT, first_name="Sevara", last_name="Jo'rayeva",
            tugilgan_sana=date(2011, 3, 3), ota_ona_telefon="")
        self.arxiv = User.objects.create_user(
            username="eski", password="x", role=User.Role.STUDENT, first_name="Eski", last_name="Talaba",
            tugilgan_sana=date(2010, 1, 1), is_active=False, ota_ona_telefon="+998 90 123 45 67")

    def test_telefon_bir_necha_farzand(self):
        topildi = {t.username for t in m.telefon_boyicha("901234567")}
        self.assertEqual(topildi, {"aziz", "aziz2"})  # faol farzandlar; arxivdagi (faol emas) yo'q

    def test_telefon_bosh_yoki_notanish(self):
        self.assertEqual(m.telefon_boyicha(""), [])
        self.assertEqual(m.telefon_boyicha("931112233"), [])

    def test_ota_ona_hisobi_telefoni(self):
        ota = User.objects.create_user(username="ota", password="x", role=User.Role.PARENT, telefon="+998 93 111 22 33")
        User.objects.filter(pk=self.t3.pk).update(ota_ona=ota)
        self.assertEqual([t.username for t in m.telefon_boyicha("931112233")], ["sevara"])

    def test_aniq_moslik_ism_va_sana(self):
        self.assertEqual([t.username for t in m.aniq_moslik("aziz karimov", date(2010, 1, 16))], ["aziz"])
        self.assertEqual([t.username for t in m.aniq_moslik("Азиз Каримов", date(2012, 5, 5))], ["aziz2"])

    def test_faqat_ism_yetmaydi_sana_noto_gri(self):
        self.assertEqual(m.aniq_moslik("Aziz Karimov", date(2000, 1, 1)), [])
        self.assertEqual(m.aniq_moslik("Aziz Karimov", None), [])

    def test_jorayeva_apostrofsiz(self):
        self.assertEqual([t.username for t in m.aniq_moslik("Sevara Jorayeva", date(2011, 3, 3))], ["sevara"])

    def test_nomzodlar_taxminiy(self):
        # imloviy xato: aniq mos kelmaydi, lekin admin ro'yxatida chiqadi
        self.assertEqual(m.aniq_moslik("Sevara Jorayva", date(2011, 3, 3)), [])
        self.assertIn(self.t3.id, m.nomzodlar("Sevara Jorayva", date(2011, 3, 3)))
        self.assertNotIn(self.arxiv.id, m.nomzodlar("Eski Talaba"))  # faol emas
