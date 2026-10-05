"""Reyting: daraja bo'yicha, IELTS va Kurslar alohida, R/L testlari, oylik/hamma vaqt (2026-10-05)."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from academics.models import Guruh
from accounts.models import Markaz, User
from courses.models import KursMashq, KursMashqYechim, KursTugun
from exercises.models import ImtihonTest, TestYechim
from gamification.models import XPYozuv, jami_xp, xp_ber
from gamification.views import oy_boshi


class ReytingAsos(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(nomi="M") if hasattr(Markaz, "nomi") else Markaz.objects.create()
        fan = KursTugun.objects.create(markaz=self.markaz, nomi="Ingliz tili", kalit="ingliz", tartib=1)
        self.beginner = KursTugun.objects.create(parent=fan, markaz=self.markaz, nomi="Beginner", kalit="beginner", tartib=1)
        self.ielts = KursTugun.objects.create(parent=fan, markaz=self.markaz, nomi="IELTS", kalit="ielts", tartib=2)
        self.g_beg = Guruh.objects.create(name="Beg guruh", markaz=self.markaz, daraja=self.beginner)
        self.g_ielts = Guruh.objects.create(name="IELTS guruh", markaz=self.markaz, daraja=self.ielts)
        self.ali = self.talaba("ali", self.g_beg)
        self.vali = self.talaba("vali", self.g_beg)
        self.sami = self.talaba("sami", self.g_ielts)
        self.mashq = KursMashq.objects.create(tugun=KursTugun.objects.create(
            parent=self.beginner, markaz=self.markaz, nomi="Unit 1", kalit="u1", tartib=1))
        self.test_r = ImtihonTest.objects.create(name="Reading 1", bolim="reading", markaz=self.markaz)
        self.test_w = ImtihonTest.objects.create(name="Writing 1", bolim="writing", markaz=self.markaz)

    def talaba(self, username, guruh):
        u = User.objects.create_user(username=username, password="x", role=User.Role.STUDENT, first_name=username.title())
        guruh.talabalar.add(u)
        return u

    def reyting(self, user, **q):
        c = APIClient()
        c.force_authenticate(user)
        return c.get("/api/leaderboard/", q)

    def kurs_yechim(self, talaba, ball, jami=10):
        return KursMashqYechim.objects.create(talaba=talaba, mashq=self.mashq, javoblar={}, ball=ball, jami=jami, natijalar={})

    def imtihon_yechim(self, talaba, band, test=None):
        return TestYechim.objects.create(talaba=talaba, test=test or self.test_r, javoblar={}, ball=30, jami=40,
                                         natijalar={}, band=band)


class RLTestXPTest(ReytingAsos):
    def test_reading_test_xp_band_bilan(self):
        self.imtihon_yechim(self.ali, "6.5")
        y = XPYozuv.objects.get(talaba=self.ali, sabab="test_yechildi")
        self.assertEqual((y.miqdor, y.tur), (10 + 26, "ielts"))  # 10 + 6.5 x 4

    def test_qayta_yechish_xp_bermaydi(self):
        self.imtihon_yechim(self.ali, "6.0")
        self.imtihon_yechim(self.ali, "8.0")
        self.assertEqual(XPYozuv.objects.filter(talaba=self.ali, sabab="test_yechildi").count(), 1)
        self.assertEqual(jami_xp(self.ali), 34)  # faqat birinchi urinish

    def test_listening_ham_hisoblanadi_writing_testi_emas(self):
        self.imtihon_yechim(self.ali, "5.0", test=ImtihonTest.objects.create(name="L", bolim="listening", markaz=self.markaz))
        self.imtihon_yechim(self.vali, "9.0", test=self.test_w)  # Writing testi: o'z tekshiruvi orqali XP oladi
        self.assertEqual(jami_xp(self.ali), 30)
        self.assertEqual(jami_xp(self.vali), 0)

    def test_bandsiz_test_faqat_asos(self):
        self.imtihon_yechim(self.ali, None)
        self.assertEqual(jami_xp(self.ali), 10)


class KurslarXPTest(ReytingAsos):
    def test_birinchi_urinish_togri_javoblar_soni(self):
        self.kurs_yechim(self.ali, 7)
        y = XPYozuv.objects.get(talaba=self.ali, sabab="kurs_mashq")
        self.assertEqual((y.miqdor, y.tur), (7, "kurs"))
        self.assertFalse(XPYozuv.objects.filter(sabab="kurs_mukammal").exists())

    def test_mukammal_bonus(self):
        self.kurs_yechim(self.ali, 10, 10)
        self.assertEqual(jami_xp(self.ali), 15)  # 10 + 5 bonus
        self.assertEqual(XPYozuv.objects.get(sabab="kurs_mukammal").tur, "kurs")

    def test_keyingi_urinishlar_xp_bermaydi(self):
        self.kurs_yechim(self.ali, 4)
        self.kurs_yechim(self.ali, 10, 10)  # ikkinchi urinishda 100% — baribir XP yo'q
        self.assertEqual(jami_xp(self.ali), 4)

    def test_nol_ball_birinchi_urinish_keyingisini_bloklaydi(self):
        self.kurs_yechim(self.ali, 0)
        self.kurs_yechim(self.ali, 9)
        self.assertEqual(jami_xp(self.ali), 0)  # "birinchi urinish" qoidasi izchil


class DarajaReytingiTest(ReytingAsos):
    def test_talaba_faqat_oz_darajasini_koradi(self):
        self.kurs_yechim(self.ali, 5)
        self.kurs_yechim(self.sami, 9)  # boshqa daraja
        d = self.reyting(self.ali, tur="kurs", davr="hammasi").data
        self.assertEqual([x["daraja"]["nomi"] for x in d["darajalar"]], ["Beginner"])
        ismlar = {r["username"] for r in d["darajalar"][0]["top"]}
        self.assertEqual(ismlar, {"ali", "vali"})  # sami (IELTS) ko'rinmaydi
        self.assertEqual(d["darajalar"][0]["mening_ornim"]["orin"], 1)

    def test_ikki_darajali_talaba_ikkalasini_koradi(self):
        self.g_ielts.talabalar.add(self.ali)
        d = self.reyting(self.ali, tur="kurs", davr="hammasi").data
        self.assertEqual([x["daraja"]["nomi"] for x in d["darajalar"]], ["Beginner", "IELTS"])

    def test_ikki_guruh_bir_darajada_xp_ikki_hisoblanmaydi(self):
        # bir darajadagi ikkinchi guruhga ham qo'shildi — join'dan qatorlar ko'payib ketmasin
        g2 = Guruh.objects.create(name="Beg 2", markaz=self.markaz, daraja=self.beginner)
        g2.talabalar.add(self.ali)
        self.kurs_yechim(self.ali, 6)
        top = self.reyting(self.ali, tur="kurs", davr="hammasi").data["darajalar"][0]["top"]
        self.assertEqual(next(r["xp"] for r in top if r["username"] == "ali"), 6)
        self.assertEqual(len([r for r in top if r["username"] == "ali"]), 1)

    def test_arxiv_guruh_darajani_bermaydi(self):
        Guruh.objects.filter(pk=self.g_beg.pk).update(faol=False)
        d = self.reyting(self.ali).data
        self.assertEqual(len(d["darajalar"]), 1)
        self.assertIsNone(d["darajalar"][0]["daraja"])  # "Darajasiz"

    def test_darajasiz_talaba(self):
        yolg = User.objects.create_user(username="yolgiz", password="x", role=User.Role.STUDENT)
        d = self.reyting(yolg).data
        self.assertEqual(len(d["darajalar"]), 1)
        self.assertIsNone(d["darajalar"][0]["daraja"])
        self.assertEqual({r["username"] for r in d["darajalar"][0]["top"]}, {"yolgiz"})

    def test_umumiy_reyting_yoq(self):
        self.assertNotIn("umumiy", self.reyting(self.ali).data)

    def test_admin_hamma_darajani_koradi(self):
        admin = User.objects.create_user(username="adm", password="x", role=User.Role.ADMIN)
        d = self.reyting(admin).data
        self.assertEqual([x["daraja"]["nomi"] for x in d["darajalar"]], ["Beginner", "IELTS"])
        self.assertEqual(d["guruhlar"], [])


class TurVaDavrTest(ReytingAsos):
    def test_ielts_va_kurs_alohida_davomat_ikkalasiga(self):
        xp_ber(self.ali, "mashq_yechildi", manba_id=1)  # ielts, 10
        self.kurs_yechim(self.ali, 3)  # kurs, 3
        xp_ber(self.ali, "davomat_keldi", manba_id=1)  # umumiy, 2
        ielts = self.reyting(self.ali, tur="ielts", davr="hammasi").data["darajalar"][0]["top"]
        kurs = self.reyting(self.ali, tur="kurs", davr="hammasi").data["darajalar"][0]["top"]
        self.assertEqual(next(r["xp"] for r in ielts if r["username"] == "ali"), 12)  # 10 + 2
        self.assertEqual(next(r["xp"] for r in kurs if r["username"] == "ali"), 5)  # 3 + 2

    def test_oylik_faqat_shu_oy(self):
        xp_ber(self.ali, "mashq_yechildi", manba_id=1)
        eski = xp_ber(self.ali, "mashq_yechildi", manba_id=2)
        XPYozuv.objects.filter(manba_id=2).update(created_at=oy_boshi() - timedelta(days=3))
        oy = self.reyting(self.ali, tur="ielts", davr="oy").data["darajalar"][0]["top"]
        hammasi = self.reyting(self.ali, tur="ielts", davr="hammasi").data["darajalar"][0]["top"]
        self.assertEqual(next(r["xp"] for r in oy if r["username"] == "ali"), 10)
        self.assertEqual(next(r["xp"] for r in hammasi if r["username"] == "ali"), 20)
        self.assertTrue(eski)

    def test_standart_oylik_ielts(self):
        d = self.reyting(self.ali).data
        self.assertEqual((d["tur"], d["davr"]), ("ielts", "oy"))

    def test_notogri_parametr_400(self):
        self.assertEqual(self.reyting(self.ali, tur="boshqa").status_code, 400)
        self.assertEqual(self.reyting(self.ali, davr="yil").status_code, 400)

    def test_xpsiz_talaba_oxirida_postgres_null_tartibi(self):
        xp_ber(self.vali, "mashq_yechildi", manba_id=1)
        top = self.reyting(self.ali, davr="hammasi").data["darajalar"][0]["top"]
        self.assertEqual([r["username"] for r in top], ["vali", "ali"])  # 0 XP'li oxirida


class OrqagaHisoblashTest(ReytingAsos):
    def hisobla(self, *a):
        out = StringIO()
        call_command("xp_orqaga_hisobla", *a, stdout=out)
        return out.getvalue()

    def eski_natijalar(self):
        """Signal ishlamasdan oldingi holatni taqlid: yozuvlar bor, XP yo'q."""
        self.imtihon_yechim(self.ali, "7.0")
        self.kurs_yechim(self.ali, 10, 10)
        self.kurs_yechim(self.ali, 2)  # ikkinchi urinish — hisoblanmaydi
        XPYozuv.objects.all().delete()

    def test_quruq_rejim_yozmaydi(self):
        self.eski_natijalar()
        self.assertIn("3 ta XP", self.hisobla("--quruq"))  # test + kurs_mashq + kurs_mukammal
        self.assertEqual(XPYozuv.objects.count(), 0)

    def test_hisoblaydi_va_takror_ikki_marta_bermaydi(self):
        self.eski_natijalar()
        self.hisobla()
        self.assertEqual(jami_xp(self.ali), (10 + 28) + 10 + 5)
        self.hisobla()  # qayta ishga tushirish
        self.assertEqual(jami_xp(self.ali), (10 + 28) + 10 + 5)

    def test_asl_sana_saqlanadi(self):
        self.eski_natijalar()
        eski_sana = timezone.now() - timedelta(days=60)
        TestYechim.objects.update(created_at=eski_sana)
        self.hisobla()
        y = XPYozuv.objects.get(sabab="test_yechildi")
        self.assertEqual(y.created_at.date(), eski_sana.date())
        oy = self.reyting(self.ali, tur="ielts", davr="oy").data["darajalar"][0]["top"]
        self.assertEqual(next(r["xp"] for r in oy if r["username"] == "ali"), 0)  # 60 kun oldingi — shu oyda emas

    def test_writing_testi_hisoblanmaydi(self):
        self.imtihon_yechim(self.ali, "8.0", test=self.test_w)
        XPYozuv.objects.all().delete()
        self.hisobla()
        self.assertEqual(jami_xp(self.ali), 0)
