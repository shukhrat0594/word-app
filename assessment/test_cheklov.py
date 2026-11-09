"""AI endpointlari cheklovi (2026-11-09 tahlili): foydalanuvchi boshiga so'rov chegarasi va
audio hajmi. AI chaqirilmaydi — cheklov undan OLDIN ishlaydi."""

from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .cheklov import AUDIO_MAKS_HAJM, AiSorovCheklovi


class AiCheklovTest(TestCase):
    def setUp(self):
        cache.clear()
        Markaz.objects.create(name="Utmost")
        self.talaba = User.objects.create_user(username="talaba", password="x", role=User.Role.STUDENT)
        self.owner = User.objects.create_user(
            username="egasi", password="x", role=User.Role.ADMIN, is_superuser=True, is_staff=True
        )

    def mijoz(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_soatlik_chegaradan_keyin_429(self):
        c = self.mijoz(self.talaba)
        with mock.patch.object(AiSorovCheklovi, "THROTTLE_RATES", {"ai": "2/hour"}):
            # Bo'sh so'rov 400 qaytaradi (AI chaqirilmaydi), lekin urinish sanaladi.
            holatlar = [c.post("/api/grammar/coach/", {}, format="json").status_code for _ in range(3)]
            boshqa_endpoint = c.post("/api/writing/tekshirish/", {"matn": "x"}, format="json")
        self.assertEqual(holatlar, [400, 400, 429])
        self.assertEqual(boshqa_endpoint.status_code, 429)      # chegara barcha AI endpointlariga umumiy
        self.assertIn("AI so'rovlari", boshqa_endpoint.data["detail"])

    def test_chegara_har_foydalanuvchiga_alohida(self):
        boshqa = User.objects.create_user(username="talaba2", password="x", role=User.Role.STUDENT)
        with mock.patch.object(AiSorovCheklovi, "THROTTLE_RATES", {"ai": "1/hour"}):
            self.assertEqual(self.mijoz(self.talaba).post("/api/grammar/coach/", {}, format="json").status_code, 400)
            self.assertEqual(self.mijoz(self.talaba).post("/api/grammar/coach/", {}, format="json").status_code, 429)
            self.assertEqual(self.mijoz(boshqa).post("/api/grammar/coach/", {}, format="json").status_code, 400)

    def test_ownerga_cheklov_yoq(self):
        c = self.mijoz(self.owner)
        with mock.patch.object(AiSorovCheklovi, "THROTTLE_RATES", {"ai": "1/hour"}):
            holatlar = [c.post("/api/grammar/coach/", {}, format="json").status_code for _ in range(3)]
        self.assertEqual(holatlar, [400, 400, 400])

    def test_juda_katta_audio_rad_etiladi(self):
        c = self.mijoz(self.talaba)
        katta = b"0" * (AUDIO_MAKS_HAJM + 1)
        for yol in ("/api/speaking/transkripsiya/", "/api/speaking/audio/", "/api/speaking/trainer/"):
            audio = SimpleUploadedFile("a.webm", katta, content_type="audio/webm")
            javob = c.post(yol, {"audio": audio, "xabarlar": "[]"}, format="multipart")
            self.assertEqual(javob.status_code, 400, yol)
            self.assertIn("MB", javob.data["detail"], yol)
