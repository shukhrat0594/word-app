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

    def test_lidni_ochirib_bolmaydi(self):
        """Shuhrat, 2026-09-25: o'chirish yo'q — faqat sabab bilan arxiv."""
        self.assertEqual(self.m.delete(self.yol).status_code, 405)
        self.assertTrue(Lid.objects.filter(pk=self.lid.pk).exists())

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

    def test_arxivlanganda_barcha_guruhlardan_chiqadi(self):
        """Shuhrat, 2026-09-25: arxiv — guruhlardan ham chiqarish, ketish hisobotiga tushsin."""
        self.azolik_qosh()
        m = self.mijoz(self.admin)
        with bugun(date(2026, 9, 20)):
            j = m.patch(f"/api/crm/talaba/{self.talaba.id}/crm/",
                        {"faol": False, "arxiv_sabab": "joylashuv", "arxiv_izoh": "ko'chib ketdi"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertFalse(GuruhAzoligi.objects.filter(talaba=self.talaba).exists())
        c = GuruhdanChiqish.objects.get()
        self.assertEqual((c.sabab_turi, c.sabab, c.sana), ("joylashuv", "ko'chib ketdi", date(2026, 9, 20)))
        # Filial tanlangan arxiv ro'yxatida ham ko'rinadi (guruhsiz bo'lib qolgani uchun).
        royxat = m.get(f"/api/crm/talabalar/?arxiv=1&filial={self.filial.id}").data
        self.assertIn(self.talaba.id, [x["id"] for x in royxat])
        # Arxivdan chiqarish guruhga qaytarmaydi.
        m.patch(f"/api/crm/talaba/{self.talaba.id}/crm/", {"faol": True}, format="json")
        self.assertFalse(GuruhAzoligi.objects.filter(talaba=self.talaba).exists())

    def test_sababsiz_arxivda_guruhdan_chiqmaydi(self):
        self.azolik_qosh()
        self.mijoz(self.admin).patch(f"/api/crm/talaba/{self.talaba.id}/crm/", {"faol": False}, format="json")
        self.assertTrue(GuruhAzoligi.objects.filter(talaba=self.talaba).exists())
        self.assertEqual(GuruhdanChiqish.objects.count(), 0)


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



class EslatmaBajarildiTest(ApiAsos):
    """Video-TZ 2026-09-25 (3-to'plam): vaqti o'tgan eslatmani "Bajarildi"
    deb belgilash — bosh sahifa va 🔔 xabarnomadan ketadi."""

    def test_bajarilgani_muddatlilarda_chiqmaydi(self):
        from django.utils import timezone

        from crm.models import Eslatma

        e = Eslatma.objects.create(talaba=self.talaba, matn="darsga chaqirish", kim=self.admin,
                                   eslatish_vaqti=timezone.now())
        m = self.mijoz(self.admin)
        self.assertEqual([x["id"] for x in m.get("/api/crm/eslatmalar/muddatli/").data], [e.id])
        j = m.patch(f"/api/crm/eslatmalar/{e.id}/", {"bajarildi": True}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertTrue(j.data["bajarildi"])
        self.assertEqual(m.get("/api/crm/eslatmalar/muddatli/").data, [])
        # Boshqa xodim birovning eslatmasini belgilay olmaydi.
        self.assertEqual(self.mijoz(self.owner).patch(f"/api/crm/eslatmalar/{e.id}/", {"bajarildi": False},
                                                      format="json").status_code, 403)

    def test_ogohlantirishlar_yoli_olib_tashlangan(self):
        self.assertEqual(self.mijoz(self.admin).get("/api/crm/ogohlantirishlar/").status_code, 404)


class KursQoshishTest(ApiAsos):
    """2026-09-26, Shuhrat: CRM'dan yangi kurs va narxi ("Narxlar" → "Kurs qo'shish")."""

    def setUp(self):
        super().setUp()
        from courses.models import KursTugun

        self.ildiz = self.daraja.parent  # CrmAsos'dagi ildiz
        self.fan = KursTugun.objects.create(markaz=self.markaz, nomi="Rus tili", parent=self.ildiz, tartib=5)

    def test_mavjud_fanga_kurs_va_narx(self):
        from courses.models import KursTugun
        from crm.models import KursNarxi

        m = self.mijoz(self.admin)
        j = m.post("/api/crm/kurs-narxlari/", {"fan_id": self.fan.id, "nomi": "Rus tili (boshlang'ich)",
                                               "narx": "450000"}, format="json")
        self.assertEqual(j.status_code, 201, j.data)
        k = KursTugun.objects.get(pk=j.data["daraja_id"])
        self.assertEqual((k.parent_id, k.markaz_id, k.tez_kunda, k.kalit), (self.fan.id, self.markaz.id, True,
                                                                           "rus_tili_boshlang_ich"))
        self.assertEqual(KursNarxi.objects.get(daraja=k).narx, 450000)
        # Guruh oynasidagi ro'yxatda darhol chiqadi va guruh shu kurs bilan yaratiladi.
        self.assertIn(k.id, [x["daraja_id"] for x in m.get("/api/crm/kurs-narxlari/").data])
        j = m.post("/api/crm/guruh-yaratish/", {"nomi": "Rus 1", "daraja_id": k.id, "filial_id": self.filial.id,
                                                "boshlanish_sana": "2026-10-01"}, format="json")
        self.assertEqual(j.status_code, 201, j.data)

    def test_yangi_fan_bilan(self):
        from courses.models import KursTugun

        j = self.mijoz(self.admin).post("/api/crm/kurs-narxlari/", {
            "fan_nomi": "Matematika", "nomi": "Matematika 5-sinf", "narx": "300000"}, format="json")
        self.assertEqual(j.status_code, 201, j.data)
        fan = KursTugun.objects.get(nomi="Matematika")
        self.assertEqual((fan.parent_id, fan.tez_kunda), (self.ildiz.id, True))
        self.assertEqual(j.data["fan"], "Matematika")

    def test_takror_nom_va_notogri_narx(self):
        m = self.mijoz(self.admin)
        tana = {"fan_id": self.fan.id, "nomi": "Kids", "narx": "300000"}
        self.assertEqual(m.post("/api/crm/kurs-narxlari/", tana, format="json").status_code, 201)
        self.assertEqual(m.post("/api/crm/kurs-narxlari/", {**tana, "nomi": "kids"}, format="json").status_code, 400)
        self.assertEqual(m.post("/api/crm/kurs-narxlari/", {**tana, "nomi": "B", "narx": "0"},
                                format="json").status_code, 400)
        self.assertEqual(m.post("/api/crm/kurs-narxlari/", {"nomi": "C", "narx": "1000"},
                                format="json").status_code, 400)  # fan yo'q

    def test_ruxsatsizga_yopiq(self):
        from accounts.models import User
        from crm.models import XodimProfil

        kassir = User.objects.create_user(username="kassir9", password="x", role=User.Role.ODDIY)
        XodimProfil.objects.create(user=kassir, lavozim="kassir")
        j = self.mijoz(kassir).post("/api/crm/kurs-narxlari/", {"fan_id": self.fan.id, "nomi": "X", "narx": "1000"},
                                    format="json")
        self.assertEqual(j.status_code, 403)
        self.assertEqual([f["nomi"] for f in self.mijoz(self.admin).get("/api/crm/kurs-fanlari/").data].count(
            "Rus tili"), 1)


class KursTahrirOchirishTest(ApiAsos):
    """2026-09-26, Shuhrat: "Narxlar"da kursni tahrirlash va o'chirish."""

    def setUp(self):
        super().setUp()
        from courses.models import KursTugun

        self.fan = KursTugun.objects.create(markaz=self.markaz, nomi="Matematika", parent=self.daraja.parent)
        self.m = self.mijoz(self.admin)
        j = self.m.post("/api/crm/kurs-narxlari/", {"fan_id": self.fan.id, "nomi": "MAtematika", "narx": "480000"},
                        format="json")
        self.kurs_id = j.data["daraja_id"]

    def test_nomini_tahrirlash(self):
        from courses.models import KursTugun

        j = self.m.patch(f"/api/crm/kurslar/{self.kurs_id}/", {"nomi": "Matematika"}, format="json")
        self.assertEqual(j.status_code, 200, j.data)
        k = KursTugun.objects.get(pk=self.kurs_id)
        self.assertEqual(k.nomi, "Matematika")
        self.assertEqual(k.kalit, "matematika")  # kalit o'zgarmaydi
        self.assertEqual(self.m.patch(f"/api/crm/kurslar/{self.kurs_id}/", {"nomi": " "}, format="json").status_code,
                         400)

    def test_bosh_kursni_ochirish_va_royxatdagi_belgi(self):
        from courses.models import KursTugun
        from crm.models import KursNarxi

        qator = next(x for x in self.m.get("/api/crm/kurs-narxlari/").data if x["daraja_id"] == self.kurs_id)
        self.assertTrue(qator["ochirsa_boladi"])
        self.assertEqual(self.m.delete(f"/api/crm/kurslar/{self.kurs_id}/").status_code, 204)
        self.assertFalse(KursTugun.objects.filter(pk=self.kurs_id).exists())
        self.assertFalse(KursNarxi.objects.filter(daraja_id=self.kurs_id).exists())

    def test_guruhi_yoki_darsi_bor_kurs_ochirilmaydi(self):
        from academics.models import Guruh
        from courses.models import KursTugun

        Guruh.objects.create(name="Mat 1", markaz=self.markaz, daraja_id=self.kurs_id, faol=False)  # arxivdagi ham
        j = self.m.delete(f"/api/crm/kurslar/{self.kurs_id}/")
        self.assertEqual(j.status_code, 400)
        self.assertIn("guruh", j.data["detail"])
        Guruh.objects.filter(daraja_id=self.kurs_id).delete()
        KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1", parent_id=self.kurs_id)
        self.assertEqual(self.m.delete(f"/api/crm/kurslar/{self.kurs_id}/").status_code, 400)
        self.assertTrue(KursTugun.objects.filter(pk=self.kurs_id).exists())
        qator = next(x for x in self.m.get("/api/crm/kurs-narxlari/").data if x["daraja_id"] == self.kurs_id)
        self.assertFalse(qator["ochirsa_boladi"])

    def test_unit_yoki_fanni_bu_yol_bilan_ochirib_bolmaydi(self):
        self.assertEqual(self.m.delete(f"/api/crm/kurslar/{self.fan.id}/").status_code, 404)

    def test_ruxsatsizga_yopiq(self):
        from accounts.models import User
        from crm.models import XodimProfil

        kassir = User.objects.create_user(username="kassir8", password="x", role=User.Role.ODDIY)
        XodimProfil.objects.create(user=kassir, lavozim="kassir")
        self.assertEqual(self.mijoz(kassir).delete(f"/api/crm/kurslar/{self.kurs_id}/").status_code, 403)

    def test_filialga_boglangan_xodimga_yopiq(self):
        """Kurs butun markazniki — filial administratori faqat ko'radi."""
        from accounts.models import User
        from crm.models import XodimProfil

        u = User.objects.create_user(username="admin_filial", password="x", role=User.Role.ADMIN, markaz=self.markaz)
        XodimProfil.objects.create(user=u, lavozim="admin").filiallar.set([self.filial])
        m = self.mijoz(u)
        self.assertEqual(m.patch(f"/api/crm/kurslar/{self.kurs_id}/", {"nomi": "X"}, format="json").status_code, 403)
        self.assertEqual(m.delete(f"/api/crm/kurslar/{self.kurs_id}/").status_code, 403)
        self.assertEqual(m.post("/api/crm/kurs-narxlari/", {"fan_id": self.fan.id, "nomi": "Y", "narx": "1000"},
                                format="json").status_code, 403)
