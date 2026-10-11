"""Matn-TZ 180: Vocabulary tarjimasi to'g'ri yozilsa ham xato hisoblanmasin."""

from django.test import SimpleTestCase

from courses.views import soz_javobi_togrimi


class SozJavobiTogrimiTest(SimpleTestCase):
    def test_apostrof_variantlari(self):
        for javob in ("o'qituvchi", "o‘qituvchi", "o’qituvchi", "oʻqituvchi", "o`qituvchi"):
            self.assertTrue(soz_javobi_togrimi(javob, "o‘qituvchi"), javob)
        self.assertTrue(soz_javobi_togrimi("to’g’ri", "to'g'ri"))

    def test_tire_variantlari(self):
        self.assertTrue(soz_javobi_togrimi("ko'k–yashil", "ko'k-yashil"))

    def test_bir_nechta_variant_boshqa_tartibda(self):
        self.assertTrue(soz_javobi_togrimi("har doim, doim", "doim, har doim"))
        self.assertTrue(soz_javobi_togrimi("ilova", "ilova (telefon dasturi)"))
        self.assertTrue(soz_javobi_togrimi("постоянно", "doim", "всегда, постоянно"))

    def test_xato_javob(self):
        self.assertFalse(soz_javobi_togrimi("", "doim"))
        self.assertFalse(soz_javobi_togrimi("doim, kitob", "doim, har doim"))
        self.assertFalse(soz_javobi_togrimi("kitob", "doim", "всегда"))
        # Tillarni aralashtirib bo'lmaydi
        self.assertFalse(soz_javobi_togrimi("doim, всегда", "doim", "всегда"))
