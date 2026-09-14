"""CRM moliya mantig'i — hisob generatsiyasi, narx, balans.

Bu modul ATAYLAB view'lardan ajratilgan: pul bilan bog'liq har bir qoida
BITTA joyda yozilishi kerak. Ikki nusxa vaqt o'tib bir-biridan uzoqlashadi
va farqni hech kim sezmaydi — pulda esa bu qimmatga tushadi.
"""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import models, transaction
from django.utils import timezone

from .models import AzolikMoliya, Hisob, Sozlama, Tolov

# Proporsional summa shuncha so'mgacha yaxlitlanadi. 660 000 / 12 * 7 =
# 385 000 kabi "chiroyli" son chiqishi uchun — kassada tiyin sanalmaydi.
YAXLITLASH = Decimal("1000")


# ── Sana yordamchilari ───────────────────────────────────────────────


def oy_boshi(sana: date) -> date:
    """Istalgan sanani o'sha oyning 1-sanasiga keltiradi.

    `Hisob.oy` HAR DOIM oyning 1-sanasi bo'lishi shart — `unique_together`
    shunga tayanadi, aks holda bir oyda bir nechta hisob paydo bo'lardi.
    """
    return sana.replace(day=1)


def oy_oxiri(oy: date) -> date:
    return oy.replace(day=calendar.monthrange(oy.year, oy.month)[1])


def keyingi_oy(oy: date) -> date:
    return date(oy.year + 1, 1, 1) if oy.month == 12 else date(oy.year, oy.month + 1, 1)


# ── Sozlama (bitta qatorli) ──────────────────────────────────────────


def sozlama_ol() -> Sozlama:
    """CRM sozlamasini qaytaradi, yo'q bo'lsa yaratadi.

    `boshlangich_oy` birinchi murojaatda JORIY oyga qo'yiladi — ya'ni
    tizim yoqilgunga qadar bo'lgan oylar uchun avtomatik qarz
    yaratilmaydi. Eski qarzlar qo'lda kiritiladi (TZ 4.7).
    """
    sozlama = Sozlama.objects.first()
    if sozlama is None:
        sozlama = Sozlama.objects.create(boshlangich_oy=oy_boshi(timezone.localdate()))
    return sozlama


# ── Narx: uch qavat ──────────────────────────────────────────────────


def amaldagi_narx(azolik_moliya: AzolikMoliya) -> Decimal | None:
    """Shu a'zolik uchun amaldagi oylik narx.

    Uch qavat, pastdan yuqoriga — birinchi to'ldirilgani olinadi:

        AzolikMoliya.narx   (bu talaba — aka-uka chegirmasi va h.k.)
              v bo'sh bo'lsa
        GuruhMoliya.narx    (bu guruh)
              v bo'sh bo'lsa
        KursNarxi.narx      (daraja — IELTS 660 000, Beginner 400 000)

    `None` qaytsa — narx hech qayerda belgilanmagan, hisob OCHILMAYDI va
    guruh ogohlantirishlar ro'yxatiga tushadi.

    Narx FAQAT shu funksiya orqali olinadi. Boshqa joyda `kurs_narxi`
    qidirilsa, uch qavatning biri unutiladi va admin kiritgan chegirma
    ishlamay qoladi.
    """
    if azolik_moliya.narx is not None:
        return azolik_moliya.narx

    guruh = azolik_moliya.azolik.guruh
    guruh_moliya = getattr(guruh, "moliya", None)
    if guruh_moliya is not None and guruh_moliya.narx is not None:
        return guruh_moliya.narx

    if guruh.daraja_id:
        kurs_narxi = getattr(guruh.daraja, "crm_narxi", None)
        if kurs_narxi is not None:
            return kurs_narxi.narx

    return None


# ── Dars kunlari ─────────────────────────────────────────────────────


def oylik_dars_kunlari(guruh, oy: date) -> list[date]:
    """Shu oydagi BARCHA dars sanalari — guruh yoki talaba sanasiga
    QARAMAYDI.

    Bu proporsional hisobning MAXRAJI. Guruh oynasi bilan kesishtirish
    ATAYLAB bu yerda qilinmaydi: avvalgi TZ shunday qilgan edi va
    15-sentabrda ochilgan guruhga to'liq narx yozib yuborardi (maxraj ham,
    surat ham 6 chiqib, nisbat 1 bo'lardi).

    Bitta kunda ikkita dars bo'lsa (ertalab + kechqurun), kun BIR MARTA
    sanaladi — narx oylik, dars soatiga bog'liq emas.
    """
    hafta_kunlari = set(guruh.crm_jadval.values_list("hafta_kuni", flat=True))
    if not hafta_kunlari:
        return []

    oxirgi_kun = calendar.monthrange(oy.year, oy.month)[1]
    return [
        date(oy.year, oy.month, kun)
        for kun in range(1, oxirgi_kun + 1)
        if date(oy.year, oy.month, kun).weekday() in hafta_kunlari
    ]


def talaba_dars_kunlari(azolik_moliya: AzolikMoliya, oy: date, oylik_kunlar: list[date]) -> list[date]:
    """Oylik dars kunlaridan SHU talabaga tegishlilari.

    Talabaning oynasi uchta chegaraning kesishmasi: oy, guruh oynasi,
    a'zolik oynasi. Shu bitta hisob-kitob uch xil holatni ham qoplaydi —
    guruh oy o'rtasida ochildi, talaba oy o'rtasida qo'shildi, talaba oy
    o'rtasida chiqdi.
    """
    guruh_moliya = getattr(azolik_moliya.azolik.guruh, "moliya", None)

    boshi = oy
    oxiri = oy_oxiri(oy)

    for sana in (
        guruh_moliya.boshlanish_sana if guruh_moliya else None,
        azolik_moliya.boshlanish_sana,
        # Muzlatishdan keyin qayta boshlagan sana — o'sha oy shu sanadan
        # boshlab hisoblanadi.
        azolik_moliya.qayta_faol_sana,
    ):
        if sana and sana > boshi:
            boshi = sana

    for sana in (
        guruh_moliya.tugash_sana if guruh_moliya else None,
        azolik_moliya.tugash_sana,
    ):
        if sana and sana < oxiri:
            oxiri = sana

    return [kun for kun in oylik_kunlar if boshi <= kun <= oxiri]


def proporsional_summa(narx: Decimal, talaba_kunlar: int, oylik_kunlar: int) -> Decimal:
    """narx * talaba_kunlar / oylik_kunlar, 1000 so'mgacha yaxlitlangan."""
    xom = narx * Decimal(talaba_kunlar) / Decimal(oylik_kunlar)
    return (xom / YAXLITLASH).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * YAXLITLASH


# ── Hisob yaratish ───────────────────────────────────────────────────

# `hisob_yarat` natijalari. Generatsiya AYNAN shu qiymatlarga qarab
# watermark'ni suradimi yo'qmi degan qarorni qabul qiladi.
YARATILDI = "yaratildi"
MAVJUD = "mavjud"
DARS_YOQ = "dars_yoq"          # oyda dars yo'q / talaba oynasiga tushmadi — XATO EMAS
SOZLANMAGAN = "sozlanmagan"    # narx yoki jadval yo'q — watermark SURILMAYDI


def hisob_yarat(azolik_moliya: AzolikMoliya, oy: date) -> str:
    """Bitta oy uchun hisob ochadi. Idempotent."""
    azolik = azolik_moliya.azolik
    guruh = azolik.guruh
    guruh_moliya = getattr(guruh, "moliya", None)

    narx = amaldagi_narx(azolik_moliya)
    if guruh_moliya is None or narx is None or narx <= 0:
        return SOZLANMAGAN

    oylik_kunlar = oylik_dars_kunlari(guruh, oy)
    if not oylik_kunlar:
        # Jadval umuman yo'q bo'lsa — bu sozlanmagan guruh, watermark
        # surilmasligi kerak (admin jadvalni keyin kiritsa, shu oy
        # o'tkazib yuborilmasin).
        if not guruh.crm_jadval.exists():
            return SOZLANMAGAN
        return DARS_YOQ

    talaba_kunlar = talaba_dars_kunlari(azolik_moliya, oy, oylik_kunlar)
    if not talaba_kunlar:
        return DARS_YOQ

    summa = proporsional_summa(narx, len(talaba_kunlar), len(oylik_kunlar))

    _, yaratildi = Hisob.objects.get_or_create(
        talaba=azolik.talaba,
        guruh=guruh,
        oy=oy,
        defaults={
            # Nom NUSXALARI — talaba/guruh keyin LMS'da o'chirilsa ham
            # yozuv o'qiladigan bo'lib qoladi (`models.Hisob` izohi).
            "talaba_ism": azolik.talaba.get_full_name() or azolik.talaba.username,
            "guruh_nomi": guruh.name,
            # Filial SNAPSHOT — guruh keyin boshqa filialga ko'chsa,
            # o'tgan oylar hisoboti o'zgarmasligi uchun.
            "filial": guruh_moliya.filial,
            "summa": summa,
            "proporsional": len(talaba_kunlar) < len(oylik_kunlar),
            "darslar_jami": len(oylik_kunlar),
            "darslar_talaba": len(talaba_kunlar),
            "holat": Hisob.Holat.QARZDOR,
        },
    )
    return YARATILDI if yaratildi else MAVJUD


# ── Generatsiya ──────────────────────────────────────────────────────


def hisoblarni_generatsiya_qil() -> dict:
    """Orqada qolgan barcha oylar uchun hisob ochadi ("dangasa" usul).

    Cron YO'Q — loyihadagi mavjud konvensiya (`Markaz.zaxira_avtomatik`:
    "shu vaqtdan keyingi birinchi so'rovda olinadi"). Bu funksiya CRM
    API'sining har bir GET so'rovi boshida chaqiriladi
    (`crm.views.CrmGetGeneratsiyaMixin`).

    NEGA WATERMARK HAR A'ZOLIKDA ALOHIDA (eng muhim qaror):

    Avvalgi rejada umumiy `Sozlama.hisob_oxirgi_oy` bor edi — generatsiya
    oyiga bir marta ishlab, keyin o'sha oyni "bajarilgan" deb belgilardi.
    Bu PUL YO'QOTARDI:

        01-sentabr  -> generatsiya ishladi, sentabr "bajarilgan"
        15-sentabr  -> admin yangi talabani guruhga qo'shdi
                    -> unga sentabr hisobi UMUMAN ochilmaydi
        01-oktabr   -> generatsiya faqat oktabrni ochadi
                    -> talaba sentabrni BEPUL o'qidi

    Bir xil xato yana uch holatda: guruh oy o'rtasida yaratildi; narx oy
    o'rtasida kiritildi; dars jadvali oy o'rtasida to'ldirildi.

    Endi har a'zolikning o'z `oxirgi_hisob_oy`i bor va so'rov faqat ORQADA
    QOLGANLARNI tanlaydi. Hech nima orqada qolmagan bo'lsa — so'rov 0
    qator qaytaradi, ya'ni xarajat nolga yaqin.
    """
    joriy_oy = oy_boshi(timezone.localdate())
    boshlangich_oy = sozlama_ol().boshlangich_oy

    azoliklar = (
        AzolikMoliya.objects.filter(
            holat=AzolikMoliya.Holat.FAOL,
            azolik__guruh__faol=True,
        )
        .filter(
            models.Q(oxirgi_hisob_oy__isnull=True) | models.Q(oxirgi_hisob_oy__lt=joriy_oy)
        )
        .select_related(
            "azolik", "azolik__talaba", "azolik__guruh",
            "azolik__guruh__moliya", "azolik__guruh__daraja",
        )
    )

    natija = {"yaratildi": 0, "sozlanmagan": 0, "azoliklar": 0}

    for azolik_moliya in azoliklar:
        natija["azoliklar"] += 1
        with transaction.atomic():
            oy = _boshlash_oyi(azolik_moliya, boshlangich_oy)
            oxirgi_bajarilgan = None

            while oy <= joriy_oy:
                holat = hisob_yarat(azolik_moliya, oy)
                if holat == SOZLANMAGAN:
                    # Watermark ATAYLAB SURILMAYDI: admin narxni yoki
                    # jadvalni keyin kiritsa, shu oy qaytadan urinib
                    # ko'riladi. Aks holda o'sha oy abadiy o'tkazib
                    # yuborilardi — aynan yuqorida tasvirlangan xato.
                    natija["sozlanmagan"] += 1
                    break
                if holat == YARATILDI:
                    natija["yaratildi"] += 1
                oxirgi_bajarilgan = oy
                oy = keyingi_oy(oy)

            if oxirgi_bajarilgan is not None:
                azolik_moliya.oxirgi_hisob_oy = oxirgi_bajarilgan
                azolik_moliya.save(update_fields=["oxirgi_hisob_oy"])

    return natija


def _boshlash_oyi(azolik_moliya: AzolikMoliya, boshlangich_oy: date) -> date:
    """Shu a'zolik uchun generatsiya qaysi oydan boshlanishi kerak."""
    nomzodlar = [boshlangich_oy, oy_boshi(azolik_moliya.boshlanish_sana)]

    if azolik_moliya.oxirgi_hisob_oy:
        nomzodlar.append(keyingi_oy(azolik_moliya.oxirgi_hisob_oy))
    if azolik_moliya.qayta_faol_sana:
        # Muzlatishdan keyin qayta boshlagan bo'lsa — muzlab turgan
        # oylarga hisob ochilmaydi.
        nomzodlar.append(oy_boshi(azolik_moliya.qayta_faol_sana))

    guruh_moliya = getattr(azolik_moliya.azolik.guruh, "moliya", None)
    if guruh_moliya and guruh_moliya.boshlanish_sana:
        nomzodlar.append(oy_boshi(guruh_moliya.boshlanish_sana))

    return max(nomzodlar)


# ── Holat va balans ──────────────────────────────────────────────────


def hisobni_yangila(hisob: Hisob) -> Hisob:
    """`Hisob.holat`ni qayta hisoblaydi — YAGONA joy.

    Har bir to'lov / chegirma / bonus / o'chirish yozuvidan keyin
    chaqiriladi. Boshqa hech qayerda `holat` qo'lda yozilmaydi, aks holda
    yozuvlar bilan holat bir-biridan uzilib ketadi va qarzdorlar ro'yxati
    yolg'on ko'rsata boshlaydi.

    `qaytarish` bu hisob-kitobga KIRMAYDI (foydalanuvchi qarori
    2026-09-14): pul qaytarish bitta oyga bog'lanmaydi, u faqat umumiy
    balansga tushadi.
    """
    yopilgan = hisob.tolovlar.filter(turi__in=Tolov.YOPUVCHI_TURLAR).aggregate(
        jami=models.Sum("summa")
    )["jami"] or Decimal("0")

    qoldiq = hisob.summa - yopilgan

    # Tartib MUHIM: `qoldiq <= 0` birinchi tekshiriladi. Aks holda
    # `summa = 0` bo'lgan hisob (0 >= 0) "qarzdor" bo'lib ko'rinardi.
    if qoldiq <= 0:
        hisob.holat = Hisob.Holat.TOLANDI
    elif qoldiq >= hisob.summa:
        hisob.holat = Hisob.Holat.QARZDOR
    else:
        hisob.holat = Hisob.Holat.QISMAN

    hisob.save(update_fields=["holat"])
    return hisob


def balans(talaba, guruh=None) -> Decimal:
    """Talabaning balansi — SAQLANMAYDI, har safar hisoblanadi.

        balans = S(tolov + chegirma + bonus) - S(qaytarish) - S(Hisob.summa)

        balans < 0  -> qarzdor          (qizil)
        balans = 0  -> toza             (yashil)
        balans > 0  -> oldindan to'lagan (ko'k)

    Saqlangan balans denormalizatsiya bo'lardi: har bir tuzatishda
    yozuvlarga mos kelmay qoladi va buni hech kim sezmaydi.
    Hisoblanadigan balans esa doim yozuvlarga teng.

    `guruh` berilsa — faqat o'sha guruh bo'yicha (SoffCRM'da har guruh
    kartasida o'z balansi ko'rsatiladi).
    """
    tolovlar = Tolov.objects.filter(talaba=talaba)
    hisoblar = Hisob.objects.filter(talaba=talaba)
    if guruh is not None:
        tolovlar = tolovlar.filter(guruh=guruh)
        hisoblar = hisoblar.filter(guruh=guruh)

    kirim = tolovlar.filter(turi__in=Tolov.YOPUVCHI_TURLAR).aggregate(
        jami=models.Sum("summa")
    )["jami"] or Decimal("0")
    chiqim = tolovlar.filter(turi=Tolov.Turi.QAYTARISH).aggregate(
        jami=models.Sum("summa")
    )["jami"] or Decimal("0")
    hisoblangan = hisoblar.aggregate(jami=models.Sum("summa"))["jami"] or Decimal("0")

    return kirim - chiqim - hisoblangan


# ── A'zolikni yakunlash / muzlatish ──────────────────────────────────


def azolikni_qayta_hisobla(azolik_moliya: AzolikMoliya, oy: date | None = None) -> Hisob | None:
    """Talaba guruhdan chiqqanda yoki muzlatilganda — o'sha oyning
    TO'LANMAGAN hisobini proporsional qayta hisoblaydi.

    Bu generatsiyada emas, AYNAN shu yerda bajariladi: `holat` `arxiv`
    yoki `muzlatilgan` bo'lgach generatsiya bu a'zolikni umuman ko'rmaydi.

    To'liq to'langan oyga TEGILMAYDI (TZ 4.6) — pul allaqachon kassada,
    uni qaytarish alohida ongli amal (`Tolov.turi="qaytarish"`).
    """
    oy = oy or oy_boshi(timezone.localdate())
    hisob = Hisob.objects.filter(
        talaba=azolik_moliya.azolik.talaba, guruh=azolik_moliya.azolik.guruh, oy=oy
    ).first()
    if hisob is None or hisob.holat == Hisob.Holat.TOLANDI:
        return hisob

    narx = amaldagi_narx(azolik_moliya)
    oylik_kunlar = oylik_dars_kunlari(azolik_moliya.azolik.guruh, oy)
    if narx is None or not oylik_kunlar:
        return hisob

    talaba_kunlar = talaba_dars_kunlari(azolik_moliya, oy, oylik_kunlar)

    hisob.summa = proporsional_summa(narx, len(talaba_kunlar), len(oylik_kunlar))
    hisob.proporsional = len(talaba_kunlar) < len(oylik_kunlar)
    hisob.darslar_talaba = len(talaba_kunlar)
    hisob.save(update_fields=["summa", "proporsional", "darslar_talaba"])
    return hisobni_yangila(hisob)
