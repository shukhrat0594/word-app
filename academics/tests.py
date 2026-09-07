"""Davomat sanasi testlari (2026-09-07 auditi).

XATO EDI: sana `datetime.date.today()` bilan olinardi — u SERVER OS
sanasini beradi, `Davomat.sana` bo'yicha taqqoslash esa TIME_ZONE
(Asia/Tashkent) bo'yicha ketadi. Prod server UTC'da ishlaydi, ya'ni
har kuni 00:00-05:00 oralig'ida ikkalasi bir kunga farq qilardi.
"""

import datetime
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Markaz, User

from .models import Davomat, Guruh

PAROL = "Sinov!Parol2026"

# Toshkent bo'yicha 2020-01-02 soat 02:00 = UTC bo'yicha 2020-01-01 21:00.
# Aynan shu "tunги oyna" xatoni ko'rsatadi: TIME_ZONE bo'yicha sana
# 2-yanvar, UTC (va shu bilan birga server OS) bo'yicha esa 1-yanvar.
QOTIRILGAN_LAHZA = datetime.datetime(2020, 1, 1, 21, 0, tzinfo=datetime.timezone.utc)
KUTILGAN_SANA = "2020-01-02"


class DavomatSanasiTest(TestCase):
    def setUp(self):
        cache.clear()
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

        self.client_ = APIClient()
        javob = self.client_.post(
            "/api/token/",
            {"username": "oqituvchi", "password": PAROL, "qurilma_id": "q1"},
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.client_.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"])

    def test_sana_berilmasa_time_zone_boyicha_olinadi(self):
        """Sanasiz GET — TIME_ZONE (Toshkent) sanasi, server OS sanasi emas."""
        with mock.patch("django.utils.timezone.now", return_value=QOTIRILGAN_LAHZA):
            javob = self.client_.get(f"/api/davomat/?guruh={self.guruh.id}")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["sana"], KUTILGAN_SANA)

    def test_sanasiz_post_ham_time_zone_boyicha_yozadi(self):
        with mock.patch("django.utils.timezone.now", return_value=QOTIRILGAN_LAHZA):
            javob = self.client_.post(
                "/api/davomat/",
                {
                    "guruh": self.guruh.id,
                    "yozuvlar": [{"talaba": self.talaba.id, "holat": "keldi"}],
                },
                format="json",
            )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["saqlandi"], 1)

        yozuv = Davomat.objects.get()
        self.assertEqual(str(yozuv.sana), KUTILGAN_SANA)

    def test_berilgan_sana_ustun_turadi(self):
        """Frontend sanani doim o'zi yuboradi — u o'zgarmasligi kerak."""
        javob = self.client_.post(
            "/api/davomat/",
            {
                "guruh": self.guruh.id,
                "sana": "2026-03-15",
                "yozuvlar": [{"talaba": self.talaba.id, "holat": "kelmadi"}],
            },
            format="json",
        )
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(str(Davomat.objects.get().sana), "2026-03-15")

    def test_begona_guruhga_ruxsat_yoq(self):
        """Tuzatish ruxsat tekshiruvini birga olib ketmaganini tasdiqlaydi."""
        boshqa = Guruh.objects.create(name="B2", markaz=self.markaz)
        javob = self.client_.get(f"/api/davomat/?guruh={boshqa.id}")
        self.assertEqual(javob.status_code, 403)

    def test_guruhda_yoq_talaba_yozilmaydi(self):
        begona = User.objects.create_user(
            username="begona", password=PAROL, role=User.Role.STUDENT
        )
        javob = self.client_.post(
            "/api/davomat/",
            {
                "guruh": self.guruh.id,
                "sana": "2026-03-15",
                "yozuvlar": [{"talaba": begona.id, "holat": "keldi"}],
            },
            format="json",
        )
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob.data["saqlandi"], 0)
        self.assertEqual(Davomat.objects.count(), 0)

    def test_localdate_haqiqatan_os_sanasidan_farq_qiladi(self):
        """Testning o'zi mazmunli ekanini tasdiqlaydi: qotirilgan lahzada
        TIME_ZONE sanasi bilan OS sanasi HAQIQATAN boshqa-boshqa."""
        with mock.patch("django.utils.timezone.now", return_value=QOTIRILGAN_LAHZA):
            self.assertEqual(str(timezone.localdate()), KUTILGAN_SANA)
        self.assertNotEqual(str(datetime.date.today()), KUTILGAN_SANA)
