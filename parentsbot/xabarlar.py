"""Ota-onaga xabar yuborish: davomat, to'lov, qarz eslatmasi, natijalar yig'masi.

Signal ISHLATILMAYDI (CRM qoidasi) — davriy tekshiruv:

1. `skanerla_*`: yangi voqealarni topib, ulangan ota-onalar uchun `Xabar` yaratadi
   (`abonent + kalit` yagona — bir voqea uchun ikki marta xabar yo'q).
   - davomat: "kelmadi"/"kechikdi"/"sababli" — `KECHIKISH` dan keyin (admin adashib qo'yib tuzatsa,
     ota-onaga xato xabar ketmasin);
   - to'lov: yangi `crm.Tolov` (faqat `turi=tolov`) — ham `KECHIKISH` bilan (o'chirilsa — bekor,
     summa tuzatilsa — TO'G'RI summa bilan yuboriladi);
   - qarz: sozlamadagi kun va soatda, balansi manfiy farzand uchun (kuniga bitta);
   - natija: sozlamadagi kun va soatda, oldingi yig'madan beri bajarilgan mashq/Writing/Speaking/
     IELTS to'liq test (Reading/Listening) yig'masi. Hech narsa qilinmagan bo'lsa — xabar yo'q
     (spam bo'lmasin).
   - 2026-10-09: davomat "keldi" ham (`davomat_keldi`); IELTS to'liq test (Listening/Reading),
     Writing/Speaking va Kurslar Vocabulary natijasi — har biri sozlamaga qarab DARHOL alohida xabar
     (`skanerla_yechim`) yoki kunlik yig'mada (`ielts_rejimi`, `ws_rejimi`, `soz_rejimi`).
     Vocabulary — har unit uchun kuniga bitta xabar (yuborish paytidagi oxirgi natija bilan).
2. `yubor_navbat`: vaqti kelgan xabarlarni yuboradi. Yuborishdan oldin qayta tekshiradi
   (davomat o'zgargan, to'lov o'chirilgan, qarz to'langan, ota-ona botni bloklagan, sozlama o'chirilgan —
   bekor qilinadi). Tinch soatlarda hech narsa yuborilmaydi — xabar kutadi.

Eski voqealar yog'ilib ketmasin:
- davomat va to'lov — faqat birinchi tekshiruvdan (`ParentsBotKuzatuv`) va ota-ona ulangandan
  (`Boglanish.faollashgan`) KEYIN yaratilgan yozuvlar;
- markaz toifani o'chirgan yoki ota-ona botni bloklagan paytda ham davomat/to'lov xabari YARATILADI, faqat
  yuborishda bekor qilinadi. Shunda qayta yoqilganda/blokdan chiqqanda o'tgan voqealar bir yo'la ketmaydi;
- qarz/natija bir kundan ko'p kutib qolsa — yuborilmaydi (eskirgan).

`crm.mantiq` (billing) faqat O'QILADI.
"""

import logging
import math
import time
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from courses.models import KursMashqYechim, KursSozYechim
from crm.mantiq import balans, balanslarni_ol
from crm.models import GuruhMoliya, Tolov
from exercises.models import MashqYechim, TestYechim

from . import matnlar, xizmat
from .models import Boglanish, NatijaRejimi, ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from .moslash import talaba_ismi
from .telegram import TgXato

log = logging.getLogger("parentsbot")

KECHIKISH = timedelta(minutes=5)
URINISH_CHEGARASI = 5
QAYTA_URINISH = timedelta(minutes=1)  # yuborilmagan xabar shundan keyin qayta uriniladi
YOSH_KUNLAR = 1  # shuncha kun oldingi sanagacha bo'lgan davomatlar xabar beradi (kecha va bugun)
TOLOV_YOSHI = timedelta(days=2)  # bot uzoq to'xtab qolsa ham, bundan eski to'lov xabar bermaydi
ESKIRISH_KUNLARI = 1  # qarz/natija xabari shuncha kundan ko'p kutib qolsa — bekor (eskirgan)
# Natija yig'masi soatdan shuncha keyin tuziladi: soat chegarasida topshirilgan Writing/Speaking
# AI tekshiruvi tugab ulgursin (aks holda u bu yig'maga ham, keyingisiga ham tushmay qolardi).
NATIJA_KUTISH = timedelta(minutes=10)
# Darhol natija xabarlari (2026-10-09): bot to'xtab qolsa ham bundan eski yechimlar xabar bermaydi.
YECHIM_YOSHI = timedelta(days=1)
# Vocabulary'ni talaba ketma-ket bir necha marta tekshiradi — oxirgi urinish ham kirsin deb biroz kutiladi.
SOZ_KUTISH = timedelta(minutes=10)
# Natija turi -> sozlamadagi rejim maydoni (o'chiq / darhol / kunlik yig'mada).
REJIM_MAYDONLARI = {"ielts": "ielts_rejimi", "ws": "ws_rejimi", "soz": "soz_rejimi"}
# Telegram'ning bu xatolari doimiy — ota-onaga boshqa urinilmaydi.
DOIMIY_XATOLAR = ("403", "chat not found", "user is deactivated")


def tinch_mi(vaqt, boshi, oxiri):
    """Tinch soatlarmi? Yarim tundan oshadigan oraliq (22:00-08:00) ham to'g'ri ishlaydi."""
    if boshi == oxiri:
        return False
    if boshi < oxiri:
        return boshi <= vaqt < oxiri
    return vaqt >= boshi or vaqt < oxiri


def toifa_yoqilgan(sozlama, turi):
    """Markaz sozlamasida (CRM) shu toifa yoqilganmi. Natija turlari — faqat "darhol" rejimida."""
    if turi in REJIM_MAYDONLARI:
        return getattr(sozlama, REJIM_MAYDONLARI[turi]) == NatijaRejimi.DARHOL
    return bool(getattr(sozlama, f"{turi}_yoqilgan", False))


def band_matni(band):
    """6.5 -> '6.5', 7 -> '7.0' (IELTS ko'rinishi)."""
    return f"{float(band):.1f}"


def summa_matni(summa):
    """1250000 -> '1 250 000' (so'mgacha yaxlitlanadi)."""
    butun = abs(Decimal(summa)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return f"{int(butun):,}".replace(",", " ")


def band_yaxlitla(x):
    """IELTS qoidasi: eng yaqin 0.5 ga, o'rtasi yuqoriga (6.25 -> 6.5, 6.75 -> 7.0)."""
    return math.floor(x * 2 + 0.5) / 2


# ── umumiy yordamchilar ────────────────────────────────────────────

def _boglanishlar(faqat_faol=False):
    """{talaba_id: [Boglanish, ...]} — faol bog'lanishlar (`abonent` bilan).

    `faqat_faol=False` (davomat/to'lov): botni bloklagan ota-ona va nofaol o'quvchi ham kiradi — xabar
    yaratiladi-yu, yuborishda bekor qilinadi (blokdan chiqqanda eski voqealar yog'ilmasin).
    """
    q = Boglanish.objects.filter(faol=True).select_related("abonent")
    if faqat_faol:
        q = q.filter(abonent__faol=True, talaba__is_active=True)
    xarita = {}
    for b in q:
        xarita.setdefault(b.talaba_id, []).append(b)
    return xarita


def _navbatga(nomzodlar):
    """nomzodlar: [(abonent, talaba_id, turi, kalit, yuborilsin, payload)]. Bor kalitlar
    o'tkazib yuboriladi (bitta so'rov bilan tekshiriladi). Qaytaradi: yangi xabarlar soni."""
    if not nomzodlar:
        return 0
    mavjud = set(
        Xabar.objects.filter(kalit__in={n[3] for n in nomzodlar}).values_list("abonent_id", "kalit")
    )
    yangi, korildi = [], set()
    for ab, talaba_id, turi, kalit, yuborilsin, payload in nomzodlar:
        juft = (ab.id, kalit)
        if juft in mavjud or juft in korildi:
            continue
        korildi.add(juft)
        yangi.append(Xabar(abonent=ab, talaba_id=talaba_id, turi=turi, kalit=kalit,
                           yuborilsin=yuborilsin, payload=payload))
    # ignore_conflicts: parallel jarayon shu orada yaratgan bo'lsa ham xato emas
    Xabar.objects.bulk_create(yangi, ignore_conflicts=True)
    return len(yangi)


def _jadval_vaqti(hozir, kunlar, soat, kutish=timedelta(0)):
    """Bugun jadval kunimi va soat (+kutish) o'tganmi? Qaytaradi: mahalliy sana yoki None."""
    mahalliy = timezone.localtime(hozir)
    chegara = timezone.make_aware(datetime.combine(mahalliy.date(), soat)) + kutish
    if mahalliy.weekday() not in (kunlar or []) or hozir < chegara:
        return None
    return mahalliy.date()


# ── davomat ────────────────────────────────────────────────────────

def davomat_kodi(d):
    """Davomat yozuvi -> 'kelmadi' | 'sababli' | 'kechikdi' | 'keldi' (2026-10-09) | None."""
    izoh = getattr(d, "crm_izoh", None)  # CRM belgilari (bo'lmasa — None)
    if d.holat == Davomat.Holat.KELMADI:
        return "sababli" if izoh is not None and izoh.sababli else "kelmadi"
    if izoh is not None and izoh.kechikdi:
        return "kechikdi"
    return "keldi" if d.holat == Davomat.Holat.KELDI else None


def _kod_yoqilgan(sozlama, kod):
    if not sozlama.davomat_yoqilgan:
        return False
    return {"kelmadi": sozlama.davomat_kelmadi, "kechikdi": sozlama.davomat_kechikdi,
            "sababli": sozlama.davomat_sababli, "keldi": sozlama.davomat_keldi}.get(kod, False)


def skanerla_davomat(hozir=None):
    """Yangi xabarlar sonini qaytaradi. Birinchi chaqiruv faqat boshlanish vaqtini belgilaydi.

    Sozlamada o'chirilgan belgilar uchun ham xabar yaratiladi (yuborishda bekor bo'ladi) —
    sozlama keyin yoqilsa, o'tgan davomatlar ota-onaga bir yo'la ketmasin."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.davomat_boshlandi is None:
        kuzatuv.davomat_boshlandi = hozir
        kuzatuv.save(update_fields=["davomat_boshlandi"])
        return 0
    if kuzatuv.keldi_boshlandi is None:  # "keldi" yangi (2026-10-09) — eski davomatlar uchun xabar yo'q
        kuzatuv.keldi_boshlandi = hozir
        kuzatuv.save(update_fields=["keldi_boshlandi"])
    xarita = _boglanishlar()
    if not xarita:
        return 0
    bugun = timezone.localdate(hozir)
    nomzodlar = []
    yozuvlar = Davomat.objects.filter(
        sana__gte=bugun - timedelta(days=YOSH_KUNLAR), created_at__gte=kuzatuv.davomat_boshlandi,
        talaba_id__in=list(xarita),
    ).select_related("guruh", "crm_izoh")
    for d in yozuvlar:
        kod = davomat_kodi(d)
        if not kod or (kod == "keldi" and d.created_at < kuzatuv.keldi_boshlandi):
            continue
        payload = {"davomat_id": d.id, "kod": kod, "sana": d.sana.isoformat(), "guruh": d.guruh.name}
        for b in xarita[d.talaba_id]:
            if d.created_at >= b.faollashgan:
                nomzodlar.append((b.abonent, d.talaba_id, "davomat", f"davomat:{d.id}:{kod}",
                                  hozir + KECHIKISH, payload))
    return _navbatga(nomzodlar)


# ── to'lov ─────────────────────────────────────────────────────────

def skanerla_tolov(hozir=None):
    """Yangi to'lovlar (`turi=tolov`; chegirma/bonus/qaytarish — xabarsiz). Birinchi chaqiruv
    faqat boshlanish vaqtini belgilaydi. Sozlama o'chiq bo'lsa ham yaratiladi (davomatdagi sabab)."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.tolov_boshlandi is None:
        kuzatuv.tolov_boshlandi = hozir
        kuzatuv.save(update_fields=["tolov_boshlandi"])
        return 0
    xarita = _boglanishlar()
    if not xarita:
        return 0
    nomzodlar = []
    tolovlar = Tolov.objects.filter(
        turi=Tolov.Turi.TOLOV, talaba_id__in=list(xarita),
        created_at__gte=max(kuzatuv.tolov_boshlandi, hozir - TOLOV_YOSHI),
    )
    for tl in tolovlar:
        for b in xarita[tl.talaba_id]:
            if tl.created_at >= b.faollashgan:
                nomzodlar.append((b.abonent, tl.talaba_id, "tolov", f"tolov:{tl.id}", hozir + KECHIKISH,
                                  {"tolov_id": tl.id}))
    return _navbatga(nomzodlar)


# ── qarz ───────────────────────────────────────────────────────────

def skanerla_qarz(hozir=None):
    """Qarz eslatmasi: sozlamadagi kunlarda, `qarz_soati`dan keyin, kuniga BIR marta skanerlanadi.
    Balans — farzandning UMUMIY balansi (barcha guruh va filiallar bo'yicha)."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.qarz_yoqilgan:
        return 0
    sana = _jadval_vaqti(hozir, sozlama.qarz_kunlari, sozlama.qarz_soati)
    kuzatuv = ParentsBotKuzatuv.ol()
    if sana is None or kuzatuv.qarz_skanlandi == sana:
        return 0
    xarita = _boglanishlar(faqat_faol=True)
    nomzodlar = []
    for talaba_id, b in (balanslarni_ol(list(xarita)) if xarita else {}).items():
        if b > -1:  # so'mdan kam "qarz" (tiyinlar) — eslatma emas
            continue
        for bg in xarita[talaba_id]:
            nomzodlar.append((bg.abonent, talaba_id, "qarz", f"qarz:{talaba_id}:{sana.isoformat()}", hozir,
                              {"sana": sana.isoformat()}))
    yangi = _navbatga(nomzodlar)
    ParentsBotKuzatuv.objects.filter(pk=kuzatuv.pk).update(qarz_skanlandi=sana)
    return yangi


# ── natijalar yig'masi ─────────────────────────────────────────────

def natija_davri(sana, kunlar, soat):
    """Yig'ma davri: oldingi jadval kunidagi `soat` dan bugungi `soat` gacha (oraliq takrorlanmaydi
    va bo'sh qolmaydi). Har kuni bo'lsa — so'nggi 24 soat."""
    oxiri = timezone.make_aware(datetime.combine(sana, soat))
    for orqaga in range(1, 8):
        oldingi = sana - timedelta(days=orqaga)
        if oldingi.weekday() in kunlar:
            return timezone.make_aware(datetime.combine(oldingi, soat)), oxiri
    return oxiri - timedelta(days=7), oxiri


def natijalar(talaba_idlar, boshi, oxiri, rejimlar=None):
    """{talaba_id: {"mashq_soni", "mashq_foiz", "listening_soni", "listening_band",
    "reading_soni", "reading_band", "writing_soni", "writing_band", "speaking_soni",
    "speaking_band"}} — faqat davrda biror natijasi bor talabalar. To'plam so'rovlar (N+1 yo'q),
    xuddi CRM `GuruhNatijalarView` dagidek manbalar + Kurslar mashqlari.

    `rejimlar` (2026-10-09) — {"ielts"|"ws"|"soz": rejim}: yig'maga faqat "kunlik yig'mada" rejimidagi
    turlar kiradi (darhol yuborilganlari ikki marta bormasin). None — hammasi. Vocabulary endi
    "Mashqlar"ga qo'shilmaydi — alohida qator ("soz_soni", "soz_foiz")."""
    rejimlar = rejimlar or {}

    def yigmada(turi):
        return rejimlar.get(turi, NatijaRejimi.YIGMA) == NatijaRejimi.YIGMA

    oraliq = {"talaba_id__in": talaba_idlar, "created_at__gte": boshi, "created_at__lt": oxiri}
    natija = {}

    def qator(tid):
        return natija.setdefault(tid, {"mashq_soni": 0, "_ball": 0, "_jami": 0})

    for model in (MashqYechim, KursMashqYechim):
        for q in model.objects.filter(**oraliq).values("talaba_id") \
                .annotate(soni=Count("id"), ball=Sum("ball"), jami=Sum("jami")):
            r = qator(q["talaba_id"])
            r["mashq_soni"] += q["soni"]
            r["_ball"] += q["ball"] or 0
            r["_jami"] += q["jami"] or 0
    if yigmada("soz"):
        for q in KursSozYechim.objects.filter(**oraliq).values("talaba_id") \
                .annotate(soni=Count("id"), ball=Sum("ball"), jami=Sum("jami")):
            r = qator(q["talaba_id"])
            r["soz_soni"] = q["soni"]
            r["soz_foiz"] = round((q["ball"] or 0) / q["jami"] * 100) if q["jami"] else None
    for nom, model in (("writing", WritingTekshiruv), ("speaking", SpeakingTekshiruv)) if yigmada("ws") else ():
        for q in model.objects.filter(**oraliq, holat=model.Holat.TAYYOR, overall_band__isnull=False) \
                .values("talaba_id").annotate(soni=Count("id"), band=Avg("overall_band")):
            r = qator(q["talaba_id"])
            r[f"{nom}_soni"] = q["soni"]
            r[f"{nom}_band"] = band_yaxlitla(q["band"])
    # IELTS to'liq testlari (Reading/Listening, masalan "Cambridge 13 Test 4") —
    # Writing/Speaking kabi alohida band bilan (video-TZ 2026-10-08: CRM/LMS
    # "Natijalar" ro'yxatidagi test tarixi ota-onaga ham yig'ma orqali yetib borsin).
    for bolim in ("listening", "reading") if yigmada("ielts") else ():
        for q in TestYechim.objects.filter(**oraliq, test__bolim=bolim, band__isnull=False) \
                .values("talaba_id").annotate(soni=Count("id"), band=Avg("band")):
            r = qator(q["talaba_id"])
            r[f"{bolim}_soni"] = q["soni"]
            r[f"{bolim}_band"] = band_yaxlitla(float(q["band"]))
    for r in natija.values():
        ball, jami = r.pop("_ball"), r.pop("_jami")
        r["mashq_foiz"] = round(ball / jami * 100) if jami else None
    return natija


def skanerla_natija(hozir=None):
    """Natijalar yig'masi: sozlamadagi kunlarda, `natija_soati`dan (+`NATIJA_KUTISH`) keyin,
    kuniga BIR marta skanerlanadi."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.natija_yoqilgan:
        return 0
    sana = _jadval_vaqti(hozir, sozlama.natija_kunlari, sozlama.natija_soati, NATIJA_KUTISH)
    kuzatuv = ParentsBotKuzatuv.ol()
    if sana is None or kuzatuv.natija_skanlandi == sana:
        return 0
    xarita = _boglanishlar(faqat_faol=True)
    boshi, oxiri = natija_davri(sana, sozlama.natija_kunlari, sozlama.natija_soati)
    nomzodlar = []
    rejimlar = {turi: getattr(sozlama, maydon) for turi, maydon in REJIM_MAYDONLARI.items()}
    for talaba_id, r in (natijalar(list(xarita), boshi, oxiri, rejimlar) if xarita else {}).items():
        payload = {**r, "sana": sana.isoformat(), "boshi": timezone.localdate(boshi).isoformat()}
        for bg in xarita[talaba_id]:
            nomzodlar.append((bg.abonent, talaba_id, "natija", f"natija:{talaba_id}:{sana.isoformat()}", hozir,
                              payload))
    yangi = _navbatga(nomzodlar)
    ParentsBotKuzatuv.objects.filter(pk=kuzatuv.pk).update(natija_skanlandi=sana)
    return yangi


# ── darhol natijalar (2026-10-09) ──────────────────────────────────

def skanerla_yechim(hozir=None):
    """IELTS to'liq testi (L/R), Writing/Speaking (AI tekshiruvi tayyor) va Vocabulary — yangi yechimlar
    uchun darhol xabar. Birinchi chaqiruv faqat boshlanish vaqtini belgilaydi. Rejim "darhol" bo'lmasa ham
    yaratiladi — yuborishda bekor bo'ladi (rejim keyin almashtirilsa, o'tgan natijalar yog'ilmasin)."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.yechim_boshlandi is None:
        kuzatuv.yechim_boshlandi = hozir
        kuzatuv.save(update_fields=["yechim_boshlandi"])
        return 0
    xarita = _boglanishlar()
    if not xarita:
        return 0
    oraliq = {"talaba_id__in": list(xarita), "created_at__gte": max(kuzatuv.yechim_boshlandi, hozir - YECHIM_YOSHI)}
    nomzodlar = []

    def qosh(talaba_id, vaqt, turi, kalit, yuborilsin, payload):
        for b in xarita[talaba_id]:
            if vaqt >= b.faollashgan:
                nomzodlar.append((b.abonent, talaba_id, turi, kalit, yuborilsin, payload))

    for y in TestYechim.objects.filter(**oraliq).only("id", "talaba_id", "created_at"):
        qosh(y.talaba_id, y.created_at, "ielts", f"ielts:{y.id}", hozir + KECHIKISH, {"id": y.id})
    for nom, model in (("writing", WritingTekshiruv), ("speaking", SpeakingTekshiruv)):
        for y in model.objects.filter(**oraliq, holat=model.Holat.TAYYOR, overall_band__isnull=False) \
                .only("id", "talaba_id", "created_at"):
            qosh(y.talaba_id, y.created_at, "ws", f"{nom}:{y.id}", hozir + KECHIKISH, {"nom": nom, "id": y.id})
    for y in KursSozYechim.objects.filter(**oraliq).only("talaba_id", "tugun_id", "created_at"):
        sana = timezone.localdate(y.created_at).isoformat()
        qosh(y.talaba_id, y.created_at, "soz", f"soz:{y.talaba_id}:{y.tugun_id}:{sana}", hozir + SOZ_KUTISH,
             {"tugun_id": y.tugun_id, "sana": sana})
    return _navbatga(nomzodlar)


def _soz_yechimlari(talaba_id, p):
    """Shu kuni shu Vocabulary tuguni bo'yicha urinishlar (eng yangisi birinchi)."""
    return KursSozYechim.objects.filter(talaba_id=talaba_id, tugun_id=p.get("tugun_id"),
                                        created_at__date=date.fromisoformat(p["sana"])).order_by("-created_at")


def skanerla_hammasi(hozir=None):
    hozir = hozir or timezone.now()
    return sum(f(hozir) for f in (skanerla_davomat, skanerla_tolov, skanerla_qarz, skanerla_natija,
                                  skanerla_yechim))


# ── yuborish ───────────────────────────────────────────────────────

def _hali_yaroqli(x, sozlama, bugun):
    """Yuborishdan oldingi tekshiruv: bekor qilish kerakmi?"""
    ab = x.abonent
    if not ab.faol or not x.talaba.is_active or not toifa_yoqilgan(sozlama, x.turi):
        return False
    if not Boglanish.objects.filter(abonent=ab, talaba_id=x.talaba_id, faol=True).exists():
        return False
    if x.turi == "davomat":
        d = Davomat.objects.filter(pk=x.payload.get("davomat_id")).select_related("crm_izoh").first()
        kod = x.payload.get("kod")
        return (d is not None and d.talaba_id == x.talaba_id and davomat_kodi(d) == kod
                and _kod_yoqilgan(sozlama, kod))
    if x.turi == "tolov":
        tl = Tolov.objects.filter(pk=x.payload.get("tolov_id")).first()
        return tl is not None and tl.turi == Tolov.Turi.TOLOV and tl.talaba_id == x.talaba_id
    if x.turi == "ielts":
        return TestYechim.objects.filter(pk=x.payload.get("id"), talaba_id=x.talaba_id).exists()
    if x.turi == "ws":
        model = WritingTekshiruv if x.payload.get("nom") == "writing" else SpeakingTekshiruv
        return model.objects.filter(pk=x.payload.get("id"), talaba_id=x.talaba_id, holat=model.Holat.TAYYOR,
                                    overall_band__isnull=False).exists()
    if x.turi == "soz":
        return _soz_yechimlari(x.talaba_id, x.payload).exists()
    if x.turi in ("qarz", "natija"):
        if (bugun - date.fromisoformat(x.payload["sana"])).days > ESKIRISH_KUNLARI:
            return False  # bot uzoq to'xtab qolgan — eskirgan eslatma yuborilmaydi
        if x.turi == "qarz":
            return balans(x.talaba) <= -1  # orada to'lagan bo'lsa — bekor
    return True


def _natija_matni(til, p, bugun):
    sana, boshi = date.fromisoformat(p["sana"]), date.fromisoformat(p["boshi"])
    if sana == bugun and (sana - boshi).days <= 1:
        davr = matnlar.t(til, "natija_kunlik")
    else:
        davr = matnlar.t(til, "natija_davr", boshi=boshi.strftime("%d.%m"), oxiri=sana.strftime("%d.%m"))
    qatorlar = []
    if p.get("mashq_soni"):
        kalit = "natija_mashq_foiz" if p.get("mashq_foiz") is not None else "natija_mashq"
        qatorlar.append(matnlar.t(til, kalit, soni=p["mashq_soni"], foiz=p.get("mashq_foiz")))
    if p.get("soz_soni"):
        kalit = "natija_soz_foiz" if p.get("soz_foiz") is not None else "natija_soz"
        qatorlar.append(matnlar.t(til, kalit, soni=p["soz_soni"], foiz=p.get("soz_foiz")))
    for nom in ("listening", "reading", "writing", "speaking"):
        if p.get(f"{nom}_soni"):
            qatorlar.append(matnlar.t(til, "natija_band", nom=nom.capitalize(), soni=p[f"{nom}_soni"],
                                      band=p[f"{nom}_band"]))
    return davr, "\n".join(qatorlar)


def _guruh_filiali(guruh):
    """Guruhning JORIY filiali (CRM sozlamasi orqali), yoki None — sozlanmagan bo'lsa."""
    if guruh is None:
        return None
    gm = GuruhMoliya.objects.filter(guruh=guruh).select_related("filial").first()
    return gm.filial if gm else None


def _talaba_filiali(talaba):
    """Talabaning joriy (faol guruhi orqali aniqlangan) filiali, yoki None."""
    gm = GuruhMoliya.objects.filter(guruh__talabalar=talaba, guruh__faol=True) \
        .select_related("filial").order_by("guruh_id").first()
    return gm.filial if gm else None


def _filial_qatori(til, filial):
    """Davomat/to'lov/qarz xabari oxiriga qo'shiladigan filial+telefon qatori.

    Filial sozlanmagan yoki telefon kiritilmagan bo'lsa — qo'shilmaydi (bo'sh qator o'rniga)."""
    if not filial or not filial.telefon:
        return ""
    return "\n\n" + matnlar.t(til, "filial_izoh", filial=filial.nomi, telefon=filial.telefon)


def _matn(x, bugun):
    ab, p = x.abonent, x.payload
    ism = talaba_ismi(x.talaba)
    if x.turi == "tolov":
        tl = Tolov.objects.select_related("guruh").get(pk=p["tolov_id"])  # joriy qiymatlar
        matn = matnlar.t(ab.til, "tolov_qabul", ism=ism, summa=summa_matni(tl.summa),
                         sana=tl.sana.strftime("%d.%m.%Y"), guruh=tl.guruh_nomi)
        return matn + _filial_qatori(ab.til, _guruh_filiali(tl.guruh))
    if x.turi == "qarz":
        matn = matnlar.t(ab.til, "qarz_eslatma", ism=ism, summa=summa_matni(balans(x.talaba)))
        return matn + _filial_qatori(ab.til, _talaba_filiali(x.talaba))
    if x.turi == "natija":
        davr, qatorlar = _natija_matni(ab.til, p, bugun)
        return matnlar.t(ab.til, "natija_yigma", ism=ism, davr=davr, qatorlar=qatorlar)
    if x.turi == "ielts":
        y = TestYechim.objects.select_related("test").get(pk=p["id"])
        natija = (matnlar.t(ab.til, "band", band=band_matni(y.band)) if y.band is not None
                  else f"{y.ball}/{y.jami}")
        return matnlar.t(ab.til, "ielts_natija", ism=ism, bolim=y.test.get_bolim_display(), nomi=y.test.name,
                         natija=natija)
    if x.turi == "ws":
        model = WritingTekshiruv if p["nom"] == "writing" else SpeakingTekshiruv
        y = model.objects.get(pk=p["id"])
        return matnlar.t(ab.til, f"{p['nom']}_natija", ism=ism, band=band_matni(y.overall_band))
    if x.turi == "soz":
        urinishlar = list(_soz_yechimlari(x.talaba_id, p).select_related("tugun__parent"))
        y = urinishlar[0]
        tugun = y.tugun.parent or y.tugun  # "Unit 3" (Vocabulary tuguni Unit ichida)
        foiz = round(y.ball / y.jami * 100) if y.jami else 0
        matn = matnlar.t(ab.til, "soz_natija", ism=ism, nomi=tugun.nomi, ball=y.ball, jami=y.jami, foiz=foiz)
        if len(urinishlar) > 1:
            matn += " " + matnlar.t(ab.til, "soz_urinish", soni=len(urinishlar))
        return matn
    sana = date.fromisoformat(p["sana"])
    davomat = Davomat.objects.select_related("guruh").filter(pk=p.get("davomat_id")).first()
    matn = matnlar.t(
        ab.til, f"davomat_{p['kod']}",
        ism=ism, kun=matnlar.kun_matni(ab.til, sana, bugun), guruh=p.get("guruh", ""),
    )
    return matn + _filial_qatori(ab.til, _guruh_filiali(davomat.guruh) if davomat else None)


def yubor_navbat(tg, hozir=None, pauza=0.05):
    """Vaqti kelgan xabarlarni yuboradi. Qaytaradi: yuborilganlar soni."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if tinch_mi(timezone.localtime(hozir).time(), sozlama.tinch_boshi, sozlama.tinch_oxiri):
        return 0  # tinch soatlar: xabarlar kutadi
    bugun = timezone.localdate(hozir)
    yuborildi = 0
    navbat = Xabar.objects.filter(holat=Xabar.Holat.KUTILMOQDA, yuborilsin__lte=hozir) \
        .select_related("abonent", "talaba")[:100]
    for x in navbat:
        if not _hali_yaroqli(x, sozlama, bugun):
            x.holat = Xabar.Holat.BEKOR
            x.save(update_fields=["holat"])
            continue
        # Xabarni "egallash": ikkinchi jarayon (masalan deploy paytida eski va yangi bot birga
        # ishlab qolsa) shu xabarni ikkinchi marta yubormasin. Muvaffaqiyatsiz bo'lsa —
        # `QAYTA_URINISH` dan keyin yana navbatga chiqadi.
        if not Xabar.objects.filter(pk=x.pk, holat=Xabar.Holat.KUTILMOQDA, yuborilsin=x.yuborilsin) \
                .update(yuborilsin=hozir + QAYTA_URINISH):
            continue
        try:
            tg.yubor(x.abonent.telegram_id, _matn(x, bugun))
        except TgXato as xato:
            matn = str(xato)
            if "429" in matn:  # Telegram "sekinroq" demoqda — bu partiyani to'xtatamiz, urinish sanalmaydi
                log.warning("Telegram cheklovi (429): yuborish keyinroq davom etadi")
                break
            if any(m in matn for m in DOIMIY_XATOLAR):  # bloklagan / hisob o'chirilgan
                x.holat = Xabar.Holat.XATO
                x.save(update_fields=["holat"])
                if xizmat.bloklandi(x.abonent):  # markazga 🔔 bildirishnoma (bir marta)
                    log.info("Ota-onaga yetkazib bo'lmaydi (bloklagan yoki hisob yo'q): markazga xabar berildi")
                continue
            x.urinish += 1
            if x.urinish >= URINISH_CHEGARASI:
                x.holat = Xabar.Holat.XATO
            x.save(update_fields=["urinish", "holat"])
            log.warning("Xabar yuborilmadi (urinish %s): %s", x.urinish, type(xato).__name__)
            continue
        x.holat, x.yuborildi = Xabar.Holat.YUBORILDI, hozir
        x.save(update_fields=["holat", "yuborildi"])
        yuborildi += 1
        if pauza:
            time.sleep(pauza)  # Telegram: sekundiga ~30 xabar
    return yuborildi
