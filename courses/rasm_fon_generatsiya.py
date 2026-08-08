"""Darslik sahifasini "RASM-FON" formatiga o'girish (2026-08-07).

Farqi `blok_generatsiya.py` (blok formati) dan: u yerda sahifa QAYTA
QURILADI — matn HTML matniga, suratlar esa alohida kesib olinadi va
elementlar mashqlarga guruhlanadi. Real sinovlarda eng ko'p xato aynan
shu qayta-qurish bosqichida chiqdi: surat chegarasi noto'g'ri kesildi,
element noto'g'ri mashqqa tushdi, joylashuv asl kitobdan farq qildi.

Bu yerda sahifa QAYTA QURILMAYDI. Mashq hududi sahifadan kesib olinib
`KursMashq.rasm`ga saqlanadi (fon), bo'sh joylar esa foizli `pozitsiya`
bilan shu rasm USTIGA input sifatida qo'yiladi (frontend:
`Kurslar.jsx: RasmMashqi`).

NEGA BU ISHONCHLIROQ: kesiladigan narsa endi TIG'IZ SURAT QUTISI emas,
KATTA MASHQ HUDUDI. Tig'iz qutida 2% xato = yuz kesiladi yoki begona
yozuv kiradi (blok formatidagi asosiy bug manbai); katta hududda 2%
xato ko'zga ham tashlanmaydi.


USUL: HUDUD — AI, BO'SH JOY — GEOMETRIYA (2026-08-08)
-----------------------------------------------------
Ikki bosqich:
  1) `HUDUD_PROMPT` butun sahifada FAQAT mashq hududlarini topadi.
     Bular katta obyektlar, AI ularni ishonchli topadi.
  2) Har hudud kesib olinadi. Kesimda bo'sh joylar AI'SIZ,
     `bosh_joy_aniqlash` orqali topiladi (piksel aniqligida), AI esa
     FAQAT gap matni va to'g'ri javobni beradi — raqamlangan
     belgilarga qarab (`_raqamlarni_chiz`).

NEGA KOORDINATA AI'DAN SO'RALMAYDI. Avval so'ralardi. Haqiqiy Headway
sahifasida uch marta sinaldi (bitta chaqiruvda; ikki bosqichda; ikki
bosqich + 2% zich to'r): eng yaxshi holatda ham 8 ta bo'sh joydan
atigi 3 tasi to'g'ri joyga tushdi. Xato tasodifiy emas — rasm pastiga
tomon TIZIMLI o'sadi, ya'ni bu promt kamchiligi emas, vision-modelning
baland rasmda mayda y-koordinatani o'qish chegarasi.

O'sha sahifada geometrik aniqlash 8 tadan 8 tasini piksel aniqligida
topdi (jumladan AI bittaga qo'shib yuborgan qo'shni ikki chiziqchani
ham alohida). Shuning uchun ish shunday taqsimlandi:
  * geometriya — QAYERDA (aniq, arzon, AI chaqiruvisiz);
  * AI — NIMA GAP va JAVOBI NIMA (buni allaqachon yaxshi qilyapti).

Narxi: sahifaga 1 emas, 1+N chaqiruv. Foydalanuvchi bilan kelishilgan
(2026-08-07) — aniqlik tezlikdan muhimroq. Amalda 4 mashqli sahifa
~30 soniya.

Qulaylik: aniqlangan koordinatalar ALLAQACHON kesim ichidagi foizda —
bu aynan frontendga kerak bo'lgan qiymat, qayta hisoblash yo'q.
"""

import io

from .blok_generatsiya import AI_RASM_KENGLIGI, _ai_sorov, rasmni_kes, tor_chiz
from .bosh_joy_aniqlash import bosh_joylarni_aniqla

# 1-BOSQICH kesim o'lchami. `rasmni_kes` ichida `draft` 1600px'da
# ishlaydi, ya'ni sahifaning yarmi ~800px bo'lib chiqadi — bu 1000
# so'ralgan bo'lsa ham kattalashtirilmaydi (`thumbnail` faqat
# KICHRAYTIRADI). Ataylab shunday qoldirildi: xotira sarfi o'zgarmaydi
# (Render'da 512 MB), sifat esa butun sahifaga nisbatan baribir 2-4
# barobar yaxshi.
KESIM_KENGLIGI = AI_RASM_KENGLIGI

HUDUD_PROMPT = (
    "Sizga ingliz tili darsligi sahifasining rasmi beriladi. Rasm ustiga "
    "PRONUMERLANGAN TO'R chizilgan: chiziqlar har 5 foizda, chetlarida 0 "
    "dan 100 gacha raqamlar.\n\n"

    "Vazifa: sahifadagi HAR BIR alohida mashqning (topshiriqning) "
    "HUDUDINI toping. Bo'sh joylarni yoki matnni o'qish SHART EMAS — "
    "faqat chegaralarni belgilang.\n\n"

    "FAQAT quyidagi JSON qaytaring:\n"
    '{"mashqlar":[\n'
    '  {"raqam":"1","x1":3,"y1":8,"x2":50,"y2":62,"audio_bor":true,\n'
    '   "sarlavha":"Read and listen."},\n'
    '  {"raqam":"4","x1":50,"y1":8,"x2":98,"y2":92,"audio_bor":false,\n'
    '   "sarlavha":"Complete the conversations."}\n'
    "]}\n\n"

    "QOIDALAR:\n"
    "- Mashq BOSILGAN RAQAMIDAN boshlanadi va SHU USTUNDAGI KEYINGI "
    "bosilgan raqamgacha davom etadi. Oradagi HAMMA NARSA — suratlar, "
    "dialog qutilari, jadvallar, rangli qutilar (masalan \"GRAMMAR "
    "SPOT\"), qo'shimcha yo'riqnoma qatorlari — O'SHA mashqning ichida, "
    "ular ALOHIDA mashq EMAS.\n"
    "- Ya'ni \"y1\" = mashq raqami turgan qator, \"y2\" = keyingi mashq "
    "raqamining bir oz tepasi. Ustundagi OXIRGI mashq uchun \"y2\" = "
    "ustun mazmuni tugagan joy (ko'pincha 90 dan katta).\n"
    "- MASHQ HUDUDLARI ODATDA KATTA. Balandligi 10 foizdan kichik "
    "hudud deyarli har doim XATO: mashqning faqat sarlavha qatorini "
    "olib, ostidagi rasm/dialog/qutilarni tashlab ketgansiz. Qayta "
    "tekshiring.\n"
    "- RAQAMSIZ hudud CHIQARMANG. Biror blok qaysi raqamga tegishli "
    "ekanini bilmasangiz — u YUQORISIDAGI eng yaqin raqamli mashqning "
    "hududi ichiga kirsin, alohida yozilmasin.\n"
    "- Chetidan 1-2 foiz ortiqcha joy qolishi MUAMMO EMAS (hudud kesib "
    "olinadi, bo'sh chet ko'rinmaydi) — lekin mashqning bir qismi "
    "tashqarida qolishi JIDDIY XATO. Shubhalansangiz KENGROQ oling.\n"
    "- Sahifa ikki ustunli bo'lsa, har mashq O'Z ustunining kengligida "
    "bo'lsin (butun sahifa kengligini olmang). Chap va o'ng ustun "
    "MUSTAQIL ketma-ketlik.\n"
    "- Sahifa sarlavhasi, bo'lim nomi, \"Grammar reference\" / \"Go "
    "online\" / \"Watch a video\" kabi havola qutilari — mashq EMAS, "
    "chiqarmang.\n"
    "- SAHIFANING ENG PASTIDAGI KOLONTITUL — sahifa raqami, unit "
    "raqami va unit nomi turgan qator (masalan \"10  Unit 1 • Hello!\") "
    "— mashq EMAS. Uni na alohida chiqaring, na oxirgi mashqning "
    "hududiga qo'shing: oxirgi mashqning \"y2\" si shu qatordan "
    "YUQORIDA tugasin.\n"
    "- Xuddi shunday, eng yuqoridagi kolontitul (bo'lim nomi takrori) "
    "ham mashq emas.\n\n"

    "\"raqam\" — sahifada BOSILGAN mashq raqami. \"audio_bor\" — mashq "
    "yonida AUDIO/DINAMIK BELGISI (ko'pincha \"1.5\" kabi trek raqami "
    "bilan) ko'rinsa true, aks holda false — taxmin qilmang. "
    "\"sarlavha\" — mashqning topshiriq yozuvi."
)

BOSH_JOY_PROMPT = (
    "Sizga ingliz tili darsligidan kesib olingan BITTA MASHQNING rasmi "
    "beriladi. Rasmdagi javob yoziladigan bo'sh joylar ALLAQACHON "
    "topilgan va har biriga QIZIL FONDA OQ RAQAM qo'yilgan (1, 2, 3...).\n\n"

    "Vazifa — HAR BIR RAQAM uchun:\n"
    "1) shu bo'sh joy joylashgan gapni o'qing;\n"
    "2) to'g'ri javobni aniqlang;\n"
    "3) bu haqiqatan javob yoziladigan bo'sh joymi yoki yo'qmi ayting.\n\n"

    "FAQAT quyidagi JSON qaytaring:\n"
    '{"javoblar":[\n'
    '  {"raqam":1,"bosh_joymi":false,"savol":"","togri":""},\n'
    '  {"raqam":2,"bosh_joymi":true,'
    '"savol":"Hello. My name\'s Usha. ___ your name?","togri":"What\'s"},\n'
    '  {"raqam":3,"bosh_joymi":true,"savol":"___ name\'s Ben.","togri":"My"}\n'
    "]}\n\n"

    "QOIDALAR:\n"
    "- ENG MUHIMI: \"raqam\" ni RASMDAN O'QING. O'zingiz bo'sh joylarni "
    "sanab chiqmang va o'z tartibingizni qo'ymang. Har bir qizil "
    "belgidagi raqam nechchi bo'lsa, o'sha yozuvning \"raqam\"i shu "
    "bo'ladi — hatto ular o'qish tartibiga mos kelmasa ham.\n"
    "- Rasmdagi HAR BIR raqam uchun bitta yozuv qaytaring, birortasini "
    "ham tashlab ketmang — jumladan bo'sh joy emas deb hisoblaganingiz "
    "uchun ham (u holda \"bosh_joymi\": false qo'ying, LEKIN yozuvni "
    "baribir qaytaring). Rasmda YO'Q raqamni O'ZINGIZDAN qo'shmang.\n"
    "- KOORDINATA SO'RALMAYDI — joylashuv allaqachon aniq. Siz faqat "
    "matn bilan ishlaysiz.\n"
    "- \"bosh_joymi\" false bo'ladigan holatlar: raqam quti/jadval "
    "chegarasiga yoki bezakka tushib qolgan; yoki bu katak NAMUNA "
    "sifatida ALLAQACHON to'ldirilgan (odatda qiyshiq yoki boshqa "
    "rangdagi yozuv bilan). Bunday yozuvda \"savol\" va \"togri\" bo'sh "
    "qolsin.\n"
    "- \"savol\" — bo'sh joy joylashgan gapni TO'LIQ yozing, o'sha bo'sh "
    "joy o'rniga \"___\" qo'ying (qolgan so'zlar joyida qolsin). Bitta "
    "gapda ikkita bo'sh joy bo'lsa, har raqam uchun FAQAT O'ZINIKI "
    "\"___\" bo'lsin, ikkinchisining javobini yozib qo'ying. Bu matn "
    "talabaga ko'rinmaydi — u faqat admin ro'yxati va javob tarixi "
    "uchun.\n"
    "- \"togri\" — to'g'ri javob. Javobni matndan KELTIRIB CHIQARISH "
    "mumkin bo'lsa (masalan yuqorida \"Write 'm, is, or are\" deb "
    "berilgan, yoki dialogdan aniq ko'rinib turibdi) — ALBATTA "
    "to'ldiring. Faqat javob haqiqatan erkin bo'lsa (talaba o'z ismini "
    "yozadi) bo'sh qoldiring (\"\")."
)

# Raqam belgisi bo'sh joyning ICHIGA chiziladi (u yer ta'rifi bo'yicha
# bo'sh — hech qanday matn yopilmaydi). O'lchami ATAYLAB katta: birinchi
# sinovda belgi PIL'ning standart bitmap shrifti bilan ~11 piksel edi va
# AI uni umuman o'qimadi — raqamlarga qaramay bo'sh joylarni o'zicha
# sanab chiqdi, natijada gaplar pozitsiyalarga bitta surilib bog'landi.
RAQAM_BALANDLIGI = 26


def _shrift(olcham):
    """Tizimda bor TrueType shriftni topadi. PIL'ning standart shrifti
    bitmap va o'lchami qat'iy kichik — raqam o'qilmay qoladi."""
    from PIL import ImageFont

    for nom in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nom, olcham)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=olcham)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _son(qiymat):
    try:
        return float(qiymat)
    except (TypeError, ValueError):
        return None


# Sahifa pastidagi kolontitul (sahifa raqami, "Unit 1 • Hello!") va
# yuqoridagi bo'lim nomi turadigan tasmalar. Foydalanuvchi talabi
# (2026-08-08): bu qismlar mashq bo'lib qolmasin. Promtda ham
# aytilgan, lekin AI ba'zan baribir chiqaradi — shuning uchun kodda
# ham to'siq bor: BUTUNLAY shu tasma ichida yotgan hudud tashlanadi.
KOLONTITUL_PAST = 93
KOLONTITUL_TEPA = 6


def _hudud_yaroqlimi(m):
    """AI ba'zan chala/teskari quti qaytaradi — bunday mashq tashlanadi."""
    qiymatlar = [_son(m.get(k)) for k in ("x1", "y1", "x2", "y2")]
    if any(q is None for q in qiymatlar):
        return False
    x1, y1, x2, y2 = qiymatlar
    if not all(0 <= q <= 100 for q in qiymatlar):
        return False
    # Kolontitul tasmasidan chiqmaydigan hudud — mashq emas.
    if y1 >= KOLONTITUL_PAST or y2 <= KOLONTITUL_TEPA:
        return False
    # Juda kichik hudud — deyarli har doim AI xatosi (masalan bitta so'zni
    # "mashq" deb belgilab qo'yishi). 5% dan kichigini qabul qilmaymiz.
    return x2 - x1 >= 5 and y2 - y1 >= 5


def _pozitsiya(joy):
    """Aniqlangan bo'sh joydan frontend kutadigan `pozitsiya`ni yasaydi.

    Koordinatalar ALLAQACHON kesim (= fon rasmi) ichidagi foizda —
    faqat markazlash kerak."""
    markaz_x = (joy["x1"] + joy["x2"]) / 2
    # Juda tor input yozib bo'lmaydi, juda keng esa qo'shni matnni yopadi.
    kenglik = max(8, min(60, joy["x2"] - joy["x1"]))
    return {
        "x": round(markaz_x, 1),
        "y": round(joy["y"], 1),
        "kenglik": round(kenglik, 1),
    }


def _raqamlarni_chiz(kesim_bytes, joylar):
    """Topilgan har bo'sh joyning ICHIGA tartib raqamini chizadi — AI
    shu raqamlar orqali gapni va javobni bog'laydi (koordinata AI'dan
    umuman so'ralmaydi)."""
    from PIL import Image, ImageDraw

    im = Image.open(io.BytesIO(kesim_bytes)).convert("RGB")
    dr = ImageDraw.Draw(im)
    W, H = im.size
    shrift = _shrift(RAQAM_BALANDLIGI - 6)
    for i, joy in enumerate(joylar, start=1):
        matn = str(i)
        x1 = joy["x1"] / 100 * W
        y = joy["y"] / 100 * H  # chiziqchaning o'zi
        en = 12 + 13 * len(matn)
        # Belgi chiziqcha USTIDAGI yozuv joyiga tushadi (talaba javob
        # yozadigan bo'shliq) — chiziqchaning o'zini ham biroz qoplaydi,
        # bu zararsiz: chiziqcha AI'ga kerak emas, o'rni allaqachon ma'lum.
        quti = [x1, y - RAQAM_BALANDLIGI + 3, x1 + en, y + 3]
        dr.rectangle(quti, fill=(200, 0, 0))
        dr.text((quti[0] + 6, quti[1] + 1), matn, fill=(255, 255, 255), font=shrift)
    bufer = io.BytesIO()
    im.save(bufer, format="JPEG", quality=90)
    return bufer.getvalue()


def _hududlarni_top(provider, rasm_bytes):
    """1-BOSQICH. Qaytaradi: (hududlar, xato)."""
    natija, xato = _ai_sorov(
        provider, HUDUD_PROMPT, tor_chiz(rasm_bytes),
        "To'r raqamlaridan foydalanib, mashq hududlarini aniqlang.")
    if xato:
        return None, xato
    hududlar = [m for m in (natija.get("mashqlar") or []) if _hudud_yaroqlimi(m)]
    if not hududlar:
        return None, "Sahifada mashq topilmadi"
    return hududlar, None


def _bosh_joylarni_top(provider, kesim_bytes):
    """2-BOSQICH — BITTA mashq kesimi uchun.

    Bo'sh joylar AI'siz, `bosh_joy_aniqlash` orqali topiladi (piksel
    aniqligida), AI esa faqat gap matni va javobini beradi.

    AI xato bersa savollar POZITSIYASI BILAN, lekin matnsiz qaytariladi
    — mashqning fon rasmi va input'lari baribir joyida bo'ladi, admin
    matn/javobni keyin qo'lda to'ldiradi. Bitta kesimdagi nosozlik
    butun sahifani yo'qotmasin."""
    joylar = bosh_joylarni_aniqla(kesim_bytes)
    if not joylar:
        return []

    natija, xato = _ai_sorov(
        provider, BOSH_JOY_PROMPT, _raqamlarni_chiz(kesim_bytes, joylar),
        "Rasmdagi har bir raqamli bo'sh joy uchun gap va javobni bering.")

    # {raqam: yozuv} — AI tartibni almashtirib yuborsa ham to'g'ri bog'lanadi.
    javoblar = {}
    for j in (natija or {}).get("javoblar") or []:
        try:
            javoblar[int(j.get("raqam"))] = j
        except (TypeError, ValueError):
            continue

    savollar = []
    for i, joy in enumerate(joylar, start=1):
        j = javoblar.get(i)
        # AI aniq "bu bo'sh joy emas" desa — tashlaymiz (namuna sifatida
        # to'ldirilgan katak, quti chegarasi va h.k.). AI umuman javob
        # bermagan bo'lsa (xato/tushib qolgan) SAQLAYMIZ: geometriya
        # ishonchli, matnni admin qo'shadi.
        if j is not None and j.get("bosh_joymi") is False:
            continue
        savollar.append({
            "savol": str((j or {}).get("savol") or "").strip() or "___",
            "togri": str((j or {}).get("togri") or "").strip(),
            "pozitsiya": _pozitsiya(joy),
        })
    return savollar


def sahifani_rasm_fonga_ajrat(provider, rasm_bytes):
    """Bitta sahifa -> mashqlar ro'yxati (ikki bosqichli, yuqoridagi
    modul izohiga qarang).

    Qaytaradi: (mashqlar, xato) — biri None bo'ladi. Har mashq:
      {"raqam", "sarlavha", "audio_kerak", "quti": {x1,y1,x2,y2},
       "savollar": [{"savol", "togri", "pozitsiya": {x,y,kenglik}}]}
    `quti` — SAHIFA foizida (chaqiruvchi shu bo'yicha kesadi),
    `pozitsiya` — kesilgan HUDUDGA nisbatan foizda."""
    hududlar, xato = _hududlarni_top(provider, rasm_bytes)
    if xato:
        return None, xato

    mashqlar = []
    for m in hududlar:
        quti = {k: _son(m[k]) for k in ("x1", "y1", "x2", "y2")}
        kesim = rasmni_kes(rasm_bytes, quti, maks_kenglik=KESIM_KENGLIGI)
        # Kesib bo'lmadi (hudud juda ingichka) — mashqning fon rasmi
        # baribir bo'lmaydi, shuning uchun uni umuman chiqarmaymiz.
        if not kesim:
            continue
        mashqlar.append({
            "raqam": str(m.get("raqam") or "").strip(),
            "sarlavha": str(m.get("sarlavha") or "").strip(),
            "audio_kerak": bool(m.get("audio_bor")),
            "quti": quti,
            "savollar": _bosh_joylarni_top(provider, kesim),
        })

    if not mashqlar:
        return None, "Sahifada mashq topilmadi"
    # Bosilgan raqam bo'yicha tartiblash — AI ba'zan aralash qaytaradi.
    mashqlar.sort(key=_tartib_kaliti)
    return mashqlar, None


def _tartib_kaliti(m):
    """Bosilgan raqam bo'yicha, raqamsizlar oxirida (sahifadagi o'rni
    bo'yicha)."""
    try:
        return (0, int(m["raqam"]), 0.0)
    except (TypeError, ValueError):
        return (1, 0, m["quti"]["y1"])
