"""Kurslar API testlari uchun umumiy asos: markaz, kurs darajasi, guruh va
har rol bo'yicha foydalanuvchi. So'rovlar HAQIQIY JWT bilan yuboriladi.

Faqat LMS modellari: `crm`ga bog'lanish taqiqlangan
(`crm.tests.IzolyatsiyaTest`) — CRM olib tashlansa ham bu testlar
ishlashi kerak.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from academics.models import Guruh
from accounts.models import Markaz, User
from accounts.tests import qurilmali_kalit
from courses.models import KursTugun


class KursApiAsos(TestCase):
    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost Academy")
        ildiz = KursTugun.objects.create(markaz=self.markaz, nomi="Ingliz tili")
        self.daraja = KursTugun.objects.create(markaz=self.markaz, nomi="IELTS", parent=ildiz)
        self.guruh = Guruh.objects.create(name="IELTS juft kun", markaz=self.markaz, daraja=self.daraja)

        self.talaba = User.objects.create_user(
            username="talaba1", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        self.admin = User.objects.create_user(
            username="kurs_admin", password="x", role=User.Role.ADMIN, markaz=self.markaz
        )
        self.owner = User.objects.create_user(
            username="kurs_owner", password="x", role=User.Role.ADMIN,
            markaz=self.markaz, is_superuser=True, is_staff=True,
        )
        self.oqituvchi = User.objects.create_user(
            username="kurs_oqituvchi", password="x", role=User.Role.TEACHER, markaz=self.markaz
        )

    def mijoz(self, user=None):
        client = APIClient()
        if user is not None:
            token = str(qurilmali_kalit(user).access_token)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client
