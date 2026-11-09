"""2026-11-09 tahlilida topilgan pul xatolari — har biri uchun takrorlanmaslik testi.

Jadval: payshanba/juma/shanba, narx 660 000 (`crm.tests.CrmAsos`).
Darslar: sentabr 12, oktabr 15, noyabr 12 (5, 6, 7, 12, 13, 14, 19, 20, 21, 26, 27, 28), dekabr 13.
"""

from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from academics.models import Guruh, GuruhAzoligi
from accounts.models import User
from crm.models import AzolikMoliya, CrmRol, DarsJadvali, GuruhdanChiqish, GuruhMoliya, Hisob, Tolov, XodimProfil
from crm.test_api import ApiAsos
from crm.tests import NARX, bugun_qilib

SEN, OKT, NOY, DEK = date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1)
BUGUN = date(2026, 11, 9)


@override_settings(CRM_YOQILGAN=True)
class PulAsos(ApiAsos):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.c = APIClient()
        self.c.force_authenticate(self.owner)

    def och(self, sana=BUGUN):
        """CRM'ni shu kuni ochish (GET -> generatsiya)."""
        with bugun_qilib(sana):
            return self.c.get("/api/crm/hisoblar/")

    def summa(self, oy, guruh=None):
        return Hisob.objects.get(guruh=guruh or self.guruh, oy=oy).summa

    def ikkinchi_guruh(self):
        g = Guruh.objects.create(name="IELTS toq kun", markaz=self.markaz, daraja=self.daraja)
        GuruhMoliya.objects.create(guruh=g, filial=self.filial, boshlanish_sana=date(2026, 1, 1))
        for kun in (DarsJadvali.HaftaKuni.PAYSHANBA, DarsJadvali.HaftaKuni.JUMA, DarsJadvali.HaftaKuni.SHANBA):
            DarsJadvali.objects.create(guruh=g, hafta_kuni=kun, boshlanish_vaqti="16:00", tugash_vaqti="17:30")
        return g

    def xodim_mijozi(self):
        """Admin nomidan mijoz — foydalanuvchi BAZADAN qayta olinadi: ruxsatlar foydalanuvchi
        obyektida keshlanadi (haqiqiy so'rovda u har safar yangidan o'qiladi)."""
        c = APIClient()
        c.force_authenticate(User.objects.get(pk=self.admin.pk))
        return c

    def tolov(self, **qoshimcha):
        body = {"talaba_id": self.talaba.id, "guruh_id": self.guruh.id, "turi": "tolov", **qoshimcha}
        with bugun_qilib(BUGUN):
            return self.c.post("/api/crm/tolov/", body, format="json")


class ChiqarishTest(PulAsos):
    def test_otgan_sana_bilan_chiqarilsa_keyingi_oy_qarz_bolib_qolmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        with bugun_qilib(BUGUN):
            r = self.c.delete(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/?talaba={self.talaba.id}"
                              "&sana=2026-10-20&sabab_turi=boshqa")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.summa(SEN), NARX)                    # o'tgan oyga tegilmaydi
        self.assertEqual(self.summa(OKT), Decimal("396000"))       # 15 darsdan 9 tasi
        noyabr = Hisob.objects.get(oy=NOY)
        self.assertEqual((noyabr.summa, noyabr.holat), (Decimal("0"), Hisob.Holat.TOLANDI))

    def test_tolangan_keyingi_oyga_tegilmaydi(self):
        """TZ 4.6: pul kelgan oy avtomatik kamaymaydi — qaytarish alohida amal."""
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.assertEqual(self.tolov(hisob_id=Hisob.objects.get(oy=NOY).id, summa="660000").status_code, 201)
        with bugun_qilib(BUGUN):
            self.c.delete(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/?talaba={self.talaba.id}"
                          "&sana=2026-10-20&sabab_turi=boshqa")
        self.assertEqual(self.summa(NOY), NARX)

    def test_oy_boshida_kochirilsa_ikki_guruhda_toliq_oy_bolmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        yangi = self.ikkinchi_guruh()
        self.och()
        with bugun_qilib(BUGUN):
            r = self.c.post(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/amal/",
                            {"amal": "kochirish", "talaba_id": self.talaba.id, "sana": "2026-11-01",
                             "yangi_guruh_id": yangi.id}, format="json")
        self.assertEqual(r.status_code, 200)
        self.och()
        self.assertEqual(self.summa(NOY), Decimal("0"))
        self.assertEqual(self.summa(NOY, yangi), NARX)

    def test_oy_ortasida_kochirish_avvalgidek_bolinadi(self):
        self.azolik_qosh(boshlanish=SEN)
        yangi = self.ikkinchi_guruh()
        self.och()
        with bugun_qilib(BUGUN):
            self.c.post(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/amal/",
                        {"amal": "kochirish", "talaba_id": self.talaba.id, "sana": "2026-11-09",
                         "yangi_guruh_id": yangi.id}, format="json")
        self.och()
        self.assertEqual(self.summa(NOY) + self.summa(NOY, yangi), NARX)

    def test_saytdan_olib_tashlansa_hisob_qayta_hisoblanadi(self):
        """Saytdagi Guruhlar sahifasi (`PATCH /api/guruhlar/<id>/`) ham CRM qoidasi bilan."""
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        with bugun_qilib(BUGUN):
            r = self.c.patch(f"/api/guruhlar/{self.guruh.id}/", {"talaba_idlar": []}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(GuruhAzoligi.objects.exists())
        self.assertEqual(self.summa(NOY), Decimal("165000"))       # 9-noyabrgacha 3 dars
        self.assertEqual(GuruhdanChiqish.objects.count(), 1)

    @override_settings(CRM_YOQILGAN=False)
    def test_crm_ochiq_bolmasa_sayt_avvalgidek_ochiradi(self):
        self.azolik_qosh(boshlanish=SEN)
        r = self.c.patch(f"/api/guruhlar/{self.guruh.id}/", {"talaba_idlar": []}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(GuruhAzoligi.objects.exists())
        self.assertEqual(GuruhdanChiqish.objects.count(), 0)


class MuzlatishTest(PulAsos):
    def muzlat(self, am, sana="2026-11-09", bugun=BUGUN):
        with bugun_qilib(bugun):
            # Interfeys aynan shu maydonlarni yuboradi (`OquvchiAmallari.jsx`).
            return self.c.patch(f"/api/crm/azoliklar/{am.id}/",
                                {"holat": "muzlatilgan", "muzlatish_sana": sana, "muzlatish_izoh": "kasal"},
                                format="json")

    def test_muzlatilsa_oy_muzlatish_sanasigacha_hisoblanadi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.assertEqual(self.muzlat(am).status_code, 200)
        self.assertEqual(self.summa(NOY), Decimal("165000"))       # 5, 6, 7-noyabr
        self.assertEqual(self.summa(OKT), NARX)

    def test_shu_oyda_qaytsa_keyingi_darslar_qoshiladi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.muzlat(am)
        with bugun_qilib(date(2026, 11, 23)):
            r = self.c.patch(f"/api/crm/azoliklar/{am.id}/", {"holat": "faol"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["muzlatish_sana"])                # tashqariga avvalgidek chiqmaydi
        self.och(date(2026, 11, 23))
        hisob = Hisob.objects.get(oy=NOY)
        self.assertEqual((hisob.summa, hisob.darslar_talaba), (Decimal("330000"), 6))   # 3 + 26, 27, 28

    def test_keyingi_oyda_qaytsa_muzlagan_kunlar_hisoblanmaydi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.muzlat(am)
        with bugun_qilib(date(2026, 12, 10)):
            self.c.patch(f"/api/crm/azoliklar/{am.id}/", {"holat": "faol"}, format="json")
        self.och(date(2026, 12, 10))
        self.assertEqual(self.summa(NOY), Decimal("165000"))
        dekabr = Hisob.objects.get(oy=DEK)
        self.assertEqual(dekabr.darslar_talaba, 10)                # 10-dekabrdan: 13 darsdan 10 tasi
        self.assertLess(dekabr.summa, NARX)

    def test_tolangan_oy_muzlatilganda_ozgarmaydi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.tolov(hisob_id=Hisob.objects.get(oy=NOY).id, summa="660000")
        self.muzlat(am)
        self.assertEqual(self.summa(NOY), NARX)


class ArxivdanQaytishTest(PulAsos):
    def test_arxivda_turgan_oylarga_hisob_ochilmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och(date(2026, 9, 15))
        Guruh.objects.filter(pk=self.guruh.pk).update(faol=False)
        self.och(date(2026, 10, 15))
        self.och(date(2026, 11, 15))
        self.assertEqual(Hisob.objects.count(), 1)
        with bugun_qilib(date(2026, 12, 10)):
            r = self.c.patch(f"/api/crm/guruhlar/{self.guruh.id}/boshqaruv/", {"faol": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.och(date(2026, 12, 10))
        self.assertEqual(sorted(Hisob.objects.values_list("oy", flat=True)), [SEN, DEK])
        self.assertEqual(Hisob.objects.get(oy=DEK).darslar_talaba, 10)

    def test_saytdan_qaytarilsa_ham_shunday(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och(date(2026, 9, 15))
        Guruh.objects.filter(pk=self.guruh.pk).update(faol=False)
        with bugun_qilib(date(2026, 12, 10)):
            r = self.c.patch(f"/api/guruhlar/{self.guruh.id}/", {"faol": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.och(date(2026, 12, 10))
        self.assertEqual(sorted(Hisob.objects.values_list("oy", flat=True)), [SEN, DEK])

    def test_shu_oyda_arxivlanib_qaytgan_guruh_ozgarmaydi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och(date(2026, 9, 15))
        Guruh.objects.filter(pk=self.guruh.pk).update(faol=False)
        with bugun_qilib(date(2026, 9, 25)):
            self.c.patch(f"/api/crm/guruhlar/{self.guruh.id}/boshqaruv/", {"faol": True}, format="json")
        am.refresh_from_db()
        self.assertIsNone(am.qayta_faol_sana)
        self.assertEqual(self.summa(SEN), NARX)


class BoshlanishSanasiTest(PulAsos):
    def test_sana_tuzatilsa_ochilgan_oy_qayta_hisoblanadi(self):
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        with bugun_qilib(BUGUN):
            r = self.c.patch(f"/api/crm/azoliklar/{am.id}/", {"boshlanish_sana": "2026-11-19"}, format="json")
        self.assertEqual(r.status_code, 200)
        hisob = Hisob.objects.get(oy=NOY)
        self.assertEqual((hisob.summa, hisob.darslar_talaba), (Decimal("330000"), 6))
        # Endi boshlanmagan oylar 0 ga tushadi (talaba u paytda hali kelmagan).
        self.assertEqual(self.summa(OKT), Decimal("0"))


class TolovYozishTest(PulAsos):
    def test_ochirilgan_guruh_qarzini_tolab_boladi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        noyabr = Hisob.objects.get(oy=NOY)
        self.guruh.delete()
        noyabr.refresh_from_db()
        self.assertIsNone(noyabr.guruh_id)
        # Interfeys `guruh_id: hisob.guruh_id` yuboradi — o'chirilgan guruhda u null.
        r = self.tolov(guruh_id=None, hisob_id=noyabr.id, summa="660000")
        self.assertEqual(r.status_code, 201, r.data)
        noyabr.refresh_from_db()
        self.assertEqual(noyabr.holat, Hisob.Holat.TOLANDI)
        self.assertEqual(Tolov.objects.get().guruh_nomi, "IELTS juft kun")

    def test_guruhsiz_tolov_boshqa_hisobga_otmaydi(self):
        """Guruhi bor hisobga `guruh_id`siz to'lov yozib bo'lmaydi."""
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        r = self.tolov(guruh_id=None, hisob_id=Hisob.objects.get(oy=NOY).id, summa="1000")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Tolov.objects.count(), 0)

    def test_bir_xil_kalitli_sorov_ikkinchi_tolov_yozmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        hisob = Hisob.objects.get(oy=NOY)
        r1 = self.tolov(hisob_id=hisob.id, summa="300000", sorov_kaliti="oyna-1-tolov")
        r2 = self.tolov(hisob_id=hisob.id, summa="300000", sorov_kaliti="oyna-1-tolov")
        self.assertEqual((r1.status_code, r2.status_code), (201, 201))
        self.assertEqual(r1.data["id"], r2.data["id"])
        self.assertEqual(Tolov.objects.count(), 1)
        # Boshqa kalit — alohida to'lov; kalitsiz so'rov (eski frontend) ham avvalgidek.
        self.tolov(hisob_id=hisob.id, summa="300000", sorov_kaliti="oyna-2-tolov")
        self.tolov(hisob_id=hisob.id, summa="1000")
        self.tolov(hisob_id=hisob.id, summa="1000")
        self.assertEqual(Tolov.objects.count(), 4)

    def test_xato_bilan_tugagan_sorov_kalitni_band_qilmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        hisob = Hisob.objects.get(oy=NOY)
        self.assertEqual(self.tolov(hisob_id=hisob.id, summa="0", sorov_kaliti="k").status_code, 400)
        self.assertEqual(self.tolov(hisob_id=hisob.id, summa="5000", sorov_kaliti="k").status_code, 201)

    def test_qaytarishni_tahrirlash_qaytarish_ruxsatini_talab_qiladi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.och()
        self.tolov(hisob_id=Hisob.objects.get(oy=NOY).id, summa="660000")
        self.tolov(summa="100000", turi="qaytarish")
        qaytarish = Tolov.objects.get(turi="qaytarish")
        rol = CrmRol.objects.create(nomi="SINOV tahrirchi", ruxsatlar=["moliya.tolov", "moliya.tolov_tahrirlash"])
        XodimProfil.objects.create(user=self.admin, lavozim="kassir", rol=rol)
        r = self.xodim_mijozi().patch(f"/api/crm/tolov/{qaytarish.id}/", {"summa": "1"}, format="json")
        self.assertEqual(r.status_code, 403)
        rol.ruxsatlar = ["moliya.tolov", "moliya.tolov_tahrirlash", "moliya.qaytarish"]
        rol.save()
        r = self.xodim_mijozi().patch(f"/api/crm/tolov/{qaytarish.id}/", {"summa": "90000"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_raqam_orniga_matn_500_bermaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        self.assertEqual(self.c.get("/api/crm/hisoblar/?guruh=abc").status_code, 400)
        self.assertEqual(self.tolov(talaba_id="abc", summa="1000").status_code, 400)


class HisobotTest(PulAsos):
    def test_ortiqcha_tolovdan_keyingi_oy_qarz_korinmaydi(self):
        self.azolik_qosh(boshlanish=SEN)
        bugun = date(2026, 10, 10)
        self.och(bugun)
        with bugun_qilib(bugun):
            self.c.post("/api/crm/tolov/", {"talaba_id": self.talaba.id, "guruh_id": self.guruh.id,
                                            "hisob_id": Hisob.objects.get(oy=SEN).id, "summa": "1320000",
                                            "turi": "tolov"}, format="json")
            hisobot = self.c.get("/api/crm/hisobot/?oy=2026-10").data["jami"]
            bosh = self.c.get("/api/crm/korsatkichlar/").data
        self.assertEqual(hisobot["qarz"], 0)
        self.assertEqual((bosh["qolgan_qarz"], bosh["jami_qarz"], bosh["qarzdorlar"]), (0, 0, 0))

    def test_haqiqiy_qarz_avvalgidek_korinadi(self):
        self.azolik_qosh(boshlanish=SEN)
        bugun = date(2026, 10, 10)
        self.och(bugun)
        with bugun_qilib(bugun):
            hisobot = self.c.get("/api/crm/hisobot/?oy=2026-10").data["jami"]
        self.assertEqual(hisobot["qarz"], NARX)

    def test_qaytarilgan_pul_hisobotda_korinadi(self):
        self.azolik_qosh(boshlanish=SEN)
        bugun = date(2026, 9, 20)
        self.och(bugun)
        with bugun_qilib(bugun):
            for body in ({"hisob_id": Hisob.objects.get(oy=SEN).id, "summa": "660000", "turi": "tolov"},
                         {"summa": "100000", "turi": "qaytarish"}):
                self.c.post("/api/crm/tolov/", {"talaba_id": self.talaba.id, "guruh_id": self.guruh.id, **body},
                            format="json")
            umumiy = self.c.get("/api/crm/hisobot/").data["jami"]
            sentabr = self.c.get("/api/crm/hisobot/?oy=2026-09").data["jami"]
            oktabr = self.c.get("/api/crm/hisobot/?oy=2026-10").data["jami"]
        self.assertEqual((umumiy["olingan"], umumiy["qaytarilgan"]), (NARX, Decimal("100000")))
        self.assertEqual(sentabr["qaytarilgan"], Decimal("100000"))
        self.assertEqual(oktabr["qaytarilgan"], 0)                 # qaytarish o'z sanasi oyida

    def test_moliyaviy_hisobot_oz_ruxsatini_talab_qiladi(self):
        """Hisobotlar bo'limining boshqa ruxsati (faqat lidlar) pul raqamlarini ochmaydi."""
        rol = CrmRol.objects.create(nomi="SINOV lid hisoboti", ruxsatlar=["hisobotlar.lidlar"])
        XodimProfil.objects.create(user=self.admin, lavozim="marketolog", rol=rol)
        xodim = self.xodim_mijozi()
        self.assertEqual(xodim.get("/api/crm/hisobot/").status_code, 403)
        self.assertEqual(xodim.get("/api/crm/hisobot/eksport/?turi=lidlar").status_code, 403)
        rol.ruxsatlar = ["hisobotlar.lidlar", "hisobotlar.excel", "bosh_sahifa.moliya"]
        rol.save()
        xodim = self.xodim_mijozi()
        self.assertEqual(xodim.get("/api/crm/hisobot/").status_code, 200)
        self.assertEqual(xodim.get("/api/crm/hisobot/eksport/?turi=lidlar").status_code, 200)


class MoslashQoidalariTest(PulAsos):
    def test_kunlari_ozgarmagan_oy_bugungi_narx_bilan_qayta_yozilmaydi(self):
        """Guruh narxi keyin o'zgargan bo'lsa ham, o'tgan oylar eski summada qoladi."""
        am = self.azolik_qosh(boshlanish=SEN)
        self.och()
        GuruhMoliya.objects.filter(guruh=self.guruh).update(narx=Decimal("800000"))
        am = AzolikMoliya.objects.get(pk=am.pk)
        with bugun_qilib(BUGUN):
            self.c.delete(f"/api/crm/guruhlar/{self.guruh.id}/talabalar/?talaba={self.talaba.id}"
                          "&sana=2026-11-09&sabab_turi=boshqa")
        self.assertEqual(self.summa(SEN), NARX)
        self.assertEqual(self.summa(OKT), NARX)
        self.assertEqual(Hisob.objects.get(oy=NOY).darslar_talaba, 3)
