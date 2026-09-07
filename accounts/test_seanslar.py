"""Seans yozuvlari testlari (2026-09-07 auditi).

XATO EDI: parol tekshiruvi `super().post()` ichida bo'ladi va SimpleJWT
o'sha zahoti refresh-kalitni yasab `OutstandingToken`ga yozadi. Qurilma
cheklovi va "kirish cheklangan" bayrog'i esa undan KEYIN tekshirilardi —
ya'ni RAD ETILGAN login ham bazada "ochiq seans" bo'lib qolardi va
"Aktiv foydalanuvchilar" panelida raqamni buzardi.
"""

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .models import Markaz, User
from .seans_views import amaldagi_kalitlar

PAROL = "Sinov!Parol2026"


class ArvohSeansTest(TestCase):
    """Rad etilgan login "ochiq seans" qoldirmasligi kerak."""

    def setUp(self):
        cache.clear()
        self.markaz = Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(
            username="talaba",
            password=PAROL,
            role=User.Role.STUDENT,
            markaz=self.markaz,
            qurilma_limiti=1,
        )

    def _login(self, qurilma):
        return APIClient().post(
            "/api/token/",
            {"username": "talaba", "password": PAROL, "qurilma_id": qurilma},
            format="json",
        )

    def test_qurilma_limitidan_oshgan_login_seans_qoldirmaydi(self):
        self.assertEqual(self._login("qurilma-1").status_code, 200)
        self.assertEqual(amaldagi_kalitlar(self.talaba.pk).count(), 1)

        for qurilma in ("qurilma-2", "qurilma-3", "qurilma-4"):
            javob = self._login(qurilma)
            self.assertEqual(javob.status_code, 403, javob.data)
            self.assertEqual(javob.data["kod"], "qurilma_mos_emas")
            # Kalit mijozga UMUMAN yuborilmasligi kerak.
            self.assertNotIn("access", javob.data)
            self.assertNotIn("refresh", javob.data)

        self.assertEqual(
            amaldagi_kalitlar(self.talaba.pk).count(),
            1,
            "rad etilgan urinishlar arvoh seans qoldirdi",
        )
        self.assertEqual(OutstandingToken.objects.filter(user=self.talaba).count(), 1)

    def test_kirish_cheklanganda_ham_seans_qoldirmaydi(self):
        self.markaz.kirish_cheklangan = True
        self.markaz.save(update_fields=["kirish_cheklangan"])

        javob = self._login("qurilma-1")
        self.assertEqual(javob.status_code, 403, javob.data)
        self.assertEqual(javob.data["kod"], "kirish_cheklangan")
        self.assertEqual(amaldagi_kalitlar(self.talaba.pk).count(), 0)
        self.assertEqual(OutstandingToken.objects.filter(user=self.talaba).count(), 0)

    def test_muvaffaqiyatli_login_seans_yaratadi(self):
        """Tozalash haqiqiy seansni birga olib ketmasligi kerak."""
        javob = self._login("qurilma-1")
        self.assertEqual(javob.status_code, 200)
        self.assertIn("access", javob.data)
        self.assertIn("refresh", javob.data)
        self.assertEqual(amaldagi_kalitlar(self.talaba.pk).count(), 1)

        # Berilgan kalit HAQIQATAN ishlashi kerak (o'chirib yuborilmagan).
        yangilash = APIClient().post(
            "/api/token/refresh/", {"refresh": javob.data["refresh"]}, format="json"
        )
        self.assertEqual(yangilash.status_code, 200, yangilash.data)

    def test_owner_qurilma_cheklovidan_ozod(self):
        owner = User.objects.create_superuser(username="owner", password=PAROL)
        c = APIClient()
        for _ in range(3):
            javob = c.post(
                "/api/token/",
                {"username": "owner", "password": PAROL, "qurilma_id": "har-xil"},
                format="json",
            )
            self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(amaldagi_kalitlar(owner.pk).count(), 3)

    def test_aktiv_foydalanuvchilar_paneli_togri_raqam_koradi(self):
        """Panel aynan shu raqamni ko'rsatadi (Foydalanuvchilar.jsx)."""
        self._login("qurilma-1")
        for qurilma in ("qurilma-2", "qurilma-3", "qurilma-4"):
            self._login(qurilma)

        owner = User.objects.create_superuser(username="owner", password=PAROL)
        c = APIClient()
        j = c.post("/api/token/", {"username": "owner", "password": PAROL}, format="json")
        c.credentials(HTTP_AUTHORIZATION="Bearer " + j.data["access"])

        javob = c.get("/api/aktiv-foydalanuvchilar/")
        self.assertEqual(javob.status_code, 200)
        qator = next(q for q in javob.data if q["id"] == self.talaba.pk)
        self.assertEqual(qator["seans_soni"], 1, "panelda arvoh seanslar ko'rindi")
        _ = owner


class EskirganKalitlarTozalashTest(TestCase):
    """`prod_boshlangich` muddati o'tgan kalitlarni tozalaydi."""

    def setUp(self):
        cache.clear()
        self.talaba = User.objects.create_user(
            username="talaba", password=PAROL, role=User.Role.STUDENT
        )

    def test_muddati_otgan_kalit_ochadi_amaldagisi_qoladi(self):
        hozir = timezone.now()
        eski = OutstandingToken.objects.create(
            user=self.talaba,
            jti="eski-kalit",
            token="x",
            created_at=hozir - timezone.timedelta(days=10),
            expires_at=hozir - timezone.timedelta(days=3),
        )
        amaldagi = OutstandingToken.objects.create(
            user=self.talaba,
            jti="amaldagi-kalit",
            token="y",
            created_at=hozir,
            expires_at=hozir + timezone.timedelta(days=1),
        )

        call_command("flushexpiredtokens")

        self.assertFalse(OutstandingToken.objects.filter(pk=eski.pk).exists())
        self.assertTrue(OutstandingToken.objects.filter(pk=amaldagi.pk).exists())

    def test_qora_royxatdagi_eski_yozuv_ham_ochadi(self):
        hozir = timezone.now()
        eski = OutstandingToken.objects.create(
            user=self.talaba,
            jti="eski-bekor",
            token="z",
            created_at=hozir - timezone.timedelta(days=10),
            expires_at=hozir - timezone.timedelta(days=3),
        )
        BlacklistedToken.objects.create(token=eski)

        call_command("flushexpiredtokens")

        self.assertEqual(OutstandingToken.objects.count(), 0)
        self.assertEqual(BlacklistedToken.objects.count(), 0)
