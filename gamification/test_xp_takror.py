"""XP'ni qayta-qayta yig'ib bo'lmasligi (2026-11-09 tahlili): bitta mashqni takror yechish,
AI xato bergan Writing/Speaking, davomatni tuzatish."""

from datetime import date

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from academics.models import Davomat, Guruh
from accounts.models import Markaz, User
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from exercises.models import Mashq

from .models import jami_xp


class XpTakrorTest(TestCase):
    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(username="talaba", password="x", role=User.Role.STUDENT)
        self.c = APIClient()
        self.c.force_authenticate(self.talaba)

    def mashq(self, nom="M"):
        return Mashq.objects.create(
            name=nom, bolim="reading", tur="multiple_choice", markaz=self.markaz, korinish="public",
            savollar=[{"savol": "q", "togri": "a"}],
        )

    def yech(self, mashq, javob="a"):
        return self.c.post(f"/api/mashqlar/{mashq.id}/yechish/", {"javoblar": [javob]}, format="json")

    def test_bitta_mashq_faqat_birinchi_urinishda_xp_beradi(self):
        mashq = self.mashq()
        for _ in range(5):
            self.assertEqual(self.yech(mashq).status_code, 200)
        self.assertEqual(jami_xp(self.talaba), 15)          # 10 + mukammal natija bonusi 5

    def test_xato_yechib_keyin_togri_yechish_bonusni_qaytadan_bermaydi(self):
        mashq = self.mashq()
        self.yech(mashq, "b")
        self.yech(mashq, "a")
        self.assertEqual(jami_xp(self.talaba), 10)

    def test_har_xil_mashqlar_alohida_xp_beradi(self):
        self.yech(self.mashq("1"))
        self.yech(self.mashq("2"))
        self.assertEqual(jami_xp(self.talaba), 30)

    @override_settings(GEMINI_API_KEY="", ANTHROPIC_API_KEY="")
    def test_ai_xato_bergan_writing_xp_bermaydi(self):
        matn = " ".join(["word"] * 25)
        for _ in range(3):
            javob = self.c.post("/api/writing/tekshirish/", {"matn": matn}, format="json")
            self.assertEqual(javob.status_code, 502)
        self.assertEqual(WritingTekshiruv.objects.filter(holat=WritingTekshiruv.Holat.XATO).count(), 3)
        self.assertEqual(jami_xp(self.talaba), 0)

    def test_writing_xp_tayyor_bolganda_va_bir_marta(self):
        t = WritingTekshiruv.objects.create(
            talaba=self.talaba, matn="x", holat=WritingTekshiruv.Holat.KUTILMOQDA
        )
        self.assertEqual(jami_xp(self.talaba), 0)
        t.holat = WritingTekshiruv.Holat.TAYYOR
        t.save()
        t.save()
        self.assertEqual(jami_xp(self.talaba), 20)

    def test_speaking_xp_tayyor_bolganda(self):
        t = SpeakingTekshiruv.objects.create(
            talaba=self.talaba, rejim=SpeakingTekshiruv.Rejim.TEZKOR, matn="",
            holat=SpeakingTekshiruv.Holat.KUTILMOQDA,
        )
        self.assertEqual(jami_xp(self.talaba), 0)
        t.holat = SpeakingTekshiruv.Holat.TAYYOR
        t.save()
        self.assertEqual(jami_xp(self.talaba), 20)

    def test_davomat_keldiga_tuzatilsa_xp_beriladi(self):
        guruh = Guruh.objects.create(name="G", markaz=self.markaz)
        d = Davomat.objects.create(guruh=guruh, talaba=self.talaba, sana=date(2026, 11, 9), holat="kelmadi")
        self.assertEqual(jami_xp(self.talaba), 0)
        d.holat = "keldi"
        d.save()
        d.save()
        self.assertEqual(jami_xp(self.talaba), 2)
