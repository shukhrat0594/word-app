"""Video-TZ 2026-10-16: Unit'ning "Tests" bo'limi talabaga faqat
o'qituvchi/admin "Testni boshlash"ni bosgandan keyin ko'rinadi, talaba
yechib bo'lgach yana yopiladi. 2026-10-17: test guruh bo'yicha ochiladi —
faqat tanlangan guruh talabalariga ko'rinadi."""

from academics.models import Guruh, GuruhAzoligi
from accounts.models import User
from courses.models import KursMashq, KursTugun
from crm.test_api import ApiAsos


def _idlar(tugun):
    yield tugun.get("id")
    for b in tugun.get("children", []):
        yield from _idlar(b)


class TestBoshlashTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.test = KursTugun.objects.create(
            markaz=self.markaz, nomi="SINOV Tests", kalit="tests", parent=self.daraja, tartib=99,
        )
        self.mashq = KursMashq.objects.create(
            tugun=self.test, savollar=[{"savol": "1", "variantlar": ["a", "b"], "togri": "a"}],
        )
        Guruh.objects.filter(pk=self.guruh.pk).update(oqituvchi=self.oqituvchi)
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.talaba)

    def daraxtda(self, user):
        j = self.mijoz(user).get("/api/kurslar/daraxt/")
        self.assertEqual(j.status_code, 200)
        return self.test.id in set(_idlar(j.data))

    def boshla(self, user, ochiq=True, guruh=None):
        return self.mijoz(user).post(
            f"/api/kurslar/{self.test.id}/test-boshlash/",
            {"ochiq": ochiq, "guruh": (guruh or self.guruh).id}, format="json",
        )

    def yubor(self):
        return self.mijoz(self.talaba).post(
            f"/api/kurslar/mashq/{self.mashq.id}/yechish/", {"javoblar": ["a"]}, format="json"
        )

    def test_boshlanmagan_test_talabaga_yopiq(self):
        self.assertFalse(self.daraxtda(self.talaba))
        self.assertTrue(self.daraxtda(self.oqituvchi))
        self.assertEqual(self.mijoz(self.talaba).get(f"/api/kurslar/{self.test.id}/mashqlar/").status_code, 403)
        self.assertEqual(self.yubor().status_code, 403)

    def test_boshlangach_ochiladi_yechgach_yopiladi(self):
        self.assertEqual(self.boshla(self.oqituvchi).status_code, 200)
        self.assertTrue(self.daraxtda(self.talaba))
        self.assertEqual(self.mijoz(self.talaba).get(f"/api/kurslar/{self.test.id}/mashqlar/").status_code, 200)
        self.assertEqual(self.yubor().status_code, 200)
        self.assertFalse(self.daraxtda(self.talaba))
        self.assertEqual(self.yubor().status_code, 403)

    def test_qayta_boshlash_yana_ochadi(self):
        self.boshla(self.admin)
        self.yubor()
        self.boshla(self.admin)
        self.assertTrue(self.daraxtda(self.talaba))

    def test_yopish(self):
        self.boshla(self.admin)
        self.assertEqual(self.boshla(self.admin, ochiq=False).data, {"guruh": self.guruh.id, "ochiq": False})
        self.assertFalse(self.daraxtda(self.talaba))

    def test_talaba_boshlay_olmaydi(self):
        self.assertEqual(self.boshla(self.talaba).status_code, 403)

    def test_boshqa_guruh_talabasiga_korinmaydi(self):
        begona = User.objects.create_user(
            username="begona_talaba", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        ikkinchi = Guruh.objects.create(name="SINOV boshqa guruh", markaz=self.markaz)
        GuruhAzoligi.objects.create(guruh=ikkinchi, talaba=begona)
        self.boshla(self.oqituvchi)
        self.assertTrue(self.daraxtda(self.talaba))
        self.assertFalse(self.daraxtda(begona))
        self.assertEqual(self.mijoz(begona).get(f"/api/kurslar/{self.test.id}/mashqlar/").status_code, 403)

    def test_oqituvchi_faqat_oz_guruhini_tanlaydi(self):
        ikkinchi = Guruh.objects.create(name="SINOV boshqa guruh", markaz=self.markaz)
        j = self.mijoz(self.oqituvchi).get(f"/api/kurslar/{self.test.id}/test-boshlash/")
        self.assertEqual([g["id"] for g in j.data], [self.guruh.id])
        self.assertEqual(self.boshla(self.oqituvchi, guruh=ikkinchi).status_code, 400)
        self.boshla(self.oqituvchi)
        j = self.mijoz(self.oqituvchi).get(f"/api/kurslar/{self.test.id}/test-boshlash/")
        self.assertTrue(j.data[0]["ochiq"])
        # Admin markazning barcha guruhlarini ko'radi.
        j = self.mijoz(self.admin).get(f"/api/kurslar/{self.test.id}/test-boshlash/")
        self.assertEqual({g["id"] for g in j.data}, {self.guruh.id, ikkinchi.id})

    def test_yopiq_test_keyingi_unitni_qulflamaydi(self):
        # Tests yopiq bo'lsa talaba uni yecha olmaydi — 60% qoidasi uni
        # kutib, keyingi Unit'ni abadiy qulflab qo'ymasligi kerak.
        unit1 = KursTugun.objects.create(
            markaz=self.markaz, nomi="Unit 1", parent=self.daraja, unit_darsi=True, tartib=0,
        )
        unit2 = KursTugun.objects.create(
            markaz=self.markaz, nomi="Unit 2", parent=self.daraja, unit_darsi=True, tartib=1,
        )
        sb = KursTugun.objects.create(markaz=self.markaz, nomi="SB", parent=unit1, tartib=0)
        oddiy = KursMashq.objects.create(
            tugun=sb, savollar=[{"savol": "1", "variantlar": ["a", "b"], "togri": "a"}],
        )
        self.test.parent = unit1
        self.test.save(update_fields=["parent"])
        self.mijoz(self.talaba).post(f"/api/kurslar/mashq/{oddiy.id}/yechish/", {"javoblar": ["a"]}, format="json")
        j = self.mijoz(self.talaba).get(f"/api/kurslar/{unit2.id}/mashqlar/")
        self.assertNotEqual(j.status_code, 403, j.data)
