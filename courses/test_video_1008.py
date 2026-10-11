"""Video-TZ 2026-10-08 (IMG_2150): Vocabulary mashqida talaba tarjima
javoblarini yuborganda, natija serverda hisoblanib saqlanadi — bu
ota-onaga yuboriladigan kunlik natija xabarida ishlatiladi (qarang
`parentsbot.test_natija`)."""

from accounts.models import User
from courses.models import KursSoz, KursSozYechim, KursTugun
from crm.test_api import ApiAsos


class SozlarTekshirishAsos(ApiAsos):
    def setUp(self):
        super().setUp()
        self.unit = KursTugun.objects.create(
            markaz=self.markaz, nomi="Unit 1", parent=self.daraja, unit_darsi=True, tartib=0,
        )
        self.vocab = KursTugun.objects.create(
            markaz=self.markaz, nomi="Vocabulary", parent=self.unit, kalit="vocabulary", tartib=0,
        )
        self.soz1 = KursSoz.objects.create(tugun=self.vocab, tartib=0, en="airport", uz="aeroport")
        self.soz2 = KursSoz.objects.create(tugun=self.vocab, tartib=1, en="hotel", uz="mehmonxona", ru="отель")

    def yubor(self, user, javoblar):
        return self.mijoz(user).post(
            f"/api/kurslar/{self.vocab.id}/sozlar/tekshirish/", {"javoblar": javoblar}, format="json"
        )


class SozlarTekshirishTest(SozlarTekshirishAsos):
    def test_togri_javoblar_serverda_hisoblanadi(self):
        j = self.yubor(self.talaba, {str(self.soz1.id): "aeroport", str(self.soz2.id): "mehmonxona"})
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual((j.data["ball"], j.data["jami"]), (2, 2))
        y = KursSozYechim.objects.get(talaba=self.talaba, tugun=self.vocab)
        self.assertEqual((y.ball, y.jami), (2, 2))

    def test_ruscha_javob_ham_togri_hisoblanadi(self):
        j = self.yubor(self.talaba, {str(self.soz1.id): "aeroport", str(self.soz2.id): "отель"})
        self.assertEqual(j.data["ball"], 2)

    def test_notogri_va_bosh_javob_hisobga_kirmaydi(self):
        j = self.yubor(self.talaba, {str(self.soz1.id): "notogri", str(self.soz2.id): ""})
        self.assertEqual((j.data["ball"], j.data["jami"]), (0, 2))

    def test_katta_kichik_harf_va_boshidagi_bosh_joy_ahamiyatsiz(self):
        j = self.yubor(self.talaba, {str(self.soz1.id): "  AeroPort  "})
        self.assertEqual(j.data["ball"], 1)

    def test_klient_yuborgan_ball_etibor_olinmaydi(self):
        # "javoblar" ichida ball/jami kabi maydon yo'q — faqat so'z_id -> matn.
        # Shu bilan birga, agar kimdir boshqa maydon qo'shsa ham ta'sir qilmasligini tekshiramiz.
        j = self.mijoz(self.talaba).post(
            f"/api/kurslar/{self.vocab.id}/sozlar/tekshirish/",
            {"javoblar": {str(self.soz1.id): "notogri"}, "ball": 99, "jami": 1},
            format="json",
        )
        self.assertEqual(j.data["ball"], 0)

    def test_oqituvchi_son_qila_olmaydi(self):
        j = self.yubor(self.oqituvchi, {str(self.soz1.id): "aeroport"})
        self.assertEqual(j.status_code, 403)
        self.assertFalse(KursSozYechim.objects.exists())

    def test_boshqa_talabaning_natijasiga_aralashmaydi(self):
        boshqa = User.objects.create_user(
            username="talaba2", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        self.yubor(self.talaba, {str(self.soz1.id): "aeroport"})
        self.yubor(boshqa, {str(self.soz1.id): "aeroport", str(self.soz2.id): "mehmonxona"})
        self.assertEqual(KursSozYechim.objects.get(talaba=self.talaba).ball, 1)
        self.assertEqual(KursSozYechim.objects.get(talaba=boshqa).ball, 2)

    def test_variantlar_yo_e_va_tinish_belgisi_ahamiyatsiz(self):
        # Matn-TZ 138: "keksa/eski / старый", "Приятно познакомиться.", ё/е
        s1 = KursSoz.objects.create(tugun=self.vocab, tartib=2, en="old", uz="keksa/eski", ru="старый")
        s2 = KursSoz.objects.create(
            tugun=self.vocab, tartib=3, en="Nice to meet you",
            uz="Tanishganimdan xursandman.", ru="Приятно познакомиться.",
        )
        s3 = KursSoz.objects.create(tugun=self.vocab, tartib=4, en="yellow", uz="sariq", ru="жёлтый")
        s4 = KursSoz.objects.create(tugun=self.vocab, tartib=5, en="cousin", uz="amakivachcha (qarindosh)")
        j = self.yubor(self.talaba, {
            str(s1.id): "eski", str(s2.id): "приятно познакомиться",
            str(s3.id): "желтый", str(s4.id): "amakivachcha",
        })
        self.assertEqual(j.data["ball"], 4)

    def test_javoblar_royxat_bolsa_400(self):
        j = self.mijoz(self.talaba).post(
            f"/api/kurslar/{self.vocab.id}/sozlar/tekshirish/", {"javoblar": ["aeroport"]}, format="json"
        )
        self.assertEqual(j.status_code, 400)
