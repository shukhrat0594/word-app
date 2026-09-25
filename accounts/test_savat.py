"""O'chirilgan foydalanuvchini 7 kun ichida tiklash (2026-09-25).

Bu yerda FAQAT LMS modellari: `crm` import qilinmaydi (`crm.tests.
IzolyatsiyaTest` qoidasi — CRM olib tashlansa sayt buzilmasin). CRM pul
yozuvlarining qayta ulanishi — `crm/test_savat.py`.
"""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from academics.models import Davomat, Guruh, GuruhAzoligi
from accounts.models import Markaz, OchirilganFoydalanuvchi, User
from accounts.savat import muddati_otganlarni_tozala


class SavatTest(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.owner = User.objects.create_user(username="owner", password="x", role=User.Role.ADMIN,
                                              markaz=self.markaz, is_superuser=True, is_staff=True)
        self.admin = User.objects.create_user(username="admin1", password="x", role=User.Role.ADMIN,
                                              markaz=self.markaz)
        self.oqituvchi = User.objects.create_user(username="ustoz", password="x", role=User.Role.TEACHER,
                                                  markaz=self.markaz)
        self.talaba = User.objects.create_user(username="talaba1", password="Eski!Parol2026",
                                               role=User.Role.STUDENT, markaz=self.markaz, first_name="Ali")
        self.guruh = Guruh.objects.create(name="IELTS", markaz=self.markaz, oqituvchi=self.oqituvchi)
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.talaba)
        Davomat.objects.create(guruh=self.guruh, talaba=self.talaba, sana=date(2026, 9, 3), holat="keldi",
                               belgilagan=self.oqituvchi)

    def mijoz(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return c

    def ochir(self, user, kim=None):
        j = self.mijoz(kim or self.admin).delete(f"/api/foydalanuvchilar/{user.id}/ochirish/")
        self.assertEqual(j.status_code, 200, j.data)
        return OchirilganFoydalanuvchi.objects.get(foydalanuvchi_id=user.id)

    def test_ochirilgan_hamma_joydan_yoqoladi_lekin_nusxa_qoladi(self):
        yozuv = self.ochir(self.talaba)
        self.assertFalse(User.objects.filter(pk=self.talaba.id).exists())
        self.assertFalse(GuruhAzoligi.objects.filter(talaba_id=self.talaba.id).exists())
        self.assertGreaterEqual(yozuv.soni, 3)  # user + a'zolik + davomat
        royxat = self.mijoz(self.admin).get("/api/ochirilganlar/").data
        self.assertEqual([x["username"] for x in royxat], ["talaba1"])
        self.assertEqual(royxat[0]["qolgan_kun"], 7)  # yuqoriga yaxlitlanadi

    def test_tiklash_hammasini_qaytaradi(self):
        yozuv = self.ochir(self.talaba)
        j = self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["tiklanmaganlar"], [])
        u = User.objects.get(pk=self.talaba.id)
        self.assertEqual((u.username, u.first_name), ("talaba1", "Ali"))
        self.assertTrue(u.check_password("Eski!Parol2026"))
        self.assertTrue(GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=u).exists())
        self.assertEqual(Davomat.objects.filter(talaba=u).count(), 1)
        self.assertFalse(OchirilganFoydalanuvchi.objects.exists())

    def test_oqituvchi_tiklansa_guruhiga_qayta_ulanadi(self):
        """SET_NULL bilan uzilgan bog'lanish (guruh o'qituvchisi) ham qaytadi."""
        yozuv = self.ochir(self.oqituvchi)
        self.guruh.refresh_from_db()
        self.assertIsNone(self.guruh.oqituvchi_id)
        self.assertEqual(self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/").status_code, 200)
        self.guruh.refresh_from_db()
        self.assertEqual(self.guruh.oqituvchi_id, self.oqituvchi.id)
        self.assertEqual(Davomat.objects.get().belgilagan_id, self.oqituvchi.id)

    def test_login_band_bolsa_tiklanmaydi(self):
        yozuv = self.ochir(self.talaba)
        User.objects.create_user(username="talaba1", password="x", role=User.Role.STUDENT)
        j = self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/")
        self.assertEqual(j.status_code, 400)
        self.assertIn("talaba1", j.data["detail"])
        self.assertTrue(OchirilganFoydalanuvchi.objects.filter(pk=yozuv.pk).exists())

    def test_oradagi_vaqtda_guruh_ochgan_bolsa_qolgani_tiklanadi(self):
        yozuv = self.ochir(self.talaba)
        self.guruh.delete()
        j = self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertTrue(User.objects.filter(pk=self.talaba.id).exists())
        self.assertEqual(len(j.data["tiklanmaganlar"]), 2)  # a'zolik va davomat — guruhsiz tiklanmaydi

    def test_7_kundan_keyin_butunlay_ochadi(self):
        yozuv = self.ochir(self.talaba)
        OchirilganFoydalanuvchi.objects.filter(pk=yozuv.pk).update(
            ochirilgan_vaqt=timezone.now() - timedelta(days=7, minutes=1))
        self.assertEqual(self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/").status_code, 400)
        self.assertEqual(muddati_otganlarni_tozala(), 1)
        self.assertFalse(OchirilganFoydalanuvchi.objects.exists())

    def test_butunlay_ochirish(self):
        yozuv = self.ochir(self.talaba)
        self.assertEqual(self.mijoz(self.admin).delete(f"/api/ochirilganlar/{yozuv.id}/").status_code, 204)
        self.assertFalse(OchirilganFoydalanuvchi.objects.exists())

    def test_adminni_faqat_owner_tiklaydi(self):
        admin2 = User.objects.create_user(username="admin2", password="x", role=User.Role.ADMIN, markaz=self.markaz)
        yozuv = self.ochir(admin2, kim=self.owner)
        self.assertEqual(self.mijoz(self.admin).get("/api/ochirilganlar/").data, [])  # admin ko'rmaydi
        self.assertEqual(self.mijoz(self.admin).post(f"/api/ochirilganlar/{yozuv.id}/").status_code, 403)
        self.assertEqual(self.mijoz(self.owner).post(f"/api/ochirilganlar/{yozuv.id}/").status_code, 200)

    def test_oqituvchi_va_talabaga_yopiq(self):
        self.assertEqual(self.mijoz(self.oqituvchi).get("/api/ochirilganlar/").status_code, 403)
        self.assertEqual(self.mijoz(self.talaba).get("/api/ochirilganlar/").status_code, 403)
