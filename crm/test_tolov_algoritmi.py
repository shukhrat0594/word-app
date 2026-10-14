"""TZ "To'lov algoritmi" (2026-10-14).

2026-yil oktabr, Dushanba/Chorshanba/Juma jadvali — 13 ta dars:
2, 5, 7, 9, 12, 14, 16, 19, 21, 23, 26, 28, 30. 14-oktabrdan — 8 ta.
"""

from datetime import date
from decimal import Decimal

from academics.models import Guruh, GuruhAzoligi
from accounts.models import User
from crm import mantiq
from crm.models import AzolikMoliya, DarsJadvali, GuruhdanChiqish, GuruhMoliya, Hisob, KursNarxi, Sozlama
from crm.tests import CrmAsos, bugun_qilib

OKTABR = date(2026, 10, 1)
NOYABR = date(2026, 11, 1)


class TolovAlgoritmiTest(CrmAsos):
    def setUp(self):
        super().setUp()
        KursNarxi.objects.filter(daraja=self.daraja).update(narx=Decimal("540000"))
        self.guruh.crm_jadval.all().delete()
        for kun in (DarsJadvali.HaftaKuni.DUSHANBA, DarsJadvali.HaftaKuni.CHORSHANBA, DarsJadvali.HaftaKuni.JUMA):
            DarsJadvali.objects.create(guruh=self.guruh, hafta_kuni=kun,
                                       boshlanish_vaqti="14:00", tugash_vaqti="15:30")
        Sozlama.objects.update(boshlangich_oy=OKTABR)

    def test_tz_misoli_yangi_talaba_12_ga_bolinadi(self):
        """540 000 / 12 * 8 = 360 000; noyabrdan to'liq."""
        self.azolik_qosh(boshlanish=date(2026, 10, 14))
        with bugun_qilib(date(2026, 11, 5)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(oy=OKTABR).summa, Decimal("360000"))
        self.assertEqual(Hisob.objects.get(oy=NOYABR).summa, Decimal("540000"))

    def test_12_va_undan_kop_dars_toliq_narx(self):
        """5-oktabrdan: 12 ta dars -> to'liq narx (13 ga bo'linmaydi)."""
        self.azolik_qosh(boshlanish=date(2026, 10, 5))
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(oy=OKTABR).summa, Decimal("540000"))

    def test_kochirilgan_talabaga_tasir_qilmaydi(self):
        """Avval boshqa guruhda o'qigan talaba — eski proporsional hisob
        (540 000 * 8 / 13 = 332 000)."""
        eski = Guruh.objects.create(name="Eski guruh", markaz=self.markaz, daraja=self.daraja)
        Hisob.objects.create(talaba=self.talaba, guruh=eski, oy=date(2026, 9, 1), talaba_ism="t",
                             guruh_nomi="Eski guruh", summa=Decimal("540000"))
        self.azolik_qosh(boshlanish=date(2026, 10, 14))
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(guruh=self.guruh, oy=OKTABR).summa, Decimal("332000"))

    def test_sinovdan_keyin_kochirilgan_yangi_talaba_12_ga_bolinadi(self):
        """Sinov darsi boshqa guruhda bo'lib, keyin bu guruhga ko'chirilgan
        talaba markazda hali o'qimagan (hisobi yo'q) — u ham yangi."""
        eski = Guruh.objects.create(name="Sinov guruhi", markaz=self.markaz, daraja=self.daraja)
        GuruhdanChiqish.objects.create(talaba=self.talaba, talaba_ism="t", guruh=eski, guruh_nomi="Sinov guruhi",
                                       sana=date(2026, 10, 10), sabab_turi=GuruhdanChiqish.SababTuri.KOCHIRILDI)
        self.azolik_qosh(boshlanish=date(2026, 10, 14))
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(guruh=self.guruh, oy=OKTABR).summa, Decimal("360000"))

    def test_individual_kurs_dars_soniga_kopaytiriladi(self):
        """1 dars 150 000, oktabrda 13 dars -> 1 950 000."""
        KursNarxi.objects.filter(daraja=self.daraja).update(narx=Decimal("150000"), dars_uchun=True)
        self.azolik_qosh(boshlanish=OKTABR)
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(oy=OKTABR).summa, Decimal("1950000"))

    def test_individual_kurs_oy_ortasida(self):
        """14-oktabrdan 8 dars -> 150 000 * 8."""
        KursNarxi.objects.filter(daraja=self.daraja).update(narx=Decimal("150000"), dars_uchun=True)
        self.azolik_qosh(boshlanish=date(2026, 10, 14))
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(oy=OKTABR).summa, Decimal("1200000"))

    def test_oyda_12_tadan_kam_dars_bolsa_birinchi_kun_toliq(self):
        """Haftada 2 kunlik guruh (oktabrda 9 dars): 1-sanada kelgan yangi
        talaba to'liq narx to'laydi — 9/12 emas."""
        self.guruh.crm_jadval.filter(hafta_kuni=DarsJadvali.HaftaKuni.JUMA).delete()
        self.azolik_qosh(boshlanish=OKTABR)
        with bugun_qilib(date(2026, 10, 20)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get(oy=OKTABR).summa, Decimal("540000"))
