"""Ota-ona/talaba statistikasida davomat hisobi (video-TZ, IMG_6917.MOV).

Avval faqat keldi/kelmadi sanalardi — kechikdi va sababli kelmagan holatlar
alohida ko'rsatilmay, "keldi"/"kelmadi"ga qo'shilib ketardi.
"""

from accounts.models import Markaz, User
from academics.models import Davomat, Guruh
from django.apps import apps as django_apps
from django.test import TestCase

from .services import talaba_statistikasi

PAROL = "Sinov!Parol2026"


class DavomatStatistikasiTest(TestCase):
    def setUp(self):
        # `stats` LMS ilovasi — `crm`ni statik import qilmaydi
        # (crm.tests.IzolyatsiyaTest), shu uchun model runtime'da olinadi.
        DavomatIzoh = django_apps.get_model("crm", "DavomatIzoh")
        self.DavomatIzoh = DavomatIzoh
        self.markaz = Markaz.objects.create(name="Utmost")
        self.oqituvchi = User.objects.create_user(
            username="oqituvchi", password=PAROL, role=User.Role.TEACHER, markaz=self.markaz
        )
        self.talaba = User.objects.create_user(
            username="talaba", password=PAROL, role=User.Role.STUDENT, markaz=self.markaz
        )
        self.guruh = Guruh.objects.create(
            name="A1", markaz=self.markaz, oqituvchi=self.oqituvchi
        )
        self.guruh.talabalar.add(self.talaba)

        kunlar = ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-05"]
        self.keldi = Davomat.objects.create(
            sana=kunlar[0], guruh=self.guruh, talaba=self.talaba, holat=Davomat.Holat.KELDI
        )
        self.kechikdi = Davomat.objects.create(
            sana=kunlar[1], guruh=self.guruh, talaba=self.talaba, holat=Davomat.Holat.KELDI
        )
        self.DavomatIzoh.objects.create(davomat=self.kechikdi, kechikdi=True)
        self.kelmadi = Davomat.objects.create(
            sana=kunlar[2], guruh=self.guruh, talaba=self.talaba, holat=Davomat.Holat.KELMADI
        )
        self.sababli = Davomat.objects.create(
            sana=kunlar[3], guruh=self.guruh, talaba=self.talaba, holat=Davomat.Holat.KELMADI
        )
        self.DavomatIzoh.objects.create(davomat=self.sababli, sababli=True)

    def test_kechikdi_va_sababli_alohida_sanaladi(self):
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(
            stat["davomat"],
            {"keldi": 1, "kechikdi": 1, "kelmadi": 1, "sababli": 1},
        )
