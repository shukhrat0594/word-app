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
    AzolikMoliya, Chegirma, CrmRol, DarsOzgarish, Eslatma, Filial, GuruhMoliya, Hisob, KursNarxi, Lid, LidBolim,
    LidDoska, Tolov, XodimProfil, Xona,
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
    FILIALSIZ = {"rol_detail", "filial_detail", "xona_detail"}

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
            "lid_doska": LidDoska.objects.create(nomi="B doska", filial=self.fb).id,
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


def _excel_fayl(*qatorlar):
    import io

    import openpyxl

    kitob = openpyxl.Workbook()
    kitob.active.append(["ism", "telefon"])
    for q in qatorlar:
        kitob.active.append(list(q))
    fayl = io.BytesIO()
    kitob.save(fayl)
    fayl.seek(0)
    fayl.name = "t.xlsx"
    return fayl


class TanadagiIdTest(FilialAsos):
    """So'rov TANASIDAGI ID'lar (talaba_id, guruh_id, xona_id, Excel) —
    `IdBoyichaTest` faqat URL'dagi `pk`ni sinaydi. Tekshiruvda (2026-09-23)
    teshiklar aynan shu yerdan chiqdi."""

    def test_boshqa_filial_idlari_rad_etiladi(self):
        m = self.mijoz(self.admin_a)
        xb = Xona.objects.create(filial=self.fb, nomi="B-1")
        doska_b = LidDoska.objects.create(nomi="B doska", filial=self.fb)
        bolim_b = LidBolim.objects.create(nomi="B ustun", filial=self.fb)
        a = self.guruh.id
        jadval_b = [{"hafta_kuni": 0, "boshlanish_vaqti": "10:00", "tugash_vaqti": "11:00", "xona_id": xb.id}]
        holatlar = [
            ("post", "/api/crm/tolov/", {"talaba_id": self.tb.id, "guruh_id": a, "summa": "1000"}),
            ("post", "/api/crm/hisoblar/", {"talaba_id": self.tb.id, "guruh_id": a, "summa": "1000", "oy": "2026-09"}),
            ("post", f"/api/crm/guruhlar/{a}/talabalar/", {"talaba_id": self.tb.id}),
            ("put", f"/api/crm/guruhlar/{a}/jadval/", {"jadval": jadval_b}),
            ("post", "/api/crm/guruh-yaratish/", {"nomi": "Z", "boshlanish_sana": "2026-09-23", "jadval": jadval_b}),
            ("post", f"/api/crm/guruhlar/{a}/dars-ozgarishlari/", {
                "turi": "qoshimcha", "yangi_sana": "2026-09-28", "xona_id": xb.id}),
            ("post", "/api/crm/lid-bolimlar/", {"nomi": "X", "doska_id": doska_b.id}),
            ("post", "/api/crm/lid-bolimlar/", {"nomi": "X", "guruh_id": self.gb.id}),
            ("patch", f"/api/crm/lidlar/{self.lid_a.id}/", {"yigilayotgan_guruh_id": self.gb.id}),
            ("patch", f"/api/crm/lidlar/{self.lid_a.id}/", {"bolim_id": bolim_b.id}),
            ("post", "/api/crm/eslatmalar/", {"guruh_id": self.gb.id, "matn": "x"}),
            ("post", "/api/crm/lidlar/guruhga/", {"lid_id": self.lid_a.id, "guruh_id": self.gb.id}),
            ("post", "/api/crm/talaba-yaratish/", {"ism": "Y", "guruh_id": self.gb.id}),
            ("post", f"/api/crm/guruhlar/{a}/chegirmalar/", {"azolik_moliya_id": self.amb.id, "narx": "1"}),
            ("post", f"/api/crm/guruhlar/{a}/davomat/", {"talaba_id": self.tb.id, "sana": "2026-09-17",
                                                           "holat": "keldi"}),
        ]
        sonlar = (Tolov.objects.count(), Hisob.objects.count(), Guruh.objects.count(), LidBolim.objects.count())
        for usul, url, tana in holatlar:
            javob = getattr(m, usul)(url, tana, format="json")
            self.assertIn(javob.status_code, (400, 403, 404), f"{usul.upper()} {url} {tana}: {javob.data}")
        self.assertEqual(
            (Tolov.objects.count(), Hisob.objects.count(), Guruh.objects.count(), LidBolim.objects.count()), sonlar)
        self.assertFalse(GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.tb).exists())

    def test_excel_boshqa_filial_talabasini_tortmaydi(self):
        self.tb.telefon = "+998901112233"
        self.tb.save()
        javob = self.mijoz(self.admin_a).post(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/",
                                              {"excel_fayl": _excel_fayl(("X", "+998901112233"))},
                                              format="multipart")
        self.assertEqual(javob.data["qoshildi"], [])
        self.assertEqual(len(javob.data["xatolar"]), 1)
        self.assertFalse(GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.tb).exists())

    def test_guruhdan_chiqqan_qarzdorga_tolov_ochiq(self):
        """Guruhdan chiqqan, lekin qarzi qolgan talaba — hisobi bor, to'lov qabul qilinadi."""
        GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.talaba).delete()
        Hisob.objects.create(talaba=self.talaba, talaba_ism="T", guruh=self.guruh, guruh_nomi="A",
                             filial=self.filial, oy=SENTABR, summa=Decimal("1000"), holat=Hisob.Holat.QARZDOR)
        javob = self.mijoz(self.admin_a).post("/api/crm/tolov/", {
            "talaba_id": self.talaba.id, "guruh_id": self.guruh.id, "summa": "1000"}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)


class IkkiFilialliTalabaTest(FilialAsos):
    def setUp(self):
        super().setUp()
        GuruhAzoligi.objects.create(guruh=self.guruh, talaba=self.tb)

    def test_karta_boshqa_filial_tolovini_korsatmaydi_balans_umumiy_belgi_bilan(self):
        d = self.mijoz(self.admin_a).get(f"/api/crm/talaba/{self.tb.id}/").data
        self.assertNotIn(self.tolov_b.id, [t["id"] for t in d["tolovlar"]])
        self.assertEqual(d["balans_jami"], Decimal("-560000"))  # umumiy (qaror)
        self.assertTrue(d["boshqa_filialda"])
        self.assertFalse(self.mijoz(self.owner).get(f"/api/crm/talaba/{self.tb.id}/").data["boshqa_filialda"])

    def test_tarix_boshqa_filialni_korsatmaydi(self):
        d = self.mijoz(self.admin_a).get(f"/api/crm/talaba/{self.tb.id}/tarix/").data
        self.assertFalse(any("B guruh" in v["matn"] for v in d), d)

    def test_guruhi_ochgan_tolov_hisob_filiali_boyicha(self):
        t = Tolov.objects.create(talaba=self.tb, talaba_ism="B", guruh=None, guruh_nomi="O'chgan",
                                 hisob=self.hisob_b, sana=date(2026, 9, 6), summa=Decimal("7000"),
                                 turi=Tolov.Turi.TOLOV)
        self.assertNotIn(t.id, [x["id"] for x in self.mijoz(self.admin_a).get("/api/crm/tolov/").data])
        self.assertIn(t.id, [x["id"] for x in self.mijoz(self.admin_b).get("/api/crm/tolov/").data])

    def test_qidiruvda_boshqa_filial_guruhi_nomi_yoq(self):
        d = self.mijoz(self.admin_a).get("/api/crm/talaba-qidiruv/?q=talaba_b").data
        self.assertEqual(d[0]["guruhlar"], [self.guruh.name])

    def test_crm_yozuvisiz_azolik_royxatda_yoqolmaydi(self):
        """A'zolik saytda qo'shilgan (AzolikMoliya hali yo'q) — ro'yxatda baribir chiqadi."""
        ids = {x["id"] for x in self.mijoz(self.admin_a).get("/api/crm/talabalar/").data}
        self.assertIn(self.tb.id, ids)


class AzolikRuxsatlariTest(FilialAsos):
    def rolli(self, nomi, kalitlar):
        u = self.xodim(nomi, [self.filial], lavozim="kassir", role=User.Role.ODDIY)
        XodimProfil.objects.filter(user=u).update(rol=CrmRol.objects.create(nomi=nomi, ruxsatlar=kalitlar))
        return self.mijoz(u)

    def test_narx_va_holat(self):
        am = AzolikMoliya.objects.get(azolik__guruh=self.guruh, azolik__talaba=self.talaba)
        url = f"/api/crm/azoliklar/{am.id}/"
        dav = self.rolli("dav", ["guruhlar.davomat"])
        self.assertEqual(dav.patch(url, {"narx": "1000"}, format="json").status_code, 403)
        self.assertEqual(dav.patch(url, {"holat": "muzlatilgan"}, format="json").status_code, 403)
        qosh = self.rolli("qosh", ["guruhlar.talaba_qoshish"])
        self.assertEqual(qosh.patch(url, {"holat": "sinov"}, format="json").status_code, 200)
        self.assertEqual(qosh.patch(url, {"narx": "1000"}, format="json").status_code, 403)
        am.refresh_from_db()
        self.assertIsNone(am.narx)


class XodimQoidalariTest(FilialAsos):
    def test_ikki_filialli_xodimni_forma_orqali_tahrirlash(self):
        """Forma mavjud filiallarni (A+B) to'liq qaytaradi — bu 403 emas."""
        ikki = self.xodim("ikki_x", [self.filial, self.fb], lavozim="kassir", role=User.Role.ODDIY)
        javob = self.mijoz(self.admin_a).patch(f"/api/crm/xodimlar/{ikki.id}/", {
            "ism": "Yangi", "filial_idlar": [self.filial.id, self.fb.id]}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(sorted(javob.data["filial_idlar"]), sorted([self.filial.id, self.fb.id]))

    def test_xodim_qoshish_va_lavozim_faqat_owner_yoki_admin(self):
        kadr = self.xodim("kadr", [self.filial], lavozim="kassir", role=User.Role.ODDIY)
        XodimProfil.objects.filter(user=kadr).update(rol=CrmRol.objects.create(
            nomi="Kadrlar", ruxsatlar=["xodimlar.qoshish", "xodimlar.tahrirlash"]))
        m = self.mijoz(kadr)
        self.assertEqual(m.post("/api/crm/xodimlar/", {"ism": "S", "telefon": "901230009", "lavozim": "support",
                                                      "parol": "Qwerty12345!"}, format="json").status_code, 403)
        boshqa = self.xodim("boshqa_k", [self.filial], lavozim="kassir", role=User.Role.ODDIY)
        self.assertEqual(m.patch(f"/api/crm/xodimlar/{boshqa.id}/", {"lavozim": "oqituvchi"},
                                 format="json").status_code, 403)
        # Lavozimga tegmaydigan tahrir — mumkin.
        self.assertEqual(m.patch(f"/api/crm/xodimlar/{boshqa.id}/", {"ism": "Yangi", "lavozim": "kassir"},
                                 format="json").status_code, 200)
        # Administrator qo'sha oladi.
        self.assertEqual(self.mijoz(self.admin_a).post("/api/crm/xodimlar/", {
            "ism": "K", "telefon": "901230010", "lavozim": "kassir"}, format="json").status_code, 201)

    def test_admin_ozini_tahrirlaydi_lekin_huquqini_emas(self):
        m = self.mijoz(self.admin_a)
        url = f"/api/crm/xodimlar/{self.admin_a.id}/"
        javob = m.patch(url, {"telefon": "901234567", "lavozim": "admin", "filial_idlar": [self.filial.id],
                              "ishga_olingan_sana": ""}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        self.assertEqual(javob.data["telefon"], "901234567")
        self.assertEqual(m.patch(url, {"oylik": "9000000"}, format="json").status_code, 403)
        self.assertEqual(m.patch(url, {"filial_idlar": []}, format="json").status_code, 403)
        self.assertEqual(m.patch(url, {"faol": False}, format="json").status_code, 403)


class DoskaVaQoraRoyxatTest(FilialAsos):
    def test_doska_filiali(self):
        umumiy = LidDoska.objects.create(nomi="Umumiy")
        doska_b = LidDoska.objects.create(nomi="B doska", filial=self.fb)
        m = self.mijoz(self.admin_a)
        idlar = [d["id"] for d in m.get("/api/crm/lid-doskalar/").data["doskalar"]]
        self.assertIn(umumiy.id, idlar)
        self.assertNotIn(doska_b.id, idlar)
        # Umumiy doskani filial xodimi o'chirmaydi va o'zgartirmaydi.
        self.assertEqual(m.delete(f"/api/crm/lid-doskalar/{umumiy.id}/").status_code, 403)
        self.assertEqual(m.patch(f"/api/crm/lid-doskalar/{umumiy.id}/", {"nomi": "X"},
                                 format="json").status_code, 403)
        # Yangi doska va uning "NEW LEADS" ustuni — o'z filialida.
        javob = m.post("/api/crm/lid-doskalar/", {"nomi": "A doska"}, format="json")
        self.assertEqual(javob.status_code, 201, javob.data)
        self.assertEqual(javob.data["filial_id"], self.filial.id)
        self.assertEqual(LidBolim.objects.get(doska_id=javob.data["id"]).filial_id, self.filial.id)
        self.assertEqual(m.delete(f"/api/crm/lid-doskalar/{javob.data['id']}/").status_code, 204)
        # Filialsiz ustun ochilmaydi — filial o'zi qo'yiladi.
        javob = m.post("/api/crm/lid-bolimlar/", {"nomi": "Ustun"}, format="json")
        self.assertEqual(javob.data["filial_id"], self.filial.id)
        umumiy_ustun = LidBolim.objects.create(nomi="Hammaniki")
        self.assertEqual(m.delete(f"/api/crm/lid-bolimlar/{umumiy_ustun.id}/").status_code, 403)
        # Owner — umumiy doskani o'chira oladi.
        self.assertEqual(self.mijoz(self.owner).delete(f"/api/crm/lid-doskalar/{umumiy.id}/").status_code, 204)

    def test_qora_royxat_hamma_filialga_korinadi(self):
        """Shuhrat, 2026-09-23: qora ro'yxat — hamma filialga (faqat ko'rish)."""
        self.lid_b.qora_royxat = True
        self.lid_b.save()
        m = self.mijoz(self.admin_a)
        self.assertIn(self.lid_b.id, [x["id"] for x in m.get("/api/crm/lidlar/?qora_royxat=1").data])
        self.assertEqual(m.get("/api/crm/lid-doskalar/").data["qora_royxat"], 1)
        self.assertEqual(m.get(f"/api/crm/lidlar/{self.lid_b.id}/").status_code, 200)
        self.assertEqual(m.get(f"/api/crm/eslatmalar/?lid={self.lid_b.id}").status_code, 200)
        # O'zgartirish — yo'q.
        self.assertEqual(m.patch(f"/api/crm/lidlar/{self.lid_b.id}/", {"qora_royxat": False},
                                 format="json").status_code, 404)
        self.assertEqual(m.delete(f"/api/crm/lidlar/{self.lid_b.id}/").status_code, 404)
        # Qora ro'yxatda bo'lmagan lid boshqa filialga baribir yopiq.
        self.lid_b.qora_royxat = False
        self.lid_b.save()
        self.assertEqual(m.get(f"/api/crm/lidlar/{self.lid_b.id}/").status_code, 404)
        # Takrorlarda — faqat qora ro'yxatdagi boshqa filial lidi.
        self.lid_a.telefon = self.lid_b.telefon
        self.lid_a.save()
        self.assertEqual(m.get(f"/api/crm/lidlar/{self.lid_a.id}/").data["takrorlar"], [])
        self.lid_b.qora_royxat = True
        self.lid_b.save()
        takror = m.get(f"/api/crm/lidlar/{self.lid_a.id}/").data["takrorlar"]
        self.assertEqual([x["id"] for x in takror], [self.lid_b.id])


class MaydaTuzatishlarTest(FilialAsos):
    def test_notogri_id_500_emas(self):
        m = self.mijoz(self.admin_a)
        self.assertEqual(m.get("/api/crm/eslatmalar/?talaba=abc").status_code, 400)
        javob = m.post("/api/crm/xonalar/", {"nomi": "q", "filial_id": "abc"}, format="json")
        self.assertEqual(javob.data["detail"], "Filial noto'g'ri")

    def test_qolda_oyga_chegirma_ogohlantiradi(self):
        from unittest import mock

        from crm import mantiq
        from crm.tests import bugun_qilib

        am = AzolikMoliya.objects.get(azolik__guruh=self.guruh, azolik__talaba=self.talaba)
        with bugun_qilib(date(2026, 9, 10)), mock.patch("crm.boshqaruv.timezone.localdate",
                                                        return_value=date(2026, 9, 10)):
            mantiq.hisoblarni_generatsiya_qil()
            h = Hisob.objects.get(talaba=self.talaba, guruh=self.guruh, oy=SENTABR)
            o = self.mijoz(self.owner)
            o.patch(f"/api/crm/hisoblar/{h.id}/", {"summa": "400000"}, format="json")
            javob = o.post(f"/api/crm/guruhlar/{self.guruh.id}/chegirmalar/", {
                "azolik_moliya_id": am.id, "narx": "100000", "boshlanish_oy": "2026-09"}, format="json")
            self.assertEqual(javob.status_code, 201, javob.data)
            self.assertIn("2026-09", javob.data["ogohlantirish"])
            h.refresh_from_db()
            self.assertEqual(h.summa, Decimal("400000"))  # qaror: `qolda`ga tegilmaydi
            izoh = [x["izoh"] for x in o.get(f"/api/crm/tolov/?hisoblar=1&talaba={self.talaba.id}").data
                    if x["turi"] == "hisob"]
            self.assertEqual(izoh, ["Qo'lda belgilangan summa"])
            javob = o.delete(f"/api/crm/chegirmalar/{javob.data['id']}/")
            self.assertEqual(javob.status_code, 200)
            self.assertIn("2026-09", javob.data["ogohlantirish"])


class SorovlarSoniTest(FilialAsos):
    def test_xodimlar_davomati_n_plus_1_emas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        m = self.mijoz(self.admin_a)

        def soni():
            with CaptureQueriesContext(connection) as c:
                m.get("/api/crm/xodimlar/davomat/")
            return len(c.captured_queries)

        oldin = soni()
        for i in range(10):
            self.xodim(f"k{i}", [self.filial], lavozim="kassir", role=User.Role.ODDIY)
        self.assertLessEqual(soni() - oldin, 1)

    def test_ruxsatlar_keshlanadi(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from crm.ruxsatlar import ruxsatlar

        u = User.objects.get(pk=self.admin_a.pk)
        ruxsatlar(u)
        with CaptureQueriesContext(connection) as c:
            birinchi = ruxsatlar(u)
            birinchi.add("buzildi")
            self.assertNotIn("buzildi", ruxsatlar(u))
        self.assertEqual(len(c.captured_queries), 0)
