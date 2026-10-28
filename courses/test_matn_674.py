"""Matn-TZ 674 (2026-10-28): Vocabulary tarjima mashqida so'zning shu
turkumdagi BARCHA to'g'ri tarjimalari qabul qilinadi — award (v):
"taqdirlamoq", "mukofotlamoq", "mukofot bermoq", "e'tirof etmoq".
Qo'shimcha tarjimalar `KursSoz.sinonimlar`da, `soz_sinonimlari` buyrug'i
AI bilan to'ldiradi (sinovda AI soxta provider bilan almashtirilgan)."""

import json
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase

from courses.models import KursSoz
from courses.soz_tarjima import sinonimlar_qil
from courses.test_video_1008 import SozlarTekshirishAsos
from courses.views import soz_javobi_togrimi

AWARD_V = {"uz": ["taqdirlamoq", "mukofot bermoq", "e‘tirof etmoq"], "ru": ["наградить", "награждать"]}


class SinonimTekshiruvTest(SimpleTestCase):
    def test_sinonimlar_togri_hisoblanadi(self):
        for javob in ("mukofotlamoq", "taqdirlamoq", "Mukofot bermoq", "e'tirof etmoq", "награждать"):
            self.assertTrue(soz_javobi_togrimi(javob, "mukofotlamoq", "наградить", AWARD_V), javob)
        # Bir nechta variant vergul bilan — har biri shu tilning variantlaridan.
        self.assertTrue(soz_javobi_togrimi("taqdirlamoq, mukofotlamoq", "mukofotlamoq", "", AWARD_V))

    def test_boshqa_turkum_va_aralash_til_xato(self):
        self.assertFalse(soz_javobi_togrimi("mukofot", "mukofotlamoq", "наградить", AWARD_V))
        self.assertFalse(soz_javobi_togrimi("taqdirlamoq, награждать", "mukofotlamoq", "наградить", AWARD_V))

    def test_bosh_yoki_buzuq_sinonimlar_eski_xatti_harakat(self):
        for sin in (None, {}, {"uz": "taqdirlamoq"}, [], {"uz": [None, ""]}):
            self.assertTrue(soz_javobi_togrimi("mukofotlamoq", "mukofotlamoq", "", sin))
            self.assertFalse(soz_javobi_togrimi("taqdirlamoq", "mukofotlamoq", "", sin))


class SoxtaProvider:
    def __init__(self, javob_fn):
        self.javob_fn = javob_fn
        self.chaqiruvlar = []

    def generate_json(self, system, user, javob_sxemasi=None, max_tokens=None):
        bandlar = json.loads(user)
        self.chaqiruvlar.append(bandlar)
        return {"natija": {"sozlar": self.javob_fn(bandlar)}}


class SinonimlarQilTest(SimpleTestCase):
    def test_javob_tozalanadi_va_turkum_yuboriladi(self):
        sozlar = [KursSoz(id=10, en="award", uz="mukofotlamoq", turkum="v"), KursSoz(id=11, en="x", uz="y")]
        provider = SoxtaProvider(lambda b: [
            {"n": 1, "uz": [" taqdirlamoq ", "Taqdirlamoq", "", "a" * 200], "ru": ["наградить"]},
            {"n": 2, "uz": [], "ru": []},
            {"n": 99, "uz": ["ortiqcha"], "ru": []},
        ])
        natija = sinonimlar_qil(sozlar, provider=provider)
        self.assertEqual(natija, {10: {"uz": ["taqdirlamoq"], "ru": ["наградить"]}})
        self.assertEqual(provider.chaqiruvlar[0][0]["turkum"], "v")


class SozSinonimlariBuyruqTest(SozlarTekshirishAsos):
    def setUp(self):
        super().setUp()
        self.award = KursSoz.objects.create(tugun=self.vocab, tartib=2, en="award", uz="mukofotlamoq", turkum="v")
        # Boshqa markaz daraxtidagi xuddi shu so'z — AI'dan qayta so'ralmaydi.
        self.award2 = KursSoz.objects.create(tugun=self.vocab, tartib=3, en="award", uz="mukofotlamoq", turkum="v")
        self.soz2.sinonimlar = {"uz": ["otel"], "ru": []}
        self.soz2.save()

    def test_bosh_sinonimlar_toldiriladi_va_tekshiruvda_ishlaydi(self):
        def javob(bandlar):
            return [
                {"n": b["n"], "uz": AWARD_V["uz"] if b["en"] == "award" else [], "ru": []}
                for b in bandlar
            ]

        provider = SoxtaProvider(javob)
        with mock.patch("courses.soz_tarjima._provider_ol", return_value=provider):
            call_command("soz_sinonimlari", stdout=mock.MagicMock())

        # To'ldirilgan (hotel) so'ralmadi; award bir marta so'raldi.
        yuborilgan = [b["en"] for chaqiruv in provider.chaqiruvlar for b in chaqiruv]
        self.assertNotIn("hotel", yuborilgan)
        self.assertEqual(yuborilgan.count("award"), 1)
        for s in (self.award, self.award2):
            s.refresh_from_db()
            self.assertEqual(s.sinonimlar["uz"], AWARD_V["uz"])
        self.soz1.refresh_from_db()
        self.assertEqual(self.soz1.sinonimlar, {})  # AI hech narsa bermadi — bo'sh qoldi
        self.soz2.refresh_from_db()
        self.assertEqual(self.soz2.sinonimlar, {"uz": ["otel"], "ru": []})

        j = self.yubor(self.talaba, {
            str(self.award.id): "mukofot bermoq", str(self.award2.id): "taqdirlamoq",
            str(self.soz2.id): "otel", str(self.soz1.id): "aeroport",
        })
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual((j.data["ball"], j.data["jami"]), (4, 4))

    def test_api_talabaga_sinonimlarni_beradi(self):
        j = self.mijoz(self.talaba).get(f"/api/kurslar/{self.vocab.id}/sozlar/")
        self.assertEqual(j.status_code, 200, j.data)
        sin = {s["en"]: s["sinonimlar"] for s in j.data}
        self.assertEqual(sin["hotel"], {"uz": ["otel"], "ru": []})
        self.assertEqual(sin["airport"], {})
