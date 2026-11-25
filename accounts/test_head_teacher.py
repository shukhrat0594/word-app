"""Head Teacher — kuzatuvchi roli (Matn-TZ 759, 2026-11-25).

Talabalar, Kurslar, Reyting, IELTS testlari, Speaking Trainer, Grammar
coach'ni admin darajasida ko'radi, lekin ma'lumotni o'zgartira olmaydi;
CRM'ga kira olmaydi. Qoida: accounts/authentication.py.
"""

from django.test import RequestFactory, TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from academics.models import Guruh, GuruhAzoligi
from accounts.authentication import head_teacher_rolini_qol
from accounts.models import Markaz, User
from accounts.tests import qurilmali_kalit


class HeadTeacherTest(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.owner = User.objects.create_user(username="owner", password="x", role=User.Role.ADMIN,
                                              markaz=self.markaz, is_superuser=True, is_staff=True)
        self.oqituvchi = User.objects.create_user(username="ustoz", password="x", role=User.Role.TEACHER,
                                                  markaz=self.markaz)
        self.talaba = User.objects.create_user(username="talaba1", password="x", role=User.Role.STUDENT,
                                               markaz=self.markaz, first_name="Ali")
        self.guruh = Guruh.objects.create(name="IELTS", markaz=self.markaz, oqituvchi=self.oqituvchi)
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.talaba)
        self.ht = User.objects.create_user(username="SINOV_head", password="x",
                                           role=User.Role.HEAD_TEACHER, markaz=self.markaz)

    def mijoz(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {qurilmali_kalit(user).access_token}")
        return c

    def test_owner_head_teacher_yarata_oladi(self):
        j = self.mijoz(self.owner).post("/api/foydalanuvchilar/yaratish/", {
            "username": "SINOV_head2", "parol": "Kuchli!Parol2026", "rol": "head_teacher",
        }, format="json")
        self.assertEqual(j.status_code, 201, j.data)
        u = User.objects.get(username="SINOV_head2")
        self.assertEqual(u.role, User.Role.HEAD_TEACHER)
        self.assertEqual(u.markaz_id, self.markaz.id)
        self.assertFalse(u.is_superuser)

    def test_profil_asl_rolni_qaytaradi(self):
        j = self.mijoz(self.ht).get("/api/profil/")
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.data["role"], "head_teacher")
        self.assertFalse(j.data["is_owner"])

    def test_bolimlarni_admin_kabi_koradi(self):
        c = self.mijoz(self.ht)
        j = c.get("/api/talabalar/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertIn("talaba1", [t["username"] for t in j.data])
        for yol in ("/api/kurslar/daraxt/", "/api/leaderboard/", "/api/imtihon/testlar/"):
            self.assertEqual(c.get(yol).status_code, 200, yol)
        # Simulyatsiya faqat xotirada — bazadagi rol o'zgarmaydi.
        self.ht.refresh_from_db()
        self.assertEqual(self.ht.role, User.Role.HEAD_TEACHER)

    def test_ozgartira_olmaydi(self):
        c = self.mijoz(self.ht)
        j = c.patch(f"/api/talabalar/{self.talaba.id}/", {"first_name": "Vali"}, format="json")
        self.assertEqual(j.status_code, 403)
        j = c.post("/api/talabalar/", {"username": "SINOV_t", "parol": "Kuchli!Parol2026"}, format="json")
        self.assertEqual(j.status_code, 403)
        j = c.delete(f"/api/foydalanuvchilar/{self.talaba.id}/ochirish/")
        self.assertEqual(j.status_code, 403)
        self.talaba.refresh_from_db()
        self.assertEqual(self.talaba.first_name, "Ali")
        self.assertFalse(User.objects.filter(username="SINOV_t").exists())

    def test_crm_yopiq(self):
        c = self.mijoz(self.ht)
        self.assertEqual(c.get("/api/crm/men/").status_code, 403)
        self.assertEqual(c.get("/api/crm/talabalar/").status_code, 403)

    def test_ai_trenajyor_va_profil_yozish_ochiq(self):
        c = self.mijoz(self.ht)
        # Bo'sh so'rov — AI chaqirilmaydi; muhimi 403 emas (kuzatuvchi bloki yo'q).
        self.assertNotEqual(c.post("/api/grammar/coach/", {}, format="json").status_code, 403)
        # Speaking trainer bo'sh so'rovda ham AI'ga murojaat qiladi — tarmoqsiz
        # tekshirish uchun qoidaning o'zi chaqiriladi.
        so_rov = RequestFactory().post("/api/speaking/trainer/")
        head_teacher_rolini_qol(self.ht, so_rov)  # PermissionDenied ko'tarilmaydi
        self.assertEqual(self.ht.role, User.Role.HEAD_TEACHER)
        with self.assertRaises(PermissionDenied):
            head_teacher_rolini_qol(self.ht, RequestFactory().post("/api/writing/tekshirish/"))
        j = c.post("/api/profil/tahrirlash/", {"bio": "SINOV"}, format="json")
        self.assertNotEqual(j.status_code, 403, getattr(j, "data", None))
