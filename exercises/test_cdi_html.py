"""CDI Listening HTML -> IELTS testi (2026-10-22). Sun'iy kichik HTML — kanal
shablonining barcha savol turlari: bo'sh joy (raqam belgisi bilan va belgisiz),
harfli quti, radio, "Choose TWO" checkbox."""

import io
import json
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Markaz, User
from exercises.cdi_html import HtmlXatosi, html_dan_test
from exercises.models import ImtihonTest, javoblarni_tekshir

HTML = """<html><body>
<div class="section">
  <h2>Part 1: Questions 1-4</h2>
  <p class="instructions">Complete the notes below. Write <b>ONE WORD</b> for each answer.</p>
  <h3>Library visit</h3>
  <div class="form-row"><label>Day: <span class="q-badge">1</span></label><input type="text" id="q1"></div>
  <div class="form-row"><label>Bring (because no <span class="q-badge">2</span>)</label><input type="text" id="q2"></div>
  <div class="form-row"><label>Stay for <span class="q-badge">3</span></label><input type="text" id="q3"> hours</div>
  <div class="options-box"><p><b>A</b> bag &nbsp; <b>B</b> book &nbsp; <b>C</b> card</p></div>
  <ul><li>&#8226; Take a <span class="q-badge">4</span> <input type="text" id="q4" maxlength="1"> home</li></ul>
</div>
<div class="section">
  <h2>PART 2 &#8212; Questions 5-8</h2>
  <p class="instructions"><strong>Questions 5-6</strong><br/>Choose the correct letter, <strong>A</strong> or <strong>B</strong>.</p>
  <div class="question"><strong>5.</strong> The library opens at<br/>
    <label><input type="radio" name="q5" value="A"> A. nine.</label><br/>
    <label><input type="radio" name="q5" value="B"> B. ten.</label>
  </div>
  <h3>Questions 6-7</h3>
  <p class="instructions">Choose <b>TWO</b> letters, A-C.</p>
  <p>Which TWO rooms are new?</p>
  <label><input type="checkbox" name="q6" value="A"> A Cafe</label><br>
  <label><input type="checkbox" name="q6" value="B"> B Studio</label><br>
  <label><input type="checkbox" name="q6" value="C"> C Hall</label>
  <p class="instructions"><strong>Questions 8-8</strong><br/>Write the correct letter, A-C.</p>
  <div style="border:1px solid"><p>A &#8211; Easy<br/>
     B &#8211; Hard<br/>
     C &#8211; Unknown</p></div>
  <div class="question"><p>8. Parking: <input type="text" id="q8" maxlength="1"></p></div>
</div>
<script>
function checkAllAnswers() {
  const correctAnswers = {
    q1: ["Monday"], q2: ["card", "cards"], q3: ["2", "two"], q4: ["a"],
    q5: ["b"], q6: ["c","a"], q8: ["c"]
  };
}
</script></body></html>"""


class CdiHtmlTest(SimpleTestCase):
    def setUp(self):
        self.test = html_dan_test(HTML)
        self.savollar = [s for q in self.test["qismlar"] for s in q["savollar"]]

    def test_tuzilish(self):
        self.assertEqual(self.test["name"], "CDI Listening — Library visit")
        self.assertEqual((self.test["bolim"], self.test["korinish"]), ("listening", "private"))
        self.assertEqual([q["sarlavha"] for q in self.test["qismlar"]], ["Part 1", "Part 2"])
        self.assertEqual(len(self.savollar), 8)

    def test_bosh_joy_belgi_turgan_yerda(self):
        self.assertEqual([s["savol"] for s in self.savollar[:3]],
                         ["Day: ___", "Bring (because no ___)", "Stay for ___ hours"])
        self.assertEqual(self.savollar[1]["togri"], ["card", "cards"])
        self.assertEqual(self.savollar[0]["guruh_korsatma"], "Complete the notes below. Write ONE WORD for each answer.")
        self.assertEqual(self.savollar[0]["guruh_boshi"], "Questions 1-4")
        # guruh sarlavhasi faqat birinchi savolda (frontend har savolda takrorlamasin)
        self.assertEqual((self.savollar[1]["guruh_boshi"], self.savollar[1]["guruh_korsatma"]), ("", ""))
        self.assertEqual(self.savollar[6]["guruh_boshi"], "")  # Choose TWO ning 2-savoli

    def test_harfli_quti(self):
        oqim, sarlavhali = self.savollar[3], self.savollar[7]
        self.assertEqual((oqim["tur"], oqim["savol"], oqim["togri"]), ("matching", "Take a ___ home", ["A"]))
        self.assertEqual(oqim["variantlar"], ["A bag", "B book", "C card"])
        self.assertEqual((sarlavhali["savol"], sarlavhali["togri"]), ("Parking", ["C"]))
        self.assertEqual(sarlavhali["variantlar"], ["A Easy", "B Hard", "C Unknown"])

    def test_radio_va_choose_two(self):
        radio, ikki_a, ikki_b = self.savollar[4:7]
        self.assertEqual((radio["savol"], radio["variantlar"], radio["togri"]),
                         ("The library opens at", ["nine.", "ten."], ["B"]))
        self.assertEqual(radio["guruh_korsatma"], "Choose the correct letter, A or B.")
        self.assertEqual(ikki_a["savol"], ikki_b["savol"])
        self.assertEqual((ikki_a["togri"], ikki_b["togri"]), (["C"], ["A"]))
        self.assertEqual(ikki_a["guruh_boshi"], "Questions 6-7")

    def test_sayt_baholashi_bilan_mos(self):
        # Choose TWO tartibsiz, ortiqcha harf ball bermaydi; matnli javob registrga sezgir emas.
        javoblar = ["monday", "Cards", "two", "A", "B", "A", "C", "C"]
        self.assertEqual(javoblarni_tekshir(self.savollar, javoblar)["ball"], 8)
        self.assertEqual(javoblarni_tekshir(self.savollar, ["", "", "", "", "", "A", "A", ""])["ball"], 1)

    def test_kaliti_yoq_html_rad_etiladi(self):
        with self.assertRaises(HtmlXatosi):
            html_dan_test(HTML.replace('q8: ["c"]', ""))
        with self.assertRaises(HtmlXatosi):
            html_dan_test("<html><body><p>bo'sh</p></body></html>")


class UmumiyAudioTest(TestCase):
    """2026-10-22: Listening ZIP'idagi bitta yozuv hamma qismga BITTA fayl
    bo'lib ulanadi (bir xil `audio_kalit`) — eksport/importdan keyin ham.
    Avval har qismga nusxa yozilardi va yozuv har qismda boshidan boshlanardi."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        sozlama = override_settings(
            MEDIA_ROOT=self.media,
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                      "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
        )
        sozlama.enable()
        self.addCleanup(sozlama.disable)
        Markaz.objects.create(name="Utmost")
        self.admin = APIClient()
        self.admin.force_authenticate(User.objects.create_user(username="adm", password="x", role=User.Role.ADMIN))

    def kalitlar(self, test):
        return {q.audio_fayl.name for q in test.qismlar.all()}

    def test_zip_va_eksport_import_bitta_fayl(self):
        bufer = io.BytesIO()
        with zipfile.ZipFile(bufer, "w") as zf:
            zf.writestr("test.json", json.dumps(html_dan_test(HTML)))
            zf.writestr("yozuv.mp3", b"ID3 sinov audio")
        j = self.admin.post("/api/imtihon/testlar-boshqaruv-zip/",
                            {"zip_fayl": SimpleUploadedFile("t.zip", bufer.getvalue())}, format="multipart")
        self.assertEqual(j.status_code, 201, getattr(j, "data", j))
        test = ImtihonTest.objects.get(name="CDI Listening — Library visit")
        self.assertEqual(test.qismlar.count(), 2)
        self.assertEqual(len(self.kalitlar(test)), 1)

        eksport = self.admin.get(f"/api/imtihon/testlar-boshqaruv/{test.pk}/eksport/")
        self.assertEqual(eksport.status_code, 200)
        zip_baytlar = b"".join(eksport.streaming_content)
        test.delete()
        j = self.admin.post("/api/imtihon/testlar-import/",
                            {"fayl": SimpleUploadedFile("e.zip", zip_baytlar)}, format="multipart")
        self.assertIn(j.status_code, (200, 201), getattr(j, "data", j))
        yangi = ImtihonTest.objects.get(name="CDI Listening — Library visit")
        self.assertEqual(len(self.kalitlar(yangi)), 1)
