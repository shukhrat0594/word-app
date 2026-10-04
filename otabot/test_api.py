from datetime import date
from unittest import mock

from academics.models import Guruh, GuruhAzoligi
from accounts.models import Bildirishnoma, User
from audit.models import FaoliyatYozuvi
from crm.models import CrmRol, Filial, GuruhMoliya, XodimProfil
from crm.test_api import ApiAsos
from otabot.models import Abonent, Boglanish, OtaBotSozlama, Sorov
from otabot.test_bot import SoxtaTg

YOL = "/api/crm/otabot/"


class OtabotApiAsos(ApiAsos):
    def setUp(self):
        super().setUp()
        self.tg = SoxtaTg()
        p = mock.patch("otabot.views.tg_ol", return_value=self.tg)
        p.start()
        self.addCleanup(p.stop)
        self.ota = Abonent.objects.create(telegram_id=555, ism="Ota Telegram", telefon="+998931112233",
                                          til="uz", holat="tayyor")
        self.t = User.objects.create_user(
            username="sevara", password="x", role=User.Role.STUDENT, first_name="Sevara", last_name="Jorayeva",
            tugilgan_sana=date(2011, 3, 3))
        self.sorov = Sorov.objects.create(abonent=self.ota, farzand_ismi="Sevara Jorayva",
                                          tugilgan_sana="03.03.2011", nomzodlar=[self.t.id])

    def rolli_xodim(self, username, ruxsatlar, filial=None):
        rol = CrmRol.objects.create(nomi=f"R-{username}", ruxsatlar=ruxsatlar)
        u = User.objects.create_user(username=username, password="x", role=User.Role.ODDIY)
        p = XodimProfil.objects.create(user=u, lavozim="boshqa", rol=rol)
        if filial:
            p.filiallar.set([filial])
        return u


class SorovlarTest(OtabotApiAsos):
    def test_royxat_nomzodlar_bilan(self):
        j = self.mijoz(self.owner).get(YOL + "sorovlar/")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(len(j.data), 1)
        d = j.data[0]
        self.assertEqual((d["farzand_ismi"], d["abonent"]["ism"]), ("Sevara Jorayva", "Ota Telegram"))
        self.assertEqual([n["id"] for n in d["nomzodlar"]], [self.t.id])

    def test_ulash(self):
        j = self.mijoz(self.owner).post(YOL + f"sorovlar/{self.sorov.id}/hal/",
                                        {"amal": "ulash", "talaba_id": self.t.id}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.sorov.refresh_from_db()
        self.assertEqual((self.sorov.holat, self.sorov.talaba, self.sorov.hal_qilgan),
                         ("ulandi", self.t, self.owner))
        b = Boglanish.objects.get()
        self.assertEqual((b.abonent, b.talaba, b.usul, b.kim), (self.ota, self.t, "admin", self.owner))
        # ota-onaga Telegram'da xabar ketdi
        self.assertEqual(self.tg.yuborilgan[-1][0], 555)
        self.assertIn("Sevara Jorayeva", self.tg.yuborilgan[-1][1])
        self.assertTrue(FaoliyatYozuvi.objects.filter(obyekt_turi="Ota-ona so'rovi").exists())

    def test_rad(self):
        j = self.mijoz(self.owner).post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "rad"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.sorov.refresh_from_db()
        self.assertEqual(self.sorov.holat, "rad")
        self.assertEqual(Boglanish.objects.count(), 0)
        self.assertEqual(self.tg.yuborilgan[-1][0], 555)

    def test_ikki_marta_hal_qilib_bolmaydi(self):
        m = self.mijoz(self.owner)
        m.post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "rad"}, format="json")
        j = m.post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "ulash", "talaba_id": self.t.id}, format="json")
        self.assertEqual(j.status_code, 400)
        self.assertEqual(Boglanish.objects.count(), 0)

    def test_notogri_talaba_va_amal(self):
        m = self.mijoz(self.owner)
        self.assertEqual(m.post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "ulash"}, format="json").status_code, 404)
        self.assertEqual(m.post(YOL + f"sorovlar/{self.sorov.id}/hal/",
                                {"amal": "ulash", "talaba_id": self.owner.id}, format="json").status_code, 404)  # talaba emas
        self.assertEqual(m.post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "yoq qil"}, format="json").status_code, 400)

    def test_telegram_ishlamasa_ham_ulanadi(self):
        self.tg.yubor = mock.Mock(side_effect=__import__("otabot.telegram", fromlist=["TgXato"]).TgXato("x"))
        j = self.mijoz(self.owner).post(YOL + f"sorovlar/{self.sorov.id}/hal/",
                                        {"amal": "ulash", "talaba_id": self.t.id}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(Boglanish.objects.count(), 1)

    def test_qidiruv(self):
        j = self.mijoz(self.owner).get(YOL + "talaba-qidiruv/?q=sev")
        self.assertEqual([x["id"] for x in j.data], [self.t.id])
        self.assertEqual(self.mijoz(self.owner).get(YOL + "talaba-qidiruv/?q=s").data, [])  # juda qisqa


class RuxsatTest(OtabotApiAsos):
    def test_bolimsiz_xodim_403(self):
        u = self.rolli_xodim("lidchi", ["lidlar"])
        m = self.mijoz(u)
        self.assertEqual(m.get(YOL + "sorovlar/").status_code, 403)
        self.assertEqual(m.get(YOL + "sozlama/").status_code, 403)

    def test_faqat_sozlama_ruxsati_ulay_olmaydi(self):
        u = self.rolli_xodim("sozlamachi", ["otabot.sozlama"])
        m = self.mijoz(u)
        self.assertEqual(m.get(YOL + "sorovlar/").status_code, 200)  # bo'lim ochiladi
        j = m.post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "rad"}, format="json")
        self.assertEqual(j.status_code, 403)
        self.sorov.refresh_from_db()
        self.assertEqual(self.sorov.holat, "kutilmoqda")

    def test_faqat_ulash_ruxsati_sozlamani_ozgartira_olmaydi(self):
        u = self.rolli_xodim("ulovchi", ["otabot.ulash"])
        self.assertEqual(self.mijoz(u).put(YOL + "sozlama/", {"qarz_soati": "11:00"}, format="json").status_code, 403)

    def test_talaba_va_ota_ona_kira_olmaydi(self):
        self.assertEqual(self.mijoz(self.t).get(YOL + "sorovlar/").status_code, 403)
        self.assertEqual(self.mijoz(self.ota_ona).get(YOL + "sorovlar/").status_code, 403)


class FilialTest(OtabotApiAsos):
    def setUp(self):
        super().setUp()
        self.fb = Filial.objects.create(markaz=self.markaz, nomi="B")
        gb = Guruh.objects.create(name="B guruh", markaz=self.markaz, daraja=self.daraja)
        GuruhMoliya.objects.create(guruh=gb, filial=self.fb, boshlanish_sana=date(2026, 1, 1))
        GuruhAzoligi.objects.create(guruh=gb, talaba=self.t)  # talaba B filialda
        self.a_xodim = self.rolli_xodim("a_admin", ["otabot"], filial=self.filial)  # faqat A filial

    def test_boshqa_filial_sorovi_korinmaydi(self):
        self.assertEqual(self.mijoz(self.a_xodim).get(YOL + "sorovlar/").data, [])
        self.assertEqual(len(self.mijoz(self.owner).get(YOL + "sorovlar/").data), 1)

    def test_boshqa_filial_talabasini_ulay_olmaydi(self):
        j = self.mijoz(self.a_xodim).post(YOL + f"sorovlar/{self.sorov.id}/hal/",
                                          {"amal": "ulash", "talaba_id": self.t.id}, format="json")
        self.assertEqual(j.status_code, 404)
        self.assertEqual(Boglanish.objects.count(), 0)

    def test_boshqa_filial_sorovini_rad_ham_etolmaydi(self):
        j = self.mijoz(self.a_xodim).post(YOL + f"sorovlar/{self.sorov.id}/hal/", {"amal": "rad"}, format="json")
        self.assertEqual(j.status_code, 404)

    def test_qidiruvda_boshqa_filial_talabasi_chiqmaydi(self):
        self.assertEqual(self.mijoz(self.a_xodim).get(YOL + "talaba-qidiruv/?q=sevara").data, [])

    def test_o_z_filiali_talabasini_ulaydi(self):
        GuruhAzoligi.objects.filter(talaba=self.t).delete()  # guruhsiz talaba hammaga ko'rinadi
        j = self.mijoz(self.a_xodim).post(YOL + f"sorovlar/{self.sorov.id}/hal/",
                                          {"amal": "ulash", "talaba_id": self.t.id}, format="json")
        self.assertEqual(j.status_code, 200, j.data)

    def test_filial_xodimi_sozlamani_ozgartira_olmaydi(self):
        u = self.rolli_xodim("a_sozlama", ["otabot", "otabot.sozlama"], filial=self.filial)
        self.assertEqual(self.mijoz(u).put(YOL + "sozlama/", {"qarz_soati": "11:00"}, format="json").status_code, 403)


class AbonentlarTest(OtabotApiAsos):
    def test_royxat_va_uzish(self):
        b = Boglanish.objects.create(abonent=self.ota, talaba=self.t, usul="telefon")
        m = self.mijoz(self.owner)
        j = m.get(YOL + "abonentlar/")
        self.assertEqual(len(j.data), 1)
        self.assertEqual(j.data[0]["farzandlar"][0]["talaba"]["id"], self.t.id)
        self.assertEqual(m.post(YOL + f"boglanishlar/{b.id}/uzish/").status_code, 204)
        b.refresh_from_db()
        self.assertFalse(b.faol)
        self.assertEqual(m.get(YOL + "abonentlar/").data, [])
        self.assertEqual(m.post(YOL + f"boglanishlar/{b.id}/uzish/").status_code, 404)  # allaqachon uzilgan


class SozlamaTest(OtabotApiAsos):
    def test_standart_qiymatlar(self):
        d = self.mijoz(self.owner).get(YOL + "sozlama/").data
        self.assertEqual((d["tinch_boshi"], d["tinch_oxiri"], d["qarz_soati"], d["natija_soati"]),
                         ("22:00", "08:00", "10:00", "19:00"))
        self.assertEqual((d["qarz_kunlari"], d["natija_kunlari"]), ([0], [0, 1, 2, 3, 4, 5, 6]))
        self.assertTrue(d["davomat_kelmadi"] and not d["davomat_sababli"])

    def test_ozgartirish(self):
        j = self.mijoz(self.owner).put(YOL + "sozlama/", {
            "tinch_boshi": "21:30", "qarz_kunlari": [4, 0, 4], "davomat_sababli": True, "natija_yoqilgan": False,
        }, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        s = OtaBotSozlama.ol()
        self.assertEqual((s.tinch_boshi.strftime("%H:%M"), s.qarz_kunlari, s.davomat_sababli, s.natija_yoqilgan),
                         ("21:30", [0, 4], True, False))
        self.assertTrue(FaoliyatYozuvi.objects.filter(obyekt_turi="Ota-ona boti sozlamasi").exists())

    def test_notogri_qiymatlar_400(self):
        m = self.mijoz(self.owner)
        for tana in ({"qarz_soati": "25:99"}, {"qarz_soati": "kech"}, {"qarz_kunlari": [7]},
                     {"qarz_kunlari": "dushanba"}, {"davomat_yoqilgan": "ha"}, {"natija_kunlari": [True]}):
            self.assertEqual(m.put(YOL + "sozlama/", tana, format="json").status_code, 400, tana)
        d = self.mijoz(self.owner).get(YOL + "sozlama/").data
        self.assertEqual(d["qarz_soati"], "10:00")  # hech narsa saqlanmadi


class AdminlarTest(OtabotApiAsos):
    def test_yangi_sorov_adminlarga_bildirishnoma(self):
        from otabot import xizmat

        yangi = Abonent.objects.create(telegram_id=777, ism="Yangi ota", holat="tayyor")
        s = xizmat.sorov_yarat(yangi, "Boshqa Ism", "01.01.2000", [])
        adminlar = {u.id for u in xizmat.adminlar()}
        self.assertIn(self.owner.id, adminlar)
        self.assertTrue(Bildirishnoma.objects.filter(foydalanuvchi=self.owner, kalit=f"otabot:sorov:{s.id}").exists())
        # rolsiz oddiy foydalanuvchiga bormaydi
        self.assertNotIn(self.talaba.id, adminlar)
