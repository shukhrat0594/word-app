"""Reliz xabarnomalari — `CHANGELOG.md` -> owner bildirishnomasi.

Foydalanuvchi talabi (2026-08-08): "har gal nimadir yangi narsa push
qilinganda ownerga xabar keladigan qila olamizmi? nimalar
qo'shilganini?"

NEGA WEBHOOK EMAS: Render'ning deploy hook'i alohida sozlash, sir
(secret) va tashqi kirish nuqtasini talab qiladi. Bu yerda soddaroq va
ishonchliroq yo'l tanlandi — `CHANGELOG.md` REPO ICHIDA keladi, ya'ni
yangi deploy = yangi fayl. Owner bildirishnomalarni ochganda fayl
o'qiladi va HALI QAYD ETILMAGAN relizlar uchun yozuv yaratiladi.
Natijada: deploy chiqishi bilan owner birinchi kirganda xabarni
ko'radi, hech qanday tashqi sozlash kerak emas.

Takrorlanmaslik `Bildirishnoma.kalit` (unique_together) bilan
ta'minlanadi — fayl necha marta o'qilsa ham bitta reliz bitta marta
xabar bo'ladi.

Telegram orqali yuborish REJADA (foydalanuvchi qarori: "botni hozircha
rejaga qo'shib tur, hozircha faqat xabarnoma qilib ber"). Qo'shilganda
shu yerdagi `yangi_relizlar()` natijasi o'zgarishsiz ishlatiladi —
faqat yuborish usuli qo'shiladi.
"""

import pathlib
import re

from django.conf import settings

# "## 2026-08-08 — Sarlavha" ko'rinishidagi bo'lim boshi.
BOLIM_NAQSHI = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*[—-]\s*(.+?)\s*$", re.M)


def changelog_yoli():
    return pathlib.Path(settings.BASE_DIR) / "CHANGELOG.md"


def relizlarni_oqi(matn=None):
    """CHANGELOG.md'ni [{sana, sarlavha, matn}] ro'yxatiga aylantiradi
    (faylda qanday tartibda bo'lsa — eng yangisi birinchi).

    Fayl yo'q/buzuq bo'lsa BO'SH ro'yxat qaytaradi, istisno ko'tarmaydi:
    xabarnoma — qo'shimcha qulaylik, uning nosozligi sahifani ochishga
    to'sqinlik qilmasligi kerak."""
    if matn is None:
        yol = changelog_yoli()
        if not yol.exists():
            return []
        try:
            matn = yol.read_text(encoding="utf-8")
        except OSError:
            return []

    mosliklar = list(BOLIM_NAQSHI.finditer(matn))
    relizlar = []
    for i, m in enumerate(mosliklar):
        boshi = m.end()
        oxiri = mosliklar[i + 1].start() if i + 1 < len(mosliklar) else len(matn)
        tana = matn[boshi:oxiri].strip()
        if not tana:
            continue
        relizlar.append({"sana": m.group(1), "sarlavha": m.group(2), "matn": tana})
    return relizlar


def relizlarni_sinxronla(foydalanuvchi):
    """Shu foydalanuvchi uchun hali yaratilmagan reliz bildirishnomalarini
    yaratadi. Qaytaradi: yaratilganlar soni.

    FAQAT owner uchun chaqiriladi (chaqiruvchi tekshiradi) — reliz
    xabari boshqa rollarga ko'rsatilmaydi."""
    from .models import Bildirishnoma

    relizlar = relizlarni_oqi()
    if not relizlar:
        return 0

    mavjud = set(
        Bildirishnoma.objects
        .filter(foydalanuvchi=foydalanuvchi, turi=Bildirishnoma.Turi.RELIZ)
        .values_list("kalit", flat=True)
    )
    yangilar = []
    for r in relizlar:
        kalit = f"reliz:{r['sana']}:{r['sarlavha']}"[:200]
        if kalit in mavjud:
            continue
        yangilar.append(Bildirishnoma(
            foydalanuvchi=foydalanuvchi,
            turi=Bildirishnoma.Turi.RELIZ,
            kalit=kalit,
            sarlavha=f"{r['sana']} — {r['sarlavha']}",
            matn=r["matn"],
        ))
    if not yangilar:
        return 0
    # `ignore_conflicts` — ikkita parallel so'rov bir vaqtda sinxronlashi
    # mumkin; unique cheklovi ikkinchisini jimgina rad etadi.
    Bildirishnoma.objects.bulk_create(yangilar, ignore_conflicts=True)
    return len(yangilar)
