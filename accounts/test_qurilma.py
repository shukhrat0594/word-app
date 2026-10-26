"""Qurilma limiti (2026-10-20, "B variant"): brauzer ID'si + brauzer belgilari,
adminga bitta so'rov, admin qarorlari, o'chirilgan qurilma darhol chiqishi."""

from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import qurilmalar as q
from accounts.models import Bildirishnoma, QurilmaSorovi, User
from accounts.tests import PAROL, DrosselsizTest, _owner_yarat

UA_ANDROID = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/141.0.0.0 Mobile Safari/537.36")
UA_WINDOWS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/141.0.0.0 Safari/537.36")
TELEFON = {"model": "SM-A515F", "gpu": "Mali-G72", "ekran": [915, 412], "dpr": 2.625,
           "yadro": 8, "xotira": 4, "teginish": 5, "vaqt": "Asia/Tashkent"}
NOUTBUK = {"gpu": "ANGLE (Intel, Intel(R) UHD Graphics 620)", "ekran": [1920, 1080], "dpr": 1,
           "yadro": 8, "xotira": 8, "teginish": 0, "vaqt": "Asia/Tashkent"}


class BelgilarTest(SimpleTestCase):
    def test_ua_tahlil(self):
        self.assertEqual(q.ua_tahlil(UA_ANDROID), ("Android", "Chrome", ""))  # "K" — yashirilgan model
        self.assertEqual(q.ua_tahlil(UA_WINDOWS), ("Windows", "Chrome", ""))
        webview = ("Mozilla/5.0 (Linux; Android 13; SM-A525F Build/TP1A.220624.014; wv) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Version/4.0 Chrome/141.0 Mobile Safari/537.36")
        self.assertEqual(q.ua_tahlil(webview), ("Android", "Ilova ichidagi brauzer", "SM-A525F"))
        samsung = ("Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "SamsungBrowser/25.0 Chrome/121.0 Mobile Safari/537.36")
        self.assertEqual(q.ua_tahlil(samsung), ("Android", "Samsung Internet", "SM-S918B"))
        iphone = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 "
                  "(KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1")
        self.assertEqual(q.ua_tahlil(iphone), ("iOS", "Safari", ""))

    def test_belgilar_tozalanadi_va_nom(self):
        b = q.belgilarni_tozala({**TELEFON, "begona": "x" * 999, "yadro": True}, UA_ANDROID)
        self.assertNotIn("begona", b)
        self.assertNotIn("yadro", b)  # bool son emas
        self.assertEqual(b["ekran"], [412, 915])  # tartiblangan — burilganda ham bir xil
        self.assertEqual(q.qurilma_nomi(b), "Android · Chrome · SM-A515F")
        ipad = q.belgilarni_tozala({"teginish": 5}, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605")
        self.assertEqual(ipad["tizim"], "iPadOS")
        self.assertEqual(q.qurilma_nomi({}), "Noma'lum qurilma")

    def test_mos_keladimi(self):
        a = q.belgilarni_tozala(TELEFON, UA_ANDROID)
        self.assertTrue(q.mos_keladimi(a, dict(a)))
        # Bitta telefondagi boshqa brauzer — baribir o'sha qurilma
        self.assertTrue(q.mos_keladimi(a, {**a, "brauzer": "Ilova ichidagi brauzer"}))
        self.assertFalse(q.mos_keladimi(a, {**a, "gpu": "Adreno 610"}))
        self.assertFalse(q.mos_keladimi(a, {**a, "ekran": [393, 873]}))
        self.assertFalse(q.mos_keladimi(a, {**a, "dpr": 3.0, "ekran": [360, 800]}))  # boshqa telefon
        # Kompyuterda brauzer masshtabi 110%: CSS o'lcham va zichlik o'zgaradi, haqiqiy piksellar — yo'q
        n = q.belgilarni_tozala(NOUTBUK, UA_WINDOWS)
        self.assertTrue(q.mos_keladimi(n, {**n, "ekran": [982, 1745], "dpr": 1.1}))
        self.assertFalse(q.mos_keladimi(n, {**n, "ekran": [1366, 768], "dpr": 1}))
        self.assertFalse(q.mos_keladimi(a, {k: v for k, v in a.items() if k != "vaqt"}))
        # Na video karta, na model — faqat ekran/yadro bilan tanilmaydi
        yalangoch = {k: v for k, v in a.items() if k not in ("gpu", "model")}
        self.assertFalse(q.mos_keladimi(yalangoch, dict(yalangoch)))
        self.assertFalse(q.mos_keladimi({}, a))


class QurilmaAsos(DrosselsizTest):
    """Qurilma testlari uchun umumiy foydalanuvchilar va yordamchilar (testlarsiz)."""

    def setUp(self):
        super().setUp()
        self.talaba = User.objects.create_user(username="talaba", password=PAROL, role=User.Role.STUDENT)
        self.admin = User.objects.create_user(username="admin1", password=PAROL, role=User.Role.ADMIN)
        self.owner = _owner_yarat("owner")
        self.admin_klient = APIClient()
        self.admin_klient.force_authenticate(self.admin)

    def kirish(self, qid, belgilar=TELEFON, ua=UA_ANDROID, username="talaba"):
        return APIClient().post(
            "/api/token/",
            {"username": username, "password": PAROL, "qurilma_id": qid, "qurilma_belgilari": belgilar},
            format="json", HTTP_USER_AGENT=ua,
        )

    def profil(self, javob):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"])
        return c.get("/api/profil/")

    def royxat(self):
        self.talaba.refresh_from_db()
        return q.royxat(self.talaba)

    def sorov_yarat(self):
        self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        return QurilmaSorovi.objects.get(foydalanuvchi=self.talaba, holat=QurilmaSorovi.Holat.KUTILMOQDA)

    def qaror(self, sorov, **tana):
        return self.admin_klient.post(f"/api/qurilma-sorovlari/{sorov.pk}/qaror/", tana, format="json")


class QurilmaKirishTest(QurilmaAsos):
    # ── Kirish ──

    def test_birinchi_qurilma_nomi_bilan_yoziladi(self):
        j = self.kirish("tel-1")
        self.assertEqual(j.status_code, 200, j.data)
        self.assertNotIn("qurilma_id", j.data)  # cookie davri tugadi
        self.assertNotIn("qurilma", j.cookies)
        [d] = self.royxat()
        self.assertEqual((d["id"], d["nom"]), ("tel-1", "Android · SM-A515F"))
        self.assertEqual([b["brauzer"] for b in d["brauzerlar"]], ["Chrome"])
        self.assertEqual(self.profil(j).status_code, 200)
        self.assertEqual(self.kirish("tel-1").status_code, 200)
        self.assertEqual(len(self.royxat()), 1)

    def test_tozalangan_telefon_belgilar_bilan_jim_kiradi(self):
        eski = self.kirish("tel-1")
        yangi = self.kirish("tel-2")  # tarix tozalandi: yangi ID, belgilar o'sha
        self.assertEqual(yangi.status_code, 200, yangi.data)
        self.assertEqual([d["id"] for d in self.royxat()], ["tel-2"])
        self.assertEqual(self.profil(yangi).status_code, 200)
        # eski brauzer seansi darhol yopildi
        r = self.profil(eski)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data["kod"], "qurilma_ochirildi")
        s = QurilmaSorovi.objects.get(foydalanuvchi=self.talaba)
        self.assertEqual((s.holat, s.almashtirilgan_nom), (QurilmaSorovi.Holat.AVTO, "Android · Chrome · SM-A515F"))
        self.assertFalse(Bildirishnoma.objects.filter(kalit__startswith="qurilma-sorov:").exists())

    def test_bir_safar_kam_belgi_kelsa_saqlangani_yoqolmaydi(self):
        # 2026-10-22, brauzerda topildi: belgisiz kirish saqlangan belgilarni o'chirib,
        # keyingi tozalashdan so'ng qurilma tanilmay qolardi.
        self.kirish("tel-1")
        self.assertEqual(self.kirish("tel-1", belgilar={}).status_code, 200)
        self.assertEqual(self.royxat()[0]["belgilar"]["gpu"], "Mali-G72")
        self.assertEqual(self.royxat()[0]["nom"], "Android · SM-A515F")
        self.assertEqual(self.kirish("tel-2").status_code, 200)  # tarix tozalandi — baribir tanildi

    def test_begona_qurilma_rad_va_adminga_bitta_xabar(self):
        self.kirish("tel-1")
        j = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.assertEqual(j.status_code, 403)
        self.assertEqual(j.data["kod"], "qurilma_mos_emas")
        self.assertEqual(j.data["ruxsat_etilgan"], ["Android · SM-A515F"])  # qurilma nomi — brauzersiz
        self.assertEqual(j.data["sorov"], "kutilmoqda")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        s = QurilmaSorovi.objects.get(foydalanuvchi=self.talaba)
        self.assertEqual((s.urinishlar, s.nom), (3, "Windows · Chrome"))
        # admin ham, owner ham — bittadan xabar, takroriy urinishlar xabar yaratmaydi
        xabarlar = Bildirishnoma.objects.filter(kalit=f"qurilma-sorov:{s.pk}")
        self.assertEqual(sorted(xabarlar.values_list("foydalanuvchi__username", flat=True)), ["admin1", "owner"])
        self.assertEqual(xabarlar.first().havola, "/qurilma-sorovlari")
        self.assertEqual(len(self.royxat()), 1)

    def test_limitda_joy_bolsa_qoshiladi_va_sorov_yopiladi(self):
        self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)  # so'rov yaratildi
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual(len(self.royxat()), 2)
        s = QurilmaSorovi.objects.get(foydalanuvchi=self.talaba)
        self.assertEqual(s.holat, QurilmaSorovi.Holat.RUXSAT)
        self.assertTrue(Bildirishnoma.objects.filter(kalit=f"qurilma-sorov:{s.pk}", oqilgan=True).exists())

    def test_ikki_bir_xil_qurilma_bolsa_avtomatik_tanilmaydi(self):
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        self.kirish("otasi")
        self.kirish("onasi")  # xuddi shu model
        j = self.kirish("uchinchi")
        self.assertEqual(j.status_code, 403)
        self.assertEqual(j.data["sorov"], "kutilmoqda")

    def test_60_kun_kirilmagan_qurilma_ochadi(self):
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        royxat = self.royxat()
        royxat[0]["brauzerlar"][0]["oxirgi"] = (timezone.now() - timedelta(days=61)).isoformat()
        User.objects.filter(pk=self.talaba.pk).update(qurilmalar=royxat)
        self.assertEqual(self.kirish("tel-1").status_code, 200)
        self.assertEqual([d["id"] for d in self.royxat()], ["tel-1"])

    def test_belgisiz_eski_kalit_qabul_qilinmaydi_owner_tegilmaydi(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        self.kirish("tel-1")
        eski = RefreshToken.for_user(self.talaba)  # 2026-10-20 dan oldingi kalit — `qid` yo'q
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {eski.access_token}")
        self.assertEqual(c.get("/api/profil/").status_code, 401)
        r = APIClient().post("/api/token/refresh/", {"refresh": str(eski)}, format="json")
        self.assertEqual((r.status_code, r.data["kod"]), (401, "qurilma_ochirildi"))
        owner = APIClient()
        owner.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.owner).access_token}")
        self.assertEqual(owner.get("/api/profil/").status_code, 200)
        self.assertEqual(self.kirish("istalgan", username="owner").status_code, 200)

    def test_refresh_oxirgi_vaqtni_yozadi(self):
        j = self.kirish("tel-1")
        royxat = self.royxat()
        royxat[0]["brauzerlar"][0]["oxirgi"] = (timezone.now() - timedelta(days=3)).isoformat()
        User.objects.filter(pk=self.talaba.pk).update(qurilmalar=royxat)
        r = APIClient().post("/api/token/refresh/", {"refresh": j.data["refresh"]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        oxirgi = timezone.datetime.fromisoformat(self.royxat()[0]["oxirgi"])
        self.assertLess(timezone.now() - oxirgi, timedelta(minutes=1))

    # ── Admin ──

    def test_almashtirish_eski_qurilmani_darhol_chiqaradi(self):
        eski = self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        s = QurilmaSorovi.objects.get(foydalanuvchi=self.talaba)
        k = self.royxat()[0]["k"]
        r = self.qaror(s, amal="almashtir", k=k)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual([d["nom"] for d in r.data["qurilmalar"]], ["Windows"])
        self.assertEqual(r.data["oy_almashtirishlari"], 1)
        self.assertEqual(r.data["jurnal"][0]["almashtirilgan_nom"], "Android · SM-A515F")
        self.assertEqual(self.profil(eski).status_code, 401)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual(self.qaror(s, amal="rad").status_code, 400)  # allaqachon hal qilingan

    def test_limitni_oshirish_hech_kimni_chiqarmaydi(self):
        s = self.sorov_yarat()
        r = self.qaror(s, amal="limit")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["limit"], 2)
        self.assertEqual(len(r.data["qurilmalar"]), 2)
        self.assertEqual(self.kirish("tel-1").status_code, 200)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)

    def test_rad_etilsa_xabar_beriladi(self):
        s = self.sorov_yarat()
        self.assertEqual(self.qaror(s, amal="rad").status_code, 200)
        j = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.assertEqual((j.status_code, j.data["sorov"]), (403, "rad"))
        self.assertEqual(QurilmaSorovi.objects.filter(foydalanuvchi=self.talaba).count(), 1)

    def test_bitta_qurilmani_ochirish(self):
        j = self.kirish("tel-1")
        k = self.royxat()[0]["k"]
        r = self.admin_klient.post(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilmalar/",
                                   {"amal": "ochir", "k": k}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["qurilmalar"], [])
        self.assertEqual(self.profil(j).status_code, 401)
        ref = APIClient().post("/api/token/refresh/", {"refresh": j.data["refresh"]}, format="json")
        self.assertEqual(ref.status_code, 401)
        # keyingi kirgan qurilma — yana 1-qurilma
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)

    def test_qurilmalar_oynasi_idni_bermaydi(self):
        self.kirish("tel-1")
        r = self.admin_klient.get(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilmalar/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.data["qurilmalar"][0]), {"k", "nom", "qoshilgan", "oxirgi", "faol", "brauzerlar"})
        self.assertEqual(r.data["qurilmalar"][0]["brauzerlar"][0]["nom"], "Chrome")
        self.assertNotIn("tel-1", str(r.data))

    def test_sorovlar_royxati_va_ruxsatlar(self):
        self.sorov_yarat()
        r = self.admin_klient.get("/api/qurilma-sorovlari/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([x["foydalanuvchi"]["username"] for x in r.data], ["talaba"])
        oqituvchi = User.objects.create_user(username="oq", password=PAROL, role=User.Role.TEACHER)
        c = APIClient()
        c.force_authenticate(oqituvchi)
        self.assertEqual(c.get("/api/qurilma-sorovlari/").status_code, 403)
        self.assertEqual(c.get(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilmalar/").status_code, 403)
        self.assertEqual(self.admin_klient.get(f"/api/foydalanuvchilar/{self.owner.pk}/qurilmalar/").status_code, 403)

    def test_limitni_admin_kiritadi_oraliqsiz(self):
        url = f"/api/foydalanuvchilar/{self.talaba.pk}/qurilma-limit/"
        self.assertEqual(self.admin_klient.post(url, {"limit": 7}, format="json").status_code, 200)
        self.talaba.refresh_from_db()
        self.assertEqual(self.talaba.qurilma_limiti, 7)
        self.assertEqual(self.admin_klient.post(url, {"limit": 0}, format="json").status_code, 400)
        owner_url = f"/api/foydalanuvchilar/{self.owner.pk}/qurilma-limit/"
        self.assertEqual(self.admin_klient.post(owner_url, {"limit": 3}, format="json").status_code, 403)

    def test_hammasini_tiklash_seansni_yopadi(self):
        j = self.kirish("tel-1")
        r = self.admin_klient.post(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilma-tiklash/",
                                   {"izoh": "yangi telefon"}, format="json")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.profil(j).status_code, 401)


UA_TELEGRAM = ("Mozilla/5.0 (Linux; Android 10; SM-A515F Build/QP1A.190711.020; wv) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Version/4.0 Chrome/141.0 Mobile Safari/537.36 Telegram-Android/11.9.0")


class KopBrauzerTest(QurilmaAsos):
    """2026-10-26 (Shuhrat qoidasi): bitta telefondagi brauzerlar bitta qurilma,
    yangi qurilma eskisini chiqarmaydi, talaba bir paytda bitta qurilmadan kiradi,
    admin bloklangan qurilmani blokdan chiqaradi. Guruhdagi 531/534/540 shikoyatlari:
    Chrome va Telegram brauzeri bir-birini navbat bilan chiqarardi."""

    def yangila(self, javob):
        return APIClient().post("/api/token/refresh/", {"refresh": javob.data["refresh"]}, format="json")

    def panel(self):
        return self.admin_klient.get(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilmalar/").data

    def test_bitta_telefondagi_brauzerlar_birga_ishlaydi(self):
        chrome = self.kirish("chrome-1")
        telegram = self.kirish("telegram-1", ua=UA_TELEGRAM)
        self.assertEqual(telegram.status_code, 200, telegram.data)
        self.assertEqual(self.profil(chrome).status_code, 200)
        self.assertEqual(self.profil(telegram).status_code, 200)
        self.assertEqual(self.kirish("chrome-1").status_code, 200)
        self.assertEqual(self.profil(telegram).status_code, 200)  # Chrome qayta kirsa ham Telegram qoladi
        [d] = self.royxat()
        self.assertEqual([b["brauzer"] for b in d["brauzerlar"]], ["Chrome", "Telegram"])
        p = self.panel()
        self.assertEqual(p["jurnal"][0]["holat"], QurilmaSorovi.Holat.BRAUZER)
        self.assertEqual(p["oy_almashtirishlari"], 0)  # boshqa brauzer — almashtirish emas
        self.assertFalse(Bildirishnoma.objects.filter(kalit__startswith="qurilma-sorov:").exists())

    def test_telegram_bosh_joyni_egallamaydi(self):
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        self.kirish("chrome-1")
        self.kirish("telegram-1", ua=UA_TELEGRAM)
        self.assertEqual(len(self.royxat()), 1)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual([d["nom"] for d in self.royxat()], ["Android · SM-A515F", "Windows"])

    def test_tozalangan_chrome_telegramga_tegmaydi(self):
        eski = self.kirish("chrome-1")
        telegram = self.kirish("telegram-1", ua=UA_TELEGRAM)
        self.assertEqual(self.kirish("chrome-2").status_code, 200)  # tarix tozalandi, limit to'la
        r = self.profil(eski)
        self.assertEqual((r.status_code, r.data["kod"]), (401, "qurilma_ochirildi"))
        self.assertEqual(self.profil(telegram).status_code, 200)
        [d] = self.royxat()
        self.assertEqual({b["id"] for b in d["brauzerlar"]}, {"chrome-2", "telegram-1"})

    def test_bir_paytda_bitta_qurilma(self):
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        tel = self.kirish("tel-1")
        nout = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        r = self.profil(tel)
        self.assertEqual((r.status_code, r.data["kod"]), (401, "boshqa_qurilmada"))
        r = self.yangila(tel)
        self.assertEqual((r.status_code, r.data["kod"]), (401, "boshqa_qurilmada"))
        self.assertEqual(len(self.royxat()), 2)  # telefon ruxsat etilganligicha qoladi
        self.assertEqual([x["faol"] for x in self.panel()["qurilmalar"]], [False, True])
        tel2 = self.kirish("tel-1")
        self.assertEqual(tel2.status_code, 200)
        self.assertEqual(self.profil(tel2).status_code, 200)
        r = self.profil(nout)
        self.assertEqual((r.status_code, r.data["kod"]), (401, "boshqa_qurilmada"))

    def test_xodimga_bir_paytda_bitta_tegishli_emas(self):
        oqituvchi = User.objects.create_user(username="oq", password=PAROL, role=User.Role.TEACHER, qurilma_limiti=2)
        tel = self.kirish("tel-1", username="oq")
        nout = self.kirish("nout-1", NOUTBUK, UA_WINDOWS, username="oq")
        self.assertEqual(self.profil(tel).status_code, 200)
        self.assertEqual(self.profil(nout).status_code, 200)
        oqituvchi.refresh_from_db()
        self.assertEqual(oqituvchi.faol_qurilma, "")

    def test_limitdan_tashqari_qurilma_ruxsat_etilganini_chiqarmaydi(self):
        tel = self.kirish("tel-1")
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 403)
        self.assertEqual(self.profil(tel).status_code, 200)

    def test_eski_shakldagi_yozuv_oqiladi_hech_kim_chiqmaydi(self):
        # 2026-10-26 gacha yozilgan bitta brauzerli yozuv — deploydan keyin ham ishlaydi.
        from rest_framework_simplejwt.tokens import RefreshToken

        belgilar = q.belgilarni_tozala(TELEFON, UA_ANDROID)
        hozir = timezone.now().isoformat()
        User.objects.filter(pk=self.talaba.pk).update(qurilmalar=[{
            "id": "eski-1", "k": "abc123", "nom": "Android · Chrome · SM-A515F",
            "belgilar": belgilar, "qoshilgan": hozir, "oxirgi": hozir,
        }])
        kalit = RefreshToken.for_user(self.talaba)
        kalit["qid"] = "eski-1"
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {kalit.access_token}")
        self.assertEqual(c.get("/api/profil/").status_code, 200)
        self.assertEqual(self.kirish("telegram-1", ua=UA_TELEGRAM).status_code, 200)  # shu qurilmaga qo'shildi
        self.assertEqual(c.get("/api/profil/").status_code, 200)
        [d] = self.royxat()
        self.assertEqual((d["k"], d["nom"], [b["id"] for b in d["brauzerlar"]]),
                         ("abc123", "Android · SM-A515F", ["eski-1", "telegram-1"]))

    def test_login_kaliti_bazaga_qurilma_belgisi_bilan_yoziladi(self):
        from rest_framework_simplejwt.state import token_backend
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        self.kirish("tel-1")
        [kalit] = OutstandingToken.objects.filter(user=self.talaba)
        self.assertEqual(token_backend.decode(kalit.token, verify=False)["qid"], "tel-1")

    def test_qurilma_almashsa_boshqa_qurilma_seansi_qoladi(self):
        # 2026-10-26 gacha `TOKEN_BACKEND` xatosi tufayli foydalanuvchining HAMMA
        # seanslari yopilardi. `on_commit` bajarilmasa testda bu ko'rinmaydi.
        oqituvchi = User.objects.create_user(username="oq", password=PAROL, role=User.Role.TEACHER, qurilma_limiti=2)
        tel = self.kirish("tel-1", username="oq")
        nout = self.kirish("nout-1", NOUTBUK, UA_WINDOWS, username="oq")
        with self.captureOnCommitCallbacks(execute=True):
            tel2 = self.kirish("tel-2", username="oq")  # tarix tozalandi, joy yo'q
        self.assertEqual(tel2.status_code, 200)
        self.assertEqual(self.yangila(nout).status_code, 200)
        self.assertEqual(self.yangila(tel2).status_code, 200)
        self.assertEqual(self.yangila(tel).status_code, 401)
        k = next(d["k"] for d in q.royxat(User.objects.get(pk=oqituvchi.pk)) if d["nom"] == "Windows")
        with self.captureOnCommitCallbacks(execute=True):
            self.admin_klient.post(f"/api/foydalanuvchilar/{oqituvchi.pk}/qurilmalar/",
                                   {"amal": "ochir", "k": k}, format="json")
        self.assertEqual(self.profil(tel2).status_code, 200)

    def test_qurilma_ochirilsa_barcha_brauzerlari_chiqadi(self):
        chrome = self.kirish("chrome-1")
        with self.captureOnCommitCallbacks(execute=True):
            telegram = self.kirish("telegram-1", ua=UA_TELEGRAM)
        k = self.royxat()[0]["k"]
        with self.captureOnCommitCallbacks(execute=True):
            self.admin_klient.post(f"/api/foydalanuvchilar/{self.talaba.pk}/qurilmalar/",
                                   {"amal": "ochir", "k": k}, format="json")
        for j in (chrome, telegram):
            self.assertEqual(self.profil(j).status_code, 401)
            self.assertEqual(self.yangila(j).status_code, 401)

    def test_bloklangan_qurilmani_blokdan_chiqarish(self):
        s = self.sorov_yarat()
        self.assertEqual(self.qaror(s, amal="rad").status_code, 200)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).data["sorov"], "rad")
        self.assertEqual([b["id"] for b in self.panel()["bloklangan"]], [s.pk])
        r = self.qaror(s, amal="blokdan_chiqar")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["bloklangan"], [x["id"] for x in r.data["sorovlar"]]), ([], [s.pk]))
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).data["sorov"], "kutilmoqda")
        self.assertEqual(self.qaror(s, amal="blokdan_chiqar").status_code, 400)  # endi bloklanmagan
        self.assertEqual(self.qaror(s, amal="limit").status_code, 200)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)

    def test_24_soatdan_keyin_bloklanganlar_royxatida_yoq(self):
        s = self.sorov_yarat()
        self.qaror(s, amal="rad")
        QurilmaSorovi.objects.filter(pk=s.pk).update(hal_vaqti=timezone.now() - timedelta(hours=25))
        self.assertEqual(self.panel()["bloklangan"], [])
