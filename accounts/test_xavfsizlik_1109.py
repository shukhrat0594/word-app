"""2026-11-09 tahlilida topilgan xavfsizlik kamchiliklari — takrorlanmaslik testlari:
parol almashganda seanslar, admin panel logini, logo tekshiruvi, eski loginli profil."""

import io
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Markaz, User
from .seans_views import amaldagi_kalitlar

PAROL = "Sinov!Parol2026"
YANGI = "Boshqa!Parol2027"


class ParolSeansAsos(TestCase):
    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.owner = User.objects.create_user(
            username="egasi", password=PAROL, role=User.Role.ADMIN, is_superuser=True, is_staff=True,
        )

    def kirish(self):
        javob = APIClient().post("/api/token/", {"username": "egasi", "password": PAROL}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        return javob.data

    def yangilash(self, refresh):
        return APIClient().post("/api/token/refresh/", {"refresh": refresh}, format="json").status_code


class ParolOzgargandaSeansTest(ParolSeansAsos):
    def parolni_ozgartir(self, kalitlar, **qoshimcha):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer " + kalitlar["access"])
        return c.post("/api/profil/parol/", {"eski_parol": PAROL, "yangi_parol": YANGI, **qoshimcha}, format="json")

    def test_boshqa_qurilmadagi_seans_yopiladi_joriysi_qoladi(self):
        shu_yer, boshqa_joy = self.kirish(), self.kirish()
        javob = self.parolni_ozgartir(shu_yer, refresh=shu_yer["refresh"])
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(self.yangilash(boshqa_joy["refresh"]), 401)
        self.assertEqual(self.yangilash(shu_yer["refresh"]), 200)

    def test_kalit_yuborilmasa_hamma_seans_yopiladi(self):
        """Eski frontend `refresh` yubormaydi — xavfsiz tomonga: hammasi yopiladi."""
        shu_yer, boshqa_joy = self.kirish(), self.kirish()
        self.assertEqual(self.parolni_ozgartir(shu_yer).status_code, 200)
        self.assertEqual(self.yangilash(boshqa_joy["refresh"]), 401)
        self.assertEqual(self.yangilash(shu_yer["refresh"]), 401)

    def test_boshqa_odamning_kaliti_bilan_seans_saqlab_bolmaydi(self):
        begona = User.objects.create_user(username="begona", password=PAROL, role=User.Role.TEACHER)
        begona_kaliti = str(RefreshToken.for_user(begona))
        shu_yer, boshqa_joy = self.kirish(), self.kirish()
        self.parolni_ozgartir(shu_yer, refresh=begona_kaliti)
        self.assertEqual(self.yangilash(boshqa_joy["refresh"]), 401)
        self.assertEqual(self.yangilash(shu_yer["refresh"]), 401)

    def test_owner_parolni_tiklasa_foydalanuvchi_seanslari_yopiladi(self):
        oqituvchi = User.objects.create_user(username="ustoz", password=PAROL, role=User.Role.TEACHER)
        RefreshToken.for_user(oqituvchi)
        RefreshToken.for_user(oqituvchi)
        self.assertEqual(amaldagi_kalitlar(oqituvchi.pk).count(), 2)
        c = APIClient()
        c.force_authenticate(self.owner)
        javob = c.post(f"/api/foydalanuvchilar/{oqituvchi.pk}/parol/", {"parol": YANGI}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(amaldagi_kalitlar(oqituvchi.pk).count(), 0)


# Admin sahifasi shabloni statik fayllar manifestini so'raydi — testda `collectstatic`
# yurgizilmaydi, shuning uchun oddiy (manifestsiz) saqlagich qo'yiladi.
_ODDIY_STATIK = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_ODDIY_STATIK)
class AdminLoginCheklovTest(ParolSeansAsos):
    def test_admin_panel_logini_cheklangan(self):
        c = Client()
        holatlar = [c.post("/admin/login/", {"username": "egasi", "password": "x"}).status_code for _ in range(12)]
        self.assertEqual(holatlar[:10], [200] * 10)   # noto'g'ri parol — forma qayta ko'rsatiladi
        self.assertEqual(holatlar[10:], [429, 429])

    def test_get_sorovlar_cheklanmaydi(self):
        c = Client()
        for _ in range(15):
            self.assertEqual(c.get("/admin/login/").status_code, 200)


def _png(olcham=(4, 4)):
    bufer = io.BytesIO()
    Image.new("RGB", olcham, "#FFD400").save(bufer, "PNG")
    return bufer.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="lms_test_logo_"))
class LogoTekshiruvTest(ParolSeansAsos):
    def setUp(self):
        super().setUp()
        self.c = APIClient()
        self.c.force_authenticate(self.owner)

    def yubor(self, **maydonlar):
        return self.c.patch("/api/markaz-sozlama/", maydonlar, format="multipart")

    def test_rasm_bolmagan_fayl_logo_bolmaydi(self):
        javob = self.yubor(logo=SimpleUploadedFile("logo.png", b"<html><script>alert(1)</script></html>",
                                                   content_type="image/png"))
        self.assertEqual(javob.status_code, 400)
        self.markaz.refresh_from_db()
        self.assertFalse(self.markaz.logo)

    def test_haqiqiy_rasm_qabul_qilinadi(self):
        javob = self.yubor(logo=SimpleUploadedFile("logo.png", _png(), content_type="image/png"))
        self.assertEqual(javob.status_code, 200, javob.data)
        self.markaz.refresh_from_db()
        self.assertTrue(self.markaz.logo)

    def test_brend_rangi_hex_bolishi_kerak(self):
        self.assertEqual(self.yubor(brend_rang="qizil; background:url(x)").status_code, 400)
        self.assertEqual(self.yubor(brend_rang="#1A2b3C").status_code, 200)


class EskiLoginProfilTest(TestCase):
    def test_logini_bosh_joyli_hisob_profilini_tahrirlay_oladi(self):
        """Joriy validatordan oldin yaratilgan loginlar (bo'sh joy bilan) prodda bor."""
        u = User.objects.create(username="eski login", role=User.Role.STUDENT, first_name="Eski")
        u.set_password(PAROL)
        u.save()
        c = APIClient()
        c.force_authenticate(u)
        javob = c.post("/api/profil/tahrirlash/", {"bio": "salom"}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        u.refresh_from_db()
        self.assertEqual(u.bio, "salom")
