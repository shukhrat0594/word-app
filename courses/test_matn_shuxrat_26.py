"""Matn-TZ Shuxrat_26: Beginner Unit 2–14 Tests savollari."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Markaz
from courses.models import KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat


class BeginnerTestlariTest(TestCase):
    def setUp(self):
        markaz = Markaz.objects.create(name="SINOV markaz")
        ingliz = KursTugun.objects.create(markaz=markaz, nomi="Ingliz tili", kalit="ingliz_tili")
        beginner = KursTugun.objects.create(markaz=markaz, nomi="Beginner", kalit="beginner", parent=ingliz)
        self.unitlar = []
        for n in range(1, 15):
            unit = KursTugun.objects.create(markaz=markaz, nomi=f"Unit {n}", parent=beginner,
                                            unit_darsi=True, tartib=n)
            unit_ichki_tuzilmasini_yarat(unit)
            self.unitlar.append(unit)

    def mashqlar(self, n):
        return list(KursTugun.objects.get(parent=self.unitlar[n - 1], kalit="tests").mashqlar.all())

    def test_kiritiladi_idempotent(self):
        call_command("beginner_testlari", stdout=StringIO())
        call_command("beginner_testlari", stdout=StringIO())
        self.assertEqual(self.mashqlar(1), [])
        for n in range(2, 15):
            mashqlar = self.mashqlar(n)
            self.assertEqual(len(mashqlar), 2, n)
            savollar = mashqlar[0].savollar + mashqlar[1].savollar
            self.assertEqual(len(savollar), 29 if n == 3 else 30, n)
            for s in savollar:
                self.assertIn(s["togri"], s["variantlar"])

    def test_pdf_kaliti(self):
        call_command("beginner_testlari", stdout=StringIO())
        u2 = self.mashqlar(2)
        self.assertEqual(u2[0].savollar[0]["togri"], "is")
        self.assertEqual(u2[1].savollar[14]["togri"], "Italy")
        u7 = self.mashqlar(7)
        self.assertEqual(u7[0].savollar[14]["togri"], "does Annie")
        u14 = self.mashqlar(14)
        self.assertEqual(u14[1].savollar[6]["togri"], "to")
