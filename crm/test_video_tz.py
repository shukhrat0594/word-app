"""Video-TZ (2026-09-25, "TZ videolar CRM") testlari: guruhdan chiqarish
sababi, ko'chirish / bitirdi / lidga qaytarish, muzlatish izohi, lid va
talaba arxivi sababi, ketish hisoboti, filialsiz guruhlar ro'yxatda."""

from datetime import date
from unittest import mock

from academics.models import Guruh, GuruhAzoligi
from crm.models import AzolikMoliya, GuruhdanChiqish, GuruhMoliya, Lid, LidTarix, TalabaProfil
from crm.test_api import ApiAsos
from crm.tests import NARX


def bugun(sana):
    """Chiqarish yo'llari `timezone.localdate()`ni ikki modulda chaqiradi."""
    return mock.patch("django.utils.timezone.localdate", return_value=sana)


class GuruhdanChiqarishTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.am = self.azolik_qosh()
        self.m = self.mijoz(self.admin)
        self.yol = f"/api/crm/guruhlar/{self.guruh.id}/talabalar/"

    def test_sabab_turi_va_izoh_yoziladi(self):
        j = self.m.delete(self.yol + f"?talaba={self.talaba.id}&sana=2026-09-10&sabab_turi=narx&sabab=qimmat")
        self.assertEqual(j.status_code, 204)
        c = GuruhdanChiqish.objects.get()
        self.assertEqual((c.sabab_turi, c.sabab), ("narx", "qimmat"))
        self.assertEqual(c.oylik_narx, NARX)
        self.assertFalse(c.chegirma_bor)
        self.assertFalse(GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.talaba).exists())

    def test_ichki_turlar_chiqarish_orqali_berilmaydi(self):
        j = self.m.delete(self.yol + f"?talaba={self.talaba.id}&sabab_turi=bitirdi")
        self.assertEqual(j.status_code, 400)
        self.assertTrue(GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.talaba).exists())

    def test_individual_narx_chegirma_deb_belgilanadi(self):
        self.am.narx = 400000
        self.am.save()
        self.m.delete(self.yol + f"?talaba={self.talaba.id}&sabab_turi=joylashuv")
        self.assertTrue(GuruhdanChiqish.objects.get().chegirma_bor)


class TalabaAmaliTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.am = self.azolik_qosh(narx=500000)
        self.m = self.mijoz(self.admin)
        self.yol = f"/api/crm/guruhlar/{self.guruh.id}/talabalar/amal/"
        self.yangi = Guruh.objects.create(name="IELTS toq kun", markaz=self.markaz, daraja=self.daraja)
        GuruhMoliya.objects.create(guruh=self.yangi, filial=self.filial, boshlanish_sana=date(2026, 1, 1))

    def test_kochirish_narx_va_holat_saqlanadi(self):
        j = self.m.post(self.yol, {"amal": "kochirish", "talaba_id": self.talaba.id,
                                   "yangi_guruh_id": self.yangi.id, "sana": "2026-09-15"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        yangi = AzolikMoliya.objects.get(azolik__guruh=self.yangi, azolik__talaba=self.talaba)
        self.assertEqual(yangi.boshlanish_sana, date(2026, 9, 15))
        self.assertEqual(yangi.narx, 500000)
        self.assertEqual(yangi.holat, AzolikMoliya.Holat.FAOL)
        c = GuruhdanChiqish.objects.get()
        self.assertEqual(c.sabab_turi, GuruhdanChiqish.SababTuri.KOCHIRILDI)
        self.assertIn(self.yangi.name, c.sabab)

    def test_kochirish_ayni_guruhga_yoki_azo_bolgan_guruhga_emas(self):
        j = self.m.post(self.yol, {"amal": "kochirish", "talaba_id": self.talaba.id,
                                   "yangi_guruh_id": self.guruh.id}, format="json")
        self.assertEqual(j.status_code, 400)
        GuruhAzoligi.objects.create(guruh=self.yangi, talaba=self.talaba)
        j = self.m.post(self.yol, {"amal": "kochirish", "talaba_id": self.talaba.id,
                                   "yangi_guruh_id": self.yangi.id}, format="json")
        self.assertEqual(j.status_code, 400)
        self.assertEqual(GuruhdanChiqish.objects.count(), 0)  # eski guruhdan ham chiqmadi

    def test_bitirdi_ketganlarga_sanalmaydi(self):
        with bugun(date(2026, 9, 20)):
            self.m.post(self.yol, {"amal": "bitirdi", "talaba_id": self.talaba.id, "sana": "2026-09-18"},
                        format="json")
            k = self.mijoz(self.owner).get("/api/crm/korsatkichlar/").data
            h = self.m.get("/api/crm/hisobot/ketganlar/?dan=2026-09-01&gacha=2026-09-30").data
        self.assertEqual(k["ketganlar"], 0)
        self.assertEqual(h["soni"], 0)
        self.assertEqual(h["bitirganlar"], 1)

    def test_lidga_qaytarish_mavjud_lidni_qayta_ochadi(self):
        lid = Lid.objects.create(ism="Talaba", telefon="901112233", talaba=self.talaba, arxiv=True,
                                 holat=Lid.Holat.QOSHILDI, arxiv_sabab="kelmadi")
        j = self.m.post(self.yol, {"amal": "lidga", "talaba_id": self.talaba.id, "izoh": "vaqti to'g'ri kelmadi"},
                        format="json")
        self.assertEqual(j.status_code, 200, j.data)
        lid.refresh_from_db()
        self.assertEqual(j.data["lid_id"], lid.id)
        self.assertFalse(lid.arxiv)
        self.assertEqual((lid.holat, lid.arxiv_sabab), (Lid.Holat.YANGI, ""))
        self.assertIn("lidlarga qaytarildi", LidTarix.objects.get(lid=lid).matn)
        self.assertEqual(GuruhdanChiqish.objects.get().sabab_turi, "lidga")

    def test_lidga_qaytarish_lid_bolmasa_yaratadi(self):
        j = self.m.post(self.yol, {"amal": "lidga", "talaba_id": self.talaba.id}, format="json")
        lid = Lid.objects.get(pk=j.data["lid_id"])
        self.assertEqual((lid.talaba_id, lid.filial_id), (self.talaba.id, self.filial.id))

    def test_ruxsatsiz_xodim_403(self):
        from accounts.models import User
        from crm.models import XodimProfil

        u = User.objects.create_user(username="kassir1", password="x", role=User.Role.ODDIY)
        XodimProfil.objects.create(user=u, lavozim="kassir")
        j = self.mijoz(u).post(self.yol, {"amal": "bitirdi", "talaba_id": self.talaba.id}, format="json")
        self.assertEqual(j.status_code, 403)


class MuzlatishTest(ApiAsos):
    def test_sana_va_izoh_saqlanadi_faollashganda_tozalanadi(self):
        am = self.azolik_qosh()
        m = self.mijoz(self.admin)
        j = m.patch(f"/api/crm/azoliklar/{am.id}/", {"holat": "muzlatilgan", "muzlatish_sana": "2026-09-12",
                                                    "muzlatish_izoh": "kasal"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual((str(j.data["muzlatish_sana"]), j.data["muzlatish_izoh"]), ("2026-09-12", "kasal"))
        j = m.patch(f"/api/crm/azoliklar/{am.id}/", {"holat": "faol"}, format="json")
        self.assertEqual((j.data["muzlatish_sana"], j.data["muzlatish_izoh"]), (None, ""))


class LidSababTest(ApiAsos):
    def setUp(self):
        super().setUp()
        self.lid = Lid.objects.create(ism="Test", telefon="901234567", filial=self.filial)
        self.m = self.mijoz(self.admin)
        self.yol = f"/api/crm/lidlar/{self.lid.id}/"

    def test_arxiv_sababsiz_bolmaydi(self):
        self.assertEqual(self.m.patch(self.yol, {"arxiv": True}, format="json").status_code, 400)
        self.assertEqual(
            self.m.patch(self.yol, {"arxiv": True, "arxiv_sabab": "boshqa"}, format="json").status_code, 400)
        self.lid.refresh_from_db()
        self.assertFalse(self.lid.arxiv)

    def test_arxiv_sabab_bilan_va_tarix_odam_tilida(self):
        j = self.m.patch(self.yol, {"arxiv": True, "arxiv_sabab": "raqobatchi"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertEqual(j.data["arxiv_sabab_nomi"], "Raqobatchiga ketdi")
        self.assertEqual(LidTarix.objects.get().matn, "Arxivlandi — Raqobatchiga ketdi")
        self.m.patch(self.yol, {"arxiv": False}, format="json")
        self.lid.refresh_from_db()
        self.assertEqual((self.lid.arxiv_sabab, self.lid.arxiv_izoh), ("", ""))
        self.assertEqual(LidTarix.objects.order_by("-id").first().matn, "Arxivdan chiqarildi")

    def test_qora_royxat_izoh_majburiy(self):
        self.assertEqual(self.m.patch(self.yol, {"qora_royxat": True}, format="json").status_code, 400)
        j = self.m.patch(self.yol, {"qora_royxat": True, "qora_royxat_izoh": "haqorat qildi"}, format="json")
        self.assertEqual(j.status_code, 200)
        self.assertEqual(LidTarix.objects.get().matn, "Qora ro'yxatga olindi: haqorat qildi")


class TalabaArxivSababiTest(ApiAsos):
    def test_arxiv_sabab_va_izoh_majburiy(self):
        m = self.mijoz(self.admin)
        yol = f"/api/crm/talaba/{self.talaba.id}/crm/"
        self.assertEqual(m.patch(yol, {"faol": False}, format="json").status_code, 400)
        self.assertEqual(m.patch(yol, {"faol": False, "arxiv_sabab": "narx"}, format="json").status_code, 400)
        j = m.patch(yol, {"faol": False, "arxiv_sabab": "narx", "arxiv_izoh": "qimmat"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.talaba.refresh_from_db()
        self.assertFalse(self.talaba.is_active)
        m.patch(yol, {"faol": True}, format="json")
        p = TalabaProfil.objects.get(user=self.talaba)
        self.assertEqual((p.arxiv_sabab, p.arxiv_izoh), ("", ""))


class KetishHisobotiTest(ApiAsos):
    def test_kartochkalar_sabablar_va_filtr(self):
        from accounts.models import User

        m = self.mijoz(self.admin)
        yol = f"/api/crm/guruhlar/{self.guruh.id}/talabalar/"
        for i, sabab in enumerate(["narx", "narx", "joylashuv"]):
            t = User.objects.create_user(username=f"k{i}", password="x", role=User.Role.STUDENT)
            self.azolik_qosh(talaba=t)
            m.delete(yol + f"?talaba={t.id}&sana=2026-09-{10 + i}&sabab_turi={sabab}")
        self.azolik_qosh()  # guruhda qolgan bitta
        d = m.get("/api/crm/hisobot/ketganlar/?dan=2026-09-01&gacha=2026-09-30").data
        self.assertEqual(d["soni"], 3)
        self.assertEqual(d["koeffitsient"], 75.0)  # 3 / (1 + 3)
        self.assertEqual(d["yoqotilgan_daromad"], NARX * 3)
        self.assertEqual(d["sabablar"][0], {"sabab_turi": "narx", "nomi": "Narx", "soni": 2})
        self.assertEqual(len(d["dinamika"]), 3)
        self.assertEqual(d["royxat"][0]["kurs"], self.daraja.nomi)
        # Sabab filtri faqat ro'yxatni toraytiradi, kartochkalarni emas.
        d = m.get("/api/crm/hisobot/ketganlar/?dan=2026-09-01&gacha=2026-09-30&sabab_turi=joylashuv").data
        self.assertEqual((d["soni"], len(d["royxat"])), (3, 1))
        eksport = m.get("/api/crm/hisobot/eksport/?turi=ketganlar&dan=2026-09-01&gacha=2026-09-30")
        self.assertEqual(eksport.status_code, 200)


class FilialsizGuruhTest(ApiAsos):
    def test_filial_tanlanganda_sozlanmagan_guruh_ham_chiqadi(self):
        saytdagi = Guruh.objects.create(name="Saytda ochilgan", markaz=self.markaz)
        idlar = [g["id"] for g in self.mijoz(self.admin).get(f"/api/crm/guruhlar/?filial={self.filial.id}").data]
        self.assertIn(saytdagi.id, idlar)
        self.assertIn(self.guruh.id, idlar)

