"""Darslik sahifasini BLOK formatiga o'girish (2026-07-28).

Farqi eski usuldan: eski usulda sahifa RASM bo'lib qolardi va uning
ustiga foizli pozitsiyada input'lar qo'yilardi. Blok formatida sahifa
QAYTADAN QURILADI — matn haqiqiy HTML matni (o'tkir, tanlanadi, mobilda
o'qiladi), suratlar esa sahifadan kesib olinadi.

=== NEGA TO'R (grid) ===

Bu modulning kaliti — sahifaga PRONUMERLANGAN TO'R chizib AI'ga yuborish.

Sabab (2026-07-28 da bir necha soatlik sinovda aniqlangan): LLM
koordinatani ko'z bilan chamalaganda ±3-5% xato beradi. 861 piksellik
sahifada bu 30-40 piksel — matn boshqa joyga tushadi, kesilgan suratga
begona yozuv kiradi. Model almashtirish (Claude -> Gemma) yordam berdi,
lekin yetarli emas edi. To'r chizilgach model chamalamaydi, chiziqni
O'QIYDI va xato deyarli nolga tushadi. Bu usulsiz blok formati ishlamaydi.

=== NEGA GEMMA ===

Xuddi shu sahifada solishtirildi:
  * audio raqami: Claude "1.3" (SAHIFADA 1.2 turgan — to'qib chiqargan),
    Gemma "1.2" — to'g'ri;
  * matn: Claude "practice", sahifada "practise" — Gemma to'g'ri;
  * rasm qutilari: Claude'niki juda katta va siljigan, Gemma'niki aniq.
7 sahifalik to'liq sinovda Gemma 12 audiodan 10 tasini topdi va BIRONTA
raqamni to'qib chiqarmadi (qolgan 2tasi qayta ishlanmagan sahifada edi).
Kamchiligi — sekin: sahifasiga ~125 sekund (Claude ~9s).
"""

import base64
import io
import json
import os
import re
import time

from assessment.providers import ProviderXatosi

# Bepul tarifda ~16K token/daqiqa; har sahifa ~3K token => daqiqasiga
# ~5 sahifa. Limitga urilganda shuncha kutib qayta uriniladi.
LIMIT_KUTISH_SONIYA = 20
LIMIT_URINISHLAR = 3

# Bitta sahifa uchun AI so'rovi timeout'i. Writing/Speaking'da 40s
# (`SOROV_TIMEOUT_MS`) yetardi, bu yerda esa Gemma ~125 sekund ishlaydi.
# 240s tanlandi: gunicorn 300s'dan past (worker o'lmasin), lekin sekin
# sahifaga ham yetarli zaxira qoladi.
SAHIFA_TIMEOUT_MS = 240_000

# AI'ga yuboriladigan rasm kengligi. Koordinatalar FOIZDA bo'lgani uchun
# kichraytirish aniqlikka ta'sir qilmaydi, lekin so'rovni tezlashtiradi va
# token sarfini kamaytiradi. Suratlar esa TO'LIQ SIFATLI asl rasmdan
# kesiladi — bu ikkisi alohida.
AI_RASM_KENGLIGI = 1000

TOR_QADAM = 5  # to'r chiziqlari har 5 foizda

BLOK_PROMPT = (
    "Sizga ingliz tili darsligi sahifasining rasmi beriladi. Rasm ustiga "
    "PRONUMERLANGAN TO'R chizilgan: chiziqlar har 5 foizda, chetlarida 0 "
    "dan 100 gacha raqamlar.\n\n"

    "Vazifa: sahifadagi HAR BIR elementni (MATN va FOTOSURAT) toping va "
    "joylashuvini TO'R RAQAMLARI bo'yicha ayting. Chamalab yozmang — "
    "element chetlari qaysi chiziqqa to'g'ri kelishini QARAB o'qing.\n\n"

    "FAQAT quyidagi JSON qaytaring:\n"
    '{"sarlavha":"...","elementlar":[\n'
    '  {"x1":8,"y1":5,"x2":40,"y2":9,"tur":"sarlavha","matn":"What\'s your name?"},\n'
    '  {"x1":8,"y1":13,"x2":31,"y2":28,"tur":"rasm","izoh":"Mara"},\n'
    '  {"x1":8,"y1":28,"x2":33,"y2":32,"tur":"pufakcha","matn":"Hello, I\'m Mara."},\n'
    '  {"x1":5,"y1":40,"x2":50,"y2":43,"tur":"korsatma","raqam":"1",'
    '"audio_raqam":"1.2","matn":"Read and listen."},\n'
    '  {"x1":8,"y1":44,"x2":45,"y2":52,"tur":"dialog",'
    '"qatorlar":[{"kim":"Serena","gap":"Hello. I\'m Serena."}]},\n'
    '  {"x1":8,"y1":56,"x2":30,"y2":64,"tur":"grammar_spot",'
    '"sarlavha":"GRAMMAR SPOT","qatorlar":["I\'m = I am"]},\n'
    '  {"x1":8,"y1":68,"x2":30,"y2":73,"tur":"mashq","mashq_raqami":"3",'
    '"bolaklar":[{"matn":"Hello, I\'m "},{"bosh_joy":true,"javob":"",'
    '"javob_turi":"erkin","band_raqami":"1"},{"matn":"."}]}\n'
    '],"sozlar":[{"en":"friend","uz":"do\'st"}]}\n\n'

    "Turlar: sarlavha | bolim_sarlavha | korsatma | matn | pufakcha | "
    "dialog | grammar_spot | mashq | rasm\n\n"

    '- "sozlar" — FAQAT sahifa asosan "Wordlist" (yoki shunga o\'xshash '
    "so'zlar ro'yxati — ingliz so'zi + tarjimasi, ko'pincha Unit oxirida "
    "bo'ladi) bo'lsa to'ldiring: har so'z {\"en\":\"inglizcha so'z\","
    '"uz":"tarjimasi"}. Bunday sahifada "elementlar" bo\'sh yoki faqat '
    "sarlavha bo'lishi mumkin — so'zlarni ALOHIDA \"elementlar\"ga emas, "
    'FAQAT "sozlar"ga yozing (takrorlamang). Sahifa Wordlist EMAS bo\'lsa '
    '— "sozlar"ni umuman yozmang (yoki bo\'sh massiv).\n'

    '- "rasm" — FOTOSURAT (odamlar, manzara). Uni biz sahifadan kesib '
    "olamiz, shuning uchun quti ANIQ bo'lsin: faqat suratning o'zi, "
    "atrofidagi matn kirmasin.\n"
    '- "mashq" — talaba TO\'LDIRADIGAN gap. "javob_turi": "aniq" — '
    "darslikda yagona to'g'ri javob bor (uni \"javob\"ga yozing); "
    '"erkin" — talaba o\'z ismini/ma\'lumotini yozadi, to\'g\'ri javob '
    "YO'Q (bunda \"javob\" bo'sh).\n"
    "- ENG KO'P UCHRAYDIGAN XATO, SHUNI QILMANG: bo'sh joydan OLDINGI va "
    "KEYINGI so'zlarni ham albatta yozing. \"Hello, I'm ______.\" uchun "
    '"bolaklar" = [{"matn":"Hello, I\'m "},{"bosh_joy":true,...},'
    '{"matn":"."}] bo\'lishi kerak — faqat {"bosh_joy":true} yozib, '
    '"Hello, I\'m" ni TASHLAB KETMANG. Har mashq gapi TO\'LIQ o\'qiladigan '
    "bo'lsin.\n"
    '- "mashq_raqami" va "band_raqami" — MUHIM, javob kaliti sahifasi '
    "bilan moslashtirish uchun ishlatiladi. \"mashq_raqami\" — sahifadagi "
    "topshiriq (Exercise) raqami; \"band_raqami\" — shu topshiriq ICHIDAGI "
    "bo'sh joy raqami (har topshiriqda qaytadan 1dan boshlanadi). Ularni "
    "sahifadagi raqamlashdan o'qing; sahifada raqam ko'rinmasa yozmang.\n"
    "- \"audio_raqam\" — faqat sahifada HAQIQATAN ko'ringan raqamni "
    "yozing. Ko'rinmasa umuman yozmang. O'zingizdan TO'QIMANG va "
    "ketma-ketlik bo'yicha TAXMIN QILMANG (oldingisi 1.2 edi deb "
    "keyingisini 1.3 deb yozmang).\n"
    "- Matnni AYNAN sahifadagidek ko'chiring.\n"
    "- Sahifa raqami va pastki kolontitulni ham kiriting."
)

def blok_provider_olish():
    """2026-07-30: sinov sifatida Gemma'dan Claude'ga o'tkazildi (foydalanuvchi
    talabi — Gemma juda sekin, ~125s/sahifa). Model — claude-haiku-4-5
    (foydalanuvchi tanladi: eng tez/arzon variant).

    ESLATMA: `assessment.providers.ClaudeProvider` shu SDK bilan ishlaydi,
    `generate_json` orqali bir xil interfeys beradi — alohida provider
    klassi yozish shart emas."""
    from django.conf import settings

    from assessment.providers import ClaudeProvider

    kalit = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not kalit:
        raise ProviderXatosi("Platforma ANTHROPIC_API_KEY sozlanmagan (.env)")
    return ClaudeProvider(kalit, model="claude-haiku-4-5", timeout_ms=SAHIFA_TIMEOUT_MS)


def tor_chiz(rasm_bytes, qadam=TOR_QADAM, kenglik=AI_RASM_KENGLIGI):
    """Rasmga pronumerlangan to'r chizadi va JPEG bytes qaytaradi.

    Rasm `kenglik` gacha kichraytiriladi — koordinatalar foizda bo'lgani
    uchun aniqlik yo'qolmaydi, lekin so'rov tezlashadi.

    2026-07-29 — HAQIQIY production OOM (Render: "Ran out of memory
    (used over 512MB)") shu funksiyada topildi: `Image.open().convert()`
    rasmni TO'LIQ o'lchamda dekodlaydi, `.thumbnail()` esa FAQAT shundan
    KEYIN kichraytiradi. Foydalanuvchining haqiqiy skanlari 6400x8067 —
    bitta shunday rasmni oddiy dekodlash 148 MB xom xotira talab qiladi
    (512 MB'lik instansda yagona shu OOM'ga yetarli). `Image.draft()` —
    JPEG dekoderiga DEKODLASH PAYTIDA kichraytirishni buyuradi (2^N
    nisbatda, DCT darajasida) — xotira sarfi ~148 MB o'rniga bir necha
    MB'ga tushadi. PNG/boshqa formatlar uchun `draft()` sekin no-op
    qaytaradi (xavfsiz)."""
    from PIL import Image, ImageDraw

    im = Image.open(io.BytesIO(rasm_bytes))
    # `kenglik * 3` (juda keng chegara) draft'ning chuqurroq (1/4, 1/8)
    # darajaga tushishiga TO'SQINLIK qilardi — o'lchov bilan tasdiqlangan:
    # (1000,3000) uchun 6400x8067 rasm faqat 1/2 (36 MB) ga tushardi,
    # (1000,1500) esa 1/4 (9 MB) ga tushadi. Darslik sahifalari deyarli
    # doim tik (bo'yi eniga nisbatan ~1.3-1.5 barobar) — shu chegara
    # xavfsiz.
    im.draft("RGB", (kenglik, int(kenglik * 1.5)))  # dekodlashdan OLDIN chaqirilishi shart
    im = im.convert("RGB")
    im.thumbnail((kenglik, kenglik * 3))
    dr = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    for p in range(0, 101, qadam):
        x, y = int(p / 100 * (W - 1)), int(p / 100 * (H - 1))
        yirik = p % 10 == 0
        rang = (255, 0, 0, 190) if yirik else (255, 120, 0, 105)
        chiziq = 2 if yirik else 1
        dr.line([(x, 0), (x, H)], fill=rang, width=chiziq)
        dr.line([(0, y), (W, y)], fill=rang, width=chiziq)
        if yirik:
            dr.rectangle([x + 1, 1, x + 22, 14], fill=(255, 255, 255, 235))
            dr.text((x + 3, 3), str(p), fill=(200, 0, 0))
            dr.rectangle([1, y + 1, 22, y + 14], fill=(255, 255, 255, 235))
            dr.text((3, y + 3), str(p), fill=(200, 0, 0))
    bufer = io.BytesIO()
    im.save(bufer, format="JPEG", quality=88)
    return bufer.getvalue()


def _limit_xatosimi(xato):
    matn = str(xato).lower()
    return "429" in matn or "quota" in matn or "rate" in matn or "resource_exhausted" in matn


def _ai_sorov(provider, prompt, rasm_bytes, topshiriq):
    """Rate limit (429) bo'lsa kutib qayta uradi — bepul tarifda
    daqiqasiga ~5 sahifa chegarasi bor, ketma-ket yuborilsa uriladi."""
    oxirgi = None
    for urinish in range(LIMIT_URINISHLAR):
        try:
            javob = provider.generate_json(prompt, topshiriq, rasm_bytes, "image/jpeg")
            return javob["natija"], None
        except ProviderXatosi as e:
            oxirgi = str(e)
            if _limit_xatosimi(e) and urinish < LIMIT_URINISHLAR - 1:
                time.sleep(LIMIT_KUTISH_SONIYA)
                continue
            break
        except Exception as e:  # SDK'ning kutilmagan xatolari
            oxirgi = f"{type(e).__name__}: {e}"
            if _limit_xatosimi(e) and urinish < LIMIT_URINISHLAR - 1:
                time.sleep(LIMIT_KUTISH_SONIYA)
                continue
            break
    return None, oxirgi or "AI yaroqli javob bermadi"


def sahifani_bloklarga_ajrat(provider, rasm_bytes):
    """Bitta oddiy sahifa -> {"sarlavha", "elementlar"}.

    Qaytaradi: (natija, xato_matni) — biri None bo'ladi."""
    torli = tor_chiz(rasm_bytes)
    natija, xato = _ai_sorov(
        provider, BLOK_PROMPT, torli,
        "To'r raqamlaridan foydalanib, barcha elementlarni aniqlang.")
    if xato:
        return None, xato
    elementlar = [e for e in natija.get("elementlar", []) if _quti_yaroqlimi(e)]
    if not elementlar:
        return None, "Sahifada yaroqli element topilmadi"
    natija["elementlar"] = rasm_qutilarini_qirq(elementlar)
    return natija, None


def _quti_yaroqlimi(e):
    """AI ba'zan chala element qaytaradi (quti yo'q yoki teskari)."""
    try:
        x1, y1, x2, y2 = float(e["x1"]), float(e["y1"]), float(e["x2"]), float(e["y2"])
    except (KeyError, TypeError, ValueError):
        return False
    if not all(0 <= q <= 100 for q in (x1, y1, x2, y2)):
        return False
    return x2 > x1 and y2 > y1


def _maydon(r):
    return max(0, r["x2"] - r["x1"]) * max(0, r["y2"] - r["y1"])


def _kesishuv(a, b):
    return (max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]))
            * max(0, min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])))


def rasm_qutilarini_qirq(elementlar):
    """Fotosurat qutisi matn qutisi bilan kesishsa — rasmni QIRQADI.

    Sabab (2026-07-28, foydalanuvchi prototipda ko'rsatdi): rasm asl
    skandan kesilgani uchun, quti matn ustiga chiqib qolsa, kesilgan
    rasmga DARSLIKNING ESKI YOZUVI ham kirib qoladi va sahifada bir joyda
    ikki xil matn ko'rinadi. 7 sahifalik sinovda 8 ta rasm shunday edi.

    Har kesishuv uchun 4 xil qirqish sinaladi va rasm maydonini ENG KAM
    yo'qotadigani tanlanadi."""
    matnlar = [e for e in elementlar if e.get("tur") != "rasm"]
    for r in [e for e in elementlar if e.get("tur") == "rasm"]:
        for m in matnlar:
            if _kesishuv(r, m) <= 0:
                continue
            nomzodlar = [
                {**r, "x1": m["x2"]}, {**r, "x2": m["x1"]},
                {**r, "y1": m["y2"]}, {**r, "y2": m["y1"]},
            ]
            yaroqli = [n for n in nomzodlar
                       if n["x2"] - n["x1"] > 3 and n["y2"] - n["y1"] > 3
                       and _kesishuv(n, m) <= 0]
            if yaroqli:
                r.update({k: max(yaroqli, key=_maydon)[k]
                          for k in ("x1", "y1", "x2", "y2")})
    return elementlar


def rasmni_kes(rasm_bytes, quti, maks_kenglik=900, sifat=85):
    """Foizdagi qutini asl (to'liq sifatli) rasmdan kesib oladi.

    AI faqat "qayerda" ekanini aytadi — kesish matematik amal, piksellar
    asl skandan olinadi, hech narsa qayta chizilmaydi.

    2026-07-29: `Image.draft()` bilan xotira sarfini cheklaymiz (tafsilot
    — `tor_chiz()`). Bu yerda nishon `tor_chiz()`dagidan KATTAROQ
    (1600px, yakuniy `maks_kenglik`=900px dan deyarli 2x) — kesim
    (crop) va aniqlik uchun yetarli zaxira, lekin 6400px+ asl skanni
    to'liq dekodlab (147 MB) keyin ulkan qismini tashlab yuborishdan
    ANCHA tejamli (o'lchov bilan tasdiqlangan: ~9 MB, 16x kam)."""
    from PIL import Image

    DRAFT_CHEGARA = 1600
    im = Image.open(io.BytesIO(rasm_bytes))
    im.draft("RGB", (DRAFT_CHEGARA, int(DRAFT_CHEGARA * 1.25)))
    im = im.convert("RGB")
    W, H = im.size
    x1 = max(0, int(quti["x1"] / 100 * W))
    y1 = max(0, int(quti["y1"] / 100 * H))
    x2 = min(W, int(quti["x2"] / 100 * W))
    y2 = min(H, int(quti["y2"] / 100 * H))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    bolak = im.crop((x1, y1, x2, y2))
    bolak.thumbnail((maks_kenglik, maks_kenglik * 3))
    bufer = io.BytesIO()
    bolak.save(bufer, format="JPEG", quality=sifat, optimize=True)
    return bufer.getvalue()


def _oqish_tartibi_kaliti(e):
    """O'qish tartibi: chap ustun TO'LIQ, keyin o'ng ustun (gazeta
    tartibi) — Headway sahifalari ko'pincha 2 ustunli (chap/o'ng) qilib
    joylashtiriladi. Faqat `y1` bo'yicha saralash bunday sahifalarda
    NOTO'G'RI tartib berardi (2026-07-29, foydalanuvchi xabar berdi):
    o'ng ustun vizual jihatdan balandroq tugasa, uning elementi (masalan
    audio belgisi) chap ustundagisidan OLDIN chiqib qolardi, garchi
    o'qish tartibida chapdan keyin kelishi kerak bo'lsa ham."""
    ustun = 0 if e["x1"] < 50 else 1
    return (ustun, e["y1"], e["x1"])


def _y_qatorda_mi(a, b, tolerans=8):
    """Ikki rasm bir QATORDA (yonma-yon) deb hisoblanadi, agar yuqori
    chetlari (y1) bir-biriga yaqin bo'lsa (foiz bo'yicha)."""
    return abs(a["y1"] - b["y1"]) <= tolerans


def _keng_kesishuv(a, b):
    return max(0, min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]))


def _rasmga_izoh_top(rasm, nomzodlar, ishlatilgan_izoh):
    """Rasmning ENG YAQIN tagidagi yozuvini (pufakcha/matn) topadi —
    shu yozuv rasm bilan bitta kartochkaga birlashtiriladi."""
    eng_yaqin = None
    eng_yaqin_masofa = None
    for c in nomzodlar:
        if c.get("tur") not in ("pufakcha", "matn") or id(c) in ishlatilgan_izoh:
            continue
        if c["y1"] < rasm["y2"] - 2:
            continue
        kenglik = min(rasm["x2"] - rasm["x1"], c["x2"] - c["x1"]) or 1
        if _keng_kesishuv(rasm, c) < 0.4 * kenglik:
            continue
        masofa = c["y1"] - rasm["y2"]
        if eng_yaqin_masofa is None or masofa < eng_yaqin_masofa:
            eng_yaqin, eng_yaqin_masofa = c, masofa
    return eng_yaqin


def rasm_qatorlarini_guruhla(elementlar):
    """Yonma-yon (bir qatordagi, 2+) FOTOSURATLARNI bitta "rasm_qatori"
    elementiga birlashtiradi — har birining tagidagi yozuvi (pufakcha)
    bilan birga (2026-07-31 talabi).

    Sabab: "3 ta odam rasmi + har birining tagida ismi" kabi sahifalarda
    avvalgi (faqat y1 bo'yicha, 2 ustunli) o'qish tartibi rasmlarni
    birga, yozuvlarni birga chiqarardi — tartib buzilardi. Endi har rasm
    o'z yozuvi bilan BIRGA, guruh esa kenglik-proporsional qator sifatida
    frontendga beriladi (mobilda pastma-past tushadi, tartib saqlanadi)."""
    rasmlar = [e for e in elementlar if e.get("tur") == "rasm"]
    ishlatilgan_rasm = set()
    ishlatilgan_izoh = set()
    qatorlar = []
    boshqalar = [e for e in elementlar if e.get("tur") != "rasm"]

    for i, r in enumerate(rasmlar):
        if id(r) in ishlatilgan_rasm:
            continue
        guruh = [r]
        band = {id(r)}
        for r2 in rasmlar[i + 1:]:
            if id(r2) in ishlatilgan_rasm or id(r2) in band:
                continue
            if _y_qatorda_mi(r, r2):
                guruh.append(r2)
                band.add(id(r2))
        if len(guruh) < 2:
            continue
        ishlatilgan_rasm |= band
        guruh.sort(key=lambda e: e["x1"])

        qator_itemlar = []
        pastki_y2 = max(e["y2"] for e in guruh)
        for rr in guruh:
            izoh_el = _rasmga_izoh_top(rr, boshqalar, ishlatilgan_izoh)
            matn = ""
            if izoh_el is not None:
                matn = izoh_el.get("matn", "")
                ishlatilgan_izoh.add(id(izoh_el))
                pastki_y2 = max(pastki_y2, izoh_el["y2"])
            qator_itemlar.append({
                "x1": rr["x1"], "y1": rr["y1"], "x2": rr["x2"], "y2": rr["y2"],
                "izoh": rr.get("izoh", ""), "matn": matn,
            })
        qatorlar.append({
            "tur": "rasm_qatori",
            "x1": min(e["x1"] for e in guruh), "y1": min(e["y1"] for e in guruh),
            "x2": max(e["x2"] for e in guruh), "y2": pastki_y2,
            "qator": qator_itemlar,
        })

    if not qatorlar:
        return elementlar

    natija = [e for e in elementlar
              if id(e) not in ishlatilgan_rasm and id(e) not in ishlatilgan_izoh]
    natija.extend(qatorlar)
    return natija


def bloklarni_tayyorla(elementlar):
    """AI elementlarini BAZAGA YOZILADIGAN ko'rinishga o'tkazadi.

    Eng muhim qismi — BO'SH JOYLARNI YASSILASH: har bo'sh joy `savollar`
    massiviga alohida savol bo'lib chiqadi, blok esa faqat `savol_idx`
    orqali unga ishora qiladi. Shu tufayli mavjud javob tekshirish
    mexanizmi (`javoblarni_tekshir`, ball, 60% qoidasi, Unit qulfi)
    UMUMAN o'zgarmaydi.

    "erkin" javoblar (talaba o'z ismini yozadi — to'g'ri javob yo'q)
    `savollar`ga TUSHMAYDI: ular baholanmaydi (foydalanuvchi qarori),
    blokda esa `erkin: true` bilan belgilanadi va frontend baribir input
    ko'rsatadi.

    Qaytaradi: (bloklar, savollar, rasm_qutilari)"""
    elementlar = rasm_qatorlarini_guruhla(elementlar)
    bloklar = []
    savollar = []
    rasm_qutilari = []

    for e in sorted(elementlar, key=_oqish_tartibi_kaliti):
        tur = e.get("tur") or "matn"
        blok = {"tur": tur}

        if tur == "rasm":
            blok["rasm_idx"] = len(rasm_qutilari)
            blok["izoh"] = e.get("izoh", "")
            rasm_qutilari.append({k: e[k] for k in ("x1", "y1", "x2", "y2")})
            bloklar.append(blok)
            continue

        if tur == "rasm_qatori":
            itemlar = []
            for it in e.get("qator", []):
                rasm_idx = len(rasm_qutilari)
                rasm_qutilari.append({k: it[k] for k in ("x1", "y1", "x2", "y2")})
                keng = max(1, it["x2"] - it["x1"])
                itemlar.append({
                    "rasm_idx": rasm_idx, "izoh": it.get("izoh", ""),
                    "matn": it.get("matn", ""), "keng": keng,
                })
            blok["qator"] = itemlar
            bloklar.append(blok)
            continue

        if tur == "mashq":
            bolaklar = []
            for b in e.get("bolaklar", []):
                if not b.get("bosh_joy"):
                    bolaklar.append({"matn": str(b.get("matn") or "")})
                    continue
                javob = str(b.get("javob") or "").strip()
                # 2026-07-30 talabi: "aniq" turdagi bo'sh joy AI hali
                # javobni bilmasa ham (bu sahifada alohida javob-kaliti
                # yo'q — masalan "mashq bo'yicha rasm" rejimida) SAVOL
                # sifatida saqlanadi (`togri` bo'sh) — shunda u admin
                # uchun mavjud "Javoblarni tahrirlash" panelida "javob
                # talab qiladi" deb ko'rinadi. Avval bo'sh javob "erkin"
                # (ochiq, tekshirilmaydigan) deb qabul qilinardi — bu
                # javobni butunlay yashirib qo'yardi.
                erkin = b.get("javob_turi") == "erkin"
                if erkin:
                    bolaklar.append({"bosh_joy": True, "erkin": True})
                else:
                    bolaklar.append({"bosh_joy": True, "savol_idx": len(savollar)})
                    savollar.append({
                        "savol": _savol_matni(e.get("bolaklar", [])),
                        "togri": javob,
                        # Javob kaliti sahifasi bilan moslashtirish uchun:
                        # topshiriq raqami ELEMENTDA, band raqami esa har
                        # BO'SH JOYDA (bitta gapda bir nechta bo'sh joy
                        # bo'lishi mumkin, har biri kalitda alohida band).
                        "mashq_raqami": e.get("mashq_raqami", ""),
                        "band_raqami": b.get("band_raqami", ""),
                    })
            if not bolaklar:
                continue
            blok["bolaklar"] = bolaklar
            bloklar.append(blok)
            continue

        for maydon in ("matn", "raqam", "audio_raqam", "sarlavha", "qatorlar", "kim"):
            if e.get(maydon):
                blok[maydon] = e[maydon]
        if len(blok) > 1:  # "tur" dan boshqa hech narsa bo'lmasa — tashlaymiz
            bloklar.append(blok)

    return bloklar, savollar, rasm_qutilari


def _savol_matni(bolaklar):
    """Savol matni — gapning o'zi, bo'sh joy o'rniga "___".

    Bu talabaga ko'rinmaydi (blok formatida gap bloklardan chiziladi),
    lekin admin ro'yxatida va `KursMashqYechim` tarixida o'qiladigan
    bo'lishi uchun kerak."""
    qismlar = []
    for b in bolaklar:
        qismlar.append("___" if b.get("bosh_joy") else str(b.get("matn") or ""))
    return "".join(qismlar).strip() or "___"


