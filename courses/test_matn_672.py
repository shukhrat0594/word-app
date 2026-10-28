"""Matn-TZ 672 (2026-10-28): Vocabulary tarjima mashqida ingliz so'zi
yonida so'z turkumi qavsda ko'rsatiladi ("award (n)") — talaba qaysi
turkumdagi tarjima so'ralayotganini bilsin. Ko'rsatish frontendda
(`Kurslar.jsx`), bu yerda esa API talabaga `turkum`ni berishi tekshiriladi."""

from courses.models import KursSoz
from courses.test_video_1008 import SozlarTekshirishAsos


class SozTurkumiKorinishiTest(SozlarTekshirishAsos):
    def test_talabaga_soz_turkumi_beriladi(self):
        KursSoz.objects.create(tugun=self.vocab, tartib=2, en="award", uz="mukofotlamoq", turkum="v")
        j = self.mijoz(self.talaba).get(f"/api/kurslar/{self.vocab.id}/sozlar/")
        self.assertEqual(j.status_code, 200, j.data)
        turkumlar = {s["en"]: s["turkum"] for s in j.data}
        self.assertEqual(turkumlar["award"], "v")
        # Turkumi yo'q so'zda bo'sh qator — frontend qavs chiqarmaydi.
        self.assertEqual(turkumlar["airport"], "")
