"""Matn-TZ 679: profil tarixida Kurslar mashqi qaysi Unit/kitobdan ekani ko'rinadi."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Markaz, User
from courses.models import KursMashq, KursMashqYechim, KursTugun
from courses.unit_qurish import unit_ichki_tuzilmasini_yarat


class TarixdaMashqJoyiTest(TestCase):
    def setUp(self):
        markaz = Markaz.objects.create(name="SINOV markaz")
        ildiz = KursTugun.objects.create(markaz=markaz, nomi="Kurslar")
        ingliz = KursTugun.objects.create(markaz=markaz, nomi="Ingliz tili", parent=ildiz)
        daraja = KursTugun.objects.create(markaz=markaz, nomi="Elementary", parent=ingliz)
        unit = KursTugun.objects.create(markaz=markaz, nomi="Unit 1", parent=daraja, unit_darsi=True)
        unit_ichki_tuzilmasini_yarat(unit)
        workbook = KursTugun.objects.get(parent=unit, kalit="workbook")
        mashq = KursMashq.objects.create(tugun=workbook, tartib=2, matn="SINOV matn", savollar=[])
        self.talaba = User.objects.create_user(username="sinov_talaba", password="x",
                                               role=User.Role.STUDENT, markaz=markaz)
        KursMashqYechim.objects.create(talaba=self.talaba, mashq=mashq, javoblar=[], ball=3, jami=5,
                                       natijalar=[])

    def test_nomida_daraja_unit_kitob_va_mashq_raqami(self):
        mijoz = APIClient()
        mijoz.force_authenticate(self.talaba)
        r = mijoz.get(f"/api/foydalanuvchilar/{self.talaba.id}/natijalar/")
        self.assertEqual(r.status_code, 200)
        kurs = [n for n in r.data["natijalar"] if n["turi"] == "kurslar"]
        self.assertEqual(kurs[0]["nomi"], "Elementary Unit 1, Workbook, Mashq #2")
