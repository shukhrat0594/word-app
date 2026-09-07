"""Speaking audiosi testlari (2026-09-07 auditi).

XATO EDI: tarix endpointlari `t.audio_fayl.url` — xom `/media/` havolasi
qaytarardi. `config/urls.py` `/media/` dan faqat markaz logolarini beradi,
ya'ni havola 404 edi va talaba o'z ovozini qayta eshita olmasdi. R2
yoqilganda esa `.url` imzolangan OCHIQ havola berardi (B3.2 buziladi).
"""

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from rest_framework.test import APIClient

from academics.models import Guruh
from accounts.models import Markaz, User

from .models import SpeakingTekshiruv

PAROL = "Sinov!Parol2026"
AUDIO = b"RIFF----WEBMsinov"


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


class SpeakingAudioHavolasiTest(TestCase):
    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(
            username="talaba", password=PAROL, role=User.Role.STUDENT, markaz=self.markaz
        )
        self.tekshiruv = SpeakingTekshiruv.objects.create(
            talaba=self.talaba,
            rejim=SpeakingTekshiruv.Rejim.TEZKOR,
            matn="salom",
            holat=SpeakingTekshiruv.Holat.TAYYOR,
        )
        self.tekshiruv.audio_fayl.save("sinov.webm", ContentFile(AUDIO), save=True)
        self.yol = f"/api/speaking/tekshiruv/{self.tekshiruv.id}/audio/"

    def test_tarix_xom_media_havolasi_bermaydi(self):
        javob = _kirish("talaba", "q1").get("/api/speaking/tarix/")
        self.assertEqual(javob.status_code, 200)
        url = javob.data[0]["audio_url"]
        self.assertEqual(url, self.yol)
        self.assertFalse(url.startswith("/media/"), "xom /media/ havolasi qaytdi")

    def test_umumiy_tarix_ham_endpoint_beradi(self):
        javob = _kirish("talaba", "q1").get("/api/tarix/")
        self.assertEqual(javob.status_code, 200)
        yozuv = next(y for y in javob.data if y["turi"] == "speaking")
        self.assertEqual(yozuv["audio_url"], self.yol)

    def test_egasi_audioni_eshita_oladi(self):
        javob = _kirish("talaba", "q1").get(self.yol)
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(b"".join(javob.streaming_content), AUDIO)
        self.assertEqual(javob["Content-Disposition"], "inline")

    def test_autentifikatsiyasiz_berilmaydi(self):
        javob = APIClient().get(self.yol)
        self.assertEqual(javob.status_code, 401)

    def test_begona_talaba_eshita_olmaydi(self):
        User.objects.create_user(
            username="begona", password=PAROL, role=User.Role.STUDENT, markaz=self.markaz
        )
        javob = _kirish("begona", "q2").get(self.yol)
        self.assertEqual(javob.status_code, 404)

    def test_begona_oqituvchi_eshita_olmaydi(self):
        User.objects.create_user(
            username="oqituvchi", password=PAROL, role=User.Role.TEACHER, markaz=self.markaz
        )
        javob = _kirish("oqituvchi", "q3").get(self.yol)
        self.assertEqual(javob.status_code, 404)

    def test_oz_guruhidagi_oqituvchi_eshita_oladi(self):
        oqituvchi = User.objects.create_user(
            username="oqituvchi", password=PAROL, role=User.Role.TEACHER, markaz=self.markaz
        )
        guruh = Guruh.objects.create(
            name="A1", markaz=self.markaz, oqituvchi=oqituvchi
        )
        guruh.talabalar.add(self.talaba)
        javob = _kirish("oqituvchi", "q3").get(self.yol)
        self.assertEqual(javob.status_code, 200)

    def test_ota_ona_faqat_oz_farzandini(self):
        ota_ona = User.objects.create_user(
            username="ota", password=PAROL, role=User.Role.PARENT
        )
        begona_ota = User.objects.create_user(
            username="begona_ota", password=PAROL, role=User.Role.PARENT
        )
        self.talaba.ota_ona = ota_ona
        self.talaba.save(update_fields=["ota_ona"])

        self.assertEqual(_kirish("ota", "q4").get(self.yol).status_code, 200)
        self.assertEqual(_kirish("begona_ota", "q5").get(self.yol).status_code, 404)
        _ = begona_ota

    def test_owner_eshita_oladi(self):
        owner = User.objects.create_superuser(username="owner", password=PAROL)
        owner.role = User.Role.ADMIN
        owner.save(update_fields=["role"])
        self.assertEqual(_kirish("owner", "q6").get(self.yol).status_code, 200)

    def test_audiosiz_yozuv_havola_bermaydi(self):
        SpeakingTekshiruv.objects.create(
            talaba=self.talaba,
            rejim=SpeakingTekshiruv.Rejim.MATN,
            matn="audiosiz",
            holat=SpeakingTekshiruv.Holat.TAYYOR,
        )
        javob = _kirish("talaba", "q1").get("/api/speaking/tarix/")
        audiosiz = [y for y in javob.data if y["matn"] == "audiosiz"]
        self.assertEqual(len(audiosiz), 1)
        self.assertIsNone(audiosiz[0]["audio_url"])

    def test_admin_natijalar_royxatida_ham_endpoint(self):
        """`accounts.FoydalanuvchiNatijalariView` ham xuddi shu havolani beradi."""
        User.objects.create_user(
            username="admin1", password=PAROL, role=User.Role.ADMIN, markaz=self.markaz
        )
        javob = _kirish("admin1", "q7").get(
            f"/api/foydalanuvchilar/{self.talaba.id}/natijalar/"
        )
        self.assertEqual(javob.status_code, 200)
        yozuv = next(y for y in javob.data["natijalar"] if y["turi"] == "speaking")
        self.assertEqual(yozuv["audio_url"], self.yol)
