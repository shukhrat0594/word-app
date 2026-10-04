"""Ota-onaga xabar yuborish: davomat, to'lov, qarz eslatmasi, natijalar yig'masi.

Signal ISHLATILMAYDI (CRM qoidasi) — davriy tekshiruv:

1. `skanerla_*`: yangi voqealarni topib, ulangan ota-onalar uchun `Xabar` yaratadi
   (`abonent + kalit` yagona — bir voqea uchun ikki marta xabar yo'q).
   - davomat: "kelmadi"/"kechikdi"/"sababli" — `KECHIKISH` dan keyin (admin adashib qo'yib tuzatsa,
     ota-onaga xato xabar ketmasin);
   - to'lov: yangi `crm.Tolov` (faqat `turi=tolov`) — ham `KECHIKISH` bilan (summa xato kiritilib
     o'chirilsa/tuzatilsa — bekor);
   - qarz: sozlamadagi kun va soatda, balansi manfiy farzand uchun (kuniga bitta, kalitda sana);
   - natija: sozlamadagi kun va soatda, oldingi yig'madan beri bajarilgan mashq/Writing/Speaking
     yig'masi. Hech narsa qilinmagan bo'lsa — xabar yo'q (spam bo'lmasin).
2. `yubor_navbat`: vaqti kelgan xabarlarni yuboradi. Yuborishdan oldin qayta tekshiradi
   (davomat/to'lov o'zgargan yoki o'chirilgan, qarz to'langan, ota-ona to'xtatgan, sozlama
   o'chirilgan — bekor qilinadi). Tinch soatlarda hech narsa yuborilmaydi — xabar kutadi.

Eski voqealar yog'ilib ketmasin: davomat va to'lov faqat birinchi tekshiruvdan KEYIN yaratilgan
yozuvlar uchun (`ParentsBotKuzatuv`), qarz/natija esa bir kundan eski bo'lsa yuborilmaydi.

`crm.mantiq` (billing) faqat O'QILADI.
"""

import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from academics.models import Davomat
from assessment.models import SpeakingTekshiruv, WritingTekshiruv
from courses.models import KursMashqYechim
from crm.mantiq import balans, balanslarni_ol
from crm.models import Tolov
from exercises.models import MashqYechim

from . import matnlar
from .models import Boglanish, ParentsBotKuzatuv, ParentsBotSozlama, Xabar
from .moslash import talaba_ismi
from .telegram import TgXato

log = logging.getLogger("parentsbot")

KECHIKISH = timedelta(minutes=5)
URINISH_CHEGARASI = 5
YOSH_KUNLAR = 1  # shuncha kun oldingi sanagacha bo'lgan davomatlar xabar beradi (kecha va bugun)
TOLOV_YOSHI = timedelta(days=2)  # bot uzoq to'xtab qolsa ham, bundan eski to'lov xabar bermaydi
ESKIRISH_KUNLARI = 1  # qarz/natija xabari shuncha kundan ko'p kutib qolsa — bekor (eskirgan)
TOIFALAR = ("davomat", "tolov", "qarz", "natija")


def tinch_mi(vaqt, boshi, oxiri):
    """Tinch soatlarmi? Yarim tundan oshadigan oraliq (22:00-08:00) ham to'g'ri ishlaydi."""
    if boshi == oxiri:
        return False
    if boshi < oxiri:
        return boshi <= vaqt < oxiri
    return vaqt >= boshi or vaqt < oxiri


def toifa_yoqilgan(sozlama, turi):
    """Markaz sozlamasida shu toifa yoqilganmi (ota-ona o'zi o'chirganidan qat'i nazar)."""
    return bool(getattr(sozlama, f"{turi}_yoqilgan", False))


def summa_matni(summa):
    """1250000 -> '1 250 000'."""
    return f"{int(abs(Decimal(summa))):,}".replace(",", " ")


# ── umumiy yordamchilar ────────────────────────────────────────────

def _abonentlar():
    """{talaba_id: [abonent, ...]} — faol ota-onalar, faol bog'lanishlar, faol o'quvchilar."""
    xarita = {}
    for b in Boglanish.objects.filter(faol=True, abonent__faol=True, talaba__is_active=True) \
            .select_related("abonent"):
        xarita.setdefault(b.talaba_id, []).append(b.abonent)
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


def _jadval_vaqti(hozir, kunlar, soat):
    """Bugun jadval kunimi va soati o'tganmi? Qaytaradi: mahalliy sana yoki None."""
    mahalliy = timezone.localtime(hozir)
    if mahalliy.weekday() not in (kunlar or []) or mahalliy.time() < soat:
        return None
    return mahalliy.date()


# ── davomat ────────────────────────────────────────────────────────

def davomat_kodi(d):
    """Davomat yozuvi -> 'kelmadi' | 'sababli' | 'kechikdi' | None (xabar kerak emas)."""
    izoh = getattr(d, "crm_izoh", None)  # CRM belgilari (bo'lmasa — None)
    if d.holat == Davomat.Holat.KELMADI:
        return "sababli" if izoh is not None and izoh.sababli else "kelmadi"
    if izoh is not None and izoh.kechikdi:
        return "kechikdi"
    return None


def _kod_yoqilgan(sozlama, kod):
    if not sozlama.davomat_yoqilgan:
        return False
    return {"kelmadi": sozlama.davomat_kelmadi, "kechikdi": sozlama.davomat_kechikdi,
            "sababli": sozlama.davomat_sababli}.get(kod, False)


def skanerla_davomat(hozir=None):
    """Yangi xabarlar sonini qaytaradi. Birinchi chaqiruv faqat boshlanish vaqtini belgilaydi."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.davomat_boshlandi is None:
        kuzatuv.davomat_boshlandi = hozir
        kuzatuv.save(update_fields=["davomat_boshlandi"])
        return 0
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.davomat_yoqilgan:
        return 0
    xarita = _abonentlar()
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
        if not kod or not _kod_yoqilgan(sozlama, kod):
            continue
        payload = {"davomat_id": d.id, "kod": kod, "sana": d.sana.isoformat(), "guruh": d.guruh.name}
        for ab in xarita[d.talaba_id]:
            nomzodlar.append((ab, d.talaba_id, "davomat", f"davomat:{d.id}:{kod}", hozir + KECHIKISH, payload))
    return _navbatga(nomzodlar)


# ── to'lov ─────────────────────────────────────────────────────────

def skanerla_tolov(hozir=None):
    """Yangi to'lovlar (`turi=tolov`; chegirma/bonus/qaytarish — xabarsiz). Birinchi chaqiruv
    faqat boshlanish vaqtini belgilaydi."""
    hozir = hozir or timezone.now()
    kuzatuv = ParentsBotKuzatuv.ol()
    if kuzatuv.tolov_boshlandi is None:
        kuzatuv.tolov_boshlandi = hozir
        kuzatuv.save(update_fields=["tolov_boshlandi"])
        return 0
    if not ParentsBotSozlama.ol().tolov_yoqilgan:
        return 0
    xarita = _abonentlar()
    if not xarita:
        return 0
    nomzodlar = []
    tolovlar = Tolov.objects.filter(
        turi=Tolov.Turi.TOLOV, talaba_id__in=list(xarita),
        created_at__gte=max(kuzatuv.tolov_boshlandi, hozir - TOLOV_YOSHI),
    )
    for tl in tolovlar:
        payload = {"tolov_id": tl.id, "summa": str(tl.summa), "sana": tl.sana.isoformat(), "guruh": tl.guruh_nomi}
        for ab in xarita[tl.talaba_id]:
            nomzodlar.append((ab, tl.talaba_id, "tolov", f"tolov:{tl.id}", hozir + KECHIKISH, payload))
    return _navbatga(nomzodlar)


# ── qarz ───────────────────────────────────────────────────────────

def skanerla_qarz(hozir=None):
    """Qarz eslatmasi: sozlamadagi kunlarda, `qarz_soati`dan keyin. Balans — farzandning UMUMIY
    balansi (barcha guruh va filiallar bo'yicha). Kuniga bitta (kalitda sana)."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.qarz_yoqilgan:
        return 0
    sana = _jadval_vaqti(hozir, sozlama.qarz_kunlari, sozlama.qarz_soati)
    if sana is None:
        return 0
    xarita = _abonentlar()
    if not xarita:
        return 0
    nomzodlar = []
    for talaba_id, b in balanslarni_ol(list(xarita)).items():
        if b >= 0:
            continue
        for ab in xarita[talaba_id]:
            nomzodlar.append((ab, talaba_id, "qarz", f"qarz:{sana.isoformat()}", hozir, {"sana": sana.isoformat()}))
    return _navbatga(nomzodlar)


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


def natijalar(talaba_idlar, boshi, oxiri):
    """{talaba_id: {"mashq_soni", "mashq_foiz", "writing_soni", "writing_band", "speaking_soni",
    "speaking_band"}} — faqat davrda biror natijasi bor talabalar. To'plam so'rovlar (N+1 yo'q),
    xuddi CRM `GuruhNatijalarView` dagidek manbalar + Kurslar mashqlari."""
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
    for nom, model in (("writing", WritingTekshiruv), ("speaking", SpeakingTekshiruv)):
        for q in model.objects.filter(**oraliq, holat=model.Holat.TAYYOR, overall_band__isnull=False) \
                .values("talaba_id").annotate(soni=Count("id"), band=Avg("overall_band")):
            r = qator(q["talaba_id"])
            r[f"{nom}_soni"] = q["soni"]
            r[f"{nom}_band"] = round(q["band"], 1)
    for r in natija.values():
        ball, jami = r.pop("_ball"), r.pop("_jami")
        r["mashq_foiz"] = round(ball / jami * 100) if jami else None
    return natija


def skanerla_natija(hozir=None):
    """Natijalar yig'masi: sozlamadagi kunlarda, `natija_soati`dan keyin; kuniga bitta."""
    hozir = hozir or timezone.now()
    sozlama = ParentsBotSozlama.ol()
    if not sozlama.natija_yoqilgan:
        return 0
    sana = _jadval_vaqti(hozir, sozlama.natija_kunlari, sozlama.natija_soati)
    if sana is None:
        return 0
    xarita = _abonentlar()
    if not xarita:
        return 0
    boshi, oxiri = natija_davri(sana, sozlama.natija_kunlari, sozlama.natija_soati)
    nomzodlar = []
    for talaba_id, r in natijalar(list(xarita), boshi, oxiri).items():
        payload = {**r, "sana": sana.isoformat(), "boshi": timezone.localdate(boshi).isoformat()}
        for ab in xarita[talaba_id]:
            nomzodlar.append((ab, talaba_id, "natija", f"natija:{sana.isoformat()}", hozir, payload))
    return _navbatga(nomzodlar)


def skanerla_hammasi(hozir=None):
    hozir = hozir or timezone.now()
    return sum(f(hozir) for f in (skanerla_davomat, skanerla_tolov, skanerla_qarz, skanerla_natija))


# ── yuborish ───────────────────────────────────────────────────────

def _hali_yaroqli(x, sozlama, bugun):
    """Yuborishdan oldingi tekshiruv: bekor qilish kerakmi?"""
    ab = x.abonent
    if not ab.faol or x.turi in (ab.toifa_ochirilgan or []):
        return False
    if not x.talaba.is_active or not toifa_yoqilgan(sozlama, x.turi):
        return False
    if not Boglanish.objects.filter(abonent=ab, talaba_id=x.talaba_id, faol=True).exists():
        return False
    if x.turi == "davomat":
        d = Davomat.objects.filter(pk=x.payload.get("davomat_id")).select_related("crm_izoh").first()
        kod = x.payload.get("kod")
        return d is not None and davomat_kodi(d) == kod and _kod_yoqilgan(sozlama, kod)
    if x.turi == "tolov":
        tl = Tolov.objects.filter(pk=x.payload.get("tolov_id")).first()
        return (tl is not None and tl.turi == Tolov.Turi.TOLOV and tl.talaba_id == x.talaba_id
                and str(tl.summa) == x.payload.get("summa"))
    if x.turi in ("qarz", "natija"):
        if (bugun - date.fromisoformat(x.payload["sana"])).days > ESKIRISH_KUNLARI:
            return False  # bot uzoq to'xtab qolgan — eskirgan eslatma yuborilmaydi
        if x.turi == "qarz":
            return balans(x.talaba) < 0  # orada to'lagan bo'lsa — bekor
    return True


def _natija_matni(til, p, bugun):
    sana, boshi = date.fromisoformat(p["sana"]), date.fromisoformat(p["boshi"])
    if sana == bugun and (sana - boshi).days <= 1:
        davr = matnlar.t(til, "natija_bugun")
    else:
        davr = matnlar.t(til, "natija_davr", boshi=boshi.strftime("%d.%m"), oxiri=sana.strftime("%d.%m"))
    qatorlar = []
    if p.get("mashq_soni"):
        kalit = "natija_mashq_foiz" if p.get("mashq_foiz") is not None else "natija_mashq"
        qatorlar.append(matnlar.t(til, kalit, soni=p["mashq_soni"], foiz=p.get("mashq_foiz")))
    for nom in ("writing", "speaking"):
        if p.get(f"{nom}_soni"):
            qatorlar.append(matnlar.t(til, "natija_band", nom=nom.capitalize(), soni=p[f"{nom}_soni"],
                                      band=p[f"{nom}_band"]))
    return davr, "\n".join(qatorlar)


def _matn(x, bugun):
    ab, p = x.abonent, x.payload
    ism = talaba_ismi(x.talaba)
    if x.turi == "tolov":
        return matnlar.t(ab.til, "tolov_qabul", ism=ism, summa=summa_matni(p["summa"]),
                         sana=date.fromisoformat(p["sana"]).strftime("%d.%m.%Y"), guruh=p.get("guruh", ""))
    if x.turi == "qarz":
        return matnlar.t(ab.til, "qarz_eslatma", ism=ism, summa=summa_matni(balans(x.talaba)))
    if x.turi == "natija":
        davr, qatorlar = _natija_matni(ab.til, p, bugun)
        return matnlar.t(ab.til, "natija_yigma", ism=ism, davr=davr, qatorlar=qatorlar)
    sana = date.fromisoformat(p["sana"])
    return matnlar.t(
        ab.til, f"davomat_{p['kod']}",
        ism=ism, kun=matnlar.kun_matni(ab.til, sana, bugun), guruh=p.get("guruh", ""),
    )


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
        try:
            tg.yubor(x.abonent.telegram_id, _matn(x, bugun))
        except TgXato as xato:
            if "403" in str(xato):  # ota-ona botni bloklagan — boshqa urinmaymiz
                x.abonent.faol = False
                x.abonent.save(update_fields=["faol"])
                x.holat = Xabar.Holat.XATO
                x.save(update_fields=["holat"])
                log.info("Ota-ona botni bloklagan: xabarlar to'xtatildi")
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
