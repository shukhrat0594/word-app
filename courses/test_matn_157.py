"""Matn-TZ #153/#157 (2026-10-10): Elementary WB Unit 2 "-or / -er"
mashqida har qanday to'g'ri javob noto'g'ri deb ko'rsatilardi —
`courses/elementary_tuzatish.py` kalitlarni so'z o'zagidan qayta quradi."""

from courses.elementary_tuzatish import tuzat
from courses.models import KursMashq, KursTugun
from crm.test_api import ApiAsos

SOZLAR = ["wait", "act", "hairdress", "profess", "doct", "manag",
          "police offic", "interpret", "film direct"]


class OrErKalitlariTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.tugun = KursTugun.objects.create(
            markaz=self.markaz, nomi="SINOV Workbook", parent=self.daraja, tartib=0,
        )
        qatorlar = [{"bolaklar": [{"matn": "1 football "}, {"matn": "er", "namuna": True}]}]
        for i, soz in enumerate(SOZLAR):
            qatorlar.append({"bolaklar": [{"matn": f"{i + 2} {soz} "}, {"bosh_joy": True, "savol_idx": i}]})
        # Buzilgan kalit: bir qatorga siljigan (prodda kuzatilgan holatga o'xshash).
        savollar = [{"savol": f"{i + 2}", "togri": "or" if i % 2 else "-"} for i in range(len(SOZLAR))]
        self.mashq = KursMashq.objects.create(
            tugun=self.tugun,
            bloklar=[
                {"tur": "korsatma", "raqam": "2", "matn": "Complete the words with -or or -er."},
                {"tur": "mashq", "qatorlar": qatorlar},
            ],
            savollar=savollar,
        )

    def yubor(self, javoblar):
        return self.mijoz(self.talaba).post(
            f"/api/kurslar/mashq/{self.mashq.id}/yechish/", {"javoblar": javoblar}, format="json"
        )

    def test_qoshimcha_ham_toliq_soz_ham_togri(self):
        tuzat(KursTugun, KursMashq)
        qosh = ["er", "or", "er", "or", "or", "er", "er", "er", "or"]
        j = self.yubor(qosh)
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual((j.data["ball"], j.data["jami"]), (9, 9))
        j = self.yubor([s + q for s, q in zip(SOZLAR, qosh)])
        self.assertEqual(j.data["ball"], 9)

    def test_notogri_qoshimcha_rad_etiladi(self):
        tuzat(KursTugun, KursMashq)
        j = self.yubor(["or", "er", "or", "er", "er", "or", "or", "or", "er"])
        self.assertEqual(j.data["ball"], 0)

    def test_idempotent(self):
        tuzat(KursTugun, KursMashq)
        hisobot = tuzat(KursTugun, KursMashq)
        self.assertFalse(any(bajarildi for _, bajarildi in hisobot))
