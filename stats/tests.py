"""Talaba statistikasi: ko'nikmalar radari, dinamika grafiklari va davomat hisobi.

Davomat (video-TZ, IMG_6917.MOV): avval faqat keldi/kelmadi sanalardi — kechikdi va
sababli kelmagan holatlar alohida ko'rsatilmay, "keldi"/"kelmadi"ga qo'shilib ketardi.
"""

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from academics.models import Davomat, Guruh
from accounts.models import Markaz
from exercises.models import Bolim, ImtihonTest, Mashq, MashqYechim, TestYechim, Tur

from .services import talaba_statistikasi

User = get_user_model()
PAROL = "Sinov!Parol2026"


class KonikmalarRadarTest(TestCase):
    """Bosh sahifadagi 'Ko'nikmalar' radar diagrammasida hamma o'q (Writing,
    Speaking, Listening, Reading) IELTS band (0-9) shkalasida bo'lishi kerak
    — avval Listening/Reading foiz (0-100) bilan hisoblanardi, bu diagramma
    chekkasini (9 ball) noto'g'ri ko'rsatardi (video-TZ: IMG_2140.MOV)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="Test markaz")
        self.talaba = User.objects.create_user(
            username="talaba1", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )

    def _mashq(self, bolim):
        return Mashq.objects.create(
            name="Test mashq", bolim=bolim, tur=Tur.MULTIPLE_CHOICE, markaz=self.markaz,
        )

    def test_yuqori_natija_band_9(self):
        """39/40 to'g'ri (97.5%) — band jadvali bo'yicha 9.0, foiz emas."""
        mashq = self._mashq(Bolim.READING)
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=mashq, javoblar={}, ball=39, jami=40, natijalar=[],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["ortacha_band"], 9.0)
        self.assertEqual(stat["konikmalar"]["reading_band"], 9.0)
        self.assertNotIn("reading_foiz", stat["konikmalar"])
        # Foiz eski joyida (OtaOna sahifasi, CRM kunlik xabar) o'zgarmagan qoladi.
        self.assertEqual(stat["reading"]["ortacha_foiz"], 98)

    def test_past_natija_band_ham_past(self):
        """4/10 to'g'ri -> 40 savolga moslashtirilsa 16 ball -> band 5.0."""
        mashq = self._mashq(Bolim.LISTENING)
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=mashq, javoblar={}, ball=4, jami=10, natijalar=[],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["konikmalar"]["listening_band"], 5.0)

    def test_yechim_yoq_bolsa_band_none(self):
        stat = talaba_statistikasi(self.talaba)
        self.assertIsNone(stat["konikmalar"]["listening_band"])
        self.assertIsNone(stat["konikmalar"]["reading_band"])


class StatistikaDinamikaTest(TestCase):
    """B6: Reading/Listening uchun ham Writing/Speaking kabi har bir
    bajarilgan mashq natijasi bo'yicha chiziqli (dinamika) grafik
    ma'lumoti qaytishi kerak (video-TZ, 2026-10-06)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(
            username="talaba",
            password="Sinov!Parol2026",
            role=User.Role.STUDENT,
            markaz=self.markaz,
        )
        self.mashq = Mashq.objects.create(
            markaz=self.markaz,
            name="Reading 1",
            bolim=Bolim.READING,
            tur=Tur.TFNG,
            matn="Sinov matni",
            savollar=[{"savol": "S1", "togri": "TRUE", "tur": "tfng"}],
        )

    def test_reading_dinamika_har_mashq_boyicha_foiz(self):
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=self.mashq, javoblar=["TRUE"],
            ball=1, jami=1, natijalar=[True],
        )
        MashqYechim.objects.create(
            talaba=self.talaba, mashq=self.mashq, javoblar=["FALSE"],
            ball=0, jami=1, natijalar=[False],
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(len(stat["reading"]["mashq_dinamika"]), 2)
        self.assertEqual(stat["reading"]["mashq_dinamika"][0]["foiz"], 100)
        self.assertEqual(stat["reading"]["mashq_dinamika"][1]["foiz"], 0)
        self.assertEqual(stat["listening"]["mashq_dinamika"], [])


class ReadingListeningDinamikaTest(TestCase):
    """2026-10-06: Reading/Listening uchun ham Writing/Speaking kabi har
    urinish bo'yicha band dinamikasi (video-TZ: 4 ko'nikma uchun alohida
    grafik)."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="M")
        self.talaba = User.objects.create_user(
            username="ali", password="x", role=User.Role.STUDENT
        )
        self.test_r = ImtihonTest.objects.create(
            name="Cambridge 11 Test 1 Reading", bolim="reading", markaz=self.markaz
        )
        self.test_l = ImtihonTest.objects.create(
            name="Cambridge 11 Test 1 Listening", bolim="listening", markaz=self.markaz
        )

    def test_reading_dinamika_band_bilan(self):
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_r, javoblar={}, ball=30, jami=40,
            natijalar={}, band="7.0",
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["soni"], 1)
        self.assertEqual(stat["reading"]["oxirgi_band"], 7.0)
        self.assertEqual(stat["reading"]["dinamika"][0]["test_nomi"], "Cambridge 11 Test 1 Reading")

    def test_listening_dinamika_oxirgi_urinish(self):
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_l, javoblar={}, ball=20, jami=40,
            natijalar={}, band="5.0",
        )
        TestYechim.objects.create(
            talaba=self.talaba, test=self.test_l, javoblar={}, ball=35, jami=40,
            natijalar={}, band="8.0",
        )
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["listening"]["soni"], 2)
        self.assertEqual(stat["listening"]["oxirgi_band"], 8.0)

    def test_hech_narsa_yechilmagan_bolsa_bosh(self):
        stat = talaba_statistikasi(self.talaba)
        self.assertEqual(stat["reading"]["dinamika"], [])
        self.assertIsNone(stat["reading"]["oxirgi_band"])


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
