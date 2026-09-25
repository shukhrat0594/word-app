"""Saytdagi "O'chirish" va CRM (2026-09-25).

- CRM o'quvchisi O'CHIRILMAYDI — faqat saytga kirishi yopiladi
  (`crm/sayt_hisobi.py`); CRM'dagi hamma narsa joyida qoladi.
- CRM'ga tegishli bo'lmagan foydalanuvchi (masalan, to'lov kiritgan
  o'qituvchi) avvalgidek o'chiriladi va tiklanganda CRM yozuvlaridagi
  bog'lanish (SET_NULL bilan uzilgan) qayta ulanadi.

Umumiy savat testlari — `accounts/test_savat.py`.
"""

from datetime import date
from decimal import Decimal

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from academics.models import GuruhAzoligi
from accounts.models import OchirilganFoydalanuvchi, User
from crm import mantiq
from crm.models import AzolikMoliya, Hisob, Tolov
from crm.test_api import ApiAsos
from crm.tests import bugun_qilib


class CrmTalabaOchirilmaydiTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.talaba.set_password("Eski!Parol2026")
        self.talaba.save()
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 20)):
            mantiq.hisoblarni_generatsiya_qil()

    def test_crm_talabasi_ochirilmaydi_faqat_kirishi_yopiladi(self):
        RefreshToken.for_user(self.talaba)  # ochiq seans
        j = self.mijoz(self.owner).delete(f"/api/foydalanuvchilar/{self.talaba.id}/ochirish/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertTrue(j.data["sayt_kirishi_yopildi"])

        u = User.objects.get(pk=self.talaba.id)
        self.assertFalse(u.has_usable_password())
        self.assertTrue(u.is_active)  # CRM'dagi "arxiv" EMAS — faqat sayt kirishi
        self.assertTrue(GuruhAzoligi.objects.filter(talaba=u).exists())
        self.assertTrue(AzolikMoliya.objects.filter(azolik__talaba=u).exists())
        self.assertTrue(Hisob.objects.filter(talaba=u).exists())
        self.assertFalse(OchirilganFoydalanuvchi.objects.exists())
        self.assertEqual(BlacklistedToken.objects.filter(token__user=u).count(),
                         OutstandingToken.objects.filter(user=u).count())

    def test_royxatda_crm_talaba_belgisi(self):
        faqat_sayt = User.objects.create_user(username="sayt_talaba", password="x", role=User.Role.STUDENT)
        royxat = {x["id"]: x["crm_talaba"] for x in self.mijoz(self.owner).get("/api/foydalanuvchilar/").data}
        self.assertTrue(royxat[self.talaba.id])
        self.assertFalse(royxat[faqat_sayt.id])
        self.assertFalse(royxat[self.oqituvchi.id])  # o'qituvchi talaba emas

    def test_crmga_tegishli_bolmagan_talaba_avvalgidek_ochiriladi(self):
        faqat_sayt = User.objects.create_user(username="sayt_talaba", password="x", role=User.Role.STUDENT)
        j = self.mijoz(self.owner).delete(f"/api/foydalanuvchilar/{faqat_sayt.id}/ochirish/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertNotIn("sayt_kirishi_yopildi", j.data)
        self.assertFalse(User.objects.filter(pk=faqat_sayt.id).exists())
        self.assertTrue(OchirilganFoydalanuvchi.objects.filter(username="sayt_talaba").exists())


class CrmBoglanishTiklanishiTest(ApiAsos):
    def test_tolov_kiritgan_oqituvchi_tiklanganda_qayta_ulanadi(self):
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        hisob = Hisob.objects.get(talaba=self.talaba)
        tolov = Tolov.objects.create(talaba=self.talaba, guruh=self.guruh, hisob=hisob, summa=Decimal("100000"),
                                     sana=date(2026, 9, 5), talaba_ism="talaba1", guruh_nomi=self.guruh.name,
                                     kim_kiritdi=self.oqituvchi)
        m = self.mijoz(self.owner)
        self.assertEqual(m.delete(f"/api/foydalanuvchilar/{self.oqituvchi.id}/ochirish/").status_code, 200)
        tolov.refresh_from_db()
        self.assertIsNone(tolov.kim_kiritdi_id)

        yozuv = OchirilganFoydalanuvchi.objects.get()
        self.assertEqual(m.post(f"/api/ochirilganlar/{yozuv.id}/").status_code, 200)
        tolov.refresh_from_db()
        self.assertEqual(tolov.kim_kiritdi_id, self.oqituvchi.id)
