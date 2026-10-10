"""Kalit qo'shimcha ko'rinishida ("-er") — Elementary WB Unit 2 (2026-10-10)."""

from django.test import SimpleTestCase

from .models import javoblarni_tekshir


class QoshimchaKalitTest(SimpleTestCase):
    savollar = [
        {"savol": "2 wait___", "togri": "-er"},
        {"savol": "3 act ___", "togri": "-or"},
    ]

    def natija(self, javoblar):
        return javoblarni_tekshir(self.savollar, javoblar)["natijalar"]

    def test_qoshimchaning_ozi(self):
        self.assertEqual(self.natija(["er", "or"]), [True, True])

    def test_defis_bilan(self):
        self.assertEqual(self.natija(["-er", " -OR "]), [True, True])

    def test_toliq_soz(self):
        self.assertEqual(self.natija(["waiter", "actor"]), [True, True])

    def test_notogri_qoshimcha(self):
        self.assertEqual(self.natija(["or", "er"]), [False, False])
        self.assertEqual(self.natija(["waitor", "acter"]), [False, False])
