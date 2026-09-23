"""Video-TZ tekshiruvidan keyingi tuzatishlar (2026-09-23): ruxsatlar
(rol o'zini kengaytirishi, xodimga rol berish), tizim rollari, pul
(retro chegirma, owner tuzatgan hisob), dars ko'chirish, arxiv."""

from datetime import date
from decimal import Decimal

from academics.models import Davomat
from accounts.models import User
from audit.models import FaoliyatYozuvi
from crm import mantiq
from crm.models import CrmRol, DarsMavzusi, GuruhMoliya, Hisob, KursNarxi, Lid, XodimProfil
from crm.test_api import ApiAsos
from crm.tests import NARX, SENTABR, bugun_qilib


class Yordamchi(ApiAsos):
    def xodim(self, username, lavozim="boshqa", rol=None, role=User.Role.ODDIY):
        u = User.objects.create_user(username=username, password="x", role=role)
        XodimProfil.objects.create(user=u, lavozim=lavozim, rol=rol, oylik=Decimal("3000000"))
        return u


class RolKengaytirishTest(Yordamchi):
    """J-1: faqat "Kurs narxlari" ruxsati bor xodim o'z rolini tahrirlab
    hamma ruxsatni ololmasin."""

    def test_narxlar_ruxsati_rolni_tahrirlay_olmaydi(self):
        rol = CrmRol.objects.create(nomi="Narxchi", ruxsatlar=["sozlamalar.narxlar"])
        m = self.mijoz(self.xodim("narxchi", rol=rol))
        javob = m.patch(f"/api/crm/rollar/{rol.id}/", {"ruxsatlar": ["moliya", "xodimlar"]}, format="json")
        self.assertEqual(javob.status_code, 403)
        rol.refresh_from_db()
        self.assertEqual(rol.ruxsatlar, ["sozlamalar.narxlar"])
        self.assertEqual(m.delete(f"/api/crm/rollar/{rol.id}/").status_code, 403)

    def test_rollar_ruxsati_bilan_tahrirlanadi(self):
        rol = CrmRol.objects.create(nomi="Boshqaruvchi", ruxsatlar=["sozlamalar.rollar"])
        boshqa = CrmRol.objects.create(nomi="Kichik", ruxsatlar=["lidlar"])
        m = self.mijoz(self.xodim("rolchi", rol=rol))
        javob = m.patch(f"/api/crm/rollar/{boshqa.id}/", {"ruxsatlar": ["lidlar", "hisobotlar"]}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)


class XodimgaRolBerishTest(Yordamchi):
    """J-2: `xodimlar` ruxsati rol berishga yetmaydi; o'zini tahrirlab
    bo'lmaydi; boshqaning parolini faqat administrator tiklaydi."""

    def setUp(self):
        super().setUp()
        self.kadr_rol = CrmRol.objects.create(nomi="Kadrchi", ruxsatlar=["xodimlar"])
        self.toliq = CrmRol.objects.create(nomi="To'liq", ruxsatlar=["moliya", "sozlamalar"])
        self.kadr = self.xodim("kadr", rol=self.kadr_rol)
        self.m = self.mijoz(self.kadr)

    def test_ozining_rolini_almashtira_olmaydi(self):
        javob = self.m.patch(f"/api/crm/xodimlar/{self.kadr.id}/", {"rol_id": self.toliq.id}, format="json")
        self.assertEqual(javob.status_code, 403)
        self.assertEqual(XodimProfil.objects.get(user=self.kadr).rol_id, self.kadr_rol.id)

    def test_boshqaga_rol_bera_olmaydi(self):
        boshqa = self.xodim("boshqa1", lavozim="kassir")
        javob = self.m.patch(f"/api/crm/xodimlar/{boshqa.id}/", {"rol_id": self.toliq.id}, format="json")
        self.assertEqual(javob.status_code, 403)
        javob = self.m.post("/api/crm/xodimlar/", {
            "ism": "Yangi", "telefon": "901112299", "lavozim": "kassir", "rol_id": self.toliq.id,
        }, format="json")
        self.assertEqual(javob.status_code, 403)

    def test_oqituvchi_parolini_tiklay_olmaydi(self):
        eski = self.oqituvchi.password
        javob = self.m.patch(f"/api/crm/xodimlar/{self.oqituvchi.id}/", {"parol_tiklash": 1}, format="json")
        self.assertEqual(javob.status_code, 403)
        self.oqituvchi.refresh_from_db()
        self.assertEqual(self.oqituvchi.password, eski)
        # Administrator esa tiklay oladi.
        javob = self.mijoz(self.admin).patch(
            f"/api/crm/xodimlar/{self.oqituvchi.id}/", {"parol_tiklash": 1}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertTrue(javob.data["parol"])

    def test_tizim_rolini_maxsus_rol_qilib_berib_bolmaydi(self):
        kassir_rol = CrmRol.objects.get(lavozim="kassir")
        boshqa = self.xodim("boshqa2")
        javob = self.mijoz(self.owner).patch(
            f"/api/crm/xodimlar/{boshqa.id}/", {"rol_id": kassir_rol.id}, format="json")
        self.assertEqual(javob.status_code, 400)


class OylikYoqolmaydiTest(Yordamchi):
    """J-4: oylikni ko'rmaydigan foydalanuvchi tahrirlasa — oylik 0 ga tushmaydi."""

    def test_bosh_oylik_etiborsiz(self):
        rol = CrmRol.objects.create(nomi="Tahrirchi", ruxsatlar=["xodimlar.tahrirlash"])
        m = self.mijoz(self.xodim("tahrirchi", rol=rol))
        nishon = self.xodim("nishon", lavozim="kassir")
        javob = m.patch(f"/api/crm/xodimlar/{nishon.id}/", {
            "ism": "Yangi ism", "oylik": "", "foiz_ulushi": ""}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        p = XodimProfil.objects.get(user=nishon)
        self.assertEqual(p.oylik, Decimal("3000000"))
        self.assertEqual(nishon.__class__.objects.get(pk=nishon.pk).first_name, "Yangi ism")


class TizimRollariTest(Yordamchi):
    def test_migratsiya_joriy_xatti_harakatni_saqlaydi(self):
        kassir = CrmRol.objects.get(lavozim="kassir")
        self.assertIn("moliya", kassir.ruxsatlar)
        self.assertIn("moliya.tolov", kassir.ruxsatlar)
        self.assertNotIn("lidlar", kassir.ruxsatlar)
        self.assertEqual(CrmRol.objects.get(lavozim="oqituvchi").ruxsatlar, [])

    def test_lavozim_roli_tahrirlansa_ruxsat_ozgaradi(self):
        m = self.mijoz(self.xodim("kassir1", lavozim="kassir"))
        self.assertEqual(m.get("/api/crm/lidlar/").status_code, 403)
        kassir = CrmRol.objects.get(lavozim="kassir")
        javob = self.mijoz(self.owner).patch(
            f"/api/crm/rollar/{kassir.id}/", {"ruxsatlar": kassir.ruxsatlar + ["lidlar"]}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(m.get("/api/crm/lidlar/").status_code, 200)

    def test_lavozim_roli_ochmaydi_va_nomi_ozgarmaydi(self):
        kassir = CrmRol.objects.get(lavozim="kassir")
        o = self.mijoz(self.owner)
        self.assertEqual(o.delete(f"/api/crm/rollar/{kassir.id}/").status_code, 400)
        self.assertEqual(o.patch(f"/api/crm/rollar/{kassir.id}/", {"nomi": "Boshqa nom"}, format="json").status_code, 400)
        self.assertEqual(o.patch(f"/api/crm/rollar/{kassir.id}/", {"faol": False}, format="json").status_code, 400)

    def test_royxatda_tizim_rollari_oldin(self):
        CrmRol.objects.create(nomi="Aaa", ruxsatlar=[])
        rollar = self.mijoz(self.owner).get("/api/crm/rollar/").data
        self.assertEqual(rollar[0]["lavozim"], "admin")
        self.assertEqual(rollar[-1]["nomi"], "Aaa")

    def test_administratorga_maxsus_rol_ishlaydi(self):
        """O-5: "Administrator 1" (cheklangan) administratorga berilsa — cheklov ishlaydi."""
        rol = CrmRol.objects.create(nomi="Administrator 1", ruxsatlar=["lidlar", "hisobotlar"])
        admin = self.xodim("admin1", lavozim="admin", rol=rol, role=User.Role.ADMIN)
        m = self.mijoz(admin)
        self.assertEqual(m.get("/api/crm/lidlar/").status_code, 200)
        self.assertEqual(m.get("/api/crm/hisoblar/").status_code, 403)
        # Owner — doim hammasi.
        self.assertEqual(self.mijoz(self.owner).get("/api/crm/hisoblar/").status_code, 200)


class ChegirmaVaQoldaTest(ApiAsos):
    """J-3: retro chegirma — faqat owner; owner tuzatgan hisob ustidan yozilmaydi."""

    def setUp(self):
        super().setUp()
        self.am = self.azolik_qosh(boshlanish=SENTABR)
        with bugun_qilib(date(2026, 9, 5)):
            mantiq.hisoblarni_generatsiya_qil()

    def chegirma(self, user, oy):
        with bugun_qilib(date(2026, 10, 5)):
            return self.mijoz(user).post(f"/api/crm/guruhlar/{self.guruh.id}/chegirmalar/", {
                "azolik_moliya_id": self.am.id, "narx": "0", "boshlanish_oy": oy, "oylar_soni": 0,
            }, format="json")

    def test_admin_otgan_oyga_chegirma_bera_olmaydi(self):
        self.assertEqual(self.chegirma(self.admin, "2026-09").status_code, 403)
        self.assertEqual(Hisob.objects.get(talaba=self.talaba, oy=SENTABR).summa, NARX)

    def test_owner_otgan_oyga_bera_oladi(self):
        self.assertEqual(self.chegirma(self.owner, "2026-09").status_code, 201)
        self.assertEqual(Hisob.objects.get(talaba=self.talaba, oy=SENTABR).summa, 0)

    def test_owner_tuzatgan_hisob_qayta_hisoblanmaydi(self):
        hisob = Hisob.objects.get(talaba=self.talaba, oy=SENTABR)
        javob = self.mijoz(self.owner).patch(f"/api/crm/hisoblar/{hisob.id}/", {
            "summa": "220000", "izoh": "Sentabrda 4 ta darsga keladi"}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        hisob.refresh_from_db()
        self.assertTrue(hisob.qolda)
        self.chegirma(self.owner, "2026-09")
        hisob.refresh_from_db()
        self.assertEqual(hisob.summa, Decimal("220000"))  # tuzatish saqlandi


class NolNarxTest(ApiAsos):
    def test_nol_narx_sozlanmagan_hisoblanadi(self):
        """P-4: tekin faqat chegirmada; kurs narxi 0 — sozlash xatosi."""
        KursNarxi.objects.filter(daraja=self.daraja).update(narx=0)
        from crm.models import AzolikMoliya

        am = AzolikMoliya.objects.get(pk=self.azolik_qosh(boshlanish=SENTABR).pk)  # keshsiz
        self.assertEqual(mantiq.hisob_yarat(am, SENTABR), mantiq.SOZLANMAGAN)


class MarketologGuruhlarTest(Yordamchi):
    def test_marketolog_guruh_royxatini_koradi_yarata_olmaydi(self):
        """O-1: lidni guruhga qo'shish uchun ro'yxat kerak."""
        m = self.mijoz(self.xodim("mark", lavozim="marketolog"))
        self.assertEqual(m.get("/api/crm/guruhlar/").status_code, 200)
        self.assertEqual(m.post("/api/crm/guruh-yaratish/", {"nomi": "X"}, format="json").status_code, 403)


class AmalRuxsatlariTest(Yordamchi):
    def test_faqat_qoshish_ruxsati_arxivlay_olmaydi(self):
        """P-6: amal kalitlari backendda ham tekshiriladi."""
        rol = CrmRol.objects.create(nomi="Faqat qo'shuvchi", ruxsatlar=["lidlar.qoshish"])
        m = self.mijoz(self.xodim("lq", rol=rol))
        lid = m.post("/api/crm/lidlar/", {"ism": "Laura", "telefon": "901112233"}, format="json")
        self.assertEqual(lid.status_code, 201, lid.data)
        self.assertEqual(m.patch(f"/api/crm/lidlar/{lid.data['id']}/", {"arxiv": True}, format="json").status_code, 403)
        self.assertEqual(m.patch(f"/api/crm/lidlar/{lid.data['id']}/", {"ism": "X"}, format="json").status_code, 403)
        self.assertFalse(Lid.objects.get(pk=lid.data["id"]).arxiv)
        # P-3: yaratish audit jurnaliga tushdi.
        self.assertTrue(FaoliyatYozuvi.objects.filter(obyekt_turi="CRM Lid", obyekt_id=lid.data["id"]).exists())

    def test_kassir_guruhni_tahrirlay_olmaydi(self):
        m = self.mijoz(self.xodim("k2", lavozim="kassir"))
        self.assertEqual(m.patch(f"/api/crm/guruhlar/{self.guruh.id}/moliya/", {"narx": "1"}, format="json").status_code, 403)


class ArxivTalabaTest(ApiAsos):
    def test_arxivdagi_talaba_filtrda_chiqadi(self):
        """O-3: arxivlangan talabaga CRM'dan qaytib bo'lsin."""
        m = self.mijoz(self.admin)
        self.assertEqual(m.patch(f"/api/crm/talaba/{self.talaba.id}/crm/", {"faol": False}, format="json").status_code, 200)
        self.assertNotIn(self.talaba.id, [x["id"] for x in m.get("/api/crm/talabalar/").data])
        self.assertIn(self.talaba.id, [x["id"] for x in m.get("/api/crm/talabalar/?arxiv=1").data])


class DarsKochirishTest(ApiAsos):
    """O-4: davomat/mavzu dars bilan ko'chadi; sana tekshiriladi."""

    def setUp(self):
        super().setUp()
        self.azolik_qosh(boshlanish=SENTABR)
        self.yol = f"/api/crm/guruhlar/{self.guruh.id}/dars-ozgarishlari/"

    def test_davomat_va_mavzu_kochadi_va_qaytadi(self):
        Davomat.objects.create(guruh=self.guruh, talaba=self.talaba, sana=date(2026, 9, 10), holat="keldi")
        DarsMavzusi.objects.create(guruh=self.guruh, sana=date(2026, 9, 10), mavzu="Present Simple")
        with bugun_qilib(date(2026, 9, 9)):
            javob = self.mijoz(self.admin).post(self.yol, {
                "turi": "kochirish", "asl_sana": "2026-09-10", "yangi_sana": "2026-09-14"}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertTrue(Davomat.objects.filter(guruh=self.guruh, sana=date(2026, 9, 14)).exists())
        self.assertFalse(Davomat.objects.filter(guruh=self.guruh, sana=date(2026, 9, 10)).exists())
        self.assertEqual(DarsMavzusi.objects.get(guruh=self.guruh).sana, date(2026, 9, 14))
        # Bekor qilinsa — asl sanaga qaytadi.
        self.assertEqual(self.mijoz(self.admin).delete(f"/api/crm/dars-ozgarishlari/{javob.data['id']}/").status_code, 204)
        self.assertTrue(Davomat.objects.filter(guruh=self.guruh, sana=date(2026, 9, 10)).exists())

    def test_sana_qoidalari(self):
        m = self.mijoz(self.admin)
        with bugun_qilib(date(2026, 9, 12)):
            # O'tgan kunga
            self.assertEqual(m.post(self.yol, {"turi": "kochirish", "asl_sana": "2026-09-17",
                                               "yangi_sana": "2026-09-08"}, format="json").status_code, 400)
            # Darsi bor kunga (18-sentabr — juma)
            self.assertEqual(m.post(self.yol, {"turi": "kochirish", "asl_sana": "2026-09-17",
                                               "yangi_sana": "2026-09-18"}, format="json").status_code, 400)
        GuruhMoliya.objects.filter(guruh=self.guruh).update(tugash_sana=date(2026, 9, 20))
        with bugun_qilib(date(2026, 9, 12)):
            # Guruh tugaganidan keyin
            self.assertEqual(m.post(self.yol, {"turi": "kochirish", "asl_sana": "2026-09-17",
                                               "yangi_sana": "2026-09-21"}, format="json").status_code, 400)


class TolovYaqinTest(ApiAsos):
    def test_tolovi_yaqin_sanaladi(self):
        """O-6: to'plam so'rov bilan hisoblangan natija eski mantiq bilan bir xil."""
        self.azolik_qosh(boshlanish=SENTABR)
        with bugun_qilib(date(2026, 9, 5)):
            mantiq.hisoblarni_generatsiya_qil()
        Hisob.objects.filter(talaba=self.talaba).update(holat=Hisob.Holat.TOLANDI)
        with bugun_qilib(date(2026, 9, 29)):
            javob = self.mijoz(self.admin).get("/api/crm/korsatkichlar/")
        self.assertEqual(javob.data["tolovi_yaqin"], 1)  # keyingisi 1-oktabr, 3 kun ichida
