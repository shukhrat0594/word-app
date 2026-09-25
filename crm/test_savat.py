"""O'chirilgan foydalanuvchi tiklanganda CRM ma'lumoti ham qaytadi
(2026-09-25). Umumiy savat testlari — `accounts/test_savat.py`; bu yerda
CRM'ga xos qism: guruh moliyasi (CASCADE) qaytadi, pul yozuvlari
(SET_NULL bilan uzilgan) o'sha talabaga qayta ulanadi."""

from datetime import date
from decimal import Decimal

from accounts.models import OchirilganFoydalanuvchi, User
from crm import mantiq
from crm.models import AzolikMoliya, Hisob, Tolov
from crm.test_api import ApiAsos
from crm.tests import bugun_qilib


class CrmSavatTest(ApiAsos):
    def test_tiklanganda_hisob_va_tolov_qayta_ulanadi(self):
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        hisob = Hisob.objects.get(talaba=self.talaba)
        tolov = Tolov.objects.create(talaba=self.talaba, guruh=self.guruh, hisob=hisob, summa=Decimal("100000"),
                                     sana=date(2026, 9, 5), talaba_ism="talaba1", guruh_nomi=self.guruh.name)
        m = self.mijoz(self.admin)

        self.assertEqual(m.delete(f"/api/foydalanuvchilar/{self.talaba.id}/ochirish/").status_code, 200)
        hisob.refresh_from_db()
        self.assertIsNone(hisob.talaba_id)  # pul tarixi qoladi, talabasiz
        self.assertFalse(AzolikMoliya.objects.exists())

        yozuv = OchirilganFoydalanuvchi.objects.get()
        j = m.post(f"/api/ochirilganlar/{yozuv.id}/")
        self.assertEqual(j.status_code, 200, j.data)
        u = User.objects.get(pk=self.talaba.id)
        hisob.refresh_from_db()
        tolov.refresh_from_db()
        self.assertEqual((hisob.talaba_id, tolov.talaba_id), (u.id, u.id))
        self.assertTrue(AzolikMoliya.objects.filter(azolik__talaba=u).exists())
        self.assertEqual(mantiq.balans(u, guruh=self.guruh), Decimal("100000") - hisob.summa)
