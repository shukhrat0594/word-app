"""Xavfsizlik regressiya testlari (2026-09-07 auditi).

Bu yerdagi har bir test AYNI kod bazasida HAQIQATAN ishlagan xatoni
qamrab oladi — uchalasi ham audit paytida avval "muvaffaqiyatsiz"
bo'lib, xatoni ko'rsatib bergan, keyin tuzatilgan.

Har xato uchun IKKI xil test bor:
  * hujum yo'li yopilganini tekshiradigan test;
  * qonuniy ish avvalgidek ishlashini tekshiradigan test (tuzatish
    kerakli funksiyani birga o'chirib yubormasin).
"""

import os
import subprocess
import sys

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Markaz, User

PAROL = "Sinov!Parol2026"


class DrosselsizTest(TestCase):
    """Login uchun `ScopedRateThrottle` (10/daqiqa) qo'yilgan va u
    DRF'ning umumiy keshiga yozadi — testlar orasida saqlanib qolib,
    keyingi testlarni "throttled" bilan yiqitadi. Kesh har test
    boshida tozalanadi (drossel mantig'ining o'zi tegilmaydi)."""

    def setUp(self):
        cache.clear()


def _owner_yarat(username, parol=PAROL):
    """Haqiqiy owner qanday yaratilsa — shunday (`FoydalanuvchiYaratishView`:
    `is_superuser=True` VA `role="admin"`). `create_superuser` o'zi rolni
    tegmaydi, ya'ni model standarti "student" bo'lib qolardi — bu
    prodda uchramaydigan holat, test esa haqiqatga mos bo'lishi kerak."""
    owner = User.objects.create_superuser(username=username, password=parol)
    owner.role = User.Role.ADMIN
    owner.markaz = None
    owner.save(update_fields=["role", "markaz"])
    return owner


def _kirish(client, username, parol, qurilma="qurilma-sinov"):
    """Login qilib, kalitni klientga o'rnatadi. Kalitni qaytaradi."""
    javob = client.post(
        "/api/token/",
        {"username": username, "password": parol, "qurilma_id": qurilma},
        format="json",
    )
    assert javob.status_code == 200, javob.data
    client.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"])
    return javob.data


class KorishRejimiParolTest(DrosselsizTest):
    """Owner "Ko'rish rejimi"da parol o'zgartirsa, owner huquqi saqlanadi.

    XATO EDI: `ParolOzgartirishView` oddiy `save()` chaqirardi va
    `accounts/authentication.py` xotirada soxtalashtirgan
    `role`/`is_staff`/`is_superuser` bazaga yozilib qolardi — owner
    o'z huquqini butunlay yo'qotardi va uni ilova ichidan qaytarib
    bo'lmasdi.
    """

    def setUp(self):
        super().setUp()
        Markaz.objects.create(name="Utmost")
        self.owner = _owner_yarat("owner")

    def test_korish_rejimida_parol_ozgartirish_owner_huquqini_buzmaydi(self):
        self.owner.korish_rejimi = User.KorishRejimi.STUDENT
        self.owner.save(update_fields=["korish_rejimi"])

        c = APIClient()
        _kirish(c, "owner", PAROL)
        javob = c.post(
            "/api/profil/parol/",
            {"eski_parol": PAROL, "yangi_parol": "YangiParol!2026"},
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)

        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_superuser, "owner superuser'ligini yo'qotdi")
        self.assertTrue(self.owner.is_staff, "owner is_staff'ni yo'qotdi")
        self.assertEqual(self.owner.role, User.Role.ADMIN, "owner roli almashib ketdi")
        # Simulyatsiya tanlovining o'zi ham saqlanib qolishi kerak.
        self.assertEqual(self.owner.korish_rejimi, User.KorishRejimi.STUDENT)

    def test_parol_haqiqatan_yangilanadi(self):
        """Tuzatish asosiy vazifani (parol almashishi) buzmaganini tekshiradi."""
        c = APIClient()
        _kirish(c, "owner", PAROL)
        javob = c.post(
            "/api/profil/parol/",
            {"eski_parol": PAROL, "yangi_parol": "YangiParol!2026"},
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)

        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password("YangiParol!2026"))
        self.assertFalse(self.owner.check_password(PAROL))

    def test_notogri_eski_parol_rad_etiladi(self):
        c = APIClient()
        _kirish(c, "owner", PAROL)
        javob = c.post(
            "/api/profil/parol/",
            {"eski_parol": "butunlay-boshqa", "yangi_parol": "YangiParol!2026"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(PAROL))


class XodimYaratishEgallashTest(DrosselsizTest):
    """`/api/xodimlar/` orqali begona hisobni egallab bo'lmaydi.

    XATO EDI: `User.objects.get_or_create(username=...)` mavjud
    ISTALGAN hisobning parolini so'rovdagi qiymatga almashtirardi.
    Owner odatda `markaz_id=None` bo'lgani uchun "boshqa markazga
    tegishli" tekshiruvi uni to'smasdi — admin owner loginini kiritib,
    owner hisobiga kirib olardi.
    """

    def setUp(self):
        super().setUp()
        self.markaz = Markaz.objects.create(name="Utmost")
        # Owner ATAYLAB markazsiz — haqiqiy holat aynan shunday va
        # xato aynan shu tufayli ishlagan edi.
        self.owner = _owner_yarat("shukhrat")
        self.admin = User.objects.create_user(
            username="admin1", password=PAROL, role=User.Role.ADMIN, markaz=self.markaz
        )

    def _admin_klienti(self):
        c = APIClient()
        _kirish(c, "admin1", PAROL, qurilma="admin-qurilma")
        return c

    def test_admin_owner_hisobini_egallay_olmaydi(self):
        javob = self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "shukhrat", "parol": "MenBilaman!2026", "ism": "egallandi"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400, javob.data)

        self.owner.refresh_from_db()
        self.assertFalse(
            self.owner.check_password("MenBilaman!2026"), "owner paroli almashtirildi"
        )
        self.assertTrue(self.owner.check_password(PAROL), "owner paroli buzildi")
        self.assertTrue(self.owner.is_superuser)
        self.assertEqual(self.owner.role, User.Role.ADMIN)
        self.assertIsNone(self.owner.markaz_id)

    def test_admin_boshqa_adminni_egallay_olmaydi(self):
        boshqa = User.objects.create_user(
            username="admin2", password=PAROL, role=User.Role.ADMIN, markaz=self.markaz
        )
        javob = self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "admin2", "parol": "MenBilaman!2026", "ism": "x"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400, javob.data)
        boshqa.refresh_from_db()
        self.assertTrue(boshqa.check_password(PAROL))
        self.assertEqual(boshqa.role, User.Role.ADMIN)

    def test_admin_talaba_hisobini_egallay_olmaydi(self):
        talaba = User.objects.create_user(
            username="talaba1", password=PAROL, role=User.Role.STUDENT
        )
        javob = self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "talaba1", "parol": "MenBilaman!2026", "ism": "x"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400, javob.data)
        talaba.refresh_from_db()
        self.assertEqual(talaba.role, User.Role.STUDENT)
        self.assertTrue(talaba.check_password(PAROL))

    def test_yangi_oqituvchi_yaratish_ishlaydi(self):
        """Qonuniy ish — tuzatish buni to'sib qo'ymasligi kerak."""
        javob = self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "yangi_teacher", "parol": PAROL, "ism": "Yangi O'qituvchi"},
            format="json",
        )
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertTrue(javob.data["yaratildi"])

        yangi = User.objects.get(username="yangi_teacher")
        self.assertEqual(yangi.role, User.Role.TEACHER)
        self.assertEqual(yangi.markaz_id, self.markaz.id)
        self.assertEqual(yangi.first_name, "Yangi O'qituvchi")
        self.assertTrue(yangi.check_password(PAROL))

    def test_mavjud_oqituvchi_parolini_yangilash_ishlaydi(self):
        """Qonuniy ish — "parol tiklash" naqshi saqlanib qolgan."""
        oqituvchi = User.objects.create_user(
            username="teacher1", password=PAROL, role=User.Role.TEACHER, markaz=self.markaz
        )
        javob = self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "teacher1", "parol": "YangiParol!2026", "ism": "Yangi ism"},
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertFalse(javob.data["yaratildi"])

        oqituvchi.refresh_from_db()
        self.assertTrue(oqituvchi.check_password("YangiParol!2026"))
        self.assertEqual(oqituvchi.role, User.Role.TEACHER)

    def test_rad_etilgan_urinish_yangi_hisob_qoldirmaydi(self):
        """`get_or_create` rad etilgan holatda ham qator yaratib
        qo'ymasligi kerak edi — endi umuman yaratilmaydi."""
        oldingi = User.objects.count()
        self._admin_klienti().post(
            "/api/xodimlar/",
            {"username": "shukhrat", "parol": "MenBilaman!2026"},
            format="json",
        )
        self.assertEqual(User.objects.count(), oldingi)


class MarkazAdminTayinlashTest(DrosselsizTest):
    """`/api/markazlar/<id>/admin-tayinlash/` — owner hisobiga tegmaydi."""

    def setUp(self):
        super().setUp()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.birinchi = _owner_yarat("owner1")
        self.ikkinchi = _owner_yarat("owner2")

    def _owner_klienti(self):
        c = APIClient()
        _kirish(c, "owner2", PAROL, qurilma="owner2-qurilma")
        return c

    def test_owner_boshqa_ownerni_pastga_tushira_olmaydi(self):
        javob = self._owner_klienti().post(
            f"/api/markazlar/{self.markaz.id}/admin-tayinlash/",
            {"username": "owner1", "parol": "MenBilaman!2026", "ism": "x"},
            format="json",
        )
        self.assertEqual(javob.status_code, 400, javob.data)

        self.birinchi.refresh_from_db()
        self.assertTrue(self.birinchi.is_superuser)
        self.assertTrue(self.birinchi.check_password(PAROL))
        self.assertIsNone(self.birinchi.markaz_id)

    def test_yangi_admin_tayinlash_ishlaydi(self):
        """Qonuniy ish — tuzatish buni to'smaydi."""
        javob = self._owner_klienti().post(
            f"/api/markazlar/{self.markaz.id}/admin-tayinlash/",
            {"username": "yangi_admin", "parol": PAROL, "ism": "Yangi Admin"},
            format="json",
        )
        self.assertEqual(javob.status_code, 201, javob.data)

        yangi = User.objects.get(username="yangi_admin")
        self.assertEqual(yangi.role, User.Role.ADMIN)
        self.assertEqual(yangi.markaz_id, self.markaz.id)
        self.assertTrue(yangi.check_password(PAROL))


class SozlamalarXavfsizligiTest(DrosselsizTest):
    """`SECRET_KEY` va `DEBUG` standart qiymatlari xavfsiz tomonga qaraydi.

    XATO EDI: `DEBUG` standarti `True`, `SECRET_KEY` standarti esa
    git'da ochiq turgan haqiqiy kalit edi — `.env` o'qilmasa prod sayt
    jimgina debug rejimida va ommaga ma'lum kalit bilan ishlardi.

    Tekshiruv ALOHIDA jarayonda bajariladi: sozlamalar import paytida
    bir marta o'qiladi, ya'ni joriy jarayonda ularni qayta sinab
    bo'lmaydi. `.env` fayli mavjud bo'lsa ham muhit o'zgaruvchisi
    undan USTUN turadi (python-decouple qoidasi), shuning uchun
    sinov ishonchli.
    """

    def _sozlamalarni_yukla(self, **muhit):
        atrof = {**os.environ, **muhit}
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=str(settings.BASE_DIR),
            env={**atrof, "DJANGO_SETTINGS_MODULE": "config.settings"},
            capture_output=True,
            text=True,
        )

    def test_secret_key_yoq_bolsa_prod_kotarilmaydi(self):
        natija = self._sozlamalarni_yukla(DEBUG="False", SECRET_KEY="")
        self.assertNotEqual(natija.returncode, 0, "sayt kalitsiz ko'tarildi")
        self.assertIn("ImproperlyConfigured", natija.stderr)
        self.assertIn("SECRET_KEY", natija.stderr)

    def test_secret_key_berilgan_bolsa_prod_kotariladi(self):
        natija = self._sozlamalarni_yukla(
            DEBUG="False", SECRET_KEY="x" * 60, ALLOWED_HOSTS="example.com"
        )
        self.assertEqual(natija.returncode, 0, natija.stderr)

    def test_debug_standarti_ochiq(self):
        """`DEBUG` umuman berilmasa — o'chiq bo'lishi kerak.

        Bu MANBA darajasidagi tekshiruv, ishga tushirish emas: lokal
        ishlab chiqish `.env`ida `DEBUG=True` turadi va python-decouple
        uni har doim topadi (fayl qidiruvi `settings.py` joylashgan
        katalogdan boshlanadi, ishchi katalogdan emas) — ya'ni "muhitda
        DEBUG yo'q" holatini shu jarayondan ishonchli yasab bo'lmaydi.
        Xavf esa aynan standart qiymatda, shuning uchun standartning
        o'zi qulflanadi."""
        manba = (settings.BASE_DIR / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertIn(
            "DEBUG = config('DEBUG', default=False, cast=bool)",
            manba,
            "DEBUG standarti xavfsiz (False) bo'lishi kerak",
        )

    def test_gitdagi_eski_kalit_qoldirilmagan(self):
        """Sizib chiqqan kalit fayldan butunlay olib tashlanganini
        qulflaydi — u endi hech qanday holatda ishlatilmasligi kerak."""
        manba = (settings.BASE_DIR / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("8a3dv", manba, "sizib chiqqan SECRET_KEY hali kodda")
