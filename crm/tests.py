"""CRM moliya testlari.

Sinov oyi ATAYLAB qat'iy tanlangan — 2026-yil sentabr:
u seshanbadan boshlanadi, 30 kun. Payshanba/juma/shanba jadvali bilan
aynan 12 ta dars kuni chiqadi:

    3, 4, 5, 10, 11, 12, 17, 18, 19, 24, 25, 26

660 000 so'm narxda har bir dars kuni 55 000 so'mga to'g'ri keladi, ya'ni
proporsional summalarni qo'lda sanab tekshirish oson.
"""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.db.models import Sum
from django.test import TestCase, override_settings

from academics.models import Guruh, GuruhAzoligi
from accounts.models import Markaz, User
from courses.models import KursTugun
from crm import mantiq
from crm.models import (
    AzolikMoliya,
    DarsJadvali,
    Filial,
    GuruhMoliya,
    Hisob,
    KursNarxi,
    Sozlama,
    Tolov,
)

SENTABR = date(2026, 9, 1)
AVGUST = date(2026, 8, 1)
NARX = Decimal("660000")


def bugun_qilib(sana):
    """`timezone.localdate()`ni qat'iy sanaga qotiradi.

    Generatsiya "joriy oy"ga tayanadi, shuning uchun testda vaqtni
    boshqarmasdan turib quvib yetish mantig'ini tekshirib bo'lmaydi.
    """
    return mock.patch("crm.mantiq.timezone.localdate", return_value=sana)


# CRM bayrog'i testlarda MAJBURAN yoqiladi: `settings.CRM_YOQILGAN`
# standart qiymati `DEBUG`ga bog'langan, test ishga tushganda esa
# `DEBUG=False` — ya'ni bayroqsiz barcha API testlari 404 olardi.
# Bayroqning O'ZI alohida sinaladi (`BayroqTest`).
@override_settings(CRM_YOQILGAN=True)
class CrmAsos(TestCase):
    """Umumiy sozlama: bitta guruh, bitta talaba, payshanba/juma/shanba."""

    def setUp(self):
        self.markaz = Markaz.objects.create(name="Utmost Academy")
        self.filial = Filial.objects.create(markaz=self.markaz, nomi="Gor-Park")

        ildiz = KursTugun.objects.create(markaz=self.markaz, nomi="Ingliz tili")
        self.daraja = KursTugun.objects.create(
            markaz=self.markaz, nomi="IELTS", parent=ildiz
        )
        KursNarxi.objects.create(daraja=self.daraja, narx=NARX)

        self.talaba = User.objects.create_user(
            username="talaba1", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        self.guruh = Guruh.objects.create(
            name="IELTS juft kun", markaz=self.markaz, daraja=self.daraja
        )
        GuruhMoliya.objects.create(
            guruh=self.guruh, filial=self.filial, boshlanish_sana=date(2026, 1, 1)
        )
        for kun in (
            DarsJadvali.HaftaKuni.PAYSHANBA,
            DarsJadvali.HaftaKuni.JUMA,
            DarsJadvali.HaftaKuni.SHANBA,
        ):
            DarsJadvali.objects.create(
                guruh=self.guruh,
                hafta_kuni=kun,
                boshlanish_vaqti="14:00",
                tugash_vaqti="15:30",
            )

        Sozlama.objects.create(boshlangich_oy=SENTABR)

    def azolik_qosh(self, talaba=None, boshlanish=SENTABR, **kwargs):
        azolik = GuruhAzoligi.objects.create(
            guruh=self.guruh, talaba=talaba or self.talaba
        )
        return AzolikMoliya.objects.create(
            azolik=azolik, boshlanish_sana=boshlanish, **kwargs
        )


class DarsKunlariTest(CrmAsos):
    def test_sentabrda_12_ta_dars_kuni(self):
        kunlar = mantiq.oylik_dars_kunlari(self.guruh, SENTABR)
        self.assertEqual(len(kunlar), 12)
        self.assertEqual(kunlar[0], date(2026, 9, 3))
        self.assertEqual(kunlar[-1], date(2026, 9, 26))

    def test_bir_kunda_ikki_dars_kun_bir_marta_sanaladi(self):
        """Narx oylik — dars soatiga bog'liq emas."""
        DarsJadvali.objects.create(
            guruh=self.guruh,
            hafta_kuni=DarsJadvali.HaftaKuni.PAYSHANBA,
            boshlanish_vaqti="18:00",
            tugash_vaqti="19:30",
        )
        self.assertEqual(len(mantiq.oylik_dars_kunlari(self.guruh, SENTABR)), 12)


class ProporsionalTest(CrmAsos):
    def test_toliq_oy_toliq_narx(self):
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()

        hisob = Hisob.objects.get(oy=SENTABR)
        self.assertEqual(hisob.summa, NARX)
        self.assertFalse(hisob.proporsional)
        self.assertEqual(hisob.darslar_jami, 12)
        self.assertEqual(hisob.darslar_talaba, 12)

    def test_talaba_oy_ortasida_qoshildi(self):
        """17-sentabrdan boshlagan talaba: 12 darsdan 6 tasi -> yarim narx."""
        self.azolik_qosh(boshlanish=date(2026, 9, 17))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()

        hisob = Hisob.objects.get(oy=SENTABR)
        self.assertEqual(hisob.summa, Decimal("330000"))
        self.assertTrue(hisob.proporsional)
        self.assertEqual(hisob.darslar_talaba, 6)

    def test_guruh_oy_ortasida_ochildi(self):
        """Avvalgi TZ'dagi XATO: maxraj ham guruh oynasiga qisqarib,
        nisbat 1 chiqardi va to'liq narx yozilardi."""
        self.guruh.moliya.boshlanish_sana = date(2026, 9, 17)
        self.guruh.moliya.save()
        self.azolik_qosh(boshlanish=date(2026, 9, 1))

        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()

        hisob = Hisob.objects.get(oy=SENTABR)
        self.assertEqual(hisob.summa, Decimal("330000"))
        self.assertEqual(hisob.darslar_jami, 12)
        self.assertEqual(hisob.darslar_talaba, 6)


class GeneratsiyaTest(CrmAsos):
    def test_idempotent(self):
        self.azolik_qosh()
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
            mantiq.hisoblarni_generatsiya_qil()
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 1)

    def test_qoldirilgan_oylar_quvib_yetiladi(self):
        """Admin CRM'ni 2 oy ochmasa, oradagi oylar ham ochilishi kerak —
        aks holda o'sha oylarning qarzi umuman yaratilmay qolardi."""
        Sozlama.objects.update(boshlangich_oy=date(2026, 7, 1))
        self.azolik_qosh(boshlanish=date(2026, 7, 1))

        with bugun_qilib(date(2026, 9, 15)):
            mantiq.hisoblarni_generatsiya_qil()

        self.assertEqual(Hisob.objects.count(), 3)
        self.assertEqual(
            sorted(Hisob.objects.values_list("oy", flat=True)),
            [date(2026, 7, 1), AVGUST, SENTABR],
        )

    def test_oy_ortasida_qoshilgan_talaba_osha_oy_hisobini_oladi(self):
        """ENG MUHIM TEST — avvalgi rejadagi pul yo'qotadigan xato.

        Umumiy oy watermark'i bilan: 1-sentabrda generatsiya ishlagach oy
        "bajarilgan" bo'lib qolardi va 15-sentabrda qo'shilgan talabaga
        sentabr hisobi UMUMAN ochilmasdi — u oyni bepul o'qirdi."""
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 1)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 1)

        kechikkan = User.objects.create_user(
            username="kechikkan", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        self.azolik_qosh(talaba=kechikkan, boshlanish=date(2026, 9, 17))

        with bugun_qilib(date(2026, 9, 17)):
            mantiq.hisoblarni_generatsiya_qil()

        self.assertEqual(Hisob.objects.filter(talaba=kechikkan).count(), 1)
        self.assertEqual(
            Hisob.objects.get(talaba=kechikkan).summa, Decimal("330000")
        )

    def test_narx_oy_ortasida_kiritilsa_hisob_ochiladi(self):
        """Narxsiz guruhda watermark SURILMASLIGI kerak — aks holda narx
        kiritilgandan keyin ham o'sha oy abadiy o'tkazib yuborilardi."""
        KursNarxi.objects.all().delete()
        azolik_moliya = self.azolik_qosh()

        with bugun_qilib(date(2026, 9, 5)):
            natija = mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 0)
        self.assertEqual(natija["sozlanmagan"], 1)
        azolik_moliya.refresh_from_db()
        self.assertIsNone(azolik_moliya.oxirgi_hisob_oy)

        KursNarxi.objects.create(daraja=self.daraja, narx=NARX)
        with bugun_qilib(date(2026, 9, 20)):
            mantiq.hisoblarni_generatsiya_qil()

        self.assertEqual(Hisob.objects.filter(oy=SENTABR).count(), 1)

    def test_jadvalsiz_guruhga_hisob_ochilmaydi(self):
        DarsJadvali.objects.all().delete()
        self.azolik_qosh()
        with bugun_qilib(date(2026, 9, 30)):
            natija = mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 0)
        self.assertEqual(natija["sozlanmagan"], 1)

    def test_sinov_va_muzlatilganga_hisob_ochilmaydi(self):
        sinovchi = User.objects.create_user(
            username="sinovchi", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        muzlatilgan = User.objects.create_user(
            username="muzlatilgan", password="x", role=User.Role.STUDENT, markaz=self.markaz
        )
        self.azolik_qosh(talaba=sinovchi, holat=AzolikMoliya.Holat.SINOV)
        self.azolik_qosh(talaba=muzlatilgan, holat=AzolikMoliya.Holat.MUZLATILGAN)
        self.azolik_qosh()

        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()

        self.assertEqual(Hisob.objects.count(), 1)
        self.assertEqual(Hisob.objects.get().talaba, self.talaba)

    def test_arxivlangan_guruhga_hisob_ochilmaydi(self):
        self.azolik_qosh()
        self.guruh.faol = False
        self.guruh.save()
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 0)

    def test_tizim_yoqilgandan_oldingi_oylar_ochilmaydi(self):
        self.azolik_qosh(boshlanish=date(2026, 1, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.count(), 1)
        self.assertEqual(Hisob.objects.get().oy, SENTABR)


class NarxQavatlariTest(CrmAsos):
    """Narx uch qavati. Har tekshiruvdan oldin obyekt BAZADAN qayta
    o'qiladi: Django bog'langan obyektlarni xotirada keshlaydi, testda esa
    o'sha kesh eskirib qolib, tekshiruv yolg'on natija berardi. Haqiqiy
    so'rovda bunday muammo yo'q — generatsiya har safar yangi obyekt
    oladi."""

    def yangilab_ol(self, azolik_moliya):
        return AzolikMoliya.objects.select_related(
            "azolik__guruh__daraja", "azolik__guruh__moliya"
        ).get(pk=azolik_moliya.pk)

    def test_uch_qavat(self):
        azolik_moliya = self.azolik_qosh()

        # 1-qavat: kurs (daraja) narxi
        self.assertEqual(mantiq.amaldagi_narx(self.yangilab_ol(azolik_moliya)), NARX)

        # 2-qavat: guruh narxi kurs narxini bekor qiladi
        GuruhMoliya.objects.filter(guruh=self.guruh).update(narx=Decimal("600000"))
        self.assertEqual(
            mantiq.amaldagi_narx(self.yangilab_ol(azolik_moliya)), Decimal("600000")
        )

        # 3-qavat: talaba narxi ikkalasini ham bekor qiladi
        AzolikMoliya.objects.filter(pk=azolik_moliya.pk).update(narx=Decimal("500000"))
        self.assertEqual(
            mantiq.amaldagi_narx(self.yangilab_ol(azolik_moliya)), Decimal("500000")
        )

    def test_narx_hech_qayerda_yoq(self):
        azolik_moliya = self.azolik_qosh()
        KursNarxi.objects.all().delete()
        self.assertIsNone(mantiq.amaldagi_narx(self.yangilab_ol(azolik_moliya)))


class TolovTest(CrmAsos):
    def setUp(self):
        super().setUp()
        self.azolik_moliya = self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        self.hisob = Hisob.objects.get(oy=SENTABR)

    def tolov_qosh(self, summa, turi=Tolov.Turi.TOLOV, hisob=True):
        tolov = Tolov.objects.create(
            talaba=self.talaba,
            talaba_ism=self.talaba.username,
            guruh=self.guruh,
            guruh_nomi=self.guruh.name,
            hisob=self.hisob if hisob else None,
            sana=date(2026, 9, 11),
            summa=Decimal(summa),
            turi=turi,
        )
        mantiq.hisobni_yangila(self.hisob)
        self.hisob.refresh_from_db()
        return tolov

    def test_toliq_tolov_yashil(self):
        self.tolov_qosh("660000")
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)
        self.assertEqual(mantiq.balans(self.talaba), Decimal("0"))

    def test_qisman_tolov_sariq(self):
        self.tolov_qosh("400000")
        self.assertEqual(self.hisob.holat, Hisob.Holat.QISMAN)
        self.assertEqual(mantiq.balans(self.talaba), Decimal("-260000"))

    def test_chegirma_qarzni_yopadi(self):
        self.tolov_qosh("400000")
        self.tolov_qosh("260000", turi=Tolov.Turi.CHEGIRMA)
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)
        self.assertEqual(mantiq.balans(self.talaba), Decimal("0"))

    def test_chegirma_kassaga_pul_qoshmaydi(self):
        """Hisobotda "olingan pul" faqat `tolov` bo'yicha sanaladi."""
        self.tolov_qosh("400000")
        self.tolov_qosh("260000", turi=Tolov.Turi.CHEGIRMA)

        olingan = Tolov.objects.filter(turi=Tolov.Turi.TOLOV).aggregate(
            j=Sum("summa")
        )["j"]
        chegirma = Tolov.objects.filter(turi=Tolov.Turi.CHEGIRMA).aggregate(
            j=Sum("summa")
        )["j"]
        self.assertEqual(olingan, Decimal("400000"))
        self.assertEqual(chegirma, Decimal("260000"))

    def test_chegirma_ochirilsa_qarz_tiklanadi(self):
        self.tolov_qosh("400000")
        chegirma = self.tolov_qosh("260000", turi=Tolov.Turi.CHEGIRMA)
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)

        chegirma.delete()
        mantiq.hisobni_yangila(self.hisob)
        self.hisob.refresh_from_db()
        self.assertEqual(self.hisob.holat, Hisob.Holat.QISMAN)

    def test_ortiqcha_tolov_balansda_plyus(self):
        self.tolov_qosh("800000")
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)
        self.assertEqual(mantiq.balans(self.talaba), Decimal("140000"))

    def test_qaytarish_holatni_ozgartirmaydi(self):
        """Foydalanuvchi qarori 2026-09-14: oy yashil qolaveradi, pul
        faqat balansdan chiqadi."""
        self.tolov_qosh("660000")
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)

        self.tolov_qosh("300000", turi=Tolov.Turi.QAYTARISH, hisob=False)
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)
        self.assertEqual(mantiq.balans(self.talaba), Decimal("-300000"))

    def test_nol_summali_hisob_qarzdor_emas(self):
        """Shartlar tartibi: `qoldiq <= 0` birinchi tekshiriladi."""
        self.hisob.summa = Decimal("0")
        self.hisob.save()
        mantiq.hisobni_yangila(self.hisob)
        self.hisob.refresh_from_db()
        self.assertEqual(self.hisob.holat, Hisob.Holat.TOLANDI)


class AzolikYakunlashTest(CrmAsos):
    def test_talaba_chiqsa_tolanmagan_hisob_qayta_hisoblanadi(self):
        azolik_moliya = self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        self.assertEqual(Hisob.objects.get().summa, NARX)

        azolik_moliya.tugash_sana = date(2026, 9, 12)
        azolik_moliya.holat = AzolikMoliya.Holat.ARXIV
        azolik_moliya.save()
        mantiq.azolikni_qayta_hisobla(azolik_moliya, SENTABR)

        hisob = Hisob.objects.get()
        self.assertEqual(hisob.summa, Decimal("330000"))
        self.assertEqual(hisob.darslar_talaba, 6)

    def test_tolangan_oyga_tegilmaydi(self):
        azolik_moliya = self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        hisob = Hisob.objects.get()
        Tolov.objects.create(
            talaba=self.talaba, talaba_ism="x", guruh=self.guruh, guruh_nomi="y",
            hisob=hisob, sana=date(2026, 9, 5), summa=NARX, turi=Tolov.Turi.TOLOV,
        )
        mantiq.hisobni_yangila(hisob)

        azolik_moliya.tugash_sana = date(2026, 9, 12)
        azolik_moliya.save()
        mantiq.azolikni_qayta_hisobla(azolik_moliya, SENTABR)

        hisob.refresh_from_db()
        self.assertEqual(hisob.summa, NARX)


class OchirishXavfsizligiTest(CrmAsos):
    """CASCADE o'rniga SET_NULL + nom nusxasi — pul tarixi yo'qolmasligi
    uchun. LMS'da talaba/guruhni BUTUNLAY o'chirish amali mavjud
    (`accounts.FoydalanuvchiOchirishView`, `academics.GuruhDetailView`)."""

    def setUp(self):
        super().setUp()
        self.azolik_qosh(boshlanish=date(2026, 9, 1))
        with bugun_qilib(date(2026, 9, 30)):
            mantiq.hisoblarni_generatsiya_qil()
        self.hisob = Hisob.objects.get()
        Tolov.objects.create(
            talaba=self.talaba, talaba_ism="Talaba Bir", guruh=self.guruh,
            guruh_nomi=self.guruh.name, hisob=self.hisob, sana=date(2026, 9, 5),
            summa=NARX, turi=Tolov.Turi.TOLOV,
        )

    def test_talaba_ochirilsa_tolov_tarixi_qoladi(self):
        self.talaba.delete()
        tolov = Tolov.objects.get()
        self.assertIsNone(tolov.talaba)
        self.assertEqual(tolov.talaba_ism, "Talaba Bir")
        self.assertEqual(tolov.summa, NARX)

    def test_guruh_ochirilsa_hisob_qoladi(self):
        nomi = self.guruh.name
        self.guruh.delete()
        hisob = Hisob.objects.get()
        self.assertIsNone(hisob.guruh)
        self.assertEqual(hisob.guruh_nomi, nomi)


class IzolyatsiyaTest(TestCase):
    """CRM o'chirilganda LMS ishlashda davom etishi kerak (TZ 3.0).

    Bu test buzilsa — kimdir LMS kodiga `crm` bog'liqligini kiritgan.
    Tuzatish yo'li: bog'liqlikni olib tashlash, testni o'chirish EMAS.
    """

    LMS_ILOVALARI = [
        "accounts", "academics", "courses", "assessment", "exercises",
        "stats", "gamification", "games", "audit", "config",
    ]

    def test_lms_crm_dan_import_qilmaydi(self):
        namuna = re.compile(r"^\s*(?:from\s+crm[\s.]|import\s+crm\b)", re.MULTILINE)
        ildiz = Path(settings.BASE_DIR)
        aybdorlar = []

        for ilova in self.LMS_ILOVALARI:
            for fayl in (ildiz / ilova).rglob("*.py"):
                if namuna.search(fayl.read_text(encoding="utf-8")):
                    aybdorlar.append(str(fayl.relative_to(ildiz)))

        self.assertEqual(
            aybdorlar, [],
            f"LMS fayllari `crm`dan import qilmoqda: {aybdorlar}. "
            "CRM olib tashlanganda sayt buziladi.",
        )

    def test_lms_frontendi_crm_papkasiga_tegmaydi(self):
        namuna = re.compile(r"""["']\.{0,2}/?src-crm""")
        ildiz = Path(settings.BASE_DIR) / "frontend" / "src"
        aybdorlar = [
            str(fayl)
            for fayl in ildiz.rglob("*.js*")
            if namuna.search(fayl.read_text(encoding="utf-8"))
        ]
        self.assertEqual(aybdorlar, [], f"LMS frontendi src-crm'ga bog'langan: {aybdorlar}")
