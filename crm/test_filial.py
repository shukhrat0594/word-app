"""Filial bo'yicha cheklov (2026-09-23, Shuhrat): xodimga filial(lar)
biriktirilsa — CRM'da faqat o'sha filiallar; owner (= CEO) va filialsiz
xodim — cheklovsiz; filiali yo'q ma'lumot hammaga ko'rinadi."""

from datetime import date
from decimal import Decimal

from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from academics.models import Guruh, GuruhAzoligi
from accounts.models import User
from crm import urls as crm_urls
from crm.models import (
    AzolikMoliya, Chegirma, DarsOzgarish, Eslatma, Filial, GuruhMoliya, Hisob, KursNarxi, Lid, LidBolim, Tolov,
    XodimProfil,
)
from crm.test_api import ApiAsos
from crm.tests import SENTABR


class FilialAsos(ApiAsos):
    """A filial — `self.filial` (asosiy guruh shu yerda); B — ikkinchi filial."""

    def setUp(self):
        super().setUp()
        self.azolik_qosh(boshlanish=SENTABR)
        self.fb = Filial.objects.create(markaz=self.markaz, nomi="Chilonzor")
        self.gb = Guruh.objects.create(name="B guruh", markaz=self.markaz, daraja=self.daraja)
        GuruhMoliya.objects.create(guruh=self.gb, filial=self.fb, boshlanish_sana=date(2026, 1, 1))
        self.tb = User.objects.create_user(username="talaba_b", password="x", role=User.Role.STUDENT)
        self.amb = AzolikMoliya.objects.create(
            azolik=GuruhAzoligi.objects.create(guruh=self.gb, talaba=self.tb), boshlanish_sana=SENTABR)
        # Hech qaysi guruhda yo'q talaba — hammaga ko'rinadi (qaror).
        self.tc = User.objects.create_user(username="talaba_c", password="x", role=User.Role.STUDENT,
                                           first_name="Guruhsiz")
        self.lid_a = Lid.objects.create(ism="Lid A", telefon="+998900000001", filial=self.filial)
        self.lid_b = Lid.objects.create(ism="Lid B", telefon="+998900000002", filial=self.fb)
        self.lid_umumiy = Lid.objects.create(ism="Lid umumiy", telefon="+998900000003")
        self.hisob_b = Hisob.objects.create(
            talaba=self.tb, talaba_ism="B", guruh=self.gb, guruh_nomi="B guruh", filial=self.fb,
            oy=SENTABR, summa=Decimal("660000"), holat=Hisob.Holat.QARZDOR)
        self.tolov_b = Tolov.objects.create(
            talaba=self.tb, talaba_ism="B", guruh=self.gb, guruh_nomi="B guruh", hisob=self.hisob_b,
            sana=date(2026, 9, 5), summa=Decimal("100000"), turi=Tolov.Turi.TOLOV)
        self.admin_a = self.xodim("admin_a", [self.filial])
        self.admin_b = self.xodim("admin_b", [self.fb])

    def xodim(self, username, filiallar, lavozim="admin", role=User.Role.ADMIN):
        u = User.objects.create_user(username=username, password="x", role=role, markaz=self.markaz)
        p = XodimProfil.objects.create(user=u, lavozim=lavozim)
        p.filiallar.set(filiallar)
        return u


class RoyxatlarTest(FilialAsos):
    def test_guruhlar_talabalar_lidlar(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual([g["id"] for g in m.get("/api/crm/guruhlar/").data], [self.guruh.id])
        talabalar = {x["id"] for x in m.get("/api/crm/talabalar/").data}
        self.assertIn(self.talaba.id, talabalar)
        self.assertIn(self.tc.id, talabalar)  # guruhsiz — hammaga
        self.assertNotIn(self.tb.id, talabalar)
        lidlar = {x["id"] for x in m.get("/api/crm/lidlar/").data}
        self.assertEqual(lidlar, {self.lid_a.id, self.lid_umumiy.id})

    def test_moliya_royxatlari(self):
        m = self.mijoz(self.admin_a)
        self.assertNotIn(self.hisob_b.id, [h["id"] for h in m.get("/api/crm/hisoblar/").data])
        self.assertNotIn(self.tolov_b.id, [t["id"] for t in m.get("/api/crm/tolov/").data])
        self.assertIn(self.tolov_b.id, [t["id"] for t in self.mijoz(self.admin_b).get("/api/crm/tolov/").data])

    def test_filtr_boshqa_filial_bilan_bosh(self):
        """`?filial=B` yuborilsa ham — bo'sh (cheklov filtr ustiga qo'yiladi)."""
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.get(f"/api/crm/guruhlar/?filial={self.fb.id}").data, [])

    def test_filiallar_royxati_va_korsatkichlar(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual([f["id"] for f in m.get("/api/crm/filiallar/").data], [self.filial.id])
        self.assertEqual(m.get("/api/crm/men/").data["filiallar"], [self.filial.id])
        self.assertEqual(m.get("/api/crm/korsatkichlar/").data["guruhlar"], 1)
        self.assertEqual(self.mijoz(self.owner).get("/api/crm/korsatkichlar/").data["guruhlar"], 2)

    def test_talaba_qidiruvi(self):
        topildi = {x["id"] for x in self.mijoz(self.admin_a).get("/api/crm/talaba-qidiruv/").data}
        self.assertNotIn(self.tb.id, topildi)
        self.assertIn(self.tc.id, topildi)


class CheklovsizlarTest(FilialAsos):
    def test_owner_hammasini_koradi(self):
        m = self.mijoz(self.owner)
        self.assertEqual(len(m.get("/api/crm/guruhlar/").data), 2)
        self.assertIsNone(m.get("/api/crm/men/").data["filiallar"])
        self.assertEqual(m.get(f"/api/crm/talaba/{self.tb.id}/").status_code, 200)

    def test_filialsiz_admin_hammasini_koradi(self):
        """Qaror: filial biriktirilmaguncha — hamma filial."""
        m = self.mijoz(self.admin)  # profili yo'q, saytda yaratilgan admin
        self.assertEqual(len(m.get("/api/crm/guruhlar/").data), 2)
        filialsiz = self.xodim("filialsiz", [])
        self.assertEqual(len(self.mijoz(filialsiz).get("/api/crm/guruhlar/").data), 2)

    def test_ikki_filialli_admin(self):
        m = self.mijoz(self.xodim("ikki", [self.filial, self.fb]))
        self.assertEqual(len(m.get("/api/crm/guruhlar/").data), 2)


class IdBoyichaTest(FilialAsos):
    """Boshqa filial yozuvi ID bo'yicha ham ochilmaydi — 404."""

    # `pk_turi` e'lon qilmasligi mumkin bo'lgan URL'lar — filialga bog'liq emas.
    FILIALSIZ = {"rol_detail", "lid_doska_detail", "filial_detail", "xona_detail"}

    def b_obyektlari(self):
        return {
            "guruh": self.gb.id,
            "talaba": self.tb.id,
            "lid": self.lid_b.id,
            "azolik": self.amb.id,
            "chegirma": Chegirma.objects.create(azolik=self.amb, narx=0, boshlanish_oy=SENTABR).id,
            "dars_ozgarish": DarsOzgarish.objects.create(
                guruh=self.gb, turi="qoshimcha", yangi_sana=date(2026, 9, 14)).id,
            "hisob": self.hisob_b.id,
            "tolov": self.tolov_b.id,
            "eslatma": Eslatma.objects.create(guruh=self.gb, matn="x").id,
            "lid_bolim": LidBolim.objects.create(nomi="B ustun", filial=self.fb).id,
            "xodim": self.xodim("kassir_b", [self.fb], lavozim="kassir", role=User.Role.ODDIY).id,
        }

    def test_har_bir_pk_url(self):
        obyektlar = self.b_obyektlari()
        m = self.mijoz(self.admin_a)
        tekshirildi = 0
        for p in crm_urls.urlpatterns:
            if "<int:pk>" not in str(p.pattern):
                continue
            view = p.callback.view_class
            turi = getattr(view, "pk_turi", None)
            if turi is None:
                self.assertIn(p.name, self.FILIALSIZ, f"{p.name}: `pk_turi` e'lon qilinmagan")
                continue
            url = reverse(f"crm:{p.name}", kwargs={"pk": obyektlar[turi]})
            for usul in ("get", "post", "put", "patch", "delete"):
                if hasattr(view, usul):
                    javob = getattr(m, usul)(url, {}, format="json")
                    # 404; `FaqatOwner` amallari (hisob/to'lov tuzatish) owner'dan boshqa
                    # HAMMAGA 403 — bu ham rad etish va yozuv borligini oshkor qilmaydi.
                    self.assertIn(javob.status_code, (403, 404) if getattr(view, "permission_classes", None)
                                  and "FaqatOwner" in str(view.permission_classes) else (404,),
                                  f"{usul.upper()} {url} ({p.name})")
                    tekshirildi += 1
        self.assertGreater(tekshirildi, 30)
        # O'z filiali — ochiladi.
        self.assertEqual(self.mijoz(self.admin_b).get(f"/api/crm/talaba/{self.tb.id}/").status_code, 200)

    def test_eslatmalar_royxati(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.get(f"/api/crm/eslatmalar/?guruh={self.gb.id}").status_code, 404)
        self.assertEqual(m.post("/api/crm/eslatmalar/", {"lid_id": self.lid_b.id, "matn": "x"},
                                format="json").status_code, 404)


class YaratishTest(FilialAsos):
    def test_guruh_filiali(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.post("/api/crm/guruh-yaratish/", {
            "nomi": "X", "boshlanish_sana": "2026-09-23", "filial_id": self.fb.id}, format="json").status_code, 403)
        javob = m.post("/api/crm/guruh-yaratish/", {"nomi": "Y", "boshlanish_sana": "2026-09-23"}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertEqual(Guruh.objects.get(pk=javob.data["id"]).moliya.filial_id, self.filial.id)

    def test_lid_filiali_ozi_qoyiladi(self):
        javob = self.mijoz(self.admin_a).post("/api/crm/lidlar/", {"ism": "Yangi", "telefon": "901234000"},
                                              format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertEqual(javob.data["filial_id"], self.filial.id)

    def test_markaz_sozlamalari_faqat_owner(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.put("/api/crm/kurs-narxlari/", {"daraja_id": self.daraja.id, "narx": "1"},
                               format="json").status_code, 403)
        self.assertEqual(KursNarxi.objects.get(daraja=self.daraja).narx, Decimal("660000"))
        self.assertEqual(m.post("/api/crm/filiallar/", {"nomi": "Yangi"}, format="json").status_code, 403)
        self.assertEqual(m.post("/api/crm/xonalar/", {"nomi": "9-xona", "filial_id": self.fb.id},
                                format="json").status_code, 403)
        self.assertEqual(m.post("/api/crm/xonalar/", {"nomi": "9-xona", "filial_id": self.filial.id},
                                format="json").status_code, 201)


class XodimFiliallariTest(FilialAsos):
    def test_owner_bir_nechta_filial_beradi_va_ceo_royxatda(self):
        o = self.mijoz(self.owner)
        javob = o.post("/api/crm/xodimlar/", {"ism": "K", "telefon": "901230001", "lavozim": "kassir",
                                              "filial_idlar": [self.filial.id, self.fb.id]}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertEqual(sorted(javob.data["filial_idlar"]), sorted([self.filial.id, self.fb.id]))
        royxat = o.get("/api/crm/xodimlar/").data
        self.assertEqual(royxat["soni"].get("ceo"), 1)
        ceo = [x for x in royxat["xodimlar"] if x["lavozim"] == "ceo"][0]
        self.assertTrue(ceo["owner"])
        # CEO lavozimi xodimga berilmaydi.
        self.assertEqual(o.post("/api/crm/xodimlar/", {"ism": "C", "telefon": "901230002", "lavozim": "ceo"},
                                format="json").status_code, 400)
        # Owner CRM'dan tahrirlanmaydi.
        self.assertEqual(o.patch(f"/api/crm/xodimlar/{self.owner.id}/", {"ism": "X"}, format="json").status_code, 404)

    def test_filial_admini_faqat_oz_filialini_beradi(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.post("/api/crm/xodimlar/", {"ism": "K", "telefon": "901230003", "lavozim": "kassir",
                                                       "filial_idlar": [self.fb.id]}, format="json").status_code, 403)
        javob = m.post("/api/crm/xodimlar/", {"ism": "K", "telefon": "901230004", "lavozim": "kassir"},
                       format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertEqual(javob.data["filial_idlar"], [self.filial.id])  # o'zi qo'yildi

    def test_tahrirda_boshqa_filial_saqlanadi_va_filialsiz_qoldirmaydi(self):
        ikki = self.xodim("ikki_f", [self.filial, self.fb], lavozim="kassir", role=User.Role.ODDIY)
        m = self.mijoz(self.admin_a)
        # A ni olib tashlaydi — B qoladi (admin A unga tegmaydi).
        javob = m.patch(f"/api/crm/xodimlar/{ikki.id}/", {"filial_idlar": []}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["filial_idlar"], [self.fb.id])
        # Faqat A dagi xodimni filialsiz qoldirib bo'lmaydi (u hamma filialni ko'rib qolardi).
        bitta = self.xodim("bitta_f", [self.filial], lavozim="kassir", role=User.Role.ODDIY)
        self.assertEqual(m.patch(f"/api/crm/xodimlar/{bitta.id}/", {"filial_idlar": []},
                                 format="json").status_code, 400)

    def test_xodimlar_royxati_filial_boyicha_oqituvchi_tanlovi_toliq(self):
        self.xodim("kassir_b2", [self.fb], lavozim="kassir", role=User.Role.ODDIY)
        m = self.mijoz(self.admin_a)
        ismlar = {x["username"] for x in m.get("/api/crm/xodimlar/").data["xodimlar"]}
        self.assertNotIn("kassir_b2", ismlar)
        self.assertNotIn("admin_b", ismlar)
        oqituvchi_b = self.xodim("oqit_b", [self.fb], lavozim="oqituvchi", role=User.Role.TEACHER)
        tanlov = {x["id"] for x in m.get("/api/crm/xodimlar/?lavozim=oqituvchi&tanlov=1").data["xodimlar"]}
        self.assertIn(oqituvchi_b.id, tanlov)


@override_settings(CRM_YOQILGAN=True)
class MigratsiyaTest(TransactionTestCase):
    """0009: eski bitta `filial` -> `filiallar`; CEO xodim -> Administrator."""

    def test_filial_kochadi_ceo_admin_boladi(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        executor.migrate([("crm", "0008_crm_xodim_sayt_menyusi")])
        eski = executor.loader.project_state([("crm", "0008_crm_xodim_sayt_menyusi")]).apps
        Markaz = eski.get_model("accounts", "Markaz")
        EskiUser = eski.get_model("accounts", "User")
        EskiFilial = eski.get_model("crm", "Filial")
        EskiProfil = eski.get_model("crm", "XodimProfil")
        f = EskiFilial.objects.create(markaz=Markaz.objects.create(name="M"), nomi="F")
        u = EskiUser.objects.create(username="eski_x", role="admin")
        EskiProfil.objects.create(user=u, lavozim="ceo", filial=f)

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
        p = XodimProfil.objects.get(user_id=u.id)
        self.assertEqual(list(p.filiallar.values_list("id", flat=True)), [f.id])
        self.assertEqual(p.lavozim, "admin")


class XodimJavobiYangiTest(FilialAsos):
    def test_tahrir_javobi_yangi_qiymatlarni_qaytaradi(self):
        """Avval javob so'rov boshida yuklangan (eski) profildan qurilardi."""
        javob = self.mijoz(self.owner).patch(f"/api/crm/xodimlar/{self.admin_a.id}/", {
            "oylik": "5000000", "ishga_olingan_sana": "2026-01-15"}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["oylik"], Decimal("5000000"))
        self.assertEqual(str(javob.data["ishga_olingan_sana"]), "2026-01-15")
