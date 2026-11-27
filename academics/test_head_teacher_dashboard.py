"""Head Teacher dashboard API (Matn-TZ 779) — academics/head_teacher.py."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient
from django.test import TestCase

from academics.models import Davomat, DarsPunktualligi, Guruh, GuruhAzoligi
from accounts.models import Markaz, User
from accounts.tests import qurilmali_kalit
from assessment.models import AiTrenajyorYozuvi
from assessment.views import ai_trenajyor_yozuvi
from courses.models import KursTugun
from exercises.models import ImtihonTest, TestYechim


class HeadTeacherDashboardTest(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.ustoz = User.objects.create_user(username="SINOV_ustoz", password="x", role=User.Role.TEACHER,
                                              markaz=self.markaz, first_name="Ustoz")
        self.t1 = User.objects.create_user(username="SINOV_t1", password="x", role=User.Role.STUDENT,
                                           markaz=self.markaz, first_name="Ali")
        self.t2 = User.objects.create_user(username="SINOV_t2", password="x", role=User.Role.STUDENT,
                                           markaz=self.markaz, first_name="Vali")
        self.daraja = KursTugun.objects.create(markaz=self.markaz, nomi="Beginner")
        self.guruh = Guruh.objects.create(name="SINOV G1", markaz=self.markaz, oqituvchi=self.ustoz,
                                          daraja=self.daraja)
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.t1)
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.t2)
        self.ht = User.objects.create_user(username="SINOV_head", password="x",
                                           role=User.Role.HEAD_TEACHER, markaz=self.markaz)
        test = ImtihonTest.objects.create(name="SINOV R", bolim="reading", markaz=self.markaz)
        TestYechim.objects.create(talaba=self.t1, test=test, javoblar={}, ball=30, jami=40,
                                  natijalar=[], band=7)
        TestYechim.objects.create(talaba=self.t2, test=test, javoblar={}, ball=10, jami=40,
                                  natijalar=[], band=4)

    def mijoz(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {qurilmali_kalit(user).access_token}")
        return c

    def test_faqat_head_teacher_admin_koradi(self):
        self.assertEqual(self.mijoz(self.t1).get("/api/head-teacher/dashboard/").status_code, 403)
        self.assertEqual(self.mijoz(self.ustoz).get("/api/head-teacher/dashboard/").status_code, 403)
        self.assertEqual(self.mijoz(self.ht).get("/api/head-teacher/dashboard/").status_code, 200)

    def test_dashboard_kpi(self):
        bugun = timezone.localdate()
        Davomat.objects.create(sana=bugun, guruh=self.guruh, talaba=self.t1, holat="keldi")
        Davomat.objects.create(sana=bugun, guruh=self.guruh, talaba=self.t2, holat="kelmadi")
        DarsPunktualligi.objects.create(guruh=self.guruh, oqituvchi=self.ustoz, sana=bugun,
                                        rejadagi_vaqt="14:00", amaliy_vaqt="14:10")
        DarsPunktualligi.objects.create(guruh=self.guruh, oqituvchi=self.ustoz,
                                        sana=bugun - timedelta(days=1),
                                        rejadagi_vaqt="14:00", amaliy_vaqt="13:58")
        j = self.mijoz(self.ht).get("/api/head-teacher/dashboard/")
        self.assertEqual(j.status_code, 200, j.data)
        k = j.data["kpi"]
        self.assertEqual(k["guruhlar"], 1)
        self.assertEqual(k["talabalar"], 2)
        self.assertEqual(k["darajalar"][0]["nomi"], "Beginner")
        self.assertEqual(k["natija_foiz"], 50.0)  # (30+10)/(40+40)
        self.assertIsNone(k["natija_ozgarish"])  # o'tgan davrda natija yo'q
        self.assertEqual(k["davomat_foiz"], 50.0)
        self.assertEqual(k["punktuallik"]["darslar"], 2)
        self.assertEqual(k["punktuallik"]["oz_vaqtida_foiz"], 50.0)
        self.assertEqual(k["punktuallik"]["ortacha_kechikish"], 5.0)
        self.assertEqual(k["sifat"]["indeks"], 50.0)
        self.assertEqual(k["sifat"]["holat"], "diqqat")
        self.assertEqual(j.data["konikmalar"]["reading_band"], 5.5)
        self.assertEqual(j.data["ustozlar_punktualligi"][0]["kechikishlar"], 1)
        self.assertEqual(j.data["diqqat_guruhlar"][0]["id"], self.guruh.id)

    def test_davr_filtri_va_ozgarish(self):
        # O'tgan davrdagi natija — joriy davr bilan solishtiriladi.
        eski = TestYechim.objects.create(
            talaba=self.t1, test=ImtihonTest.objects.first(), javoblar={}, ball=20, jami=40, natijalar=[]
        )
        TestYechim.objects.filter(pk=eski.pk).update(created_at=timezone.now() - timedelta(days=40))
        j = self.mijoz(self.ht).get("/api/head-teacher/dashboard/")
        self.assertEqual(j.data["kpi"]["oldingi_natija_foiz"], 50.0)
        self.assertEqual(j.data["kpi"]["natija_ozgarish"], 0.0)
        # Davr faqat o'tgan oyni qamrasa — joriy natijalar tushmaydi.
        gacha = (timezone.localdate() - timedelta(days=35)).isoformat()
        dan = (timezone.localdate() - timedelta(days=45)).isoformat()
        j = self.mijoz(self.ht).get(f"/api/head-teacher/dashboard/?dan={dan}&gacha={gacha}")
        self.assertEqual(j.data["kpi"]["natija_foiz"], 50.0)
        self.assertEqual(j.data["kpi"]["bajarilgan"], 1)

    def test_guruhlar_va_talabalar_royxati(self):
        c = self.mijoz(self.ht)
        j = c.get("/api/head-teacher/guruhlar/")
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.data[0]["talaba_soni"], 2)
        self.assertEqual(j.data[0]["natija_foiz"], 50.0)
        self.assertEqual(j.data[0]["oqituvchi"]["ism"], "Ustoz")
        j = c.get("/api/head-teacher/talabalar/?q=vali")
        self.assertEqual([t["id"] for t in j.data], [self.t2.id])
        self.assertEqual(j.data[0]["natija_foiz"], 25.0)
        self.assertEqual(j.data[0]["darajalar"], ["Beginner"])
        boshqa = Guruh.objects.create(name="SINOV G2", markaz=self.markaz)
        j = c.get(f"/api/head-teacher/talabalar/?guruh={boshqa.id}")
        self.assertEqual(j.data, [])

    def test_talaba_profili_ai_tarixi_bilan(self):
        ai_trenajyor_yozuvi(self.t1, "speaking_trainer", sessiya="123", mavzu="B1",
                            xabar_soni=0, javob="Savol 1")
        ai_trenajyor_yozuvi(self.t1, "speaking_trainer", sessiya="123", mavzu="B1",
                            xabar_soni=1, javob="Ball: 6/10")
        ai_trenajyor_yozuvi(self.t1, "grammar_coach", mavzu="Present Perfect", javob={"a": 1})
        ai_trenajyor_yozuvi(self.t1, "grammar_coach", mavzu="nega?", javob="izoh", davomi=True)
        self.assertEqual(AiTrenajyorYozuvi.objects.filter(talaba=self.t1).count(), 2)
        j = self.mijoz(self.ht).get(f"/api/head-teacher/talabalar/{self.t1.id}/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["guruhlar"][0]["nomi"], "SINOV G1")
        ai = {y["tur"]: y for y in j.data["ai_trenajyorlar"]}
        self.assertEqual(ai["speaking_trainer"]["xabar_soni"], 1)
        self.assertEqual(ai["speaking_trainer"]["oxirgi_javob"], "Ball: 6/10")
        self.assertEqual(ai["grammar_coach"]["mavzu"], "Present Perfect")
        self.assertEqual(ai["grammar_coach"]["xabar_soni"], 2)
        # Natijalar ro'yxati (mavjud endpoint) ham ochiq.
        self.assertEqual(
            self.mijoz(self.ht).get(f"/api/foydalanuvchilar/{self.t1.id}/natijalar/").status_code, 200
        )

    def test_punktuallik_kiritish_yangilash_ochirish_yoq(self):
        c = self.mijoz(self.ht)
        bugun = timezone.localdate().isoformat()
        j = c.post("/api/head-teacher/punktuallik/", {
            "guruh": self.guruh.id, "sana": bugun, "rejadagi_vaqt": "14:00", "amaliy_vaqt": "14:07",
            "sabab": "Tirbandlik",
        }, format="json")
        self.assertEqual(j.status_code, 201, j.data)
        self.assertEqual(j.data["kechikish_daqiqa"], 7)
        self.assertEqual(j.data["oqituvchi"]["id"], self.ustoz.id)
        pk = j.data["id"]
        # Shu dars qayta yuborilsa — yangi yozuv emas, yangilanadi.
        j = c.post("/api/head-teacher/punktuallik/", {
            "guruh": self.guruh.id, "sana": bugun, "rejadagi_vaqt": "14:00", "amaliy_vaqt": "14:03",
        }, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(DarsPunktualligi.objects.count(), 1)
        j = c.patch(f"/api/head-teacher/punktuallik/{pk}/", {"sabab": "Majlis"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["kechikish_daqiqa"], 3)
        self.assertEqual(j.data["sabab"], "Majlis")
        self.assertEqual(c.delete(f"/api/head-teacher/punktuallik/{pk}/").status_code, 405)
        self.assertTrue(DarsPunktualligi.objects.filter(pk=pk).exists())
        j = c.get("/api/head-teacher/punktuallik/?guruhlash=hafta")
        self.assertEqual(j.status_code, 200)
        self.assertEqual(j.data["xulosa"]["kechikishlar"], 1)
        self.assertEqual(len(j.data["dinamika"]), 1)
        self.assertEqual(j.data["ustozlar"][0]["oqituvchi"]["id"], self.ustoz.id)

    def test_punktuallik_xatolari_va_ruxsat(self):
        c = self.mijoz(self.ht)
        j = c.post("/api/head-teacher/punktuallik/", {"guruh": self.guruh.id, "amaliy_vaqt": "14:00"},
                   format="json")
        self.assertEqual(j.status_code, 400)  # jadval yo'q, rejadagi vaqt berilmagan
        j = c.post("/api/head-teacher/punktuallik/", {"guruh": self.guruh.id, "rejadagi_vaqt": "abc"},
                   format="json")
        self.assertEqual(j.status_code, 400)
        j = self.mijoz(self.t1).post("/api/head-teacher/punktuallik/", {
            "guruh": self.guruh.id, "rejadagi_vaqt": "14:00",
        }, format="json")
        self.assertEqual(j.status_code, 403)
        # Head Teacher boshqa ma'lumotni hamon o'zgartira olmaydi.
        j = c.patch(f"/api/talabalar/{self.t1.id}/", {"first_name": "X"}, format="json")
        self.assertEqual(j.status_code, 403)
