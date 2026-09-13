"""Kurslar tarixi testlari (2026-09-14, Shuhrat: "o'tilgan testlarning
tarixini matn ko'rinishida saqlash ... papka ko'rinishida").

Asosiy e'tibor RUXSATda: tarixda talabaning javoblari bor, ya'ni uni
faqat `natijalarni_korish_ruxsati` ruxsat bergan odam ko'rishi kerak
(o'zi, o'z guruhidagi o'qituvchi, o'z farzandi uchun ota-ona,
admin/owner). Shuhrat aynan shu uchtasini so'ragan edi.
"""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from academics.models import Guruh
from accounts.models import Markaz, User

from .models import KursMashq, KursMashqYechim, KursTugun

PAROL = "Sinov!Parol2026"


def _kirish(username, qurilma):
    c = APIClient()
    javob = c.post(
        "/api/token/",
        {"username": username, "password": PAROL, "qurilma_id": qurilma},
        format="json",
    )
    assert javob.status_code == 200, javob.data
    c.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"])
    return c


class KursTarixTest(TestCase):
    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")

        def foydalanuvchi(username, rol, **qoshimcha):
            return User.objects.create_user(
                username=username, password=PAROL, role=rol,
                markaz=self.markaz, **qoshimcha,
            )

        self.talaba = foydalanuvchi("talaba", User.Role.STUDENT)
        self.ozga = foydalanuvchi("ozga", User.Role.STUDENT)
        self.oqituvchi = foydalanuvchi("oqituvchi", User.Role.TEACHER)
        self.ozga_oqituvchi = foydalanuvchi("oqituvchi2", User.Role.TEACHER)
        self.ota_ona = foydalanuvchi("otaona", User.Role.PARENT)
        self.talaba.ota_ona = self.ota_ona
        self.talaba.save(update_fields=["ota_ona"])

        guruh = Guruh.objects.create(
            name="G1", markaz=self.markaz, oqituvchi=self.oqituvchi
        )
        guruh.talabalar.add(self.talaba)

        # Daraxt: Kurslar > Ingliz tili > Beginner > Unit 1 > SB
        def tugun(nomi, parent=None):
            return KursTugun.objects.create(nomi=nomi, parent=parent, markaz=self.markaz)

        ildiz = tugun("Kurslar")
        fan = tugun("Ingliz tili", ildiz)
        self.daraja = tugun("Beginner", fan)
        unit = tugun("Unit 1 — Hello!", self.daraja)
        bolim = tugun("Student's Book", unit)

        self.mashq = KursMashq.objects.create(
            tugun=bolim,
            tartib=3,
            savollar=[
                {"savol": "Nechta?", "togri": "besh"},
                {"savol": "Qachon?", "togri": "ertaga"},
            ],
        )
        self.yechim = KursMashqYechim.objects.create(
            talaba=self.talaba,
            mashq=self.mashq,
            javoblar=["besh", "kecha"],
            ball=1,
            jami=2,
            natijalar=[True, False],
        )

    # ── Ro'yxat ────────────────────────────────────────────────────

    def test_talaba_oz_tarixini_koradi(self):
        javob = _kirish("talaba", "q1").get("/api/kurslar/tarix/")
        self.assertEqual(javob.status_code, 200)
        darajalar = javob.data["darajalar"]
        self.assertEqual(len(darajalar), 1)
        self.assertEqual(darajalar[0]["nomi"], "Beginner")
        yozuv = darajalar[0]["yechimlar"][0]
        self.assertEqual((yozuv["ball"], yozuv["jami"]), (1, 2))
        self.assertEqual(yozuv["yol"], "Unit 1 — Hello! > Student's Book")

    def test_oqituvchi_oz_guruhidagini_koradi(self):
        javob = _kirish("oqituvchi", "q2").get(
            f"/api/kurslar/tarix/?talaba={self.talaba.id}"
        )
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(len(javob.data["darajalar"]), 1)

    def test_ota_ona_farzandinikini_koradi(self):
        javob = _kirish("otaona", "q3").get(
            f"/api/kurslar/tarix/?talaba={self.talaba.id}"
        )
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(len(javob.data["darajalar"]), 1)

    def test_begona_oqituvchi_kora_olmaydi(self):
        javob = _kirish("oqituvchi2", "q4").get(
            f"/api/kurslar/tarix/?talaba={self.talaba.id}"
        )
        self.assertEqual(javob.status_code, 403)

    def test_boshqa_talaba_kora_olmaydi(self):
        javob = _kirish("ozga", "q5").get(
            f"/api/kurslar/tarix/?talaba={self.talaba.id}"
        )
        self.assertEqual(javob.status_code, 403)

    # ── Tafsilot ───────────────────────────────────────────────────

    def test_tafsilot_savol_javobni_qaytaradi(self):
        javob = _kirish("talaba", "q1").get(f"/api/kurslar/tarix/{self.yechim.id}/")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob.data["daraja"], "Beginner")
        savollar = javob.data["savollar"]
        self.assertEqual(len(savollar), 2)
        self.assertEqual(
            savollar[0],
            {"raqam": 1, "savol": "Nechta?", "javob": "besh",
             "togri_javob": "besh", "togrimi": True},
        )
        self.assertEqual(savollar[1]["javob"], "kecha")
        self.assertEqual(savollar[1]["togri_javob"], "ertaga")
        self.assertFalse(savollar[1]["togrimi"])

    def test_tafsilot_begonaga_berilmaydi(self):
        javob = _kirish("ozga", "q5").get(f"/api/kurslar/tarix/{self.yechim.id}/")
        self.assertEqual(javob.status_code, 403)

    def test_mashq_tahrirlanib_savol_kamaysa_yiqilmaydi(self):
        """Yechim saqlangach mashq tahrirlangan bo'lishi mumkin —
        javoblar ro'yxati savollardan uzun qolib ketadi."""
        self.mashq.savollar = [{"savol": "Nechta?", "togri": "besh"}]
        self.mashq.save(update_fields=["savollar"])
        javob = _kirish("talaba", "q1").get(f"/api/kurslar/tarix/{self.yechim.id}/")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(len(javob.data["savollar"]), 2, "talaba javobi yo'qoldi")
        self.assertEqual(javob.data["savollar"][1]["savol"], "")
        self.assertEqual(javob.data["savollar"][1]["javob"], "kecha")

    def test_royxat_javobi_ro_yxat_sifatida_korsatiladi(self):
        """Ko'p javobli savolda javob massiv bo'lishi mumkin."""
        self.yechim.javoblar = [["a", "b"], "kecha"]
        self.yechim.save(update_fields=["javoblar"])
        javob = _kirish("talaba", "q1").get(f"/api/kurslar/tarix/{self.yechim.id}/")
        self.assertEqual(javob.data["savollar"][0]["javob"], "a, b")
