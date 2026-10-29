"""Qurilmalar limiti, 2-tizim (2026-10-29): qurilma (brauzer emas), qurilma kaliti (passkey),
bir vaqtda bitta seans, «Qurilmalar» oynasi, eski tizimdan ko'chirish va unga nusxa yozish.

Qurilma kaliti `SoxtaKalit` bilan taqlid qilinadi — telefon qulfi bilan tasdiqlashning
o'zi (ECDSA imzo), serverdagi tekshiruv esa haqiqiy (`webauthn` kutubxonasi)."""

import base64
import hashlib
import json
import os
import struct
from datetime import timedelta

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import (
    Bildirishnoma,
    BrauzerEslatmasi,
    FaolSeans,
    KirishJurnali,
    Qurilma,
    QurilmaKaliti,
    QurilmaSorovi,
    User,
)
from accounts.qurilma_kochirish import kochir
from accounts.tests import PAROL, DrosselsizTest, _owner_yarat

ORIGIN = "http://localhost:3000"
UA_ANDROID = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/141.0.0.0 Mobile Safari/537.36")
UA_SAMSUNG = ("Mozilla/5.0 (Linux; Android 10; SAMSUNG SM-A515F) AppleWebKit/537.36 (KHTML, like Gecko) "
              "SamsungBrowser/25.0 Chrome/121.0 Mobile Safari/537.36")
UA_WINDOWS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/141.0.0.0 Safari/537.36")
TELEFON = {"model": "SM-A515F", "gpu": "Mali-G72", "ekran": [915, 412], "dpr": 2.625,
           "yadro": 8, "xotira": 4, "teginish": 5, "vaqt": "Asia/Tashkent"}
BOSHQA_TELEFON = {**TELEFON, "model": "Redmi Note 12", "gpu": "Adreno 610"}
NOUTBUK = {"gpu": "ANGLE (Intel, Intel(R) UHD Graphics 620)", "ekran": [1920, 1080], "dpr": 1,
           "yadro": 8, "xotira": 8, "teginish": 0, "vaqt": "Asia/Tashkent"}


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class SoxtaKalit:
    """Dasturiy qurilma kaliti — telefondagi kalitni taqlid qiladi (faqat testlar uchun)."""

    def __init__(self):
        self.kalit = ec.generate_private_key(ec.SECP256R1())
        self.kalit_id = os.urandom(16)

    def _malumot(self, rp_id, bayroqlar, qoshimcha=b""):
        return hashlib.sha256(rp_id.encode()).digest() + bytes([bayroqlar]) + struct.pack(">I", 0) + qoshimcha

    def _mijoz(self, turi, sozlama):
        return json.dumps({"type": turi, "challenge": sozlama["challenge"], "origin": ORIGIN,
                           "crossOrigin": False}).encode()

    def yarat(self, sozlama):
        r = self.kalit.public_key().public_numbers()
        ochiq = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: r.x.to_bytes(32, "big"), -3: r.y.to_bytes(32, "big")})
        qoshimcha = b"\0" * 16 + struct.pack(">H", len(self.kalit_id)) + self.kalit_id + ochiq
        malumot = self._malumot(sozlama["rp"]["id"], 0x45, qoshimcha)  # UP | UV | AT
        return {"id": _b64(self.kalit_id), "rawId": _b64(self.kalit_id), "type": "public-key",
                "response": {"clientDataJSON": _b64(self._mijoz("webauthn.create", sozlama)),
                             "attestationObject": _b64(cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": malumot}))}}

    def tasdiqla(self, sozlama):
        mijoz = self._mijoz("webauthn.get", sozlama)
        malumot = self._malumot(sozlama["rpId"], 0x05)  # UP | UV
        imzo = self.kalit.sign(malumot + hashlib.sha256(mijoz).digest(), ec.ECDSA(hashes.SHA256()))
        return {"id": _b64(self.kalit_id), "rawId": _b64(self.kalit_id), "type": "public-key",
                "response": {"clientDataJSON": _b64(mijoz), "authenticatorData": _b64(malumot),
                             "signature": _b64(imzo)}}


@override_settings(WEBAUTHN_ORIGINS=[ORIGIN])
class QurilmaAsos(DrosselsizTest):
    def setUp(self):
        super().setUp()
        self.talaba = User.objects.create_user(username="talaba", password=PAROL, role=User.Role.STUDENT)
        self.admin = User.objects.create_user(username="admin1", password=PAROL, role=User.Role.ADMIN)
        self.owner = _owner_yarat("owner")
        self.admin_klient = APIClient()
        self.admin_klient.force_authenticate(self.admin)

    def kirish(self, qid, belgilar=TELEFON, ua=UA_ANDROID, username="talaba", kalit=False):
        tana = {"username": username, "password": PAROL, "qurilma_id": qid, "qurilma_belgilari": belgilar}
        if kalit:
            tana["kalit_qollaydi"] = True
        return APIClient().post("/api/token/", tana, format="json", HTTP_USER_AGENT=ua, HTTP_ORIGIN=ORIGIN)

    def klient(self, javob):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer " + javob.data["access"], HTTP_ORIGIN=ORIGIN)
        return c

    def profil(self, javob):
        return self.klient(javob).get("/api/profil/")

    def kalit_yarat(self, javob, soxta):
        c = self.klient(javob)
        r = c.post("/api/qurilma/kalit/boshlash/")
        self.assertEqual(r.status_code, 200, r.data)
        return c.post("/api/qurilma/kalit/saqlash/", {"chipta": r.data["chipta"], "javob": soxta.yarat(r.data["kalit"])},
                      format="json")

    def ikkinchi_bosqich(self, javob, soxta=None, kalitsiz=False):
        self.assertEqual((javob.status_code, javob.data.get("kod")), (409, "kalit_kerak"), javob.data)
        tana = {"chipta": javob.data["chipta"]}
        if kalitsiz:
            tana["kalitsiz"] = True
        else:
            tana["javob"] = soxta.tasdiqla(javob.data["kalit"])
        return APIClient().post("/api/token/kalit/", tana, format="json", HTTP_ORIGIN=ORIGIN)

    def amal(self, qurilma, amal, **tana):
        return self.admin_klient.post(f"/api/qurilmalar/{qurilma.pk}/amal/", {"amal": amal, **tana}, format="json")

    def qurilmalar(self, holat=None):
        qs = Qurilma.objects.filter(foydalanuvchi=self.talaba)
        return list(qs.filter(holat=holat) if holat else qs)


class KirishTest(QurilmaAsos):
    def test_birinchi_qurilma_va_tanish_brauzer(self):
        r = self.kirish("tel-1")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(AccessToken(r.data["access"])["qid"], "tel-1")
        self.assertEqual(self.profil(r).status_code, 200)
        [q] = self.qurilmalar()
        self.assertEqual((q.holat, q.nom), ("ruxsat", "Android · SM-A515F"))
        self.assertEqual(self.kirish("tel-1").status_code, 200)
        self.assertEqual(Qurilma.objects.count(), 1)
        self.assertEqual(list(KirishJurnali.objects.values_list("sabab", flat=True).order_by("id")),
                         ["yangi_qurilma", "tanish"])

    def test_login_boshi_va_oxiridagi_bosh_joy(self):
        """2026-10-28 xatosi: bo'sh joyli login qurilma tekshiruvini chetlab o'tib,
        kalit belgisiz berilardi va keyingi so'rovda «Вход с этого устройства закрыт» chiqardi."""
        for login in ("talaba ", " talaba"):
            r = self.kirish("tel-1", username=login)
            self.assertEqual(r.status_code, 200, r.data)
            self.assertEqual(AccessToken(r.data["access"])["qid"], "tel-1")
            self.assertEqual(self.profil(r).status_code, 200)

    def test_limitdan_tashqari_qurilma_sorov_va_adminga_bitta_xabar(self):
        self.kirish("tel-1")
        r = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.assertEqual(r.status_code, 403)
        self.assertEqual((r.data["kod"], r.data["sabab"], r.data["sorov"]), ("qurilma_mos_emas", "sorov_yuborildi", "kutilmoqda"))
        self.assertNotIn("access", r.data)
        [s] = self.qurilmalar("kutilmoqda")
        xabar = Bildirishnoma.objects.get(foydalanuvchi=self.admin)
        self.assertEqual(xabar.havola, f"/qurilmalar?holat=kutilmoqda&foydalanuvchi={self.talaba.pk}")
        r = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.assertEqual(r.data["sabab"], "sorov_kutilmoqda")
        s.refresh_from_db()
        self.assertEqual(s.urinishlar, 2)
        self.assertEqual(Bildirishnoma.objects.filter(foydalanuvchi=self.admin).count(), 1)
        # Yangi qurilma eskisining o'rnini egallamaydi.
        self.assertEqual(self.kirish("tel-1").status_code, 200)

    def test_qurilma_id_yoq_va_owner_tekshiruvsiz(self):
        r = APIClient().post("/api/token/", {"username": "talaba", "password": PAROL}, format="json")
        self.assertEqual((r.status_code, r.data["kod"]), (400, "qurilma_id_yoq"))
        for _ in range(2):
            r = APIClient().post("/api/token/", {"username": "owner", "password": PAROL}, format="json")
            self.assertEqual(r.status_code, 200, r.data)
            self.assertEqual(self.profil(r).status_code, 200)
        self.assertFalse(Qurilma.objects.filter(foydalanuvchi=self.owner).exists())

    def test_60_kun_ishlatilmagan_qurilma_joyni_boshatadi(self):
        self.kirish("tel-1")
        Qurilma.objects.update(oxirgi=timezone.now() - timedelta(days=61))
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual([q.nom for q in self.qurilmalar()], ["Windows"])


class KalitTest(QurilmaAsos):
    def test_kalit_yaratish_va_profil(self):
        r = self.kirish("tel-1")
        self.assertEqual(self.profil(r).data["qurilma"], {"nom": "Android · SM-A515F", "kalit_bor": False})
        self.assertEqual(self.kalit_yarat(r, SoxtaKalit()).status_code, 200)
        self.assertTrue(self.profil(r).data["qurilma"]["kalit_bor"])
        self.assertEqual(QurilmaKaliti.objects.count(), 1)

    def test_tarix_tozalansa_yoki_boshqa_brauzer_kalit_bilan_shu_qurilma(self):
        kalit = SoxtaKalit()
        birinchi = self.kirish("tel-1")
        self.kalit_yarat(birinchi, kalit)
        # Tarix tozalandi (yangi brauzer ID) — admin'siz, o'sha qurilma.
        r = self.ikkinchi_bosqich(self.kirish("tel-2", kalit=True), kalit)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.profil(r).status_code, 200)
        # Shu telefondagi Samsung Internet — ham o'sha qurilma.
        r = self.ikkinchi_bosqich(self.kirish("tel-samsung", ua=UA_SAMSUNG, kalit=True), kalit)
        self.assertEqual(r.status_code, 200, r.data)
        [q] = self.qurilmalar()
        self.assertEqual(sorted(q.brauzerlar.values_list("qid", flat=True)), ["tel-1", "tel-2", "tel-samsung"])
        self.assertFalse(self.qurilmalar("kutilmoqda"))
        # Bitta seans: oldingi brauzerdagi seans yopildi.
        self.assertEqual(self.profil(birinchi).data["kod"], "boshqa_qurilmada")

    def test_kalitsiz_bosilsa_yangi_qurilma(self):
        self.kalit_yarat(self.kirish("tel-1"), SoxtaKalit())
        r = self.ikkinchi_bosqich(self.kirish("nout-1", NOUTBUK, UA_WINDOWS, kalit=True), kalitsiz=True)
        self.assertEqual((r.status_code, r.data["sabab"]), (403, "sorov_yuborildi"))

    def test_kalit_boshqa_telefonda_bolsa_sorov(self):
        """Kalit Google akkaunti orqali boshqa telefonga o'tgan — model mos emas, admin hal qiladi."""
        kalit = SoxtaKalit()
        self.kalit_yarat(self.kirish("tel-1"), kalit)
        r = self.ikkinchi_bosqich(self.kirish("tel-dost", BOSHQA_TELEFON, kalit=True), kalit)
        self.assertEqual((r.status_code, r.data["sabab"]), (403, "sorov_yuborildi"))
        self.assertTrue(KirishJurnali.objects.filter(sabab="kalit_boshqa_telefon").exists())

    def test_tasdiqni_qayta_ishlatib_bolmaydi(self):
        kalit = SoxtaKalit()
        self.kalit_yarat(self.kirish("tel-1"), kalit)
        javob = self.kirish("tel-2", kalit=True)
        tana = {"chipta": javob.data["chipta"], "javob": kalit.tasdiqla(javob.data["kalit"])}
        self.assertEqual(APIClient().post("/api/token/kalit/", tana, format="json").status_code, 200)
        BrauzerEslatmasi.objects.filter(qid="tel-2").delete()
        qayta = APIClient().post("/api/token/kalit/", tana, format="json")
        self.assertEqual((qayta.status_code, qayta.data["kod"]), (400, "kalit_xatosi"))

    def test_eski_frontend_kalit_bosqichisiz(self):
        """Eski frontend `kalit_qollaydi` yubormaydi — login odatdagi yo'ldan ketadi."""
        self.kalit_yarat(self.kirish("tel-1"), SoxtaKalit())
        r = self.kirish("tel-2")
        self.assertEqual((r.status_code, r.data["kod"]), (403, "qurilma_mos_emas"))


class SeansTest(QurilmaAsos):
    def test_talabada_bir_vaqtda_bitta_seans(self):
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        a = self.kirish("tel-1")
        b = self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.assertEqual(b.status_code, 200)
        self.assertEqual(self.profil(a).data["kod"], "boshqa_qurilmada")
        self.assertEqual(self.profil(b).status_code, 200)
        yangilash = APIClient().post("/api/token/refresh/", {"refresh": a.data["refresh"]}, format="json")
        self.assertEqual(yangilash.status_code, 401)
        self.assertTrue(KirishJurnali.objects.filter(natija="chiqarildi", sabab="boshqa_joyda").exists())

    def test_xodimda_ikki_qurilma_birga_ishlaydi(self):
        User.objects.create_user(username="ustoz", password=PAROL, role=User.Role.TEACHER, qurilma_limiti=2)
        a = self.kirish("tel-1", username="ustoz")
        b = self.kirish("nout-1", NOUTBUK, UA_WINDOWS, username="ustoz")
        self.assertEqual((self.profil(a).status_code, self.profil(b).status_code), (200, 200))

    def test_kalit_yangilash_ishlaydi(self):
        r = self.kirish("tel-1")
        y = APIClient().post("/api/token/refresh/", {"refresh": r.data["refresh"]}, format="json")
        self.assertEqual(y.status_code, 200, y.data)
        self.assertEqual(AccessToken(y.data["access"])["sid"], AccessToken(r.data["access"])["sid"])


class AdminAmallariTest(QurilmaAsos):
    def sorov(self):
        self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        return self.qurilmalar("kutilmoqda")[0]

    def test_ruxsat_limitni_oshiradi(self):
        s = self.sorov()
        self.assertEqual(self.amal(s, "ruxsat").status_code, 200)
        self.talaba.refresh_from_db()
        self.assertEqual(self.talaba.qurilma_limiti, 2)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertTrue(Bildirishnoma.objects.get(foydalanuvchi=self.admin).oqilgan)

    def test_orniga_eski_qurilma_darhol_chiqadi(self):
        eski = self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        s, [q] = self.qurilmalar("kutilmoqda")[0], self.qurilmalar("ruxsat")
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.amal(s, "orniga", boshqa=q.pk).status_code, 200)
        self.assertEqual(self.profil(eski).data["kod"], "qurilma_ochirildi")
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual(self.kirish("tel-1").status_code, 403)

    def test_shu_qurilmaga_qoshish_yangi_joy_egallamaydi(self):
        s = self.sorov()
        [q] = self.qurilmalar("ruxsat")
        self.assertEqual(self.amal(s, "shu_qurilmaga", boshqa=q.pk).status_code, 200)
        self.assertEqual(self.kirish("nout-1", NOUTBUK, UA_WINDOWS).status_code, 200)
        self.assertEqual(len(self.qurilmalar()), 1)

    def test_bloklash_kaliti_bilan_va_blokdan_chiqarish(self):
        kalit = SoxtaKalit()
        r = self.kirish("tel-1")
        self.kalit_yarat(r, kalit)
        [q] = self.qurilmalar()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.amal(q, "blokla").status_code, 200)
        self.assertEqual(self.profil(r).data["kod"], "qurilma_bloklandi")
        self.assertEqual(self.kirish("tel-1").data["sabab"], "bloklangan")
        # Tarixni tozalab, kalit bilan kirishga urinsa ham — bloklangan.
        b = self.ikkinchi_bosqich(self.kirish("tel-9", kalit=True), kalit)
        self.assertEqual((b.status_code, b.data["sabab"]), (403, "bloklangan"))
        self.assertEqual(self.amal(q, "blokla").status_code, 400)
        self.assertEqual(self.amal(q, "blokdan_chiqar").status_code, 200)
        self.assertEqual(self.kirish("tel-9").status_code, 200)

    def test_ochirish_va_seans_yopish_va_limit(self):
        r = self.kirish("tel-1")
        url = f"/api/qurilmalar/foydalanuvchi/{self.talaba.pk}/"
        self.assertEqual(self.admin_klient.post(url, {"amal": "seans_yop"}, format="json").status_code, 200)
        self.assertEqual(self.profil(r).data["kod"], "boshqa_qurilmada")
        self.assertEqual(self.admin_klient.post(url, {"amal": "limit", "limit": 0}, format="json").status_code, 400)
        self.assertEqual(self.admin_klient.post(url, {"amal": "limit", "limit": 3}, format="json").status_code, 200)
        self.talaba.refresh_from_db()
        self.assertEqual(self.talaba.qurilma_limiti, 3)
        [q] = self.qurilmalar()
        self.assertEqual(self.amal(q, "ochir").status_code, 200)
        self.assertFalse(self.qurilmalar())
        jurnal = self.admin_klient.get(url).data
        self.assertEqual([j["sabab"] for j in jurnal][:3], ["ochir", "limit", "admin_seans_yopdi"])

    def test_oyna_royxati_va_ruxsatlar(self):
        self.sorov()
        javob = self.admin_klient.get("/api/qurilmalar/")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob.data["sanoq"], {"hammasi": 2, "kutilmoqda": 1, "blok": 0, "kalitsiz": 1})
        [odam] = javob.data["foydalanuvchilar"]
        self.assertEqual((odam["username"], odam["limit"], odam["ruxsat_soni"]), ("talaba", 1, 1))
        self.assertEqual(odam["seans"]["qurilma"], "Android · SM-A515F")
        self.assertNotIn("tel-1", json.dumps(javob.data, default=str))  # brauzer ID tashqariga chiqmaydi
        self.assertEqual(len(self.admin_klient.get("/api/qurilmalar/?holat=blok").data["foydalanuvchilar"]), 0)
        # Qurilmasiz foydalanuvchi — `foydalanuvchi` bilan ko'rinadi (limitni oldindan qo'yish uchun).
        yangi = User.objects.create_user(username="yangi", password=PAROL, role=User.Role.STUDENT)
        royxat = self.admin_klient.get(f"/api/qurilmalar/?foydalanuvchi={yangi.pk}").data["foydalanuvchilar"]
        self.assertEqual([o["username"] for o in royxat], ["yangi"])
        ustoz = User.objects.create_user(username="ustoz", password=PAROL, role=User.Role.TEACHER)
        c = APIClient()
        c.force_authenticate(ustoz)
        self.assertEqual(c.get("/api/qurilmalar/").status_code, 403)


class EskiTizimBilanMoslikTest(QurilmaAsos):
    def test_eski_formatdan_kochirish_takrorlansa_ham_xavfsiz(self):
        hozir = timezone.now().isoformat()
        self.talaba.qurilmalar = [
            {"k": "abc", "nom": "Android · SM-A515F", "qoshilgan": hozir, "oxirgi": hozir,
             "brauzerlar": [{"id": "tel-1", "brauzer": "Chrome", "belgilar": TELEFON, "qoshilgan": hozir, "oxirgi": hozir}]},
            {"id": "nout-eski", "belgilar": {**NOUTBUK, "tizim": "Windows"}, "qoshilgan": hozir, "oxirgi": hozir},
        ]
        self.talaba.save(update_fields=["qurilmalar"])
        QurilmaSorovi.objects.create(foydalanuvchi=self.talaba, qid="kutgan", nom="X", belgilar={})
        QurilmaSorovi.objects.create(foydalanuvchi=self.talaba, qid="blok-1", nom="Y", belgilar={}, holat="blok")
        sanoq = kochir(User, Qurilma, BrauzerEslatmasi, QurilmaSorovi, sorovlar=True)
        self.assertEqual(sanoq, {"qurilma": 2, "brauzer": 4, "sorov": 1, "blok": 1})
        self.assertEqual(sorted(q.holat for q in self.qurilmalar()), ["blok", "kutilmoqda", "ruxsat", "ruxsat"])
        self.assertEqual(Qurilma.objects.get(brauzerlar__qid="tel-1").k, "abc")
        # Eski brauzerdagi seans (belgisiz eski kalit ham) ishlayveradi.
        from accounts.tests import qurilmali_kalit
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {qurilmali_kalit(self.talaba, 'tel-1').access_token}")
        self.assertEqual(c.get("/api/profil/").status_code, 200)
        # Qayta ishga tushirish hech narsa qo'shmaydi; admin hal qilgan so'rov qaytib kelmaydi.
        Qurilma.objects.filter(holat="kutilmoqda").delete()
        self.assertEqual(kochir(User, Qurilma, BrauzerEslatmasi, QurilmaSorovi),
                         {"qurilma": 0, "brauzer": 0, "sorov": 0, "blok": 0})

    def test_eski_formatga_nusxa(self):
        self.talaba.qurilma_limiti = 2
        self.talaba.save(update_fields=["qurilma_limiti"])
        self.kirish("tel-1")
        self.kirish("nout-1", NOUTBUK, UA_WINDOWS)
        self.talaba.refresh_from_db()
        royxat = self.talaba.qurilmalar
        self.assertEqual([[b["id"] for b in d["brauzerlar"]] for d in royxat], [["tel-1"], ["nout-1"]])
        self.assertEqual({d["id"] for d in royxat}, {"tel-1", "nout-1"})
        windows = Qurilma.objects.get(brauzerlar__qid="nout-1")
        self.assertEqual(self.talaba.faol_qurilma, windows.k)
        self.assertEqual(self.amal(windows, "blokla").status_code, 200)
        self.talaba.refresh_from_db()
        self.assertEqual([d["id"] for d in self.talaba.qurilmalar], ["tel-1"])
        self.assertEqual(list(QurilmaSorovi.objects.filter(holat="blok").values_list("qid", flat=True)), ["nout-1"])
        self.assertEqual(self.amal(windows, "blokdan_chiqar").status_code, 200)
        self.assertFalse(QurilmaSorovi.objects.filter(holat="blok").exists())
        self.assertEqual(FaolSeans.objects.get(foydalanuvchi=self.talaba).qurilma, windows)
