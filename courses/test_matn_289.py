"""Matn-TZ 289: Tests bo'limiga testni PDF fayl ko'rinishida yuklash.
Javoblar PDF'ning oxirgi sahifasida — u mashq emas, javob kaliti."""

import io
import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from courses.models import KursTugun, KursZipJarayoni
from courses.test_asos import KursApiAsos

TMP_MEDIA = tempfile.mkdtemp()


def _pdf(sahifa_soni):
    rasmlar = [Image.new("RGB", (200, 280), "white") for _ in range(sahifa_soni)]
    bufer = io.BytesIO()
    rasmlar[0].save(bufer, format="PDF", save_all=True, append_images=rasmlar[1:])
    return bufer.getvalue()


def _mashq(raqam):
    return {
        "raqam": raqam, "sarlavha": f"SINOV {raqam}", "bloklar": [{"tur": "mashq"}],
        "savollar": [
            {"savol": "I ___ a student", "togri": "", "mashq_raqami": raqam, "band_raqami": "1"},
            {"savol": "She ___ ok", "togri": "", "mashq_raqami": raqam, "band_raqami": "2"},
        ],
    }


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class TestPdfYuklashTest(KursApiAsos):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.tests = KursTugun.objects.create(markaz=self.markaz, nomi="SINOV Tests", kalit="tests")

    def yukla(self, pdf_bytes):
        fayl = SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")
        return self.mijoz(self.admin).post(
            f"/api/kurslar/{self.tests.id}/blok-zip/", {"zip_fayl": fayl}, format="multipart"
        )

    def test_pdf_sahifalarga_ajraladi_oxirgisi_javob_kaliti(self):
        j = self.yukla(_pdf(3))
        self.assertEqual(j.status_code, 201, j.data)
        self.assertEqual(j.data["jami_sahifa"], 3)
        jarayon = KursZipJarayoni.objects.get(pk=j.data["jarayon_id"])
        self.assertEqual(jarayon.natijalar["javob_kaliti_indekslari"], [2])

    def test_javoblar_oxirgi_sahifadan_savollarga_yoziladi(self):
        jid = self.yukla(_pdf(3)).data["jarayon_id"]
        kalit = ({"turi": "javob_kaliti", "javoblar": [
            {"mashq_raqami": "1", "band_raqami": "1", "javob": "am"},
            {"mashq_raqami": "1", "band_raqami": "2", "javob": "is"},
            {"mashq_raqami": "2", "band_raqami": "2", "javob": "are"},
        ]}, None)
        mashqlar = iter([([_mashq("1")], [], []), ([_mashq("2")], [], [])])
        with mock.patch(
            "courses.blok_views._rasmni_mashqqa_aylantir", side_effect=lambda _b: next(mashqlar)
        ), mock.patch(
            "courses.blok_views.javob_kaliti_sahifasini_tahlil_qil", return_value=kalit
        ) as kalit_ai, mock.patch("courses.blok_views.blok_provider_olish"):
            for _ in range(3):
                j = self.mijoz(self.admin).post(f"/api/kurslar/blok-jarayon/{jid}/sahifa/")
                self.assertEqual(j.status_code, 200, j.data)
        self.assertTrue(j.data["tugadimi"])
        self.assertEqual(kalit_ai.call_count, 1)

        tasdiq = self.mijoz(self.admin).get(f"/api/kurslar/blok-jarayon/{jid}/tasdiq/").data
        s = tasdiq["sahifalar"]
        self.assertEqual([x["togri"] for x in s[0]["mashqlar"][0]["savollar"]], ["am", "is"])
        self.assertEqual([x["togri"] for x in s[1]["mashqlar"][0]["savollar"]], ["", "are"])
        self.assertEqual(s[2]["mashqlar"], [])

    def test_tests_dan_boshqa_bolimda_oxirgi_sahifa_mashq(self):
        self.tests.kalit = "students_book"
        self.tests.save(update_fields=["kalit"])
        j = self.yukla(_pdf(3))
        self.assertEqual(j.status_code, 201, j.data)
        jarayon = KursZipJarayoni.objects.get(pk=j.data["jarayon_id"])
        self.assertEqual(jarayon.natijalar["javob_kaliti_indekslari"], [])

    def test_buzuq_pdf_rad_etiladi(self):
        j = self.yukla(b"%PDF-buzuq")
        self.assertEqual(j.status_code, 400)
