"""Matn-TZ 246: har Unit'da "Tests" bo'limi."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Markaz
from courses.models import KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat


class UnitTestsTuguniTest(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="SINOV markaz")

    def test_yangi_unitda_tests_bor(self):
        unit = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1", unit_darsi=True)
        unit_ichki_tuzilmasini_yarat(unit)
        kalitlar = list(unit.children.values_list("kalit", flat=True))
        self.assertEqual(kalitlar, ["students_book", "workbook", "vocabulary", "tests", "games"])

    def test_eski_unitga_qoshiladi_idempotent(self):
        unit = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1", unit_darsi=True)
        KursTugun.objects.create(markaz=self.markaz, nomi="Games", kalit="games", parent=unit, tartib=4)
        call_command("tests_tugun_qoshish", stdout=StringIO())
        call_command("tests_tugun_qoshish", stdout=StringIO())
        tests = KursTugun.objects.filter(parent=unit, kalit="tests")
        self.assertEqual(tests.count(), 1)
        # 2026-10-14: Tests Games'dan oldinga o'tkaziladi (tartiblar almashadi).
        self.assertEqual(tests.first().tartib, 4)
        self.assertEqual(KursTugun.objects.get(parent=unit, kalit="games").tartib, 5)

    def test_beginner_unit1_testlari_kiritiladi(self):
        ingliz = KursTugun.objects.create(markaz=self.markaz, nomi="Ingliz tili", kalit="ingliz_tili")
        beginner = KursTugun.objects.create(markaz=self.markaz, nomi="Beginner", kalit="beginner", parent=ingliz)
        unit = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1", parent=beginner, unit_darsi=True)
        unit_ichki_tuzilmasini_yarat(unit)
        call_command("beginner_unit1_testlari", stdout=StringIO())
        call_command("beginner_unit1_testlari", stdout=StringIO())
        mashqlar = list(KursTugun.objects.get(parent=unit, kalit="tests").mashqlar.all())
        self.assertEqual(len(mashqlar), 1)
        savollar = mashqlar[0].savollar
        self.assertEqual(len(savollar), 30)
        # PDF'dagi ANSWER KEY
        kalit = "ABCCABCBBCACBCCBACBABCABBBDBAA"
        for s, h in zip(savollar, kalit):
            self.assertEqual(s["togri"], s["variantlar"]["ABCD".index(h)])
            self.assertEqual(len(s["variantlar"]), 4)
        self.assertEqual(savollar[0]["togri"], "am")
        self.assertEqual(savollar[29]["togri"], "See you later")
