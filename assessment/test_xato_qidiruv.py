from unittest import mock

from django.test import SimpleTestCase

from assessment import xato_qidiruv as xq
from assessment.providers import GeminiProvider


def xato(x, t, daraja="xato", turi="agreement"):
    return {"xato": x, "tuzatish": t, "turi": turi, "daraja": daraja,
            "izoh": {"en": "e", "uz": "u", "ru": "r"}}


class SoxtaAI:
    """generate_json javoblarini navbat bilan qaytaradi; chaqiruvlarni yozib boradi."""

    def __init__(self, *javoblar):
        self.javoblar = list(javoblar)
        self.chaqiruvlar = []

    def generate_json(self, system, matn, javob_sxemasi=None, max_tokens=None, **k):
        self.chaqiruvlar.append((system, matn))
        r = self.javoblar.pop(0)
        if isinstance(r, Exception):
            raise r
        return {"natija": r, "input_tokens": 100, "output_tokens": 50}


class GaplarTest(SimpleTestCase):
    def test_gaplarga_bolish(self):
        g = xq.gaplarga_bol("First one. Second one! Third?\n\nFourth line without end")
        self.assertEqual(g, ["First one.", "Second one!", "Third?", "Fourth line without end"])

    def test_tinish_belgisiz_transkript_bolaklarga(self):
        matn = " ".join(["word"] * 95)
        g = xq.gaplarga_bol(matn, "speaking")
        self.assertEqual([len(x.split()) for x in g], [40, 40, 15])

    def test_bosh_matn(self):
        self.assertEqual(xq.gaplarga_bol("  "), [])


class DasturTekshiruviTest(SimpleTestCase):
    def topilgan(self, matn):
        return {(e["xato"], e["tuzatish"]) for e in xq.dastur_xatolari(matn)}

    def test_takror_soz(self):
        self.assertIn(("the the", "the"), self.topilgan("This is the the problem."))

    def test_takror_mustasno(self):
        self.assertEqual(self.topilgan("He said that that was fine and had had enough."), set())

    def test_a_an(self):
        self.assertIn(("a opportunity", "an opportunity"), self.topilgan("It is a opportunity."))
        self.assertIn(("an book", "a book"), self.topilgan("I read an book."))

    def test_a_an_mustasnolar_xato_emas(self):
        self.assertEqual(self.topilgan("He studies at a university for an hour in a European city, a one-way trip."), set())

    def test_kichik_i_faqat_writing(self):
        self.assertIn(("i", "I"), self.topilgan("Yesterday i went home."))
        self.assertEqual({(e["xato"]) for e in xq.dastur_xatolari("yesterday i went home", "speaking")}, set())

    def test_xatosiz_matn(self):
        self.assertEqual(self.topilgan("Technology plays an important role. I believe it helps us."), set())


class BirlashtirTest(SimpleTestCase):
    def test_takror_va_ichiga_olingan(self):
        a = [xato("play", "plays")]
        b = [xato("technology play", "technology plays"), xato("lifes", "lives")]
        r = xq.birlashtir(a, b)
        self.assertEqual([e["xato"] for e in r], ["play", "lifes"])  # "technology play" = "play" takrori

    def test_bir_xil_xato_ikki_gapda_alohida_qoladi(self):
        a = dict(xato("they is", "they are"), gap=1)
        b = dict(xato("they is", "they are"), gap=3)
        self.assertEqual(len(xq.birlashtir([a, b])), 2)

    def test_asosiy_baholash_faqat_bitta_takrorni_yutadi(self):
        asosiy = [xato("play", "plays")]  # gap raqami yo'q
        chuqur = [dict(xato("technology play", "technology plays"), gap=1),
                  dict(xato("people play", "people plays"), gap=4)]  # xuddi shu xato, boshqa gapda — haqiqiy
        r = xq.birlashtir(asosiy, chuqur)
        self.assertEqual(len(r), 2)

    def test_farqi_bir_xil_lekin_boshqacha_qirqilgan(self):
        r = xq.birlashtir([xato("technology play", "technology plays")], [dict(xato("play an", "plays an"), gap=1)])
        self.assertEqual(len(r), 1)

    def test_ma_nosiz_yozuv_tashlanadi(self):
        self.assertEqual(xq.birlashtir([xato("same", "same"), xato("a", "b")]), [xato("a", "b")])

    def test_notogri_element_tashlanadi(self):
        self.assertEqual(xq.birlashtir(["matn", None, xato("x1x", "y")]), [xato("x1x", "y")])


class ChuqurXatolarTest(SimpleTestCase):
    MATN = "He go home. She like tea. They is happy."

    def test_tushib_qolgan_gap_qayta_tekshiriladi(self):
        ai = SoxtaAI(
            {"gaplar": [{"n": 1, "xatolar": [xato("He go", "He goes")]},
                        {"n": 2, "xatolar": [xato("She like", "She likes")]}]},  # 3-gap yo'q!
            {"gaplar": [{"n": 3, "xatolar": [xato("They is", "They are")]}]},     # faqat 3-gap qayta so'raldi
            {"yangi": []},                                                         # auditor: yangi yo'q
        )
        r = xq.chuqur_xatolar(ai, self.MATN)
        self.assertEqual(r["gaplar_soni"], 3)
        self.assertEqual(r["tekshirilgan_gaplar"], 3)
        self.assertEqual(len(r["xatolar"]), 3)
        # qayta so'rovda FAQAT 3-gap yuborilgan
        qayta = ai.chaqiruvlar[1][1]
        self.assertIn("3. They is happy.", qayta)
        self.assertNotIn("1. He go home.", qayta)

    def test_auditor_yangi_topsa_yana_aylanadi_takrorni_hisoblamaydi(self):
        ai = SoxtaAI(
            {"gaplar": [{"n": 1, "xatolar": []}, {"n": 2, "xatolar": []}, {"n": 3, "xatolar": []}]},
            {"yangi": [dict(xato("He go", "He goes"), n=1), dict(xato("She like", "She likes"), n=2)]},
            {"yangi": [dict(xato("He go", "He goes"), n=1), dict(xato("They is", "They are"), n=3)]},  # biri takror
        )
        r = xq.chuqur_xatolar(ai, self.MATN)
        self.assertEqual([x["xato"] for x in r["xatolar"]], ["He go", "She like", "They is"])
        self.assertEqual(len(ai.chaqiruvlar), 3)  # pass1 + 2 auditor (AUDIT_AYLANISH = 2)

    def test_auditor_hech_narsa_topmasa_toxtaydi(self):
        ai = SoxtaAI(
            {"gaplar": [{"n": i, "xatolar": []} for i in (1, 2, 3)]},
            {"yangi": []},
        )
        r = xq.chuqur_xatolar(ai, self.MATN)
        self.assertEqual((len(r["xatolar"]), len(ai.chaqiruvlar)), (0, 2))

    def test_vaqt_byudjeti_tugasa_qoshimcha_chaqiruv_yoq(self):
        ai = SoxtaAI()
        with mock.patch.object(xq, "BYUDJET_SEK", 0):
            r = xq.chuqur_xatolar(ai, self.MATN)
        self.assertEqual((r["xatolar"], ai.chaqiruvlar), ([], []))

    def test_auditorga_mavjud_xatolar_beriladi(self):
        ai = SoxtaAI(
            {"gaplar": [{"n": 1, "xatolar": [xato("He go", "He goes")]}, {"n": 2, "xatolar": []}, {"n": 3, "xatolar": []}]},
            {"yangi": []},
        )
        xq.chuqur_xatolar(ai, self.MATN)
        self.assertIn("- [1] He go -> He goes", ai.chaqiruvlar[1][1])


class ChuqurlashtirTest(SimpleTestCase):
    MATN = "Technology play an important role. It is a opportunity. Style is fine."

    def javob(self):
        return {
            "natija": {"errors": [xato("technology play", "technology plays")], "overall_band": 6.5},
            "provider": "gemini", "model": "m", "input_tokens": 1000, "output_tokens": 500,
        }

    def ai(self):
        return SoxtaAI(
            {"gaplar": [
                {"n": 1, "xatolar": [xato("play an", "plays an"), xato("role", "a role", daraja="tavsiya", turi="word_choice")]},
                {"n": 2, "xatolar": []},
                {"n": 3, "xatolar": []},
            ]},
            {"yangi": []},
        )

    def test_birlashtirish_va_ajratish(self):
        r = xq.chuqurlashtir(self.ai(), self.javob(), self.MATN)
        n = r["natija"]
        xatolar = [e["xato"] for e in n["errors"]]
        self.assertIn("technology play", xatolar)       # asosiy baholashdan
        self.assertIn("a opportunity", xatolar)         # dastur tekshiruvidan
        self.assertEqual(len([x for x in xatolar if "play" in x]), 1)  # "play an" = takror
        self.assertEqual([e["xato"] for e in n["suggestions"]], ["role"])  # uslub — alohida
        self.assertEqual(n["overall_band"], 6.5)          # ball tegilmaydi
        self.assertTrue(n["tekshiruv"]["chuqur"])

    def test_xatolar_matndagi_tartibda(self):
        n = xq.chuqurlashtir(self.ai(), self.javob(), self.MATN)["natija"]
        orinlar = [self.MATN.lower().find(e["xato"].lower()) for e in n["errors"]]
        self.assertEqual(orinlar, sorted(orinlar))

    def test_tokenlar_qoshiladi(self):
        r = xq.chuqurlashtir(self.ai(), self.javob(), self.MATN)
        self.assertEqual((r["input_tokens"], r["output_tokens"]), (1000 + 200, 500 + 100))  # 2 qo'shimcha chaqiruv

    def test_xatoda_asosiy_natija_ozgarmaydi(self):
        javob = self.javob()
        asl = [dict(e) for e in javob["natija"]["errors"]]
        r = xq.chuqurlashtir(SoxtaAI(RuntimeError("Gemini 503")), javob, self.MATN)
        self.assertEqual(r["natija"]["errors"], asl)
        self.assertNotIn("suggestions", r["natija"])
        self.assertEqual(r["input_tokens"], 1000)


class ProviderUlanishiTest(SimpleTestCase):
    def provider(self, ai):
        p = GeminiProvider("kalit")
        p.tez_nusxa = lambda: ai
        return p

    def test_writing_chuqur_tekshiruv_ulanadi(self):
        ai = SoxtaAI({"gaplar": [{"n": 1, "xatolar": [xato("play", "plays")]}]}, {"yangi": []})
        p = self.provider(ai)
        with mock.patch.object(GeminiProvider, "_generate", return_value={
            "natija": {"errors": [], "overall_band": 6.0}, "provider": "gemini", "model": "m",
            "input_tokens": 1, "output_tokens": 1,
        }):
            r = p.writing_baholash("Technology play a role.", savol_matni="Q", tur="task2")
        self.assertEqual([e["xato"] for e in r["natija"]["errors"]], ["play"])
        self.assertIn("NUMBERED SENTENCES", ai.chaqiruvlar[0][1])

    def test_speaking_chuqur_tekshiruv_ulanadi(self):
        ai = SoxtaAI({"gaplar": [{"n": 1, "xatolar": [xato("I goed", "I went", turi="tense")]}]}, {"yangi": []})
        p = self.provider(ai)
        with mock.patch.object(GeminiProvider, "_generate", return_value={
            "natija": {"errors": []}, "provider": "gemini", "model": "m", "input_tokens": 1, "output_tokens": 1,
        }):
            r = p.speaking_matn_baholash("I goed to school yesterday", savol_matni="Q", tur="part1")
        self.assertEqual([e["xato"] for e in r["natija"]["errors"]], ["I goed"])
        self.assertIn("NUMBERED SEGMENTS", ai.chaqiruvlar[0][1])
