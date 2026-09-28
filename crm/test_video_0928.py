"""Video-TZ 2026-09-28 (TZ videolar CRM/IMG_6783..6791, CRM TZ.mp4) tuzatishlari."""

from datetime import date

from django.utils import timezone

from academics.models import Davomat, GuruhAzoligi
from accounts.models import User
from courses.models import KursMashq, KursMashqYechim, KursTugun
from crm.models import GuruhdanChiqish, Lid, TalabaProfil
from crm.test_api import ApiAsos
from crm.test_filial import FilialAsos
from crm.tests import SENTABR


class SaytHolatiTest(ApiAsos):
    """CRM TZ.mp4: saytdan foydalanayotgan o'quvchi "Saytga hali kirmagan" edi —
    `last_login` JWT'da yangilanmaydi."""

    def test_faollik_bor_bolsa_kirgan(self):
        self.azolik_qosh()
        m = self.mijoz(self.owner)
        self.assertFalse(m.get(f"/api/crm/talaba/{self.talaba.id}/").data["sayt"]["kirgan"])
        User.objects.filter(pk=self.talaba.pk).update(oxirgi_faollik=timezone.now())
        sayt = m.get(f"/api/crm/talaba/{self.talaba.id}/").data["sayt"]
        self.assertTrue(sayt["kirgan"])
        self.assertIsNotNone(sayt["oxirgi_faollik"])
        q = m.get("/api/crm/talaba-qidiruv/?q=talaba1").data
        self.assertTrue(q[0]["saytga_kirgan"])


class ArxivdagilarDavomatiTest(ApiAsos):
    """IMG_6783: guruhdan chiqqan o'quvchining davomati ko'rinsin (faqat ko'rish)."""

    def test_sobiqlar(self):
        self.azolik_qosh()
        Davomat.objects.create(guruh=self.guruh, talaba=self.talaba, sana=date(2026, 9, 3), holat=Davomat.Holat.KELDI)
        GuruhAzoligi.objects.filter(guruh=self.guruh, talaba=self.talaba).delete()
        GuruhdanChiqish.objects.create(talaba=self.talaba, talaba_ism="T", guruh=self.guruh, guruh_nomi="G",
                                       filial=self.filial, boshlagan_sana=SENTABR, sana=date(2026, 9, 10))
        m = self.mijoz(self.owner)
        d = m.get(f"/api/crm/guruhlar/{self.guruh.id}/davomat/?oy=2026-09").data
        self.assertEqual((d["talabalar"], d["sobiqlar"], d["sobiqlar_soni"]), ([], [], 1))
        d = m.get(f"/api/crm/guruhlar/{self.guruh.id}/davomat/?oy=2026-09&sobiqlar=1").data
        s = d["sobiqlar"][0]
        self.assertEqual((s["id"], s["keldi"], s["chiqqan_sana"]), (self.talaba.id, 1, date(2026, 9, 10)))
        self.assertTrue(all(k["qulf"] for k in s["kunlar"] if k["sana"] > date(2026, 9, 10)))
        # Arxivdagi o'quvchiga davomat qo'yib bo'lmaydi.
        self.assertEqual(m.post(f"/api/crm/guruhlar/{self.guruh.id}/davomat/", {
            "talaba_id": self.talaba.id, "sana": "2026-09-04", "holat": "keldi"}, format="json").status_code, 400)


class UnitNatijalariTest(ApiAsos):
    """IMG_6784: General o'quvchi kartasida har Unit uy vazifasi — to'g'ri/noto'g'ri foiz."""

    def test_unitlar(self):
        u1 = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 1", parent=self.daraja, unit_darsi=True, tartib=1)
        u2 = KursTugun.objects.create(markaz=self.markaz, nomi="Unit 2", parent=self.daraja, unit_darsi=True, tartib=2)
        KursTugun.objects.create(markaz=self.markaz, nomi="Unit 3 (bo'sh)", parent=self.daraja, unit_darsi=True, tartib=3)
        sb = KursTugun.objects.create(markaz=self.markaz, nomi="Student's Book", parent=u1)
        m1 = KursMashq.objects.create(tugun=sb, savollar=[])
        m2 = KursMashq.objects.create(tugun=KursTugun.objects.create(markaz=self.markaz, nomi="WB", parent=sb),
                                      savollar=[])
        KursMashq.objects.create(tugun=u2, savollar=[])
        self.azolik_qosh()
        KursMashqYechim.objects.create(talaba=self.talaba, mashq=m1, javoblar=[], ball=2, jami=10, natijalar=[])
        KursMashqYechim.objects.create(talaba=self.talaba, mashq=m1, javoblar=[], ball=8, jami=10, natijalar=[])
        KursMashqYechim.objects.create(talaba=self.talaba, mashq=m2, javoblar=[], ball=6, jami=10, natijalar=[])
        g = self.mijoz(self.owner).get(f"/api/crm/talaba/{self.talaba.id}/").data["guruhlar"][0]
        unitlar = {u["nomi"]: u for u in g["unitlar"]}
        self.assertEqual(set(unitlar), {"Unit 1", "Unit 2"})  # mashqsiz Unit chiqmaydi
        u = unitlar["Unit 1"]
        # Eng yangi yechim hisobga olinadi: (8 + 6) / 20 = 70%.
        self.assertEqual((u["bajarilgan"], u["mashqlar"], u["togri_foiz"], u["notogri_foiz"], u["otildi"]),
                         (2, 2, 70, 30, True))
        u = unitlar["Unit 2"]
        self.assertEqual((u["bajarilgan"], u["togri_foiz"], u["otildi"]), (0, None, False))


class BoshSahifaTest(ApiAsos):
    def test_tolovi_yaqin_yoq(self):
        """IMG_6786: "To'lovi yaqin" kerak emas."""
        self.assertNotIn("tolovi_yaqin", self.mijoz(self.owner).get("/api/crm/korsatkichlar/").data)


class LidQoraRoyxatOquvchilarTest(FilialAsos):
    """IMG_6788: qora ro'yxatdagi o'quvchi Lidlar -> "Qora ro'yxat"da hamma filialga."""

    def test_boshqa_filial_qora_oquvchisi_korinadi(self):
        TalabaProfil.objects.create(user=self.tb, qora_royxat=True, qora_royxat_sabab="to'lamagan")
        Lid.objects.create(ism="Qora lid", telefon="+998900000009", filial=self.fb, qora_royxat=True)
        m = self.mijoz(self.admin_a)
        d = m.get("/api/crm/lidlar/qora-oquvchilar/").data
        self.assertEqual([(x["id"], x["sabab"], x["filial"]) for x in d], [(self.tb.id, "to'lamagan", "Chilonzor")])
        self.assertEqual(m.get("/api/crm/lid-doskalar/").data["qora_royxat"], 2)  # lid + o'quvchi
        # Marketolog (faqat lidlar bo'limi) ham ko'radi.
        mk = self.xodim("mk", [self.filial], lavozim="marketolog", role=User.Role.ODDIY)
        self.assertEqual(len(self.mijoz(mk).get("/api/crm/lidlar/qora-oquvchilar/").data), 1)


class KechikdiTest(ApiAsos):
    """IMG_6791: davomat variantlari — keldi / kechikdi / kelmadi (+ sababli)."""

    def test_kechikdi(self):
        from crm.tests import bugun_qilib

        self.azolik_qosh()
        m = self.mijoz(self.owner)
        yol = f"/api/crm/guruhlar/{self.guruh.id}/davomat/"
        with bugun_qilib(date(2026, 9, 20)):
            javob = m.post(yol, {"talaba_id": self.talaba.id, "sana": "2026-09-03", "holat": "kechikdi"}, format="json")
        self.assertEqual(javob.status_code, 200, javob.data)
        # LMS'da — "keldi" (dars qoldirilmagan), belgi CRM'da.
        d = Davomat.objects.get(guruh=self.guruh, talaba=self.talaba, sana=date(2026, 9, 3))
        self.assertEqual((d.holat, d.crm_izoh.kechikdi), (Davomat.Holat.KELDI, True))
        t = m.get(yol + "?oy=2026-09").data["talabalar"][0]
        self.assertEqual((t["keldi"], t["kechikdi"]), (1, 1))
        self.assertIn("kechikdi", [k["holat"] for k in t["kunlar"]])
        g = m.get(f"/api/crm/talaba/{self.talaba.id}/?oy=2026-09").data["guruhlar"][0]
        self.assertEqual((g["taqvim_sanogi"]["keldi"], g["taqvim_sanogi"]["kechikdi"]), (1, 1))
        # "Keldi"ga qaytarilsa — belgi olinadi.
        m.post(yol, {"talaba_id": self.talaba.id, "sana": "2026-09-03", "holat": "keldi"}, format="json")
        self.assertFalse(Davomat.objects.filter(pk=d.pk, crm_izoh__isnull=False).exists())
