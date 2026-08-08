"""Darslik mashqidagi javob yoziladigan BO'SH JOYlarni rasmdan topish
(2026-08-08). AI ISHLATILMAYDI — sof rasm tahlili.

NEGA AI EMAS
------------
`rasm_fon_generatsiya` avval bo'sh joy koordinatalarini AI'dan
so'rardi (rasm ustiga pronumerlangan to'r chizib). Haqiqiy Headway
sahifasida ikki bosqichli tahlil va zich to'r bilan ham sinaldi:
8 ta bo'sh joydan atigi 3 tasi to'g'ri joyga tushdi, qolganlari 1-3
matn qatori pastga surildi — xato tasodifiy emas, rasm pastiga tomon
TIZIMLI o'sadi. Bu vision-modelning chegarasi: baland rasmda mayda
y-koordinatani chizmadan aniq o'qiy olmaydi.

Holbuki bo'sh joy — vizual jihatdan JUDA ODDIY narsa: oq qog'ozdagi
uzun, ingichka, gorizontal qora chiziq, ustida bo'sh joy. Buni topish
uchun model kerak emas, oddiy piksel tahlili YETARLI va u PIKSEL
ANIQLIGIDA ishlaydi (o'sha sahifada 8 tadan 8 tasi topildi, jumladan
AI bittaga qo'shib yuborgan qo'shni ikki chiziqcha ham alohida).

Shuning uchun ish taqsimlandi:
  * shu modul — QAYERDA (aniq koordinata);
  * AI (`rasm_fon_generatsiya`) — NIMA GAP va JAVOBI NIMA (buni
    allaqachon yaxshi bajaryapti).

FILTRLAR
--------
Xom qidiruv chiziqchadan tashqari yana ikki narsani topadi, ikkalasi
ham ishonchli filtrlanadi:
  * QUTI/JADVAL CHEGARALARI — ulardan farqli o'laroq, haqiqiy bo'sh
    joyning yonida SHU QATORDA matn bo'ladi ("B ___ ___ Ben.");
  * SURAT ICHIDAGI chiziqlar — atrofi oq qog'oz emas.

CHEKLOV (2026-08-08, sinovda aniqlandi)
---------------------------------------
Faqat CHIZIQCHA turidagi bo'sh joy topiladi. Javob BO'SH QUTIGA
yoziladigan mashqlar (Headway 12-bet, 1-mashq: surat ostidagi 12 ta oq
katak) TOPILMAYDI. Sabab o'lchandi: bunday katakning chegarasi och
kulrang (115-160 kulranglik, ya'ni `SIYOH_CHEGARASI`dan yorug') va
katak surat ustiga qo'yilgani uchun USTKI chegarasi umuman
ko'rinmaydi — surat qirrasi bilan qo'shilib ketadi. To'rtta chegarani
qidiradigan aniqlagich yozib sinaldi va shu sababdan ishlamadi, kod
saqlanmadi. Bu tur uchun boshqa alomat kerak (masalan "surat ostidagi
bo'sh oq to'rtburchak" + yonidagi tartib raqami).

Filtrlardan o'tib ketgan kam sonli yolg'on topilma (masalan namuna
sifatida ALLAQACHON to'ldirilgan katak) AI bosqichida rad etiladi —
u rasmga qarab "bu javob yoziladigan joy emas" deb ayta oladi.
Ish taqsimoti shu: geometriya — QAYERDA, AI — NIMA.
"""

import io

# Barcha chegaralar kesim KENGLIGIGA nisbatan (foizda) yoki piksel —
# qaysi biri kattaroq bo'lsa. Kesimlar ~800px keladi (`KESIM_KENGLIGI`),
# lekin kichik mashq kesimi ancha tor bo'lishi mumkin.
MIN_UZUNLIK_ULUSH = 0.035   # chiziqcha kamida kesim kengligining 3.5%
MIN_UZUNLIK_PIKSEL = 16
# Bo'sh joy — BITTA SO'Z yoziladigan katak, ya'ni qisqa. Bundan uzuni
# amalda har doim quti/pufakcha/jadval chizig'i bo'lib chiqdi (o'lchov,
# Headway 10-bet: haqiqiy bo'sh joylar 0.05-0.18, ramkalar 0.27-0.66).
MAKS_UZUNLIK_ULUSH = 0.30
SIYOH_CHEGARASI = 150       # bundan qorong'i piksel = siyoh
QOGOZ_CHEGARASI = 195       # oq qog'oz shundan yorug'
MAKS_QALINLIK = 6           # chiziqcha ingichka; qalinrog'i — quti/ramka
QATOR_BALANDLIGI_ULUSH = 0.028  # taxminiy matn qatori (kesim BO'YIGA nisbatan)


def _rasmni_massivga(rasm_bytes):
    from PIL import Image
    import numpy as np

    im = Image.open(io.BytesIO(rasm_bytes)).convert("L")
    return np.array(im), im.size  # (H, W) massiv, (W, H) o'lcham


def _xom_yugurishlar(qora, W, min_uz, maks_uz):
    """Har qatordagi uzun uzluksiz qora bo'laklar: [(y, x1, x2), ...]."""
    natija = []
    H = qora.shape[0]
    for y in range(H):
        qator = qora[y]
        x = 0
        while x < W:
            if not qator[x]:
                x += 1
                continue
            bosh = x
            while x < W and qator[x]:
                x += 1
            uzunlik = x - bosh
            if min_uz <= uzunlik <= maks_uz:
                natija.append((y, bosh, x))
    return natija


def _guruhla(yugurishlar):
    """Chiziqcha 2-4 piksel qalin — qo'shni qatorlardagi ustma-ust
    yugurishlar BITTA chiziqchaga birlashtiriladi."""
    guruhlar = []
    for y, x1, x2 in sorted(yugurishlar):
        for g in guruhlar:
            ustma_ust = not (x2 < g["x1"] - 4 or x1 > g["x2"] + 4)
            if ustma_ust and y - g["y2"] <= 2:
                g["x1"] = min(g["x1"], x1)
                g["x2"] = max(g["x2"], x2)
                g["y2"] = y
                break
        else:
            guruhlar.append({"x1": x1, "x2": x2, "y1": y, "y2": y})
    return [g for g in guruhlar if g["y2"] - g["y1"] < MAKS_QALINLIK]


def _tepasi_boshmi(qora, g, qator_h):
    """Chiziqchaning USTIDA yozuv bo'lmasligi kerak — aks holda bu
    chiziqcha emas, matn ostidagi tagchiziq yoki surat qismi."""
    tepa = max(0, g["y1"] - qator_h)
    if tepa >= g["y1"] - 1:
        return True
    bolak = qora[tepa:g["y1"] - 1, g["x1"]:g["x2"]]
    return bolak.size == 0 or bolak.mean() < 0.10


def _qogoz_ustidami(kul, g, qator_h, W):
    """Atrofi OQ QOG'OZ bo'lishi shart — surat ichidagi gorizontal
    chiziqlar (mebel qirrasi, deraza romi) shu bilan chiqib ketadi."""
    tepa = max(0, g["y1"] - qator_h)
    past = min(kul.shape[0], g["y2"] + qator_h)
    chap = max(0, g["x1"] - 4)
    ong = min(W, g["x2"] + 4)
    atrof = kul[tepa:past, chap:ong]
    if atrof.size == 0:
        return False
    # Qog'oz: piksellarning KATTA qismi yorug'. Matn/chiziqcha siyohi
    # ozchilikni tashkil qiladi, surat esa deyarli butunlay to'ldirilgan.
    return (atrof > QOGOZ_CHEGARASI).mean() > 0.72


def _qatorida_matn_bormi(qora, g, qator_h, W):
    """Haqiqiy bo'sh joyning yonida SHU QATORDA matn bo'ladi
    ("B ___ ___ Ben.", "How ___ you?"). Quti yoki jadval chegarasining
    qatorida esa hech narsa yo'q — asosiy farqlovchi shu."""
    tepa = max(0, g["y1"] - qator_h)
    past = max(tepa + 1, g["y1"] - 1)
    band = qora[tepa:past]
    if band.size == 0:
        return False
    # Chiziqchaning o'zidan tashqaridagi siyoh (chapda va o'ngda).
    chapda = band[:, max(0, g["x1"] - int(W * 0.45)):max(0, g["x1"] - 2)]
    ongda = band[:, min(W, g["x2"] + 2):min(W, g["x2"] + int(W * 0.45))]
    return (chapda.size and chapda.mean() > 0.012) or (ongda.size and ongda.mean() > 0.012)


def bosh_joylarni_aniqla(kesim_bytes):
    """Kesim (bitta mashq rasmi) -> bo'sh joylar ro'yxati.

    Qaytaradi: [{"x1", "x2", "y"}] — hammasi KESIMGA nisbatan FOIZDA,
    o'qish tartibida (yuqoridan-pastga, qatorda chapdan-o'ngga).
    Topilmasa bo'sh ro'yxat."""
    kul, (W, H) = _rasmni_massivga(kesim_bytes)
    qora = kul < SIYOH_CHEGARASI
    qator_h = max(6, int(H * QATOR_BALANDLIGI_ULUSH))
    min_uz = max(MIN_UZUNLIK_PIKSEL, int(W * MIN_UZUNLIK_ULUSH))
    maks_uz = int(W * MAKS_UZUNLIK_ULUSH)

    guruhlar = _guruhla(_xom_yugurishlar(qora, W, min_uz, maks_uz))

    topilgan = [
        {"x1": g["x1"], "x2": g["x2"], "y": (g["y1"] + g["y2"]) / 2}
        for g in guruhlar
        if _tepasi_boshmi(qora, g, qator_h)
        and _qogoz_ustidami(kul, g, qator_h, W)
        and _qatorida_matn_bormi(qora, g, qator_h, W)
    ]
    # O'qish tartibi: avval qatorga guruhlab (y yaqin bo'lsa bir qator),
    # keyin qator ichida chapdan o'ngga.
    topilgan.sort(key=lambda t: (round(t["y"] / max(1, qator_h)), t["x1"]))

    return [
        {
            "x1": round(t["x1"] / W * 100, 1),
            "x2": round(t["x2"] / W * 100, 1),
            "y": round(t["y"] / H * 100, 1),
        }
        for t in topilgan
    ]
